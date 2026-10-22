import httpx
import pytest
from app.github_service.client import GitHubClient, GitHubServiceError
from app.github_service.files import fetch_pull_request_files
from app.github_service.parser import parse_pull_request_url
from app.github_service.pull_requests import ingest_pull_request


def sample_pr_response():
    return {
        "number": 12,
        "title": "Improve parser",
        "body": "Handle edge cases",
        "state": "open",
        "html_url": "https://github.com/acme/widget/pull/12",
        "user": {"login": "contributor"},
        "base": {"ref": "main", "sha": "base-sha"},
        "head": {"ref": "fix/parser", "sha": "head-sha"},
        "changed_files": 1,
    }


def sample_file_response():
    return {
        "filename": "src/parser.py",
        "previous_filename": None,
        "status": "modified",
        "additions": 2,
        "deletions": 1,
        "changes": 3,
        "sha": "file-sha",
        "patch": "@@ -1,2 +1,3 @@\n+return True",
    }


def test_parse_pull_request_url_accepts_github_tabs():
    coords = parse_pull_request_url("https://github.com/acme/widget/pull/12/files")

    assert coords.owner == "acme"
    assert coords.repo == "widget"
    assert coords.number == 12


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/acme/widget/pull/12",
        "https://github.com/acme/widget/issues/12",
        "https://evil.example/acme/widget/pull/12",
        "https://github.com/acme/widget/pull/0",
        "https://user@github.com/acme/widget/pull/12",
    ],
)
def test_parse_pull_request_url_rejects_non_pr_or_unsafe_urls(url):
    with pytest.raises(ValueError):
        parse_pull_request_url(url)


def test_ingest_pull_request_builds_agreed_payload():
    def handler(request):
        assert request.headers["Accept"] == "application/vnd.github+json"
        if request.url.path.endswith("/pulls/12"):
            return httpx.Response(200, json=sample_pr_response())
        if request.url.path.endswith("/pulls/12/files"):
            assert request.url.params["per_page"] == "100"
            assert request.url.params["page"] == "1"
            return httpx.Response(200, json=[sample_file_response()])
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        payload = ingest_pull_request(
            "https://github.com/acme/widget/pull/12",
            client=GitHubClient(http_client=http_client, token="test-token"),
        )

    assert payload["pull_request"] == {
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
    }
    assert payload["files"] == [
        {
            **sample_file_response(),
            "source_content": None,
            "content_unavailable_reason": None,
        }
    ]
    assert payload["files_truncated"] is False


def test_ingest_marks_file_list_truncated_at_page_limit():
    class FullPageClient:
        def get_json(self, path, *, params):
            assert path.endswith("/pulls/12/files")
            return [sample_file_response()] * 100

    files, truncated = fetch_pull_request_files(
        FullPageClient(), "acme", "widget", 12, max_pages=1
    )

    assert len(files) == 100
    assert truncated is True


def test_github_404_is_reported_without_leaking_request_details():
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(404))
    ) as http_client:
        client = GitHubClient(http_client=http_client, token="secret-token")

        with pytest.raises(GitHubServiceError, match="not found") as error:
            client.get_json("/repos/acme/widget/pulls/12")

    assert error.value.status_code == 404
    assert "secret-token" not in str(error.value)


def test_malformed_pull_request_response_is_an_upstream_error():
    class MalformedResponseClient:
        def get_json(self, _path, *, params=None):
            return {}

    with pytest.raises(GitHubServiceError, match="malformed") as error:
        ingest_pull_request(
            "https://github.com/acme/widget/pull/12",
            client=MalformedResponseClient(),
        )

    assert error.value.status_code == 502

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
