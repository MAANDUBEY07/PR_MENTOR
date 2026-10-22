"""Run Ruff in JSON mode and return parsed, tool-native findings."""

import json
import subprocess
from pathlib import Path
from typing import Any, Sequence

from .path_validation import validate_python_files


class ToolExecutionError(RuntimeError):
    """A static-analysis tool could not run or returned invalid output."""


def _path(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return Path(value.replace("\\", "/")).as_posix()


def _positive_line(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def run_ruff(
    paths: Sequence[str], timeout: float = 30, executable: str = "ruff", *, root: str | Path
) -> list[dict[str, Any]]:
    """Run Ruff on validated checkout files without a shell.

    Ruff exit 1 means findings were detected. Absolute validated paths cannot
    be interpreted as options, including files whose names begin with ``-``.
    """
    target_paths = validate_python_files(paths, root)
    command = [executable, "check", "--output-format", "json", *target_paths]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise ToolExecutionError(f"Ruff executable not found: {executable}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolExecutionError(f"Ruff timed out after {timeout} seconds") from exc
    except OSError as exc:
        raise ToolExecutionError(f"Ruff could not be started: {exc}") from exc
    if completed.returncode not in (0, 1):
        stderr = completed.stderr if isinstance(completed.stderr, str) else ""
        raise ToolExecutionError(f"Ruff failed with exit code {completed.returncode}: {stderr.strip()}")
    try:
        data = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as exc:
        raise ToolExecutionError("Ruff returned malformed JSON") from exc
    if not isinstance(data, list):
        raise ToolExecutionError("Ruff JSON output must be a list")
    results = []
    for item in data:
        if not isinstance(item, dict):
            continue
        location = item.get("location")
        if not isinstance(location, dict):
            location = {}
        code = item.get("code")
        message = item.get("message")
        source = item.get("source_code")
        if not isinstance(source, str):
            source = item.get("cell")
        results.append({
            "file_path": _path(item.get("filename")),
            "line": _positive_line(location.get("row")),
            "rule_id": code if isinstance(code, str) else None,
            "message": message if isinstance(message, str) else "",
            "evidence": source if isinstance(source, str) else None,
        })
    return results
