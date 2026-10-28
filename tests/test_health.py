"""API health smoke (no live DB required; bootstrap degrades)."""
from app import create_app


def test_health_ok():
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "flask-fullstack-starter"


def test_request_id_header():
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/health", headers={"X-Request-ID": "test-rid-123"})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == "test-rid-123"
