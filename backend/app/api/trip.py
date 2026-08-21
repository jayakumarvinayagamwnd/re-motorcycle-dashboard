from fastapi import APIRouter, Path
from fastapi.responses import JSONResponse

from ..models.db_check import DBHealthError
from ..models.trip import (
    CurrentTripResponse,
    TripConflictError,
    TripFinishResponse,
    TripPauseResponse,
    TripStartRequest,
    TripStartResponse,
    TripStartupResponse,
)
from ..services.trip_service import (
    TripAlreadyActiveError,
    TripNotActiveError,
    TripNotFinishableError,
    finish_trip,
    get_current_trip,
    get_trip_history,
    get_trip_startup,
    pause_trip,
    start_trip,
)

router = APIRouter(prefix="/trip", tags=["trip"])


@router.get(
    "/current",
    response_model=CurrentTripResponse,
    responses={
        503: {
            "model": DBHealthError,
            "description": "Database health check failed",
        }
    },
)
def current_trip() -> CurrentTripResponse:
    """Return the current ACTIVE trip, or null if no active trip exists."""
    try:
        return get_current_trip()
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content=DBHealthError(
                status="unhealthy",
                database="sqlite",
                error="Database health check failed",
            ).model_dump(),
        )


@router.get(
    "/startup",
    response_model=TripStartupResponse,
    responses={
        503: {
            "model": DBHealthError,
            "description": "Database health check failed",
        }
    },
)
def trip_startup() -> TripStartupResponse:
    """Return startup state: unfinished trip if any, otherwise the last completed trip."""
    try:
        return get_trip_startup()
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content=DBHealthError(
                status="unhealthy",
                database="sqlite",
                error="Database health check failed",
            ).model_dump(),
        )


@router.post(
    "/start",
    response_model=TripStartResponse,
    status_code=201,
    responses={
        409: {
            "model": TripConflictError,
            "description": "Another trip is already active",
        },
        503: {
            "model": DBHealthError,
            "description": "Database health check failed",
        },
    },
)
def trip_start(request: TripStartRequest) -> TripStartResponse:
    """Start a new trip. Returns 409 if another trip is already active."""
    try:
        return start_trip(request)
    except TripAlreadyActiveError as exc:
        return JSONResponse(
            status_code=409,
            content=TripConflictError(
                error="TRIP_ALREADY_ACTIVE",
                message=f"Trip {exc.active_trip_id} is already active.",
            ).model_dump(),
        )
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content=DBHealthError(
                status="unhealthy",
                database="sqlite",
                error="Database health check failed",
            ).model_dump(),
        )


@router.post(
    "/{trip_id}/pause",
    response_model=TripPauseResponse,
    responses={
        409: {
            "model": TripConflictError,
            "description": "Trip is not ACTIVE",
        },
        503: {
            "model": DBHealthError,
            "description": "Database health check failed",
        },
    },
)
def trip_pause(trip_id: int = Path(ge=1)) -> TripPauseResponse:
    """Pause an ACTIVE trip. Returns 409 if the trip is not ACTIVE."""
    try:
        return pause_trip(trip_id)
    except TripNotActiveError as exc:
        return JSONResponse(
            status_code=409,
            content=TripConflictError(
                error="TRIP_NOT_ACTIVE",
                message=f"Trip {exc.trip_id} is not active (status: {exc.current_status}).",
            ).model_dump(),
        )
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content=DBHealthError(
                status="unhealthy",
                database="sqlite",
                error="Database health check failed",
            ).model_dump(),
        )


@router.post(
    "/{trip_id}/finish",
    response_model=TripFinishResponse,
    responses={
        409: {
            "model": TripConflictError,
            "description": "Trip is not ACTIVE or PAUSED",
        },
        503: {
            "model": DBHealthError,
            "description": "Database health check failed",
        },
    },
)
def trip_finish(trip_id: int = Path(ge=1)) -> TripFinishResponse:
    """Finish an ACTIVE or PAUSED trip, marking it COMPLETED."""
    try:
        return finish_trip(trip_id)
    except TripNotFinishableError as exc:
        return JSONResponse(
            status_code=409,
            content=TripConflictError(
                error="TRIP_NOT_FINISHABLE",
                message=f"Trip {exc.trip_id} cannot be finished (status: {exc.current_status}).",
            ).model_dump(),
        )
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content=DBHealthError(
                status="unhealthy",
                database="sqlite",
                error="Database health check failed",
            ).model_dump(),
        )


@router.get("/history")
def trip_history() -> list:
    return get_trip_history()