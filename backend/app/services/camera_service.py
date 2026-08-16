import asyncio
import logging
import os
import random
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx

from ..config.settings import settings
from ..models.camara import CamaraPosition, CamaraSaveStatus

CAMERA_CHECK_INTERVAL_S = 5
CAMERA_TIMEOUT_S = 2.0
CAMERA_CAPTURE_READ_TIMEOUT_S = 15.0
RECORDING_DURATION_S = 30
RECORDING_FPS = 20
FFMPEG_COMMAND = "ffmpeg"

CAPTURE_DIR = Path(__file__).resolve().parents[3] / "data" / "capture"
RECORDING_DIR = Path(__file__).resolve().parents[3] / "data" / "recordings"

logger = logging.getLogger(__name__)


@dataclass
class CameraState:
    """Per-camera runtime state."""
    camera_id: int
    url: str
    online: bool = False
    active_streams: int = 0
    monitor_task: asyncio.Task | None = None
    shared_stream_task: asyncio.Task | None = None
    stream_subscribers: set[asyncio.Queue[bytes]] = field(default_factory=set)
    recording_subscribers: set[asyncio.Queue[bytes]] = field(default_factory=set)
    latest_jpeg: bytes | None = None
    frame_available: asyncio.Event = field(default_factory=asyncio.Event)


def _resolve_ffmpeg_command() -> str | None:
    """Find FFmpeg even when this process started before PATH was refreshed."""
    if command := shutil.which(FFMPEG_COMMAND):
        return command

    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    windows_app_alias = local_app_data / "Microsoft" / "WindowsApps" / "ffmpeg.exe"
    if windows_app_alias.exists():
        return str(windows_app_alias)

    winget_packages = local_app_data / "Microsoft" / "WinGet" / "Packages"
    if winget_packages.exists():
        matches = winget_packages.glob("Gyan.FFmpeg*/**/bin/ffmpeg.exe")
        if command := next(matches, None):
            return str(command)

    return None


def _get_camera_state(camera_id: int) -> CameraState:
    """Return the runtime state for a camera, creating it on first use."""
    if camera_id not in _camera_states:
        url = settings.camera_1_url if camera_id == 1 else settings.camera_2_url
        _camera_states[camera_id] = CameraState(camera_id=camera_id, url=url)
    return _camera_states[camera_id]


_camera_states: dict[int, CameraState] = {}


async def _check_camera(state: CameraState) -> bool:
    """Quick connectivity check: open the stream, read the first bytes, then close."""
    try:
        async with httpx.AsyncClient(timeout=CAMERA_TIMEOUT_S) as client:
            async with client.stream("GET", state.url) as response:
                if response.status_code != 200:
                    return False
                async for _ in response.aiter_bytes():
                    return True
                return False
    except Exception as exc:  # noqa: BLE001
        logger.debug("Camera %s connectivity check failed: %s", state.camera_id, exc)
        return False


async def _monitor_camera(state: CameraState) -> None:
    """Background loop that probes the camera when no active streams are consuming it.

    Probing is skipped while streams are active to avoid competing with the
    stream connection for the camera's limited simultaneous connections.
    """
    while True:
        if state.active_streams == 0:
            state.online = await _check_camera(state)
            if state.online:
                logger.info("Camera %s is online", state.camera_id)
            else:
                logger.warning(
                    "Camera %s is offline - will retry in %ss",
                    state.camera_id,
                    CAMERA_CHECK_INTERVAL_S,
                )
        await asyncio.sleep(CAMERA_CHECK_INTERVAL_S)


def start_camera_monitor() -> None:
    """Start the background camera monitor tasks (idempotent)."""
    for camera_id in (1, 2):
        state = _get_camera_state(camera_id)
        if state.monitor_task is None or state.monitor_task.done():
            state.monitor_task = asyncio.create_task(_monitor_camera(state))


def set_camera_online(camera_id: int) -> None:
    _get_camera_state(camera_id).online = True


def set_camera_offline(camera_id: int) -> None:
    _get_camera_state(camera_id).online = False


def increment_active_streams(camera_id: int) -> None:
    state = _get_camera_state(camera_id)
    state.active_streams += 1
    state.online = True


def decrement_active_streams(camera_id: int) -> None:
    state = _get_camera_state(camera_id)
    state.active_streams = max(0, state.active_streams - 1)


async def _read_shared_camera_stream(state: CameraState) -> None:
    """Read one upstream MJPEG connection and share it with all consumers."""
    stream_timeout = httpx.Timeout(None, connect=CAMERA_TIMEOUT_S)

    increment_active_streams(state.camera_id)
    try:
        while state.stream_subscribers or state.recording_subscribers:
            frame_buffer = bytearray()
            try:
                async with httpx.AsyncClient(timeout=stream_timeout) as client:
                    async with client.stream("GET", state.url) as response:
                        if response.status_code != 200:
                            raise RuntimeError(
                                f"Camera {state.camera_id} stream error: HTTP {response.status_code}"
                            )

                        state.online = True
                        async for chunk in response.aiter_bytes():
                            for subscriber in tuple(state.stream_subscribers):
                                try:
                                    subscriber.put_nowait(chunk)
                                except asyncio.QueueFull:
                                    # A slow browser should not block the shared camera stream.
                                    continue

                            frame_buffer.extend(chunk)
                            while True:
                                jpeg_start = frame_buffer.find(b"\xff\xd8")
                                if jpeg_start < 0:
                                    # Keep a trailing SOI prefix that may be split
                                    # across two network chunks.
                                    if frame_buffer[-1:] != b"\xff":
                                        frame_buffer.clear()
                                    break

                                jpeg_end = frame_buffer.find(b"\xff\xd9", jpeg_start + 2)
                                if jpeg_end < 0:
                                    if jpeg_start > 0:
                                        del frame_buffer[:jpeg_start]
                                    break

                                state.latest_jpeg = bytes(frame_buffer[jpeg_start : jpeg_end + 2])
                                state.frame_available.set()
                                for subscriber in tuple(state.recording_subscribers):
                                    try:
                                        subscriber.put_nowait(state.latest_jpeg)
                                    except asyncio.QueueFull:
                                        # Dropping a frame is preferable to blocking
                                        # the shared stream for a slow encoder.
                                        continue
                                del frame_buffer[: jpeg_end + 2]
            except Exception as exc:  # noqa: BLE001
                state.online = False
                logger.warning(
                    "Camera %s shared stream disconnected: %s",
                    state.camera_id,
                    exc,
                )

            if state.stream_subscribers or state.recording_subscribers:
                await asyncio.sleep(1)
    finally:
        decrement_active_streams(state.camera_id)


def _ensure_shared_camera_stream(camera_id: int) -> None:
    """Start the single upstream camera connection when needed."""
    state = _get_camera_state(camera_id)
    if state.shared_stream_task is None or state.shared_stream_task.done():
        state.shared_stream_task = asyncio.create_task(_read_shared_camera_stream(state))


async def get_shared_camera_stream(camera_id: int):
    """Yield MJPEG bytes from the shared upstream camera connection."""
    state = _get_camera_state(camera_id)
    subscriber: asyncio.Queue[bytes] = asyncio.Queue(maxsize=16)
    state.stream_subscribers.add(subscriber)
    _ensure_shared_camera_stream(camera_id)

    try:
        while True:
            yield await subscriber.get()
    finally:
        state.stream_subscribers.discard(subscriber)


async def get_latest_camera_frame(camera_id: int) -> bytes:
    """Return a JPEG frame read from the shared upstream stream."""
    state = _get_camera_state(camera_id)
    _ensure_shared_camera_stream(camera_id)
    if state.latest_jpeg is None:
        try:
            await asyncio.wait_for(
                state.frame_available.wait(), timeout=CAMERA_CAPTURE_READ_TIMEOUT_S
            )
        except TimeoutError as exc:
            raise RuntimeError(
                f"Camera {camera_id} stream timed out while waiting for a JPEG frame"
            ) from exc

    if state.latest_jpeg is None:
        raise RuntimeError(f"Camera {camera_id} stream did not provide a JPEG frame")
    return state.latest_jpeg


async def record_video(camera_id: int, camera_position: CamaraPosition) -> CamaraSaveStatus:
    """Encode 30 wall-clock seconds of frames from the shared stream into an MP4."""
    ffmpeg_command = _resolve_ffmpeg_command()
    if ffmpeg_command is None:
        raise RuntimeError("FFmpeg is not installed or is not available on PATH")

    state = _get_camera_state(camera_id)
    RECORDING_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{camera_position.camera}_{timestamp}.mp4"
    filepath = RECORDING_DIR / filename
    frame_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=RECORDING_FPS * 2)
    state.recording_subscribers.add(frame_queue)
    _ensure_shared_camera_stream(camera_id)

    try:
        process = await asyncio.create_subprocess_exec(
            ffmpeg_command,
            "-y",
            "-loglevel",
            "error",
            "-f",
            "mjpeg",
            "-framerate",
            str(RECORDING_FPS),
            "-i",
            "pipe:0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(filepath),
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        raise RuntimeError(f"Unable to start FFmpeg: {exc}") from exc

    recording_error: RuntimeError | None = None
    try:
        deadline = asyncio.get_running_loop().time() + RECORDING_DURATION_S
        while asyncio.get_running_loop().time() < deadline:
            timeout = deadline - asyncio.get_running_loop().time()
            try:
                jpeg_data = await asyncio.wait_for(frame_queue.get(), timeout=timeout)
            except TimeoutError as exc:
                recording_error = RuntimeError("Camera stream stopped while recording")
                recording_error.__cause__ = exc
                break

            try:
                process.stdin.write(jpeg_data)
                await process.stdin.drain()
            except (BrokenPipeError, ConnectionResetError) as exc:
                recording_error = RuntimeError("FFmpeg stopped while encoding the video")
                recording_error.__cause__ = exc
                break
    finally:
        state.recording_subscribers.discard(frame_queue)
        if process.stdin is not None:
            process.stdin.close()

    try:
        await asyncio.wait_for(process.wait(), timeout=15)
    except TimeoutError:
        process.kill()
        await process.wait()
        raise RuntimeError("FFmpeg did not finish the recording")

    error_output = (await process.stderr.read()).decode(errors="replace").strip()
    if recording_error is not None:
        if error_output:
            raise RuntimeError(f"{recording_error}: {error_output}") from recording_error
        raise recording_error

    if process.returncode != 0 or not filepath.exists() or filepath.stat().st_size == 0:
        raise RuntimeError(f"FFmpeg recording failed: {error_output or process.returncode}")

    return CamaraSaveStatus(
        success=True,
        message="30-second video saved successfully",
        camera=camera_position.camera,
        filename=filename,
    )


def is_camera_online(camera_id: int) -> bool:
    state = _get_camera_state(camera_id)
    return state.online or state.active_streams > 0


def get_camera_status() -> dict:
    """Return status for both cameras."""
    camera_1_online = is_camera_online(1)
    camera_2_online = is_camera_online(2)
    return {
        "camera_1": {
            "is_streaming": camera_1_online,
            "source": settings.camera_1_url,
        },
        "camera_2": {
            "is_streaming": camera_2_online,
            "source": settings.camera_2_url,
        },
    }


def save_snapshot_bytes(
    jpeg_data: bytes, camera_position: CamaraPosition
) -> CamaraSaveStatus:
    """Save the captured JPEG byte content to data/capture/.

    Returns the capture save status.
    """
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = random.randint(1000, 9999)
    filename = f"{camera_position.camera}_{timestamp}_{random_suffix}.jpg"
    filepath = CAPTURE_DIR / filename
    filepath.write_bytes(jpeg_data)

    return CamaraSaveStatus(
        success=True,
        message="Snapshot saved successfully",
        camera=camera_position.camera,
        filename=filename,
    )


async def capture_snapshot(camera_id: int, camera_position: CamaraPosition) -> CamaraSaveStatus:
    """Read one JPEG frame from the camera stream and save its byte content.

    The requested camera position is carried through to the saved capture status.
    Raises RuntimeError if the camera stream is unavailable.
    """
    logger.info(
        "Capturing snapshot for camera %s position: %s",
        camera_id,
        camera_position.camera,
    )
    jpeg_data = await get_latest_camera_frame(camera_id)
    return save_snapshot_bytes(jpeg_data, camera_position)
