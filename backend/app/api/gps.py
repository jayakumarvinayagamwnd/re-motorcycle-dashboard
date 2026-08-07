from fastapi import APIRouter

from ..services.gps_service import get_latest_gps

router = APIRouter(prefix="/gps", tags=["gps"])


@router.get("/latest")
def latest_gps() -> dict:
    return get_latest_gps()
