"""Validate Python analyzer targets against an explicitly supplied checkout."""

from collections.abc import Sequence
from pathlib import Path


class PathValidationError(ValueError):
    """A requested analysis target is not a safe Python file in the checkout."""


def validate_python_files(paths: Sequence[str | Path], root: str | Path) -> list[str]:
    """Return absolute target paths after checking checkout containment.

    Resolving targets before containment checks also rejects symlinks that point
    outside the checkout. Absolute paths are accepted only when they resolve
    beneath the explicitly supplied root.
    """
    if not isinstance(root, (str, Path)) or not str(root):
        raise PathValidationError("repository root must be a non-empty path")
    if isinstance(paths, (str, bytes)) or not isinstance(paths, Sequence) or not paths:
        raise PathValidationError("targets must be a non-empty sequence of Python file paths")

    try:
        resolved_root = Path(root).resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise PathValidationError(f"repository root cannot be resolved: {root}") from exc
    if not resolved_root.is_dir():
        raise PathValidationError(f"repository root is not a directory: {root}")

    validated: list[str] = []
    for raw_path in paths:
        if not isinstance(raw_path, (str, Path)) or not str(raw_path):
            raise PathValidationError("each target must be a non-empty string or Path")
        try:
            candidate = Path(raw_path)
            if not candidate.is_absolute():
                candidate = resolved_root / candidate
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError, ValueError) as exc:
            raise PathValidationError(f"target cannot be resolved: {raw_path}") from exc

        try:
            resolved.relative_to(resolved_root)
        except ValueError as exc:
            raise PathValidationError(f"target is outside the repository root: {raw_path}") from exc

        if not resolved.is_file():
            raise PathValidationError(f"target is not a file: {raw_path}")
        if resolved.suffix.lower() != ".py":
            raise PathValidationError(f"target is not a Python file: {raw_path}")
        validated.append(str(resolved))

    return validated
