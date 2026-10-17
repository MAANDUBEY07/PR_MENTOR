from app.github_service.files import parse_patch
from app.schemas.finding import ReviewFinding
from app.verification.normalizer import verify_finding

def make_finding():
    return ReviewFinding(id="x",title="Possible issue",description="Check behavior",file_path="src/a.py",line_start=2,severity="medium",category="bug",confidence=.99,source="ai_candidate",verification_status="needs_review",evidence=[],why_it_matters="Could fail",suggested_fix="Handle the case",learning_explanation="Lookups may be empty")

def test_ai_confidence_alone_does_not_verify_finding():
    finding=verify_finding(make_finding(),[{"filename":"src/a.py","patch":"@@ -1 +1,2 @@\n+x\n"}],[])
    assert finding.verification_status == "needs_review"

def test_missing_patch_cannot_substantiate_finding():
    finding=verify_finding(make_finding(),[],[])
    assert finding.verification_status == "unsupported"

def test_diff_parser_uses_github_patch_lines():
    result=parse_patch({"filename":"src/a.py","status":"modified","patch":"@@ -1 +1,2 @@\n-old\n+new\n+more"})
    assert result["added"] == 0  # The API summary, not inferred from an incomplete patch.
    assert [line["kind"] for line in result["hunks"][0]["lines"]] == ["removed","added","added"]
