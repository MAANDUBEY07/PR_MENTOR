"""Typed GitHub pull request data returned by the ingestion service."""


from pydantic import BaseModel, Field


class PullRequestReference(BaseModel):
    """Repository coordinates parsed from a canonical GitHub PR URL."""

    owner: str
    repo: str
    number: int = Field(gt=0)


class PullRequestMetadata(BaseModel):
    """Metadata needed to identify and review a pull request revision."""

    owner: str
    repo: str
    number: int = Field(gt=0)
    title: str
    body: str | None = None
    state: str
    html_url: str
    author: str | None = None
    base_ref: str
    base_sha: str
    head_ref: str
    head_sha: str
    changed_files: int = Field(ge=0)


class ChangedFile(BaseModel):
    """A changed path, diff patch, and optional content at the PR head."""

    filename: str
    previous_filename: str | None = None
    status: str
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    changes: int = Field(ge=0)
    sha: str | None = None
    patch: str | None = None
    source_content: str | None = None
    content_unavailable_reason: str | None = None


class PullRequestData(BaseModel):
    """Complete ingestion result for one pull request."""

    pull_request: PullRequestMetadata
    files: list[ChangedFile]
    files_truncated: bool = False
