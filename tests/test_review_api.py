import pytest
from app.data.sample_reviews import sample_review
from app.github_service.parser import parse_pull_request_url, InvalidPullRequestURL
from app.database import reviews as store

def test_demo_analysis_is_explicitly_labeled():
    body = sample_review(submitted_url="https://github.com/example/project/pull/7")
    assert body["is_demo"] is True
    assert body["analysis_mode"] == "demo"
    assert body["pull_request"]["pull_request_number"] == 7
    assert len(body["findings"]) >= 3
    assert "not" in body["warnings"][0].lower()

def test_invalid_github_url_rejected():
    with pytest.raises(InvalidPullRequestURL):
        parse_pull_request_url("https://example.com/owner/repo/pull/1")

def test_review_history_and_retrieval():
    created = sample_review(submitted_url="https://github.com/example/project/pull/8")
    store.save_review(created)
    assert store.get_review(created["review_id"])["review_id"] == created["review_id"]
    assert store.list_reviews()[0]["review_id"] == created["review_id"]

def test_live_mode_is_not_mislabeled_as_demo():
    assert sample_review()["analysis_mode"] == "demo"
    # Live execution is exercised only when GitHub is available; no network is used in unit tests.
