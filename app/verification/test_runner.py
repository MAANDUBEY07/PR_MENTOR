"""PR Mentor never executes tests from untrusted pull-request repositories."""
def inspect_ci_evidence(checks: list[dict] | None = None) -> dict:
    checks = checks or []
    return {"tool":"trusted_ci","status":"observed" if checks else "unavailable","executed":False,"checks":checks,"message":"Only GitHub-provided check metadata is reported; submitted repository code is never executed."}
