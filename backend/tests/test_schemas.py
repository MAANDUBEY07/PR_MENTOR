import pytest
from pydantic import ValidationError

from app.schemas.finding import ReviewFinding
from app.schemas.github import PullRequestMetadata
from app.schemas.review import AnalyzeRequest, DiffResponse


def test_review_finding_contract_preserves_null_lines_and_provenance():
    finding = ReviewFinding(id="f1", title="Candidate", description="Check this", file_path="a.py", line_start=None, line_end=None, severity="medium", category="bug", confidence=0.4, source="ai_candidate", verification_status="needs_review", evidence=[], why_it_matters="Context", suggested_fix="Inspect", learning_explanation="", limitations=[])
    assert finding.line_start is None and finding.source == "ai_candidate"
    with pytest.raises(ValidationError):
        ReviewFinding(id="f2", title="Bad", description="x", file_path="a.py", severity="urgent", category="bug", confidence=0.4, source="ai_candidate", verification_status="needs_review", why_it_matters="x", suggested_fix="x")


def test_analyze_request_aliases_and_required_url():
    assert AnalyzeRequest(url="https://github.com/a/b/pull/1").mode == "demo"
    assert AnalyzeRequest(pull_request_url="https://github.com/a/b/pull/1", mode="live").mode == "live"
    with pytest.raises(ValidationError):
        AnalyzeRequest(mode="unknown")


def test_github_metadata_nullable_values_and_diff_contract():
    metadata = PullRequestMetadata(repository_owner="o", repository_name="r", repository_url="https://github.com/o/r", pull_request_number=1, pull_request_url="https://github.com/o/r/pull/1", title="T", description=None, author=None, base_branch=None, head_branch=None, head_sha=None, state="open", changed_files=0, additions=0, deletions=0)
    assert metadata.description is None and metadata.head_sha is None
    assert DiffResponse(review_id="r1", files=[], warnings=[]).files == []
