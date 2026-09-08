"""Pydantic request/response contracts.

Schemas are the API's public surface: every response is declared here so that
OpenAPI documentation, client generation and validation stay in step with the
implementation.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIModel(BaseModel):
    """Base for all schemas: ORM-friendly, strict about unknown fields."""

    model_config = ConfigDict(from_attributes=True, extra="forbid", populate_by_name=True)


class Page(BaseModel, Generic[T]):
    """A page of results."""

    items: list[T]
    total: int = Field(description="Total matching records, ignoring pagination.")
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        """Whether further pages exist."""
        return self.offset + len(self.items) < self.total


class ErrorDetail(BaseModel):
    """The body of an error envelope."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None


class ErrorResponse(BaseModel):
    """Every non-2xx response has this shape."""

    error: ErrorDetail


class MessageResponse(BaseModel):
    """A simple acknowledgement."""

    message: str
