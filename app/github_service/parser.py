from urllib.parse import urlparse
import re

class InvalidPullRequestURL(ValueError):
    pass

def parse_pull_request_url(url: str) -> tuple[str, str, int]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"} or parsed.port or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise InvalidPullRequestURL("Enter a valid HTTPS GitHub pull request URL.")
    parts = parsed.path.strip("/").split("/")
    if len(parts) != 4 or parts[2] != "pull" or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", parts[0]) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", parts[1]) or not parts[3].isdigit() or int(parts[3]) < 1:
        raise InvalidPullRequestURL("Enter a valid GitHub URL in the form /owner/repository/pull/123.")
    return parts[0], parts[1], int(parts[3])
