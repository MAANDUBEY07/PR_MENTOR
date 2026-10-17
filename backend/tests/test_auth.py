from fastapi.testclient import TestClient

from app.main import app


def test_otp_routes_fail_closed_without_delivery_or_storage():
    client = TestClient(app)
    sent = client.post("/api/auth/otp/send", json={"identity": "user@example.com", "channel": "email"})
    assert sent.status_code == 503
    assert "not configured" in sent.json()["detail"].lower()
    verified = client.post("/api/auth/otp/verify", json={"challenge_id": "any", "code": "123456"})
    assert verified.status_code == 503
    assert "not configured" in verified.json()["detail"].lower()
