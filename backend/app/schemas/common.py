"""The single response envelope used by every endpoint.

The frontend therefore has exactly one success shape and one error shape to
handle, instead of a different contract per endpoint.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorBody(BaseModel):
    code: str = Field(examples=["INVALID_INPUT"])
    message: str
    details: list[ErrorDetail] = []
    request_id: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorBody


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T


class PageMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    meta: PageMeta


def envelope(data: Any) -> dict[str, Any]:
    return {"success": True, "data": data}
