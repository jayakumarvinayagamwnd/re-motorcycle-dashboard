from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_telemetry_latest() -> None:
    response = client.get("/api/telemetry/latest")
    assert response.status_code == 200
    data = response.json()
    assert "speed_kmh" in data
    assert "engine_rpm" in data
