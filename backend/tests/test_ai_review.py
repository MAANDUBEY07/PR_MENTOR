import asyncio
import json

import pytest

from app.ai_review import reviewer
from app.ai_review.client import AIReviewUnavailable


def test_ai_is_honestly_unavailable_without_credentials(monkeypatch):
    from app.ai_review import client

    monkeypatch.setattr(client, "llm_configuration", lambda: (None, None, "https://api.openai.com/v1/chat/completions"))
    with pytest.raises(AIReviewUnavailable, match="not configured"):
        asyncio.run(client.complete_json("system", "user"))


def test_reviewer_validates_provider_findings_and_marks_them_unverified(monkeypatch):
    async def complete(*_args):
        return json.dumps({"findings": [{"title": "Possible bug", "description": "Check this branch.", "file_path": "src/a.py", "line_start": None, "line_end": None, "severity": "medium", "category": "bug", "confidence": 0.62, "evidence": ["The diff adds a conditional."], "why_it_matters": "The alternate case may be skipped.", "suggested_fix": "Add a case-specific test.", "learning_explanation": "Review both paths.", "limitations": ["Candidate requires human review."]}]})

    monkeypatch.setattr(reviewer, "complete_json", complete)
    findings = asyncio.run(reviewer.generate_candidates({"title": "T"}, [], []))
    assert findings[0].source == "ai_candidate"
    assert findings[0].verification_status == "needs_review"
    assert findings[0].line_start is None


def test_reviewer_rejects_malformed_provider_json(monkeypatch):
    async def complete(*_args):
        return "not json"

    monkeypatch.setattr(reviewer, "complete_json", complete)
    with pytest.raises(AIReviewUnavailable, match="invalid JSON"):
        asyncio.run(reviewer.generate_candidates({}, [], []))
