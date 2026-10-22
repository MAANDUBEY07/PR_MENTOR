"""Tests for the URL-to-review API integration without external services."""

import pytest
from app.ai_review.client import AIConfigurationError, AIProviderError
from app.github_service.client import GitHubServiceError
from app.main import app
from app.routes import review as review_route
from app.schemas.review import ReviewAnalyzeRequest, ReviewResponse
from fastapi import HTTPException
from pydantic import ValidationError


def test_analyze_endpoint_ingests_url_and_returns_frontend_shape(monkeypatch):
    payload = {"pull_request": {"owner": "acme", "repo": "widget", "number": 12}}
    review = {
        "repository": "acme/widget",
        "pull_request_title": "Improve parser",
        "pull_request_number": 12,
        "url": "https://github.com/acme/widget/pull/12",
        "findings": [
            {
                "severity": "High",
                "title": "Missing guard",
                "file": "src/parser.py",
                "line": 14,
                "text": "The changed code dereferences the value before checking it.",
                "proof": "value is accessed before the null check",
                "status": "unverified AI suggestion",
            }
        ],
        "status": "completed",
    }
    ingested_urls = []
    reviewed_payloads = []

    def fake_ingest(url):
        ingested_urls.append(url)
        return payload

    def fake_review(received_payload):
        reviewed_payloads.append(received_payload)
        return review

    monkeypatch.setattr(review_route, "ingest_pull_request", fake_ingest)
    monkeypatch.setattr(review_route, "run_review", fake_review)

    response = review_route.analyze_pull_request(
        ReviewAnalyzeRequest(url="https://github.com/acme/widget/pull/12")
    )

    assert response == review
    assert ReviewResponse.model_validate(response).model_dump(exclude_none=True) == review
    assert ingested_urls == ["https://github.com/acme/widget/pull/12"]
    assert reviewed_payloads == [payload]


def test_analyze_endpoint_maps_invalid_pull_request_url_to_422(monkeypatch):
    def reject_url(_url):
        raise ValueError("Only GitHub pull request URLs are supported.")

    monkeypatch.setattr(review_route, "ingest_pull_request", reject_url)

    with pytest.raises(HTTPException) as error:
        review_route.analyze_pull_request(ReviewAnalyzeRequest(url="not-a-pr"))

    assert error.value.status_code == 422
    assert "pull request URLs" in error.value.detail


def test_analyze_endpoint_maps_github_errors(monkeypatch):
    def github_failure(_url):
        raise GitHubServiceError("The pull request was not found.", status_code=404)

    monkeypatch.setattr(review_route, "ingest_pull_request", github_failure)

    with pytest.raises(HTTPException) as error:
        review_route.analyze_pull_request(
            ReviewAnalyzeRequest(url="https://github.com/acme/widget/pull/12")
        )

    assert error.value.status_code == 404
    assert error.value.detail == "The pull request was not found."


@pytest.mark.parametrize(
    ("ai_error", "expected_status", "expected_detail"),
    [
        (AIConfigurationError("missing key"), 503, "AI review is not configured. Set AI_API_KEY and AI_MODEL."),
        (AIProviderError("provider unavailable"), 502, "provider unavailable"),
    ],
)
def test_analyze_endpoint_maps_ai_errors(
    monkeypatch, ai_error, expected_status, expected_detail
):
    monkeypatch.setattr(
        review_route,
        "ingest_pull_request",
        lambda _url: {"pull_request": {"owner": "acme"}},
    )

    def fail_review(_payload):
        raise ai_error

    monkeypatch.setattr(review_route, "run_review", fail_review)

    with pytest.raises(HTTPException) as http_error:
        review_route.analyze_pull_request(
            ReviewAnalyzeRequest(url="https://github.com/acme/widget/pull/12")
        )

    assert http_error.value.status_code == expected_status
    assert http_error.value.detail == expected_detail


def test_analyze_endpoint_validates_request_and_keeps_health_route():
    with pytest.raises(ValidationError):
        ReviewAnalyzeRequest(url="")

    paths = app.openapi()["paths"]
    assert "/api/reviews/analyze" in paths
    assert "/health" in paths

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.github import ChangedFile, PullRequestBundle, PullRequestMetadata


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PR_MENTOR_STORAGE", "sqlite")
    monkeypatch.setenv("PR_MENTOR_DATABASE_PATH", str(tmp_path / "api.sqlite3"))
    return TestClient(app)


def test_demo_review_history_detail_and_diff_are_persisted(client):
    submitted_url = "https://github.com/example/project/pull/7"
    response = client.post("/api/reviews/analyze", json={"url": submitted_url, "mode": "demo", "include_learning": True})
    assert response.status_code == 200
    body = response.json()
    assert body["analysis_mode"] == "demo" and body["is_demo"] is True
    assert "not describe" in body["warnings"][0].lower()
    assert {item["source"] for item in body["findings"]} == {"demo"}
    assert body["pull_request"]["pull_request_number"] == 7
    assert client.get("/api/reviews/history").json()[0]["review_id"] == body["review_id"]
    assert client.get(f"/api/reviews/{body['review_id']}").json()["review_id"] == body["review_id"]
    assert client.get(f"/api/reviews/{body['review_id']}/diff").json() == {"review_id": body["review_id"], "files": [], "warnings": body["warnings"]}

    second = client.post("/api/reviews/analyze", json={"url": submitted_url, "mode": "demo", "include_learning": False}).json()
    assert second["review_id"] != body["review_id"]
    assert all(not finding["learning_explanation"] for finding in second["findings"])
    assert len(client.get("/api/reviews/history").json()) == 2


def test_review_request_validation_and_unknown_records(client):
    assert client.post("/api/reviews/analyze", json={"mode": "demo"}).status_code == 422
    assert client.post("/api/reviews/analyze", json={"url": "https://example.com/a/b/pull/1"}).status_code == 400
    assert client.get("/api/reviews/not-found").status_code == 404
    assert client.get("/api/reviews/not-found/diff").status_code == 404
    assert client.get("/api/reviews/history?limit=0").status_code == 422


def test_saved_pr_create_list_duplicate_and_delete(client):
    url = "https://github.com/owner/repo/pull/12"
    created = client.post("/api/reviews/saved", json={"url": url})
    assert created.status_code == 201
    item = created.json()
    assert item == {"saved_id": item["saved_id"], "url": url, "temporary": False}
    assert client.post("/api/reviews/saved", json={"url": url}).json()["saved_id"] == item["saved_id"]
    assert client.get("/api/reviews/saved").json() == [item]
    assert client.delete(f"/api/reviews/saved/{item['saved_id']}").json() == {"deleted": True}
    assert client.delete(f"/api/reviews/saved/{item['saved_id']}").status_code == 404


def test_live_review_uses_ingestion_and_reports_unavailable_stages(client, monkeypatch):
    from app.services import review_orchestrator as service

    metadata = PullRequestMetadata(repository_owner="owner", repository_name="repo", repository_url="https://github.com/owner/repo", pull_request_number=2, pull_request_url="https://github.com/owner/repo/pull/2", title="Fix", description=None, author="dev", base_branch="main", head_branch="fix", head_sha="abc123", state="open", changed_files=1, additions=1, deletions=0)
    bundle = PullRequestBundle(metadata=metadata, files=[ChangedFile(filename="src/a.py", status="modified", additions=1, deletions=0, changes=1, patch="@@ -1 +1 @@\n-old\n+new", size=12)])

    async def fetch(_url):
        return bundle

    async def content(*_args):
        return "value = 1\n"

    def ruff(paths, *, root):
        return [{"file_path": str(root / paths[0]), "line": 1, "rule_id": "F401", "message": "unused import", "evidence": "import os"}]

    def bandit(_paths, *, root):
        return []

    monkeypatch.setattr(service, "fetch_pull_request", fetch)
    monkeypatch.setattr(service, "get_file_content", content)
    monkeypatch.setattr(service, "run_ruff", ruff)
    monkeypatch.setattr(service, "run_bandit", bandit)
    monkeypatch.setattr(service, "is_configured", lambda: False)
    response = client.post("/api/reviews/analyze", json={"url": metadata.pull_request_url, "mode": "live"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_demo"] is False and body["analysis_mode"] == "live"
    assert body["status"] == "partial"  # AI and isolated test execution are not configured.
    assert body["findings"][0]["file_path"] == "src/a.py"  # Never expose the temporary workspace path.
    assert body["findings"][0]["verification_status"] == "needs_review"
    assert any(tool["tool"] == "tests" and tool["executed"] is False for tool in body["tool_results"])
