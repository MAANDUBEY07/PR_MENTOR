import os
import httpx
import base64
from urllib.parse import quote

class GitHubAPIError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(message)

async def get_json(path: str):
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0), follow_redirects=False) as client:
        response = await client.get(f"https://api.github.com/{path.lstrip('/')}", headers=headers)
    if response.status_code >= 400:
        message = "GitHub rate limit exceeded." if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0" else "GitHub could not provide this pull request. Check its URL and access permissions."
        raise GitHubAPIError(response.status_code, message)
    return response.json()

async def get_file_content(owner: str, repo: str, path: str, ref: str) -> str | None:
    encoded_path = quote(path, safe="/")
    try:
        payload = await get_json(f"repos/{owner}/{repo}/contents/{encoded_path}?ref={quote(ref, safe='')}")
        if payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str): return None
        decoded = base64.b64decode(payload["content"], validate=False)
        return decoded[:100_000].decode("utf-8", errors="replace")
    except (GitHubAPIError, ValueError):
        return None
