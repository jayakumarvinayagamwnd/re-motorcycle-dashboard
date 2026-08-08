import asyncio
import io
import logging
import random
from datetime import datetime
from pathlib import Path

import httpx

CAMERA_URL = "http://192.168.1.3/camera/stream"
CAMERA_CHECK_INTERVAL_S = 5
CAMERA_TIMEOUT_S = 2.0

CAPTURE_DIR = Path(__file__).resolve().parents[3] / "data" / "capture"

logger = logging.getLogger(__name__)

_camera_online = False
_active_streams = 0
_monitor_task: asyncio.Task | None = None


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


def is_camera_online() -> bool:
    return _camera_online or _active_streams > 0


def get_camera_status() -> dict:
    online = is_camera_online()
    return {
        "is_streaming": online,
        "source": "192.168.1.3" if online else "none",
    }


def save_snapshot_bytes(jpeg_data: bytes) -> dict:
    """Save raw JPEG bytes to data/capture/{{YYYYMMDD_HHMMSS}}_random.jpg.

    Returns the saved file path relative to the project root.
    """
    if not jpeg_data.startswith(b"\xff\xd8"):
        raise ValueError("Captured data is not a valid JPEG image")

    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = random.randint(1000, 9999)
    filename = f"{timestamp}_{random_suffix}.jpg"
    filepath = CAPTURE_DIR / filename
    filepath.write_bytes(jpeg_data)

    return {
        "filename": filename,
        "path": str(filepath.relative_to(Path(__file__).resolve().parents[3])),
        "size_bytes": len(jpeg_data),
    }


async def capture_snapshot() -> dict:
    """Capture a single JPEG frame from the camera and save it to data/capture/.

    Returns the saved file path relative to the project root.
    Raises RuntimeError if the camera stream is unavailable.
    """
    if not is_camera_online():
        raise RuntimeError("Camera is offline")

    buffer = io.BytesIO()
    try:
        async with httpx.AsyncClient(timeout=CAMERA_TIMEOUT_S) as client:
            async with client.stream("GET", CAMERA_URL) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"Camera stream error: HTTP {response.status_code}")
                boundary = b"--frame"
                start = None
                async for chunk in response.aiter_bytes():
                    buffer.write(chunk)
                    if start is None:
                        idx = buffer.getvalue().find(boundary)
                        if idx != -1:
                            start = idx
                            # Trim everything before the first JPEG SOI marker
                            soi = buffer.getvalue().find(b"\xff\xd8", start)
                            if soi != -1:
                                buffer.seek(0)
                                buffer.truncate(0)
                                buffer.write(buffer.getvalue()[soi:])
                    else:
                        # Look for the JPEG EOI marker and the next boundary
                        data = buffer.getvalue()
                        eoi = data.find(b"\xff\xd9", len(data) - 32)
                        if eoi != -1:
                            jpeg = data[: eoi + 2]
                            # Re-check that this is a complete JPEG (SOI at start)
                            if jpeg.startswith(b"\xff\xd8"):
                                break
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.debug("Snapshot capture failed: %s", exc)
        raise RuntimeError(f"Failed to capture frame: {exc}") from exc

    jpeg_data = buffer.getvalue()
    if not jpeg_data.startswith(b"\xff\xd8"):
        # Fallback: if we didn't capture a clean frame from the MJPEG parser,
        # read raw bytes from the stream URL directly (some cameras serve JPEG on a single request).
        try:
            async with httpx.AsyncClient(timeout=CAMERA_TIMEOUT_S) as client:
                response = await client.get(CAMERA_URL)
                if response.status_code == 200:
                    jpeg_data = response.content
                else:
                    raise RuntimeError(f"Camera stream error: HTTP {response.status_code}")
        except RuntimeError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Failed to capture frame: {exc}") from exc

    if not jpeg_data.startswith(b"\xff\xd8"):
        raise RuntimeError("Captured data is not a valid JPEG image")

    return save_snapshot_bytes(jpeg_data)
