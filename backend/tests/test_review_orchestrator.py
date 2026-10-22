import json

from app.services.review_orchestrator import run_ai_review, run_review


class FakeProvider:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return json.dumps(
            {
                "findings": [
                    {
                        "file_path": "src/parser.py",
                        "line": 1,
                        "rule_id": None,
                        "severity": "medium",
                        "message": "The fallback may accept an invalid user.",
                        "evidence": "return True",
                        "explanation": "This branch accepts every user value.",
                        "suggested_fix": "Validate the user before returning success.",
                    }
                ]
            }
        )


def sample_payload():
    return {
        "pull_request": {
            "owner": "acme",
            "repo": "widget",
            "number": 12,
            "title": "Improve parser",
            "body": "Handle edge cases",
            "state": "open",
            "html_url": "https://github.com/acme/widget/pull/12",
            "author": "contributor",
            "base_ref": "main",
            "base_sha": "base-sha",
            "head_ref": "fix/parser",
            "head_sha": "head-sha",
            "changed_files": 1,
        },
        "files": [
            {
                "filename": "src/parser.py",
                "previous_filename": None,
                "status": "modified",
                "additions": 2,
                "deletions": 1,
                "changes": 3,
                "sha": "file-sha",
                "patch": "@@ -1,2 +1,3 @@\n+return True",
                "source_content": "def run():\n    return True\n",
                "content_unavailable_reason": None,
            }
        ],
        "files_truncated": False,
    }


def test_orchestrator_sends_ingestion_payload_to_ai_reviewer():
    findings = run_ai_review(sample_payload(), provider=FakeProvider())

    assert len(findings) == 1
    assert findings[0].file_path == "src/parser.py"
    assert findings[0].source == "ai"
    assert findings[0].verification_status == "unverified"


def test_orchestrator_maps_findings_to_frontend_response_contract():
    response = run_review(sample_payload(), provider=FakeProvider())

    assert response["repository"] == "acme/widget"
    assert response["pull_request_title"] == "Improve parser"
    assert response["pull_request_number"] == 12
    assert response["url"] == "https://github.com/acme/widget/pull/12"
    assert response["status"] == "completed"
    assert response["findings"] == [
        {
            "severity": "Medium",
            "title": "The fallback may accept an invalid user.",
            "file": "src/parser.py",
            "line": 1,
            "text": (
                "This branch accepts every user value.\n\n"
                "Suggested improvement: Validate the user before returning success."
            ),
            "proof": "return True",
            "status": "unverified AI suggestion",
        }
    ]
