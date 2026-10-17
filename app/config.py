"""Environment loading and small typed settings object."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

def load_dotenv_file() -> None:
    path = Path(__file__).resolve().parents[1] / ".env"
    if not path.is_file(): return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line=raw.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        key,value=line.split("=",1)
        key=key.strip(); value=value.strip().strip('"').strip("'")
        if key and key.replace("_", "").isalnum(): os.environ.setdefault(key,value)

load_dotenv_file()

@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "PR Mentor API")
    app_env: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true" and os.getenv("APP_ENV", "development").lower() not in {"production", "prod"}
    demo_mode: bool = os.getenv("DEMO_MODE", "true").lower() == "true"
    api_prefix: str = os.getenv("API_PREFIX", "/api")
    frontend_origins: tuple[str, ...] = tuple(x.strip() for x in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip())

settings = Settings()
