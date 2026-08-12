import logging
from fastapi import APIRouter, HTTPException, Path

from ..models.camara import CamaraPosition, CamaraSaveStatus
from fastapi.responses import StreamingResponse

from ..services.camera_service import (
    capture_snapshot,
    get_camera_status,
    get_shared_camera_stream,
    record_video,
)

router = APIRouter(prefix="/camera", tags=["camera"])
logger = logging.getLogger(__name__)


@router.get("/status")
def camera_status() -> dict:
    return get_camera_status()


@router.post("/{camera_id}/capture", response_model=CamaraSaveStatus)
async def camera_capture(
    camera_id: int = Path(ge=1, le=2),
    camera_position: CamaraPosition = ...,
) -> CamaraSaveStatus:
    """Save a captured JPEG frame to data/capture/.

    If a file is uploaded, it is saved directly. Otherwise, the backend
    captures a frame from the camera stream itself.
    """
    try:
        logger.info("Capturing snapshot for camera %s: %s", camera_id, camera_position.camera)
        return await capture_snapshot(camera_position)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{camera_id}/record", response_model=CamaraSaveStatus)
async def camera_record(
    camera_id: int = Path(ge=1, le=2),
    camera_position: CamaraPosition = ...,
) -> CamaraSaveStatus:
    """Record and save 30 seconds from the shared camera stream."""
    try:
        logger.info("Recording 30 seconds from camera %s: %s", camera_id, camera_position.camera)
        return await record_video(camera_position)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{camera_id}/stream")
async def camera_stream(camera_id: int = Path(ge=1, le=2)) -> StreamingResponse:
    """Proxy the camera MJPEG stream through the backend to avoid CORS/mixed-content issues."""
    return StreamingResponse(
        get_shared_camera_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
