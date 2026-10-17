from typing import Literal
from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low", "informational"]
Category = Literal["bug", "security", "performance", "maintainability", "code_quality", "testing", "documentation", "learning"]
Verification = Literal["verified", "needs_review", "unsupported"]

class ReviewFinding(BaseModel):
    id: str
    title: str
    description: str
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    severity: Severity
    category: Category
    confidence: float = Field(ge=0, le=1)
    source: Literal["static_analysis", "ai_candidate", "test_evidence", "combined"]
    verification_status: Verification
    evidence: list[str] = Field(default_factory=list)
    why_it_matters: str
    suggested_fix: str
    learning_explanation: str
    limitations: list[str] = Field(default_factory=list)
