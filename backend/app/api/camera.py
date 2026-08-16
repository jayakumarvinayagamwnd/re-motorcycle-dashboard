import logging
from pathlib import Path as FilePath

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import FileResponse, StreamingResponse

from ..models.camara import CamaraPosition, CamaraSaveStatus
from ..services.camera_service import (
    capture_snapshot,
    get_camera_status,
    get_shared_camera_stream,
    record_video,
)

router = APIRouter(prefix="/camera", tags=["camera"])
logger = logging.getLogger(__name__)
DATA_DIR = FilePath(__file__).resolve().parents[3] / "data"
GALLERY_DIRECTORIES = {
    "images": DATA_DIR / "capture",
    "videos": DATA_DIR / "recordings",
}


@router.get("/status")
def camera_status() -> dict:
    return get_camera_status()


@router.get("/gallery")
def camera_gallery() -> dict[str, list[dict[str, str]]]:
    """Return saved captures and recordings newest first."""
    gallery: dict[str, list[dict[str, str]]] = {"images": [], "videos": []}
    for media_type, directory in GALLERY_DIRECTORIES.items():
        extension = ".jpg" if media_type == "images" else ".mp4"
        if not directory.exists():
            continue
        files = sorted(
            (file for file in directory.iterdir() if file.is_file() and file.suffix.lower() == extension),
            key=lambda file: file.stat().st_mtime,
            reverse=True,
        )
        gallery[media_type] = [
            {
                "name": file.name,
                "url": f"/api/camera/gallery/{media_type}/{file.name}",
                "created_at": file.stat().st_mtime_ns.__str__(),
            }
            for file in files
        ]
    return gallery


@router.get("/gallery/{media_type}/{filename}")
def gallery_media(media_type: str, filename: str) -> FileResponse:
    """Serve one gallery file after restricting it to its media directory."""
    directory = GALLERY_DIRECTORIES.get(media_type)
    if not directory or FilePath(filename).name != filename:
        raise HTTPException(status_code=404, detail="Media not found")
    filepath = directory / filename
    if not filepath.is_file():
        raise HTTPException(status_code=404, detail="Media not found")
    media_type_header = "image/jpeg" if media_type == "images" else "video/mp4"
    return FileResponse(filepath, media_type=media_type_header, filename=filename)


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
        return await capture_snapshot(camera_id, camera_position)
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
        return await record_video(camera_id, camera_position)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{camera_id}/stream")
async def camera_stream(camera_id: int = Path(ge=1, le=2)) -> StreamingResponse:
    """Proxy the camera MJPEG stream through the backend to avoid CORS/mixed-content issues."""
    return StreamingResponse(
        get_shared_camera_stream(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )