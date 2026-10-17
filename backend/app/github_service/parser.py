"""Parse public GitHub pull-request URLs without making network requests."""

import re
from urllib.parse import urlsplit


class InvalidPullRequestURL(ValueError):
    """The submitted value is not a supported GitHub pull request URL."""


_SEGMENT = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


def parse_pull_request_url(value: str) -> tuple[str, str, int]:
    if not isinstance(value, str) or not value.strip():
        raise InvalidPullRequestURL("A pull request URL is required.")
    try:
        parts = urlsplit(value.strip())
        if parts.scheme != "https" or parts.hostname != "github.com" or parts.username or parts.password or parts.port:
            raise ValueError
        segments = parts.path.strip("/").split("/")
        if len(segments) != 4 or segments[2].lower() != "pull":
            raise ValueError
        owner, repo, _, raw_number = segments
        if not _SEGMENT.fullmatch(owner) or not _SEGMENT.fullmatch(repo) or owner in {".", ".."} or repo in {".", ".."}:
            raise ValueError
        if not raw_number.isascii() or not raw_number.isdigit() or int(raw_number) < 1:
            raise ValueError
    except (ValueError, UnicodeError) as exc:
        raise InvalidPullRequestURL("Use an https://github.com/{owner}/{repo}/pull/{number} URL.") from exc
    return owner, repo.removesuffix(".git"), int(raw_number)
