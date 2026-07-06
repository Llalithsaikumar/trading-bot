"""
Shared Pydantic base schemas and reusable types.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from datetime import datetime

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Root schema — all schemas inherit from this."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TimestampSchema(BaseSchema):
    created_at: datetime
    updated_at: datetime


class PaginatedResponse[T](BaseSchema):
    """Generic paginated list response envelope."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def from_list(
        cls, items: list[T], total: int, page: int, page_size: int
    ) -> PaginatedResponse[T]:
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=-(-total // page_size),  # ceiling division
        )


class MessageResponse(BaseSchema):
    """Simple message envelope for non-data responses."""

    message: str
    detail: dict[str, Any] | None = None


class ErrorResponse(BaseSchema):
    """Standard error response body."""

    error: str
    code: str
    detail: dict[str, Any] | None = None
