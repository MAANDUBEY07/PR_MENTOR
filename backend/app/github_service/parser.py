"""Validate and parse canonical GitHub pull request URLs."""

import re
from urllib.parse import urlsplit

from app.schemas.github import PullRequestReference


class InvalidPullRequestURLError(ValueError):
    """The supplied URL is not a supported GitHub pull request URL."""


_SLUG = r"[A-Za-z0-9_.-]+"
_PR_PATH = re.compile(rf"^/({_SLUG})/({_SLUG})/pull/([1-9][0-9]*)/?$")
_ALLOWED_HOSTS = {"github.com", "www.github.com"}


def parse_pull_request_url(url: str) -> PullRequestReference:
    """Return owner/repository/number from a standard GitHub PR URL.

    The API hostname is fixed elsewhere; arbitrary hosts and URL credentials
    are rejected so user input cannot redirect authenticated API requests.
    """
    if not isinstance(url, str) or not url.strip():
        raise InvalidPullRequestURLError("A GitHub pull request URL is required")

    try:
        parsed = urlsplit(url.strip())
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise InvalidPullRequestURLError("The pull request URL is malformed") from exc

    if parsed.scheme != "https" or host not in _ALLOWED_HOSTS or port is not None:
        raise InvalidPullRequestURLError(
            "Use an HTTPS GitHub URL such as https://github.com/owner/repo/pull/123"
        )
    if parsed.username is not None or parsed.password is not None:
        raise InvalidPullRequestURLError("Credentials are not allowed in the pull request URL")

    match = _PR_PATH.fullmatch(parsed.path)
    if not match:
        raise InvalidPullRequestURLError(
            "The URL must point to a pull request: /owner/repo/pull/number"
        )

    owner, repo, number = match.groups()
    return PullRequestReference(owner=owner, repo=repo, number=int(number))
