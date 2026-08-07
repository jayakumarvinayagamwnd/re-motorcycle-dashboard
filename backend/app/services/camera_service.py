import asyncio
import logging

import httpx

CAMERA_URL = "http://192.168.1.3/camera/stream"
CAMERA_CHECK_INTERVAL_S = 5
CAMERA_TIMEOUT_S = 2.0

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