"""Predictable public error response schema."""

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str | list[dict[str, Any]]
