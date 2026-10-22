 member-3-ai-review
"""Review API routes."""

from app.ai_review.client import AIConfigurationError, AIProviderError
from app.github_service.client import GitHubServiceError
from app.github_service.pull_requests import ingest_pull_request
from app.schemas.review import ReviewAnalyzeRequest, ReviewResponse
from app.services.review_orchestrator import run_review
from fastapi import APIRouter, HTTPException

"""Stable review API consumed by the frontend."""

from fastapi import APIRouter, HTTPException, Query

from app.database.reviews import get_store
from app.github_service.client import GitHubAPIError
from app.github_service.parser import InvalidPullRequestURL
from app.schemas.review import AnalyzeRequest, DiffResponse, ReviewResponse, SavedPullRequestRequest
from app.services.review_orchestrator import analyze
 main

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("/analyze", response_model=ReviewResponse)
member-3-ai-review
def analyze_pull_request(request: ReviewAnalyzeRequest) -> ReviewResponse:
    """Analyze a public GitHub PR URL and return the frontend response shape."""
    try:
        payload = ingest_pull_request(request.url)
        return run_review(payload)
    except GitHubServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except AIConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail="AI review is not configured. Set AI_API_KEY and AI_MODEL.",
        ) from exc
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

async def analyze_review(payload: AnalyzeRequest):
    try:
        return await analyze(payload)
    except InvalidPullRequestURL as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GitHubAPIError as exc:
        status = exc.status_code
        if status is None:
            status = 503
        elif status == 404:
            status = 404
        elif status == 429:
            status = 429
        elif status == 401:
            status = 401
        elif status == 403:
            status = 403
        elif status >= 500:
            status = 502
        else:
            status = 502
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="GitHub returned data that could not be processed.") from exc
    except Exception as exc:
        # Keep implementation details and local paths out of the public response.
        raise HTTPException(status_code=503, detail="Review could not be completed or persisted.") from exc


@router.get("/history", response_model=list[ReviewResponse])
def history(limit: int = Query(default=50, ge=1, le=100)):
    try:
        return get_store().list_reviews(limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Review history is unavailable.") from exc


@router.get("/saved")
def saved_pull_requests():
    try:
        return get_store().list_saved()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Saved pull requests are unavailable.") from exc


@router.post("/saved", status_code=201)
def save_pull_request(payload: SavedPullRequestRequest):
    url = payload.pull_request_url or payload.url or ""
    try:
        from app.github_service.parser import parse_pull_request_url

        owner, repo, number = parse_pull_request_url(url)
    except InvalidPullRequestURL as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    canonical_url = f"https://github.com/{owner}/{repo}/pull/{number}"
    try:
        return get_store().save_pull_request(canonical_url)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Pull request could not be saved.") from exc


@router.delete("/saved/{saved_id}")
def delete_saved_pull_request(saved_id: str):
    try:
        deleted = get_store().delete_saved(saved_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Saved pull requests are unavailable.") from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved pull request not found.")
    return {"deleted": True}


@router.get("/{review_id}/diff", response_model=DiffResponse)
def review_diff(review_id: str):
    try:
        review = get_store().get_review(review_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Review data is unavailable.") from exc
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    return {"review_id": review_id, "files": review.get("diff_files", []), "warnings": review.get("warnings", [])}


@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(review_id: str):
    try:
        review = get_store().get_review(review_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Review data is unavailable.") from exc
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    return review
 main
