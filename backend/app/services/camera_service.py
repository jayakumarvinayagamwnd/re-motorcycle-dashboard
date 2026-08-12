import asyncio
import logging
import os
import random
import shutil
from datetime import datetime
from pathlib import Path

import httpx

from ..models.camara import CamaraPosition, CamaraSaveStatus

CAMERA_URL = "http://192.168.1.5/camera/stream"
CAMERA_CHECK_INTERVAL_S = 5
CAMERA_TIMEOUT_S = 2.0
CAMERA_CAPTURE_READ_TIMEOUT_S = 15.0
RECORDING_DURATION_S = 30
RECORDING_FPS = 20
FFMPEG_COMMAND = "ffmpeg"

CAPTURE_DIR = Path(__file__).resolve().parents[3] / "data" / "capture"
RECORDING_DIR = Path(__file__).resolve().parents[3] / "data" / "recordings"

logger = logging.getLogger(__name__)

_camera_online = False
_active_streams = 0
_monitor_task: asyncio.Task | None = None
_shared_stream_task: asyncio.Task | None = None
_stream_subscribers: set[asyncio.Queue[bytes]] = set()
_recording_subscribers: set[asyncio.Queue[bytes]] = set()
_latest_jpeg: bytes | None = None
_frame_available = asyncio.Event()


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


async def _check_camera() -> bool:
    """Quick connectivity check: open the stream, read the first bytes, then close."""
    try:
        async with httpx.AsyncClient(timeout=CAMERA_TIMEOUT_S) as client:
            async with client.stream("GET", CAMERA_URL) as response:
                if response.status_code != 200:
                    return False
                async for _ in response.aiter_bytes():
                    return True
                return False
    except Exception as exc:  # noqa: BLE001
        logger.debug("Camera connectivity check failed: %s", exc)
        return False


async def _monitor_camera() -> None:
    """Background loop that probes the camera when no active streams are consuming it.

    Probing is skipped while streams are active to avoid competing with the
    stream connection for the camera's limited simultaneous connections.
    """
    global _camera_online
    while True:
        if _active_streams == 0:
            _camera_online = await _check_camera()
            if _camera_online:
                logger.info("Camera is online")
            else:
                logger.warning("Camera is offline - will retry in %ss", CAMERA_CHECK_INTERVAL_S)
        await asyncio.sleep(CAMERA_CHECK_INTERVAL_S)


def start_camera_monitor() -> None:
    """Start the background camera monitor task (idempotent)."""
    global _monitor_task
    if _monitor_task is None or _monitor_task.done():
        _monitor_task = asyncio.create_task(_monitor_camera())


def set_camera_online() -> None:
    global _camera_online
    _camera_online = True


def set_camera_offline() -> None:
    global _camera_online
    _camera_online = False


def increment_active_streams() -> None:
    global _active_streams
    _active_streams += 1
    set_camera_online()


def decrement_active_streams() -> None:
    global _active_streams
    _active_streams = max(0, _active_streams - 1)


async def _read_shared_camera_stream() -> None:
    """Read one upstream MJPEG connection and share it with all consumers."""
    global _latest_jpeg
    stream_timeout = httpx.Timeout(None, connect=CAMERA_TIMEOUT_S)

    increment_active_streams()
    try:
        while _stream_subscribers or _recording_subscribers:
            frame_buffer = bytearray()
            try:
                async with httpx.AsyncClient(timeout=stream_timeout) as client:
                    async with client.stream("GET", CAMERA_URL) as response:
                        if response.status_code != 200:
                            raise RuntimeError(
                                f"Camera stream error: HTTP {response.status_code}"
                            )

                        set_camera_online()
                        async for chunk in response.aiter_bytes():
                            for subscriber in tuple(_stream_subscribers):
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

                                _latest_jpeg = bytes(frame_buffer[jpeg_start : jpeg_end + 2])
                                _frame_available.set()
                                for subscriber in tuple(_recording_subscribers):
                                    try:
                                        subscriber.put_nowait(_latest_jpeg)
                                    except asyncio.QueueFull:
                                        # Dropping a frame is preferable to blocking
                                        # the shared stream for a slow encoder.
                                        continue
                                del frame_buffer[: jpeg_end + 2]
            except Exception as exc:  # noqa: BLE001
                set_camera_offline()
                logger.warning("Shared camera stream disconnected: %s", exc)

            if _stream_subscribers or _recording_subscribers:
                await asyncio.sleep(1)
    finally:
        decrement_active_streams()


def _ensure_shared_camera_stream() -> None:
    """Start the single upstream camera connection when needed."""
    global _shared_stream_task
    if _shared_stream_task is None or _shared_stream_task.done():
        _shared_stream_task = asyncio.create_task(_read_shared_camera_stream())


async def get_shared_camera_stream():
    """Yield MJPEG bytes from the shared upstream camera connection."""
    subscriber: asyncio.Queue[bytes] = asyncio.Queue(maxsize=16)
    _stream_subscribers.add(subscriber)
    _ensure_shared_camera_stream()

    try:
        while True:
            yield await subscriber.get()
    finally:
        _stream_subscribers.discard(subscriber)


async def get_latest_camera_frame() -> bytes:
    """Return a JPEG frame read from the shared upstream stream."""
    _ensure_shared_camera_stream()
    if _latest_jpeg is None:
        try:
            await asyncio.wait_for(
                _frame_available.wait(), timeout=CAMERA_CAPTURE_READ_TIMEOUT_S
            )
        except TimeoutError as exc:
            raise RuntimeError(
                "Camera stream timed out while waiting for a JPEG frame"
            ) from exc

    if _latest_jpeg is None:
        raise RuntimeError("Camera stream did not provide a JPEG frame")
    return _latest_jpeg


async def record_video(camera_position: CamaraPosition) -> CamaraSaveStatus:
    """Encode 30 wall-clock seconds of frames from the shared stream into an MP4."""
    ffmpeg_command = _resolve_ffmpeg_command()
    if ffmpeg_command is None:
        raise RuntimeError("FFmpeg is not installed or is not available on PATH")

    RECORDING_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{camera_position.camera}_{timestamp}.mp4"
    filepath = RECORDING_DIR / filename
    frame_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=RECORDING_FPS * 2)
    _recording_subscribers.add(frame_queue)
    _ensure_shared_camera_stream()

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
        _recording_subscribers.discard(frame_queue)
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


def is_camera_online() -> bool:
    return _camera_online or _active_streams > 0


def get_camera_status() -> dict:
    online = is_camera_online()
    return {
        "is_streaming": online,
        "source": "192.168.1.3" if online else "none",
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


async def capture_snapshot(camera_position: CamaraPosition) -> CamaraSaveStatus:
    """Read one JPEG frame from the camera stream and save its byte content.

    The requested camera position is carried through to the saved capture status.
    Raises RuntimeError if the camera stream is unavailable.
    """
    logger.info("Capturing snapshot for camera position: %s", camera_position.camera)
    jpeg_data = await get_latest_camera_frame()
    return save_snapshot_bytes(jpeg_data, camera_position)
