"""Small, read-only GitHub REST API client with bounded error reporting."""

import os
import time
from typing import Any
from urllib.parse import urlsplit

import httpx

API_BASE_URL = "https://api.github.com"
API_VERSION = "2026-03-10"
MAX_PULL_REQUEST_FILES = 3000


class GitHubServiceError(RuntimeError):
    """Base class for errors safe to translate at the API boundary."""


class GitHubAuthenticationError(GitHubServiceError):
    """GitHub rejected the supplied credentials."""


class GitHubAccessError(GitHubServiceError):
    """The token cannot access the repository or required endpoint."""


class GitHubNotFoundError(GitHubServiceError):
    """The PR is missing or inaccessible (GitHub may hide private resources)."""


class GitHubRateLimitError(GitHubServiceError):
    """GitHub rate-limited the request; retry_after_seconds may be present."""

    def __init__(self, message: str, retry_after_seconds: int | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class GitHubNetworkError(GitHubServiceError):
    """A timeout or network failure prevented a GitHub API request."""


class GitHubAPIError(GitHubServiceError):
    """GitHub returned an unexpected response."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def _retry_after(headers: httpx.Headers) -> int | None:
    value = headers.get("retry-after")
    if value:
        try:
            return max(0, int(value))
        except ValueError:
            pass

    reset_at = headers.get("x-ratelimit-reset")
    if reset_at and headers.get("x-ratelimit-remaining") == "0":
        try:
            return max(0, int(reset_at) - int(time.time()))
        except ValueError:
            return None
    return None


class GitHubClient:
    """Read-only API client. Inject an httpx client for deterministic tests."""

    def __init__(
        self,
        token: str | None = None,
        *,
        http_client: httpx.Client | None = None,
        timeout: float = 20.0,
    ) -> None:
        self._owns_client = http_client is None
        self.http = http_client or httpx.Client(
            base_url=API_BASE_URL,
            timeout=timeout,
            follow_redirects=False,
        )
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "PR-Mentor",
        }
        credential = token if token is not None else os.getenv("GITHUB_TOKEN")
        if credential and credential.strip():
            self.headers["Authorization"] = f"Bearer {credential.strip()}"

    def close(self) -> None:
        if self._owns_client:
            self.http.close()

    @staticmethod
    def _safe_target(path_or_url: str) -> str:
        if path_or_url.startswith("/") and not path_or_url.startswith("//"):
            return path_or_url
        try:
            parsed = urlsplit(path_or_url)
            port = parsed.port
        except ValueError as exc:
            raise GitHubAPIError(0, "GitHub returned an unsafe pagination URL") from exc
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api.github.com"
            or port not in (None, 443)
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise GitHubAPIError(0, "GitHub returned an unsafe pagination URL")
        return path_or_url

    def get_json(self, path_or_url: str, *, params: dict[str, Any] | None = None) -> Any:
        """GET JSON from GitHub and translate expected failures to typed errors."""
        target = self._safe_target(path_or_url)

        try:
            response = self.http.get(target, params=params, headers=self.headers)
        except httpx.TimeoutException as exc:
            raise GitHubNetworkError("GitHub API request timed out") from exc
        except httpx.RequestError as exc:
            raise GitHubNetworkError("Could not connect to the GitHub API") from exc

        self._raise_for_response(response)
        try:
            return response.json()
        except ValueError as exc:
            raise GitHubAPIError(response.status_code, "GitHub returned invalid JSON") from exc

    @staticmethod
    def _next_link(link_header: str | None) -> str | None:
        if not link_header:
            return None
        for link in link_header.split(","):
            parts = link.split(";")
            if any(part.strip() == 'rel="next"' for part in parts[1:]):
                target = parts[0].strip()
                if target.startswith("<") and target.endswith(">"):
                    return target[1:-1]
        return None

    def get_paginated(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        max_items: int = MAX_PULL_REQUEST_FILES,
    ) -> list[Any]:
        """Read a GitHub Link-paginated list, capped to avoid unbounded work."""
        results: list[Any] = []
        target = path
        page_params = dict(params or {})
        page_params.setdefault("per_page", 100)

        while target and len(results) < max_items:
            target = self._safe_target(target)
            try:
                response = self.http.get(
                    target,
                    params=page_params or None,
                    headers=self.headers,
                )
            except httpx.TimeoutException as exc:
                raise GitHubNetworkError("GitHub API request timed out") from exc
            except httpx.RequestError as exc:
                raise GitHubNetworkError("Could not connect to the GitHub API") from exc

            self._raise_for_response(response)
            try:
                page = response.json()
            except ValueError as exc:
                raise GitHubAPIError(response.status_code, "GitHub returned invalid JSON") from exc
            if not isinstance(page, list):
                raise GitHubAPIError(response.status_code, "GitHub returned an invalid file list")

            results.extend(page[: max_items - len(results)])
            target = self._next_link(response.headers.get("link"))
            page_params = {}  # Link URLs already contain their pagination query.

        return results

    @staticmethod
    def _raise_for_response(response: httpx.Response) -> None:
        """Translate status errors from a response already obtained."""
        if not response.is_error:
            return
        if response.status_code == 401:
            raise GitHubAuthenticationError("GitHub rejected the token; check GITHUB_TOKEN")
        if response.status_code == 404:
            raise GitHubNotFoundError(
                "Pull request was not found or the token cannot access this repository"
            )
        if response.status_code in (403, 429):
            try:
                body = response.json()
            except ValueError:
                body = {}
            message = body.get("message", "") if isinstance(body, dict) else ""
            if (
                response.status_code == 429
                or response.headers.get("x-ratelimit-remaining") == "0"
                or "rate limit" in str(message).lower()
                or "abuse detection" in str(message).lower()
            ):
                raise GitHubRateLimitError(
                    "GitHub API rate limit reached",
                    retry_after_seconds=_retry_after(response.headers),
                )
            raise GitHubAccessError(
                "The GitHub token lacks permission to read this pull request or its contents"
            )
        raise GitHubAPIError(response.status_code, f"GitHub API returned HTTP {response.status_code}")
