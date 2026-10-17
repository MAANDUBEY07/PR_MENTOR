# PR Mentor backend

FastAPI service for the frontend review workspace. API schemas and routes are the stable boundary; ingestion, analysis, AI, and storage implementations can be replaced behind their current interfaces.

## Run locally

From this directory, create and activate a virtual environment, install dependencies, and start the service:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Copy `.env.example` to `.env` and export the desired values in the shell (the service intentionally does not load dotenv files implicitly). `PR_MENTOR_DATABASE_PATH` defaults to `backend/data/pr_mentor.sqlite3`. `GITHUB_TOKEN` is optional. AI needs both `LLM_API_KEY` and `LLM_MODEL`; the OpenAI-compatible endpoint may be changed with `LLM_API_BASE_URL`. `PR_MENTOR_CORS_ORIGINS` is a comma-separated allowlist. `PR_MENTOR_HTTP_TIMEOUT` is bounded to 1–60 seconds.

Run tests from this directory with `python -m pytest -q`. Tests use temporary SQLite files and mock external services; they need no GitHub token, LLM key, or production database.

## API contracts

- `GET /api/health` is a liveness check; `GET /api/health/ready` verifies SQLite can open.
- `POST /api/reviews/analyze` accepts `{ "url": "https://github.com/owner/repo/pull/42", "mode": "demo" | "live", "include_learning": true }`. `pull_request_url` is also accepted for compatibility. Responses use `schemas/review.py` and `schemas/finding.py`, including explicit `is_demo`, analysis provenance, tool statuses, warnings, verification counts, and diff files.
- `GET /api/reviews/history?limit=50`, `GET /api/reviews/{review_id}`, and `GET /api/reviews/{review_id}/diff` read persisted review records.
- `GET /api/reviews/saved`, `POST /api/reviews/saved` with `{ "url": "..." }`, and `DELETE /api/reviews/saved/{saved_id}` manage saved PR links.
- `GET /api/learning/exercises`, `GET /api/learning/exercises/{exercise_id}`, `POST /api/learning/exercises/{exercise_id}/submit` with `{ "answer": "..." }`, `GET /api/learning/progress`, and `GET /api/learning/history` serve authored exercises and persistent progress. Answers are omitted until submission.
- `POST /api/auth/otp/send` and `POST /api/auth/otp/verify` currently return 503 because secure OTP delivery and challenge storage are not configured. They never log or accept a fake demo code.

FastAPI validation and HTTP errors use the standard `{ "detail": ... }` shape consumed by the frontend. Fixed paths are declared before dynamic review IDs.

## Module boundaries and team ownership

The public request/response schemas in `app/schemas/` and route paths above are shared contracts. Keep them stable while replacing internals.

- **Member 1 — GitHub ingestion:** `app/github_service/parser.py`, `client.py`, `pull_requests.py`, and `files.py`. `parse_pull_request_url()` validates a GitHub PR URL; `fetch_pull_request()` returns a `PullRequestBundle` with typed metadata, statuses, and patches. Requests go only to the fixed GitHub API host, use timeouts, paginate with a cap, and report upstream failures explicitly.
- **Member 2 — static analysis and verification:** `app/verification/`. `path_validation.py` is a security boundary: retain its checkout containment and symlink checks. Ruff and Bandit consume only Python files materialized into a temporary directory. `test_runner.py` reports unavailable; PR code is never executed on the host.
- **Member 3 — AI review:** `app/ai_review/client.py`, `prompts.py`, and `reviewer.py`. Replace the OpenAI-compatible transport behind `complete_json()` while keeping `generate_candidates()` schema-validating and provider-independent. Credentials are environment-only. Missing credentials and provider errors produce unavailable tool status, never fabricated AI findings.
- **Integration owner:** `app/services/review_orchestrator.py` coordinates modules and partial failures. `app/routes/`, `app/schemas/`, `app/database/`, and `app/main.py` own the API, persistence boundary, and application configuration. Coordinate contract changes here rather than having module owners independently change routes or frontend types.

## Runtime behavior and security

Demo mode returns stable educational findings labelled with source `demo`; it does not fetch or analyze the submitted repository. Live mode fetches GitHub metadata and diffs, retrieves at most 20 bounded Python files, runs available static analyzers in a temporary workspace, and includes AI findings only when configured. Tests are not run; the response explicitly says so. Tool unavailability creates `partial` status and warnings. The submitted repository URL is parsed and restricted to HTTPS `github.com`; server requests use a fixed `api.github.com` base to avoid arbitrary outbound destinations.

SQLite is the replaceable `ReviewStore` implementation. Reviews, saved PR links, and learning attempts survive process restarts. A failed database write returns an API error; the service does not claim success. Before production deployment, configure managed storage, secrets, rate limiting, and an isolated runner if test execution is ever introduced. OTP authentication remains unavailable until secure delivery, hashed challenges, expiry, throttling, and persistent session handling are designed and tested.

The orchestration layer has no dependency on the nested backend repository from Ritik's fork. `backend/` is an ordinary tracked directory in this canonical repository.
