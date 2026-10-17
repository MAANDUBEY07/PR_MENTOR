from uuid import uuid4
from app.ai_review.client import complete_json
from app.ai_review.prompts import review_prompt
from app.schemas.finding import ReviewFinding

async def generate_candidates(files: list[dict]) -> list[ReviewFinding]:
    result = await complete_json(review_prompt(files))
    candidates = []
    for raw in result.get("findings", [])[:50]:
        raw = dict(raw)
        raw.setdefault("id", uuid4().hex)
        raw.setdefault("confidence", 0.5)
        raw["source"] = "ai_candidate"
        raw["verification_status"] = "needs_review"
        raw.setdefault("evidence", [])
        candidates.append(ReviewFinding.model_validate(raw))
    return candidates
