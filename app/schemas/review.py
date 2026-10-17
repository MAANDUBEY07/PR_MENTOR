from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.finding import ReviewFinding
from app.schemas.github import PullRequestMetadata

class AnalyzeRequest(BaseModel):
    url: str | None = None
    pull_request_url: str | None = None
    mode: str = "demo"
    include_learning: bool = True

class ReviewResponse(BaseModel):
    review_id: str
    status: str
    analysis_mode: str
    is_demo: bool
    pull_request: PullRequestMetadata
    summary: str
    findings: list[ReviewFinding] = Field(default_factory=list)
    verification_summary: dict[str, int]
    tool_results: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime
    duration_ms: int = 0
