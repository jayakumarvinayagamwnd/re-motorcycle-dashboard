from fastapi import APIRouter

from ..services.telemetry_service import get_latest_telemetry

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("/latest")
def latest_telemetry() -> dict:
    return get_latest_telemetry()
