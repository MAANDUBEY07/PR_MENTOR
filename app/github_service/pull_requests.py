from app.github_service.client import get_json
from app.github_service.parser import parse_pull_request_url

async def fetch_pull_request(url: str):
    owner, repo, number = parse_pull_request_url(url)
    base = f"repos/{owner}/{repo}/pulls/{number}"
    metadata, files = await get_json(base), await get_json(base + "/files?per_page=100")
    return metadata, files
