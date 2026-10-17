"""Review pipeline coordination helpers."""
from app.verification.normalizer import verify_finding, verification_counts

def finalize_findings(candidates, files, diagnostics=None):
    normalized=[]
    seen=set()
    for finding in candidates:
        key=(finding.file_path, finding.line_start, finding.title.casefold())
        if key in seen: continue
        seen.add(key)
        normalized.append(verify_finding(finding, files, diagnostics))
    return normalized, verification_counts(normalized)
