"""Shared response envelopes: consistent error format and pagination metadata."""

import math

from pydantic import BaseModel, Field

from app.core.exceptions import JsonValue


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, JsonValue] = Field(default_factory=dict)
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PageMeta(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_next: bool
    has_prev: bool


class PaginatedResponse[ItemT](BaseModel):
    """Uniform paginated list response returned by every list API endpoint."""

    items: list[ItemT]
    meta: PageMeta

    @classmethod
    def create(
        cls,
        *,
        items: list[ItemT],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[ItemT]":
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        return cls(
            items=items,
            meta=PageMeta(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1 and total_pages > 0,
            ),
        )
