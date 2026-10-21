
"""Request and response schemas for the PR review API."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.finding import Finding
from app.schemas.github import PullRequestMetadata


class AnalyzeRequest(BaseModel):
    """Request to analyze a GitHub pull request."""

    url: str | None = None
    pull_request_url: str | None = None
    mode: Literal["demo", "live"] = "demo"
    include_learning: bool = True

    @model_validator(mode="after")
    def require_pull_request_url(self) -> "AnalyzeRequest":
        if not (self.pull_request_url or self.url):
            raise ValueError("A pull request URL is required.")
        return self


class ReviewResponse(BaseModel):
    """Review result returned by the API."""

    review_id: str
    status: Literal["completed", "partial"]
    analysis_mode: Literal["demo", "live"]
    is_demo: bool
    pull_request: PullRequestMetadata
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    verification_summary: dict[str, int] = Field(default_factory=dict)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime
    duration_ms: int = Field(default=0, ge=0)
    diff_files: list[dict[str, Any]] = Field(default_factory=list)


class DiffLine(BaseModel):
    """One parsed line in a pull-request diff."""

    kind: Literal["added", "removed", "context"]
    line: int = Field(ge=0)
    text: str


class DiffHunk(BaseModel):
    """A diff section with its original header and lines."""

    header: str
    lines: list[DiffLine] = Field(default_factory=list)


class DiffFile(BaseModel):
    """Parsed diff data for one changed file."""

    path: str
    previous_path: str | None = None
    status: str
    added: int = Field(default=0, ge=0)
    removed: int = Field(default=0, ge=0)
    hunks: list[DiffHunk] = Field(default_factory=list)
    truncated: bool = False


class DiffResponse(BaseModel):
    """Diff data returned for a saved review."""

    review_id: str
    files: list[DiffFile]
    warnings: list[str] = Field(default_factory=list)
