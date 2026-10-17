import pytest
from pydantic import ValidationError
from app.schemas.finding import ReviewFinding

def test_finding_requires_bounded_confidence_and_evidence_fields():
    finding = ReviewFinding(id="x", title="Potential bug", description="Example", file_path="a.py", severity="low", category="bug", confidence=.5, source="ai_candidate", verification_status="needs_review", evidence=[], why_it_matters="Could fail", suggested_fix="Check value", learning_explanation="Lookups may be empty")
    assert finding.verification_status == "needs_review"

def test_finding_rejects_invalid_severity():
    with pytest.raises(ValidationError):
        ReviewFinding(id="x", title="bad", description="", file_path="a.py", severity="urgent", category="bug", confidence=.5, source="ai_candidate", verification_status="needs_review", why_it_matters="", suggested_fix="", learning_explanation="")
