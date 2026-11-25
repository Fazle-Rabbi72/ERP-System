"""Unit tests for pagination, sorting, and filtering helpers."""

import pytest

from app.core.exceptions import BadRequestError
from app.core.query import (
    FilterRule,
    PaginationParams,
    SortParams,
    build_filters,
    build_order_by,
    escape_like,
)
from app.models.tenant import Tenant
from app.schemas.common import PaginatedResponse

pytestmark = pytest.mark.unit


def test_pagination_params_offset_and_limit() -> None:
    params = PaginationParams(page=3, page_size=25)
    assert params.offset == 50
    assert params.limit == 25


def test_paginated_response_metadata() -> None:
    page1 = PaginatedResponse[str].create(items=["a", "b"], total=5, page=1, page_size=2)
    assert page1.meta.total_pages == 3
    assert page1.meta.has_prev is False
    assert page1.meta.has_next is True

    page3 = PaginatedResponse[str].create(items=["e"], total=5, page=3, page_size=2)
    assert page3.meta.has_prev is True
    assert page3.meta.has_next is False

    empty = PaginatedResponse[str].create(items=[], total=0, page=1, page_size=20)
    assert empty.meta.total_pages == 0
    assert empty.meta.has_prev is False
    assert empty.meta.has_next is False


def test_build_order_by_uses_default_and_validates_allowlist() -> None:
    allowed = {"name": Tenant.name, "code": Tenant.code}
    default = [Tenant.created_at.desc()]

    assert build_order_by(SortParams(), allowed=allowed, default=default) == default

    asc_clauses = build_order_by(
        SortParams(sort_by="name", sort_dir="asc"),
        allowed=allowed,
        default=default,
    )
    assert "ASC" in str(asc_clauses[0])

    desc_clauses = build_order_by(
        SortParams(sort_by="code", sort_dir="desc"),
        allowed=allowed,
        default=default,
    )
    assert "DESC" in str(desc_clauses[0])

    with pytest.raises(BadRequestError) as excinfo:
        build_order_by(
            SortParams(sort_by="password_hash", sort_dir="asc"),
            allowed=allowed,
            default=default,
        )
    assert excinfo.value.details["allowed"] == ["code", "name"]


def test_escape_like_escapes_sql_wildcards() -> None:
    assert escape_like(r"100%_test\ok") == r"100\%\_test\\ok"


def test_build_filters_handles_operators_and_skips_none() -> None:
    clauses = build_filters(
        [
            FilterRule(column=Tenant.is_active, operator="eq", value=True),
            FilterRule(column=Tenant.name, operator="ilike", value="  Nex_zen%  "),
            FilterRule(column=Tenant.code, operator="eq", value=None),
            FilterRule(column=Tenant.code, operator="in", value=["a", "b"]),
        ]
    )
    assert len(clauses) == 3
    rendered = str(clauses[1])
    assert "LIKE" in rendered
    assert "ESCAPE" in rendered


def test_build_filters_rejects_invalid_in_value() -> None:
    with pytest.raises(BadRequestError):
        build_filters([FilterRule(column=Tenant.code, operator="in", value="not-a-list")])
