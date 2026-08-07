from fastapi import APIRouter

from ..services.trip_service import get_current_trip

router = APIRouter(prefix="/trip", tags=["trip"])


@router.get("/current")
def current_trip() -> dict:
    return get_current_trip()
