"""Retrieve pull request metadata, changed files, patches, and source text."""

from typing import Any

from app.schemas.github import (
    ChangedFile,
    PullRequestData,
    PullRequestMetadata,
    PullRequestReference,
)

from .client import MAX_PULL_REQUEST_FILES, GitHubAPIError, GitHubClient
from .files import fetch_source_contents, normalize_changed_file
from .parser import parse_pull_request_url


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise GitHubAPIError(200, f"GitHub pull request response is missing {field}")
    return value


def _metadata(reference: PullRequestReference, data: Any) -> PullRequestMetadata:
    if not isinstance(data, dict):
        raise GitHubAPIError(200, "GitHub returned an invalid pull request response")
    base = data.get("base")
    head = data.get("head")
    if not isinstance(base, dict) or not isinstance(base.get("repo"), dict):
        raise GitHubAPIError(200, "GitHub pull request response is missing base repository data")
    if not isinstance(head, dict):
        raise GitHubAPIError(200, "GitHub pull request response is missing head data")
    base_repo = base["repo"].get("name")
    if isinstance(base_repo, str) and base_repo.casefold() != reference.repo.casefold():
        raise GitHubAPIError(200, "GitHub pull request repository does not match the URL")

    author = data.get("user")
    author_login = author.get("login") if isinstance(author, dict) else None
    changed_files = data.get("changed_files", 0)
    if isinstance(changed_files, bool) or not isinstance(changed_files, int) or changed_files < 0:
        raise GitHubAPIError(200, "GitHub returned an invalid changed-file count")

    return PullRequestMetadata(
        owner=reference.owner,
        repo=reference.repo,
        number=reference.number,
        title=_required_text(data.get("title"), "title"),
        body=data.get("body") if isinstance(data.get("body"), str) else None,
        state=_required_text(data.get("state"), "state"),
        html_url=_required_text(data.get("html_url"), "html_url"),
        author=author_login if isinstance(author_login, str) else None,
        base_ref=_required_text(base.get("ref"), "base.ref"),
        base_sha=_required_text(base.get("sha"), "base.sha"),
        head_ref=_required_text(head.get("ref"), "head.ref"),
        head_sha=_required_text(head.get("sha"), "head.sha"),
        changed_files=changed_files,
    )


def get_pull_request(
    url: str,
    *,
    token: str | None = None,
    client: GitHubClient | None = None,
    include_source: bool = True,
) -> PullRequestData:
    """Fetch one GitHub PR using a validated URL.

    The supplied client remains caller-owned. If no client is supplied, this
    function creates and closes one for the duration of the operation.
    """
    reference = parse_pull_request_url(url)
    owns_client = client is None
    api = client or GitHubClient(token=token)
    try:
        prefix = f"/repos/{reference.owner}/{reference.repo}/pulls/{reference.number}"
        metadata = _metadata(reference, api.get_json(prefix))
        raw_files = api.get_paginated(
            f"{prefix}/files",
            params={"per_page": 100},
            max_items=MAX_PULL_REQUEST_FILES,
        )
        files: list[ChangedFile] = [normalize_changed_file(item) for item in raw_files]
        if include_source:
            fetch_source_contents(api, reference, metadata.head_sha, files)
        return PullRequestData(
            pull_request=metadata,
            files=files,
            files_truncated=metadata.changed_files > len(files),
        )
    finally:
        if owns_client:
            api.close()
