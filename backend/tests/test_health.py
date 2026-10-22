from fastapi.testclient import TestClient

from app.main import app


def test_health_and_readiness_use_api_prefix(tmp_path, monkeypatch):
    monkeypatch.setenv("PR_MENTOR_STORAGE", "sqlite")
    monkeypatch.setenv("PR_MENTOR_DATABASE_PATH", str(tmp_path / "health.sqlite3"))
    client = TestClient(app)
    assert client.get("/api/health").json() == {"status": "ok", "service": "pr-mentor"}
    assert client.get("/api/health/ready").json() == {"status": "ready", "service": "pr-mentor"}


def test_cors_allows_frontend_development_origin(tmp_path, monkeypatch):
    monkeypatch.setenv("PR_MENTOR_STORAGE", "sqlite")
    monkeypatch.setenv("PR_MENTOR_DATABASE_PATH", str(tmp_path / "cors.sqlite3"))
    response = TestClient(app).options("/api/health", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
