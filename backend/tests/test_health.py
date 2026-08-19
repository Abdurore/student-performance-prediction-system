"""System endpoint tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_check_returns_ready_status() -> None:
    """Confirm the local service advertises a usable startup state."""
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
