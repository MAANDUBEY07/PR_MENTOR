import json
from app.main import health, readiness

def test_health_reports_demo_mode():
    response = health()
    assert response["status"] == "ok"
    assert response["mode"] == "demo"

def test_readiness_without_optional_mongo():
    response = readiness()
    assert response.status_code == 200
    assert json.loads(response.body)["dependencies"]["mongodb"] == "optional_unconfigured"
