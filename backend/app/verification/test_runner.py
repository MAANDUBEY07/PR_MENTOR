"""Safe placeholder for test execution until an isolated runner is configured."""

from typing import Any


def run_tests(*, target: str | None = None, command: str | None = None) -> dict[str, Any]:
    """Report that tests are unavailable; never execute supplied code or commands."""
    del target, command  # Inputs are intentionally not executed or interpreted.
    return {
        "status": "unavailable",
        "executed": False,
        "message": "PR tests are unavailable until an isolated container or sandbox runner is configured.",
        "findings": [],
    }
