"""Run Bandit in JSON mode and return parsed, tool-native findings."""

import json
import subprocess
from pathlib import Path
from typing import Any, Sequence

from .path_validation import validate_python_files
from .ruff_runner import ToolExecutionError


def _path(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return Path(value.replace("\\", "/")).as_posix()


def _positive_line(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def run_bandit(
    paths: Sequence[str], timeout: float = 30, executable: str = "bandit", *, root: str | Path
) -> list[dict[str, Any]]:
    """Run Bandit on validated checkout files without a shell.

    Exit 1 is a normal findings result. Absolute validated paths cannot be
    interpreted as options, including files whose names begin with ``-``.
    """
    target_paths = validate_python_files(paths, root)
    command = [executable, "-f", "json", *target_paths]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise ToolExecutionError(f"Bandit executable not found: {executable}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolExecutionError(f"Bandit timed out after {timeout} seconds") from exc
    except OSError as exc:
        raise ToolExecutionError(f"Bandit could not be started: {exc}") from exc
    if completed.returncode not in (0, 1):
        stderr = completed.stderr if isinstance(completed.stderr, str) else ""
        raise ToolExecutionError(f"Bandit failed with exit code {completed.returncode}: {stderr.strip()}")
    try:
        data = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as exc:
        raise ToolExecutionError("Bandit returned malformed JSON") from exc
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ToolExecutionError("Bandit JSON output must contain a results list")
    results = []
    for item in data["results"]:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        if isinstance(code, str):
            evidence = code.rstrip("\r\n") or None
        elif isinstance(code, list):
            lines = [line.rstrip("\r\n") for line in code if isinstance(line, str)]
            evidence = "\n".join(lines).rstrip("\r\n") or None
        else:
            evidence = None
        rule_id = item.get("test_id")
        message = item.get("issue_text")
        severity = item.get("issue_severity")
        results.append({
            "file_path": _path(item.get("filename")),
            "line": _positive_line(item.get("line_number")),
            "rule_id": rule_id if isinstance(rule_id, str) else None,
            "message": message if isinstance(message, str) else "",
            "severity": severity if isinstance(severity, str) else None,
            "evidence": evidence,
        })
    return results
