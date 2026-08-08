import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from ..services.camera_service import (
    CAMERA_URL,
    capture_snapshot,
    decrement_active_streams,
    get_camera_status,
    increment_active_streams,
    is_camera_online,
    save_snapshot_bytes,
)

router = APIRouter(prefix="/camera", tags=["camera"])


@router.get("/status")
def camera_status() -> dict:
    return get_camera_status()


@router.post("/capture")
async def camera_capture(file: UploadFile | None = File(default=None)) -> dict:
    """Save a captured JPEG frame to data/capture/.

    If a file is uploaded, it is saved directly. Otherwise, the backend
    captures a frame from the camera stream itself.
    """
    try:
        if file is not None:
            jpeg_data = await file.read()
            return save_snapshot_bytes(jpeg_data)
        return await capture_snapshot()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/stream")
async def camera_stream() -> StreamingResponse:
    """Proxy the camera MJPEG stream through the backend to avoid CORS/mixed-content issues."""
    if not is_camera_online():
        raise HTTPException(status_code=503, detail="Camera is offline")

    increment_active_streams()

    async def stream():
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", CAMERA_URL) as response:
                    if response.status_code != 200:
                        raise HTTPException(status_code=502, detail="Camera stream error")
                    async for chunk in response.aiter_bytes():
                        yield chunk
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"Camera stream failed: {exc}")
        finally:
            decrement_active_streams()

    return StreamingResponse(
        stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )