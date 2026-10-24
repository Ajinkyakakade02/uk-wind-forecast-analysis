"""
Tests for the /health endpoint supporting GET and HEAD methods (UptimeRobot compatibility).
"""

from fastapi.testclient import TestClient
from app.main import app


def test_health_check_get():
    """Verify GET /health returns HTTP 200 with status ok."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_head():
    """Verify HEAD /health returns HTTP 200 without body for uptime monitors."""
    client = TestClient(app)
    response = client.head("/health")
    assert response.status_code == 200
    assert response.text == ""
