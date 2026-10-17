from datetime import datetime, timezone
import os
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.data.sample_reviews import sample_review
from app.database import reviews as store
from app.github_service.parser import InvalidPullRequestURL, parse_pull_request_url
from app.github_service.pull_requests import fetch_pull_request
from app.github_service.client import GitHubAPIError, get_file_content
from app.github_service.files import parse_patch
from app.verification.ruff_runner import run_ruff
from app.verification.bandit_runner import run_bandit
from app.verification.normalizer import verify_finding, verification_counts
from app.schemas.review import AnalyzeRequest

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

@router.post("/analyze")
async def analyze(payload: AnalyzeRequest):
    url = payload.pull_request_url or payload.url
    if not url:
        raise HTTPException(422, "A pull request URL is required.")
    try:
        owner, repo, number = parse_pull_request_url(url)
    except InvalidPullRequestURL as exc:
        raise HTTPException(400, str(exc)) from exc
    if payload.mode not in {"demo", "live"}:
        raise HTTPException(422, "mode must be 'demo' or 'live'.")
    if payload.mode == "demo":
        result = sample_review(submitted_url=url)
        # Preserve compatibility with the current frontend while exposing the richer API shape.
        result["pull_request"]["pull_request_number"] = number
    else:
        try:
            pr, files = await fetch_pull_request(url)
        except GitHubAPIError as exc:
            status = 404 if exc.status_code == 404 else 401 if exc.status_code == 401 else 429 if "rate limit" in str(exc).lower() else 403 if exc.status_code == 403 else 502 if exc.status_code >= 500 else 503
            raise HTTPException(status, str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise HTTPException(504, "GitHub did not respond in time.") from exc
        except httpx.RequestError as exc:
            raise HTTPException(503, "GitHub is temporarily unavailable.") from exc
        findings = []
        warnings = []
        supported = [f for f in files if f.get("patch") and f.get("status") != "removed"]
        if any(f.get("patch") is None for f in files):
            warnings.append("GitHub omitted patch text for one or more changed files.")
        source_files=[]
        for item in files[:20]:
            name=item.get("filename", "")
            if name.endswith(".py") and item.get("status") != "removed" and item.get("size",0) <= 100_000:
                content=await get_file_content(owner,repo,name,(pr.get("head") or {}).get("sha", ""))
                if content is not None: source_files.append({"filename":name,"content":content})
        analyzer_results=[run_ruff(source_files),run_bandit(source_files)]
        diagnostics=[f for result_item in analyzer_results for f in result_item.get("findings",[])]
        for item in diagnostics:
            severity="high" if item["tool"] == "bandit" and item.get("severity") == "HIGH" else "low"
            finding={"id":uuid4().hex,"title":f"{item['tool'].title()} {item.get('code') or 'finding'}","description":item.get("message", "Static analyzer reported a potential issue."),"file_path":item["file_path"],"line_start":item.get("line"),"line_end":item.get("line"),"severity":severity,"category":"security" if item["tool"] == "bandit" else "code_quality","confidence":0.9,"source":"static_analysis","verification_status":"verified","evidence":[f"{item['tool']} {item.get('code')}: {item.get('message','')}"],"why_it_matters":"A static analyzer reported this concrete diagnostic.","suggested_fix":"Review the diagnostic and update the affected code.","learning_explanation":"Static analysis checks code patterns without executing the submitted code.","limitations":[]}
            findings.append(finding)
        tool_results=[{"tool":"github_rest_api","status":"completed","files_received":len(files),"analyzable_patch_files":len(supported)},*analyzer_results]
        if (os.getenv("LLM_PROVIDER", "none").lower() != "none" and os.getenv("LLM_API_KEY") and os.getenv("LLM_MODEL")):
            try:
                from app.ai_review.reviewer import generate_candidates
                candidates=await generate_candidates(files)
                findings.extend([verify_finding(finding,files,diagnostics).model_dump() for finding in candidates])
            except Exception:
                warnings.append("LLM review was unavailable or returned invalid findings; analyzer results are shown without AI candidates.")
        else:
            warnings.append("No configured LLM provider is enabled; AI review candidates were not generated.")
        counts={status:sum((item.get("verification_status") if isinstance(item,dict) else item.verification_status)==status for item in findings) for status in ("verified","needs_review","unsupported")}
        result = {"review_id":uuid4().hex, "status":"completed", "analysis_mode":"live", "is_demo":False,
          "pull_request":{"repository_owner":owner,"repository_name":repo,"repository_url":f"https://github.com/{owner}/{repo}","pull_request_number":number,"pull_request_url":url,"title":pr.get("title", ""),"description":pr.get("body") or "","author":(pr.get("user") or {}).get("login", "unknown"),"base_branch":(pr.get("base") or {}).get("ref", ""),"head_branch":(pr.get("head") or {}).get("ref", ""),"head_sha":(pr.get("head") or {}).get("sha", ""),"state":pr.get("state", "unknown"),"changed_files":pr.get("changed_files",len(files)),"additions":pr.get("additions",0),"deletions":pr.get("deletions",0),"repository":f"{owner}/{repo}","pull_request_title":pr.get("title", ""),"url":url},
          "summary":f"Retrieved {len(files)} changed files and ran available static analysis. Tests were not executed.", "findings":findings, "diff_files":[parse_patch(f) for f in files[:100]], "verification_summary":counts,"tool_results":tool_results,"warnings":warnings,"created_at":datetime.now(timezone.utc),"duration_ms":0}
    _add_legacy_fields(result)
    store.save_review(result)
    return result

@router.get("/history")
async def history(limit: int = Query(50, ge=1, le=100)):
    return store.list_reviews()[:limit]

@router.get("/saved")
async def saved():
    return store.list_saved()

@router.post("/saved", status_code=201)
async def save(payload: AnalyzeRequest):
    url = payload.pull_request_url or payload.url
    if not url:
        raise HTTPException(422, "A pull request URL is required.")
    try:
        parse_pull_request_url(url)
    except InvalidPullRequestURL as exc:
        raise HTTPException(400, str(exc)) from exc
    return store.save_pull_request(url)

@router.delete("/saved/{saved_id}")
async def remove_saved(saved_id: str):
    if not store.delete_saved(saved_id):
        raise HTTPException(404, "Saved pull request not found.")
    return {"deleted": True}

@router.get("/{review_id}/diff")
async def diff(review_id: str):
    review = store.get_review(review_id)
    if not review:
        raise HTTPException(404, "Review not found.")
    return {"review_id":review_id,"files":review.get("diff_files",[]),"warnings":review.get("warnings",[])}

@router.get("/{review_id}")
async def get_review(review_id: str):
    review = store.get_review(review_id)
    if not review:
        raise HTTPException(404, "Review not found.")
    return review

def _add_legacy_fields(result: dict) -> None:
    pr=result["pull_request"]
    result.setdefault("repository",pr.get("repository") or f"{pr['repository_owner']}/{pr['repository_name']}")
    result.setdefault("pull_request_title",pr.get("pull_request_title") or pr["title"])
    result.setdefault("pull_request_number",pr["pull_request_number"])
    result.setdefault("url",pr.get("url") or pr["pull_request_url"])
    for finding in result.get("findings",[]):
        finding.setdefault("file",finding["file_path"])
        finding.setdefault("line",finding.get("line_start") or "—")
        finding.setdefault("text",finding["description"])
        finding.setdefault("proof",finding["evidence"][0] if finding.get("evidence") else "Evidence is insufficient; human review is needed.")
        finding.setdefault("status",finding["verification_status"])
        finding.setdefault("severity_label",finding["severity"].title())
