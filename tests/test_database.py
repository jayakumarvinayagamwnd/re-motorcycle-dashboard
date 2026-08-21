from fastapi.testclient import TestClient

from backend.app.database import get_db_connection
from backend.app.main import app

client = TestClient(app)


def _clear_trips() -> None:
    with get_db_connection() as conn:
        conn.execute("DELETE FROM trips")


def _insert_trip(
    trip_name: str,
    status: str,
    distance_km: float = 0.0,
    started_at: str = "2026-08-20T07:30:00+05:30",
) -> int:
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO trips (trip_name, status, started_at, distance_km,
                               duration_sec, avg_speed_kmh, max_speed_kmh,
                               created_at, updated_at)
            VALUES (?, ?, ?, ?, 0, 0.0, 0.0, ?, ?)
            """,
            (trip_name, status, started_at, distance_km, started_at, started_at),
        )
        return cursor.lastrowid


def test_db_health() -> None:
    response = client.get("/healthcheck/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "sqlite"
    assert "check_date" in data
    assert data["created_by"] == "healthcheck"


def test_trip_current_no_active() -> None:
    _clear_trips()
    response = client.get("/api/trip/current")
    assert response.status_code == 200
    data = response.json()
    assert data == {"trip": None}


def test_trip_history() -> None:
    _clear_trips()
    response = client.get("/api/trip/history")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_trip_startup_ready_with_previous() -> None:
    _clear_trips()
    _insert_trip("Evening Ride", "COMPLETED", 72.42, "2026-08-19T18:00:00+05:30")
    response = client.get("/api/trip/startup")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "READY"
    assert data["current_trip"] is None
    assert data["previous_trip"]["trip_name"] == "Evening Ride"
    assert data["previous_trip"]["status"] == "COMPLETED"
    assert data["previous_trip"]["date"] == "2026-08-19"


def test_trip_startup_continue_or_new() -> None:
    _clear_trips()
    _insert_trip("Evening Ride", "PAUSED", 72.42, "2026-08-19T18:00:00+05:30")
    response = client.get("/api/trip/startup")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "CONTINUE_OR_NEW"
    assert data["current_trip"]["trip_name"] == "Evening Ride"
    assert data["current_trip"]["status"] == "PAUSED"
    assert data["current_trip"]["distance_km"] == 72.42
    assert data["previous_trip"] is None


def test_trip_start_created() -> None:
    _clear_trips()
    response = client.post("/api/trip/start", json={"trip_name": "Morning Commute"})
    assert response.status_code == 201
    data = response.json()
    assert data["trip_name"] == "Morning Commute"
    assert data["status"] == "ACTIVE"
    assert data["distance_km"] == 0.0
    assert data["duration_sec"] == 0
    assert data["avg_speed_kmh"] == 0.0
    assert data["max_speed_kmh"] == 0.0
    assert "id" in data
    assert "started_at" in data


def test_trip_start_conflict() -> None:
    _clear_trips()
    active_id = _insert_trip("Existing Trip", "ACTIVE", 10.0)
    response = client.post("/api/trip/start", json={"trip_name": "New Trip"})
    assert response.status_code == 409
    data = response.json()
    assert data["error"] == "TRIP_ALREADY_ACTIVE"
    assert data["message"] == f"Trip {active_id} is already active."


def test_trip_pause_active() -> None:
    _clear_trips()
    trip_id = _insert_trip("Morning Commute", "ACTIVE", 22.31)
    response = client.post(f"/api/trip/{trip_id}/pause")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == trip_id
    assert data["status"] == "PAUSED"
    assert data["distance_km"] == 22.31
    assert data["duration_sec"] == 0
    assert data["avg_speed_kmh"] == 0.0


def test_trip_pause_conflict() -> None:
    _clear_trips()
    trip_id = _insert_trip("Already Paused", "PAUSED", 5.0)
    response = client.post(f"/api/trip/{trip_id}/pause")
    assert response.status_code == 409
    data = response.json()
    assert data["error"] == "TRIP_NOT_ACTIVE"
    assert f"Trip {trip_id} is not active" in data["message"]


def test_trip_finish_active() -> None:
    _clear_trips()
    trip_id = _insert_trip("Morning Commute", "ACTIVE", 42.71)
    response = client.post(f"/api/trip/{trip_id}/finish")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == trip_id
    assert data["trip_name"] == "Morning Commute"
    assert data["status"] == "COMPLETED"
    assert data["distance_km"] == 42.71
    assert "started_at" in data
    assert "ended_at" in data
    assert "duration_sec" in data
    assert "avg_speed_kmh" in data
    assert "max_speed_kmh" in data


def test_trip_finish_paused() -> None:
    _clear_trips()
    trip_id = _insert_trip("Evening Ride", "PAUSED", 72.42)
    response = client.post(f"/api/trip/{trip_id}/finish")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == trip_id
    assert data["status"] == "COMPLETED"
    assert data["distance_km"] == 72.42


def test_trip_finish_conflict() -> None:
    _clear_trips()
    trip_id = _insert_trip("Already Completed", "COMPLETED", 10.0)
    response = client.post(f"/api/trip/{trip_id}/finish")
    assert response.status_code == 409
    data = response.json()
    assert data["error"] == "TRIP_NOT_FINISHABLE"
    assert f"Trip {trip_id} cannot be finished" in data["message"]
