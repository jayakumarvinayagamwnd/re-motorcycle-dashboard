from datetime import datetime

from ..database import get_db_connection
from ..models.trip import (
    CurrentTripResponse,
    Trip,
    TripFinishResponse,
    TripPauseResponse,
    TripResumeResponse,
    TripStartRequest,
    TripStartResponse,
    TripStartupCurrentTrip,
    TripStartupPreviousTrip,
    TripStartupResponse,
)


class TripAlreadyActiveError(Exception):
    """Raised when trying to start a trip while another is already active."""

    def __init__(self, active_trip_id: int):
        self.active_trip_id = active_trip_id
        super().__init__(f"Trip {active_trip_id} is already active.")


class TripNotActiveError(Exception):
    """Raised when trying to pause a trip that is not ACTIVE."""

    def __init__(self, trip_id: int, current_status: str):
        self.trip_id = trip_id
        self.current_status = current_status
        super().__init__(f"Trip {trip_id} is not active (status: {current_status}).")


class TripNotFinishableError(Exception):
    """Raised when trying to finish a trip that is not ACTIVE or PAUSED."""

    def __init__(self, trip_id: int, current_status: str):
        self.trip_id = trip_id
        self.current_status = current_status
        super().__init__(f"Trip {trip_id} cannot be finished (status: {current_status}).")


class TripNotPausedError(Exception):
    """Raised when trying to resume a trip that is not PAUSED."""

    def __init__(self, trip_id: int, current_status: str):
        self.trip_id = trip_id
        self.current_status = current_status
        super().__init__(f"Trip {trip_id} is not paused (status: {current_status}).")


def get_current_trip() -> CurrentTripResponse:
    """Return the most recent ACTIVE trip from the database, or null if none."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, trip_name, status, started_at, distance_km,
                   duration_sec, avg_speed_kmh, max_speed_kmh
            FROM trips
            WHERE status = 'ACTIVE'
            ORDER BY id DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()

    if row is None:
        return CurrentTripResponse(trip=None)

    trip = Trip(
        id=row["id"],
        trip_name=row["trip_name"],
        status=row["status"],
        started_at=row["started_at"],
        distance_km=row["distance_km"],
        duration_sec=row["duration_sec"],
        avg_speed_kmh=row["avg_speed_kmh"],
        max_speed_kmh=row["max_speed_kmh"],
    )
    return CurrentTripResponse(trip=trip)


def get_trip_startup() -> TripStartupResponse:
    """Return startup state: unfinished trip if any, otherwise the last completed trip."""
    with get_db_connection() as conn:
        # Check for an unfinished trip (ACTIVE or PAUSED)
        cursor = conn.execute(
            """
            SELECT id, trip_name, status, distance_km
            FROM trips
            WHERE status IN ('ACTIVE', 'PAUSED')
            ORDER BY id DESC
            LIMIT 1
            """
        )
        unfinished = cursor.fetchone()

        if unfinished is not None:
            current_trip = TripStartupCurrentTrip(
                id=unfinished["id"],
                trip_name=unfinished["trip_name"],
                status=unfinished["status"],
                distance_km=unfinished["distance_km"],
            )
            return TripStartupResponse(
                state="CONTINUE_OR_NEW",
                current_trip=current_trip,
            )

        # No unfinished trip — return the most recent completed trip
        cursor = conn.execute(
            """
            SELECT id, trip_name, status, started_at
            FROM trips
            WHERE status = 'COMPLETED'
            ORDER BY id DESC
            LIMIT 1
            """
        )
        previous = cursor.fetchone()

    if previous is None:
        return TripStartupResponse(state="READY")

    previous_trip = TripStartupPreviousTrip(
        id=previous["id"],
        trip_name=previous["trip_name"],
        status=previous["status"],
        date=previous["started_at"][:10],
    )
    return TripStartupResponse(
        state="READY",
        previous_trip=previous_trip,
    )


def start_trip(request: TripStartRequest) -> TripStartResponse:
    """Start a new trip. Raises TripAlreadyActiveError if another trip is active."""
    now = datetime.now().astimezone().isoformat()

    with get_db_connection() as conn:
        # Check for an existing ACTIVE trip
        cursor = conn.execute(
            "SELECT id FROM trips WHERE status = 'ACTIVE' ORDER BY id DESC LIMIT 1"
        )
        active = cursor.fetchone()
        if active is not None:
            raise TripAlreadyActiveError(active["id"])

        # Insert the new trip
        cursor = conn.execute(
            """
            INSERT INTO trips (trip_name, status, started_at, distance_km,
                               duration_sec, avg_speed_kmh, max_speed_kmh,
                               created_at, updated_at)
            VALUES (?, 'ACTIVE', ?, 0.0, 0, 0.0, 0.0, ?, ?)
            """,
            (request.trip_name, now, now, now),
        )
        trip_id = cursor.lastrowid

    return TripStartResponse(
        id=trip_id,
        trip_name=request.trip_name,
        status="ACTIVE",
        started_at=now,
        distance_km=0.0,
        duration_sec=0,
        avg_speed_kmh=0.0,
        max_speed_kmh=0.0,
    )


def pause_trip(trip_id: int) -> TripPauseResponse:
    """Pause an ACTIVE trip. Raises TripNotActiveError if the trip is not ACTIVE."""
    now = datetime.now().astimezone().isoformat()

    with get_db_connection() as conn:
        # Find the trip
        cursor = conn.execute(
            """
            SELECT id, status, distance_km, duration_sec, avg_speed_kmh
            FROM trips
            WHERE id = ?
            """,
            (trip_id,),
        )
        row = cursor.fetchone()

        if row is None:
            raise TripNotActiveError(trip_id, "NOT_FOUND")

        if row["status"] != "ACTIVE":
            raise TripNotActiveError(trip_id, row["status"])

        # Update status to PAUSED
        conn.execute(
            """
            UPDATE trips
            SET status = 'PAUSED', updated_at = ?
            WHERE id = ?
            """,
            (now, trip_id),
        )

    return TripPauseResponse(
        id=row["id"],
        status="PAUSED",
        distance_km=row["distance_km"],
        duration_sec=row["duration_sec"],
        avg_speed_kmh=row["avg_speed_kmh"],
    )


def resume_trip(trip_id: int) -> TripResumeResponse:
    """Resume a PAUSED trip. Raises TripNotPausedError if it is not PAUSED."""
    now = datetime.now().astimezone().isoformat()

    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, status, distance_km, duration_sec, avg_speed_kmh
            FROM trips
            WHERE id = ?
            """,
            (trip_id,),
        )
        row = cursor.fetchone()

        if row is None:
            raise TripNotPausedError(trip_id, "NOT_FOUND")

        if row["status"] != "PAUSED":
            raise TripNotPausedError(trip_id, row["status"])

        conn.execute(
            """
            UPDATE trips
            SET status = 'ACTIVE', updated_at = ?
            WHERE id = ?
            """,
            (now, trip_id),
        )

    return TripResumeResponse(
        id=row["id"],
        status="ACTIVE",
        distance_km=row["distance_km"],
        duration_sec=row["duration_sec"],
        avg_speed_kmh=row["avg_speed_kmh"],
    )


def finish_trip(trip_id: int) -> TripFinishResponse:
    """Finish an ACTIVE or PAUSED trip, marking it COMPLETED."""
    now = datetime.now().astimezone().isoformat()

    with get_db_connection() as conn:
        # Find the trip
        cursor = conn.execute(
            """
            SELECT id, trip_name, status, started_at, distance_km,
                   duration_sec, avg_speed_kmh, max_speed_kmh
            FROM trips
            WHERE id = ?
            """,
            (trip_id,),
        )
        row = cursor.fetchone()

        if row is None:
            raise TripNotFinishableError(trip_id, "NOT_FOUND")

        if row["status"] not in ("ACTIVE", "PAUSED"):
            raise TripNotFinishableError(trip_id, row["status"])

        # Update status to COMPLETED
        conn.execute(
            """
            UPDATE trips
            SET status = 'COMPLETED', ended_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (now, now, trip_id),
        )

    return TripFinishResponse(
        id=row["id"],
        trip_name=row["trip_name"],
        status="COMPLETED",
        started_at=row["started_at"],
        ended_at=now,
        distance_km=row["distance_km"],
        duration_sec=row["duration_sec"],
        avg_speed_kmh=row["avg_speed_kmh"],
        max_speed_kmh=row["max_speed_kmh"],
    )


def get_trip_history() -> list:
    """Return all trips from the database, newest first."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, trip_name, status, started_at, distance_km,
                   duration_sec, avg_speed_kmh, max_speed_kmh
            FROM trips
            ORDER BY id DESC
            """
        )
        rows = cursor.fetchall()

    return [
        {
            "id": row["id"],
            "trip_name": row["trip_name"],
            "status": row["status"],
            "started_at": row["started_at"],
            "distance_km": row["distance_km"],
            "duration_sec": row["duration_sec"],
            "avg_speed_kmh": row["avg_speed_kmh"],
            "max_speed_kmh": row["max_speed_kmh"],
        }
        for row in rows
    ]
