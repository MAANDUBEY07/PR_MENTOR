"""Validated GitHub pull request data returned by the ingestion boundary."""

from pydantic import BaseModel, ConfigDict, Field


class PullRequestMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository_owner: str
    repository_name: str
    repository_url: str
    pull_request_number: int = Field(gt=0)
    pull_request_url: str
    title: str
    description: str | None = None
    author: str | None = None
    base_branch: str | None = None
    head_branch: str | None = None
    head_sha: str | None = None
    state: str
    changed_files: int = Field(ge=0)
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)


class ChangedFile(BaseModel):
    filename: str
    status: str
    additions: int = Field(default=0, ge=0)
    deletions: int = Field(default=0, ge=0)
    changes: int = Field(default=0, ge=0)
    previous_filename: str | None = None
    patch: str | None = None
    size: int | None = Field(default=None, ge=0)


class PullRequestBundle(BaseModel):
    metadata: PullRequestMetadata
    files: list[ChangedFile]
    warnings: list[str] = Field(default_factory=list)
