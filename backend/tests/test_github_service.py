import base64
from pathlib import Path

import httpx
import pytest

from app.github_service.client import (
    GitHubAccessError,
    GitHubAPIError,
    GitHubClient,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from app.github_service.files import UnsafeChangedFilePathError, stage_python_files
from app.github_service.parser import InvalidPullRequestURLError, parse_pull_request_url
from app.github_service.pull_requests import get_pull_request
from app.schemas.github import ChangedFile


def make_client(handler):
    return GitHubClient(http_client=httpx.Client(
        base_url="https://api.github.com",
        transport=httpx.MockTransport(handler),
    ))


def pr_response():
    return {
        "title": "Improve parser",
        "body": "Handle edge cases",
        "state": "open",
        "html_url": "https://github.com/acme/widget/pull/12",
        "user": {"login": "contributor"},
        "base": {
            "ref": "main",
            "sha": "base-sha",
            "repo": {"name": "widget"},
        },
        "head": {"ref": "fix/parser", "sha": "head-sha"},
        "changed_files": 1,
    }


def test_parse_github_pull_request_url():
    parsed = parse_pull_request_url("https://github.com/acme/widget/pull/12?tab=files")
    assert parsed.owner == "acme"
    assert parsed.repo == "widget"
    assert parsed.number == 12


@pytest.mark.parametrize("url", [
    "",
    "http://github.com/acme/widget/pull/12",
    "https://github.com.evil.test/acme/widget/pull/12",
    "https://example.com/acme/widget/pull/12",
    "https://github.com/acme/widget/issues/12",
    "https://user:password@github.com/acme/widget/pull/12",
    "https://github.com/acme/widget/pull/0",
])
def test_reject_invalid_pull_request_urls(url):
    with pytest.raises(InvalidPullRequestURLError):
        parse_pull_request_url(url)


def test_get_pull_request_handles_pagination_patchless_file_and_source_content():
    source = "def run():\n    return True\n"
    encoded = base64.b64encode(source.encode()).decode()
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("/pulls/12"):
            return httpx.Response(200, json=pr_response())
        if request.url.path.endswith("/pulls/12/files"):
            return httpx.Response(200, json=[{
                "filename": "src/parser.py",
                "status": "modified",
                "additions": 2,
                "deletions": 1,
                "changes": 3,
                "sha": "file-sha",
                # GitHub may omit patches for large or binary diffs.
            }])
        if request.url.path.endswith("/contents/src/parser.py"):
            assert request.url.params["ref"] == "head-sha"
            return httpx.Response(200, json={
                "type": "file",
                "encoding": "base64",
                "size": len(source),
                "content": encoded,
            })
        raise AssertionError(f"Unexpected request: {request.url}")

    result = get_pull_request(
        "https://github.com/acme/widget/pull/12",
        client=make_client(handler),
    )

    assert result.pull_request.head_sha == "head-sha"
    assert result.pull_request.base_ref == "main"
    assert result.files_truncated is False
    assert len(result.files) == 1
    assert result.files[0].filename == "src/parser.py"
    assert result.files[0].patch is None
    assert result.files[0].source_content == source
    assert len(requests) == 3


def test_file_list_follows_link_pagination():
    def handler(request):
        if request.url.path == "/repos/acme/widget/pulls/12/files" and request.url.params.get("page") != "2":
            return httpx.Response(
                200,
                json=[{"filename": "one.py"}],
                headers={"Link": '<https://api.github.com/repos/acme/widget/pulls/12/files?page=2>; rel="next"'},
            )
        if request.url.params.get("page") == "2":
            return httpx.Response(200, json=[{"filename": "two.py"}])
        raise AssertionError(f"Unexpected request: {request.url}")

    client = make_client(handler)
    result = client.get_paginated("/repos/acme/widget/pulls/12/files", max_items=5)
    assert [item["filename"] for item in result] == ["one.py", "two.py"]


@pytest.mark.parametrize("status,headers,body,error", [
    (404, {}, {"message": "Not Found"}, GitHubNotFoundError),
    (403, {}, {"message": "Resource not accessible by integration"}, GitHubAccessError),
    (429, {"Retry-After": "30"}, {"message": "rate limit exceeded"}, GitHubRateLimitError),
])
def test_github_errors_are_translated(status, headers, body, error):
    client = make_client(lambda request: httpx.Response(status, headers=headers, json=body))
    with pytest.raises(error) as caught:
        client.get_json("/repos/acme/widget/pulls/12")
    if error is GitHubRateLimitError:
        assert caught.value.retry_after_seconds == 30


def test_removed_file_does_not_fetch_head_content():
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/pulls/12"):
            data = pr_response()
            data["changed_files"] = 1
            return httpx.Response(200, json=data)
        if request.url.path.endswith("/pulls/12/files"):
            return httpx.Response(200, json=[{
                "filename": "src/gone.py",
                "status": "removed",
                "additions": 0,
                "deletions": 5,
                "changes": 5,
                "patch": "@@ -1,5 +0,0 @@",
            }])
        raise AssertionError(f"Unexpected request: {request.url}")

    result = get_pull_request("https://github.com/acme/widget/pull/12", client=make_client(handler))
    assert len(calls) == 2
    assert result.files[0].source_content is None
    assert result.files[0].content_unavailable_reason == "deleted_in_head"


def test_api_client_does_not_follow_foreign_pagination_url():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("/files"):
            return httpx.Response(
                200,
                json=[],
                headers={"Link": '<https://attacker.example/steal-token>; rel="next"'},
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    client = make_client(handler)
    with pytest.raises(GitHubAPIError, match="unsafe pagination URL"):
        client.get_paginated("/repos/acme/widget/pulls/12/files")
    assert len(requests) == 1


def test_stage_python_files_returns_temp_paths_and_cleans_them_up():
    files = [
        ChangedFile(
            filename="src/review.py",
            status="modified",
            additions=1,
            deletions=0,
            changes=1,
            source_content="print('review')\n",
        ),
        ChangedFile(
            filename="README.md",
            status="modified",
            additions=1,
            deletions=0,
            changes=1,
            source_content="# docs\n",
        ),
        ChangedFile(
            filename="src/removed.py",
            status="removed",
            additions=0,
            deletions=2,
            changes=2,
            source_content=None,
        ),
    ]

    with stage_python_files(files) as paths:
        assert len(paths) == 1
        staged_file = Path(paths[0])
        assert staged_file.name == "review.py"
        assert staged_file.read_text(encoding="utf-8") == "print('review')\n"
        staging_root = staged_file.parents[1]
    assert not staging_root.exists()


@pytest.mark.parametrize("filename", [
    "../outside.py",
    "/absolute/path.py",
    "C:/absolute/path.py",
    "nested\\windows.py",
])
def test_stage_python_files_rejects_unsafe_paths(filename):
    file = ChangedFile(
        filename=filename,
        status="modified",
        additions=1,
        deletions=0,
        changes=1,
        source_content="print('unsafe')\n",
    )
    with pytest.raises(UnsafeChangedFilePathError), stage_python_files([file]):
        pass
