import asyncio

import httpx
import pytest

from app.github_service.client import GitHubAPIError, request_json
from app.github_service.files import parse_patch
from app.github_service.parser import InvalidPullRequestURL, parse_pull_request_url


@pytest.mark.parametrize("value", [
    "http://github.com/o/r/pull/1", "https://github.com.evil.test/o/r/pull/1",
    "https://user@github.com/o/r/pull/1", "https://github.com/o/r/issues/1",
    "https://github.com/o/r/pull/0", "https://github.com/o/r/pull/1/extra",
    "https://127.0.0.1/o/r/pull/1",
])
def test_parser_rejects_unsafe_or_non_pr_urls(value):
    with pytest.raises(InvalidPullRequestURL):
        parse_pull_request_url(value)


def test_parser_accepts_canonical_github_url():
    assert parse_pull_request_url("https://github.com/owner/repo/pull/42?tab=files") == ("owner", "repo", 42)
    assert parse_pull_request_url("https://github.com/owner/repo/pull/42#diff") == ("owner", "repo", 42)


def test_patch_parser_tracks_added_removed_and_context_lines():
    parsed = parse_patch({"filename": "a.py", "previous_filename": "old.py", "status": "renamed", "additions": 1, "deletions": 1, "patch": "@@ -4,2 +4,2 @@ def f():\n keep\n-old\n+new"})
    assert parsed["previous_path"] == "old.py" and parsed["truncated"] is False
    assert parsed["hunks"][0]["lines"] == [
        {"kind": "context", "line": 4, "text": "keep"},
        {"kind": "removed", "line": 5, "text": "old"},
        {"kind": "added", "line": 5, "text": "new"},
    ]


def test_patch_parser_marks_missing_patch_as_truncated():
    assert parse_patch({"filename": "image.png", "status": "added"})["truncated"] is True


def test_github_client_uses_fixed_host_and_maps_rate_limit():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(403, headers={"X-RateLimit-Remaining": "0"}, json={"message": "rate limit"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
            with pytest.raises(GitHubAPIError) as error:
                await request_json(client, "/repos/owner/repo/pulls/1")
        return error.value

    exc = asyncio.run(run())
    assert exc.status_code == 429
    assert requests[0].url.host == "api.github.com"
