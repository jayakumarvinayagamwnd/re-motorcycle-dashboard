from fastapi import APIRouter

from ..services.trip_service import get_current_trip, get_trip_history

router = APIRouter(prefix="/trip", tags=["trip"])


@router.get("/current")
def current_trip() -> dict:
    return get_current_trip()


@router.get("/history")
def trip_history() -> list:
    return get_trip_history()
