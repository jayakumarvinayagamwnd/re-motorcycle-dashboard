from pydantic import BaseModel


class Trip(BaseModel):
    """Model for a row in the trips table."""
    id: int
    trip_name: str
    status: str
    started_at: str
    distance_km: float
    duration_sec: int
    avg_speed_kmh: float
    max_speed_kmh: float


class CurrentTripResponse(BaseModel):
    """Response for GET /api/trip/current."""
    trip: Trip | None = None


class TripStartupCurrentTrip(BaseModel):
    """Unfinished trip returned by GET /api/trip/startup."""
    id: int
    trip_name: str
    status: str
    distance_km: float


class TripStartupPreviousTrip(BaseModel):
    """Most recent completed trip returned by GET /api/trip/startup."""
    id: int
    trip_name: str
    status: str
    date: str


class TripStartupResponse(BaseModel):
    """Response for GET /api/trip/startup."""
    state: str
    current_trip: TripStartupCurrentTrip | None = None
    previous_trip: TripStartupPreviousTrip | None = None


class TripStartRequest(BaseModel):
    """Request payload for POST /api/trip/start."""
    trip_name: str


class TripStartResponse(BaseModel):
    """Response payload for POST /api/trip/start (201 Created)."""
    id: int
    trip_name: str
    status: str
    started_at: str
    distance_km: float
    duration_sec: int
    avg_speed_kmh: float
    max_speed_kmh: float


class TripConflictError(BaseModel):
    """409 Conflict response when another trip is already active."""
    error: str
    message: str


class TripPauseResponse(BaseModel):
    """Response payload for POST /api/trip/{id}/pause."""
    id: int
    status: str
    distance_km: float
    duration_sec: int
    avg_speed_kmh: float


class TripResumeResponse(BaseModel):
    """Response payload for POST /api/trip/{id}/resume."""

    id: int
    status: str
    distance_km: float
    duration_sec: int
    avg_speed_kmh: float


class TripFinishResponse(BaseModel):
    """Response payload for POST /api/trip/{id}/finish."""
    id: int
    trip_name: str
    status: str
    started_at: str
    ended_at: str
    distance_km: float
    duration_sec: int
    avg_speed_kmh: float
    max_speed_kmh: float
