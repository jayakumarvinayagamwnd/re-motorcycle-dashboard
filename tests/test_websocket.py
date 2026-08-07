from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_websocket_echo() -> None:
    with client.websocket_connect("/ws/dashboard") as websocket:
        websocket.send_text("ping")
        data = websocket.receive_text()
    assert data == "echo:ping"


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
