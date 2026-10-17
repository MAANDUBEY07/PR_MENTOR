# PR Mentor backend

FastAPI service for the current React client and the PR Mentor review/learning API. Demo review data is deterministic and explicitly marked `is_demo: true`; it never claims to analyze the submitted repository. Live mode retrieves the GitHub pull request, runs installed static analyzers on supported Python files, and optionally requests LLM review candidates.

## Run locally

From the repository root:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs`. The Vite client runs from `frontend/` with `npm run dev`; set `VITE_API_BASE_URL=http://127.0.0.1:8000` in `frontend/.env.local` (the current client appends `/api`).

## Configuration

Demo mode requires no credentials. Set explicit comma-separated `FRONTEND_ORIGINS` for CORS. Public GitHub pull requests can be fetched without a token; `GITHUB_TOKEN` is optional and must be a server-side token. MongoDB is optional and `MONGODB_URI`/`MONGODB_DATABASE` enable connectivity/readiness checks; history and saved records currently use temporary in-process storage and are lost on restart. `LLM_PROVIDER` set to a non-`none` value together with `LLM_API_KEY`, `LLM_MODEL`, and optional `LLM_BASE_URL` enables the OpenAI-compatible candidate adapter; no LLM is enabled by default. Never place server credentials in frontend `VITE_` variables.

OTP routes preserve the existing frontend contract: `POST /api/auth/otp/send` and `/api/auth/otp/verify`. Development `PR_MENTOR_OTP_MODE=demo` returns a clearly labeled demo code; it is rejected in production. SMTP and Twilio message delivery can be configured with the variables shown in `.env.example`. In-memory challenge/session records are temporary and this demo token store is not a production identity system.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health`, `/api/health/ready` | Liveness/readiness |
| POST | `/api/reviews/analyze` | `{ "url": "https://github.com/owner/repo/pull/42" }`; defaults to labeled demo. Pass `mode: "live"` for GitHub metadata retrieval. |
| GET | `/api/reviews/{review_id}` | Retrieve an in-process review |
| GET | `/api/reviews/history` | Recent in-process reviews |
| GET/POST | `/api/reviews/saved` | List/save temporary PR links |
| DELETE | `/api/reviews/saved/{saved_id}` | Remove saved link |
| GET | `/api/reviews/{review_id}/diff` | Changed-file patch summaries (available for the process lifetime) |
| GET | `/api/learning/exercises` | List safe exercise descriptions (answers withheld) |
| GET | `/api/learning/exercises/{exercise_id}` | Read an exercise |
| POST | `/api/learning/exercises/{exercise_id}/submit` | Submit `{ "answer": "..." }` |
| GET | `/api/learning/progress`, `/api/learning/history` | Temporary session progress |
| POST | `/api/auth/otp/send`, `/api/auth/otp/verify` | Existing optional OTP demo/delivery flow |

Analyze responses include `pull_request`, structured `findings`, `verification_summary`, `tool_results`, `warnings`, and `is_demo`. Top-level legacy fields `repository`, `pull_request_title`, `pull_request_number`, `url`, and finding fields `file`, `line`, `text`, and `proof` are also supplied for the current frontend.

## Security and limits

GitHub URLs must be HTTPS `github.com` pull-request URLs. API requests are built only from validated owner/repository/number components; arbitrary URLs are never fetched. The backend does not execute repository code. Live retrieval uses GitHub's first 100 changed files; up to 20 supported Python file contents are fetched with a 100 KB per-file cap and analyzed in temporary directories when Ruff and Bandit are installed. Tests are not executed. Diffs, history, and saved records are temporary process-local data and are lost on restart. Demo findings are fictional educational samples. OTP throttling and state are process-local, and authentication is not enforced on review/history endpoints. MongoDB connectivity/readiness is available when configured, but durable repository persistence and ownership controls are not yet wired into those endpoints.

## Checks

From `backend/`: `pytest -q` and `ruff check app tests`. External integrations require credentials/configuration and should be exercised with mocked tests in a future integration suite; no credentials are needed for demo use.
