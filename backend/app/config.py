"""Small environment-backed configuration for the API service."""

import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def database_path() -> Path:
    value = os.getenv("PR_MENTOR_DATABASE_PATH")
    return Path(value).expanduser().resolve() if value else BACKEND_ROOT / "data" / "pr_mentor.sqlite3"


def cors_origins() -> list[str]:
    value = os.getenv("PR_MENTOR_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in value.split(",") if origin.strip()]


def http_timeout() -> float:
    return max(1.0, min(float(os.getenv("PR_MENTOR_HTTP_TIMEOUT", "15")), 60.0))


def github_token() -> str | None:
    return os.getenv("GITHUB_TOKEN") or None


def llm_configuration() -> tuple[str | None, str | None, str]:
    return os.getenv("LLM_API_KEY") or None, os.getenv("LLM_MODEL") or None, os.getenv("LLM_API_BASE_URL", "https://api.openai.com/v1/chat/completions")
