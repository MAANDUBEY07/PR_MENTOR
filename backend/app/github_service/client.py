"""Narrow HTTP boundary for GitHub's public REST API."""

from typing import Any

import httpx

from app.config import github_token, http_timeout

API_ROOT = "https://api.github.com"


class GitHubAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def headers() -> dict[str, str]:
    result = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = github_token()
    if token:
        result["Authorization"] = f"Bearer {token}"
    return result


async def request_json(client: httpx.AsyncClient, path: str, *, params: dict[str, Any] | None = None) -> Any:
    if not path.startswith("/") or path.startswith("//") or ".." in path.split("/"):
        raise ValueError("GitHub API paths must be relative to the fixed API host.")
    try:
        response = await client.get(f"{API_ROOT}{path}", params=params, headers=headers())
    except httpx.TimeoutException as exc:
        raise GitHubAPIError("GitHub did not respond in time.") from exc
    except httpx.RequestError as exc:
        raise GitHubAPIError("GitHub is temporarily unavailable.") from exc
    if response.status_code >= 400:
        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            raise GitHubAPIError("GitHub API rate limit reached.", 429)
        message = "GitHub rejected the request."
        try:
            body = response.json()
            if isinstance(body, dict) and isinstance(body.get("message"), str):
                message = body["message"]
        except (ValueError, TypeError):
            pass
        raise GitHubAPIError(message, response.status_code)
    try:
        return response.json()
    except (ValueError, TypeError) as exc:
        raise GitHubAPIError("GitHub returned malformed JSON.", 502) from exc


def async_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=http_timeout(), follow_redirects=False)
