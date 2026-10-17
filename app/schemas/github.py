from pydantic import BaseModel

class PullRequestMetadata(BaseModel):
    repository_owner: str
    repository_name: str
    repository_url: str
    pull_request_number: int
    pull_request_url: str
    title: str
    description: str = ""
    author: str
    base_branch: str
    head_branch: str
    head_sha: str
    state: str
    changed_files: int = 0
    additions: int = 0
    deletions: int = 0
