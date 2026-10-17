from app.schemas.finding import ReviewFinding

def verify_finding(finding: ReviewFinding, changed_files: list[dict], diagnostics: list[dict] | None = None) -> ReviewFinding:
    diagnostics = diagnostics or []
    matching = [d for d in diagnostics if d.get("file_path") == finding.file_path and (not finding.line_start or d.get("line") == finding.line_start)]
    patch = next((f.get("patch", "") for f in changed_files if f.get("filename") == finding.file_path), "")
    if matching:
        finding.verification_status = "verified"
        finding.source = "combined"
        finding.evidence.extend([f"Analyzer diagnostic {d.get('code', 'finding')}: {d.get('message', '')}" for d in matching])
    elif not patch:
        finding.verification_status = "unsupported"
        finding.limitations.append("No matching changed-file patch was available to substantiate this claim.")
    else:
        finding.verification_status = "needs_review"
        finding.evidence.append("Finding refers to a changed file; no matching static diagnostic was available. AI confidence is not verification.")
    return finding

def verification_counts(findings):
    return {status: sum(item.verification_status == status for item in findings) for status in ("verified", "needs_review", "unsupported")}
