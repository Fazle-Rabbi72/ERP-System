"""Reusable pagination, sorting, and filtering helpers for list endpoints.

All sort and filter columns are strictly allow-listed so client query
parameters can never reference arbitrary columns or inject SQL.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Literal, Protocol

from fastapi import Query
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.roles import ExpressionElementRole

from app.core.exceptions import BadRequestError, JsonValue

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

SortDirection = Literal["asc", "desc"]
FilterOperator = Literal["eq", "ilike", "gte", "lte", "in"]


class SortableColumn(Protocol):
    """Any SQLAlchemy column expression supporting `.asc()` and `.desc()`."""

    def asc(self) -> ExpressionElementRole[object]: ...
    def desc(self) -> ExpressionElementRole[object]: ...


@dataclass(frozen=True, slots=True)
class PaginationParams:
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass(frozen=True, slots=True)
class SortParams:
    sort_by: str | None = None
    sort_dir: SortDirection = "desc"


def get_pagination_params(
    page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_SIZE, description="Items per page (1-100)"),
    ] = DEFAULT_PAGE_SIZE,
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


def get_sort_params(
    sort_by: Annotated[str | None, Query(description="Field name to sort by")] = None,
    sort_dir: Annotated[SortDirection, Query(description="Sort direction: asc or desc")] = "desc",
) -> SortParams:
    return SortParams(sort_by=sort_by, sort_dir=sort_dir)


def build_order_by(
    sort: SortParams,
    *,
    allowed: Mapping[str, SortableColumn],
    default: Sequence[ExpressionElementRole[object]],
) -> list[ExpressionElementRole[object]]:
    """Build SQLAlchemy ORDER BY clauses from an allow-list of columns."""
    if sort.sort_by is None:
        return list(default)
    column = allowed.get(sort.sort_by)
    if column is None:
        allowed_fields: list[JsonValue] = [*sorted(allowed.keys())]
        raise BadRequestError(
            "Invalid sort field.",
            details={"sort_by": sort.sort_by, "allowed": allowed_fields},
        )
    ordered = column.asc() if sort.sort_dir == "asc" else column.desc()
    return [ordered]


def escape_like(value: str) -> str:
    """Escape SQL LIKE wildcards (`\\`, `%`, `_`) so user search text is literal."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass(frozen=True, slots=True)
class FilterRule:
    """Maps a query value to an allow-listed SQLAlchemy column and operator."""

    column: InstrumentedAttribute[object]
    operator: FilterOperator
    value: object


def build_filters(rules: Sequence[FilterRule]) -> list[ColumnElement[bool]]:
    """Convert non-None allow-listed FilterRules into SQLAlchemy WHERE clauses."""
    clauses: list[ColumnElement[bool]] = []
    for rule in rules:
        if rule.value is None:
            continue
        if rule.operator == "eq":
            clauses.append(rule.column == rule.value)
        elif rule.operator == "ilike":
            if not isinstance(rule.value, str):
                raise BadRequestError("Search filter must be text.")
            escaped = escape_like(rule.value.strip())
            if escaped:
                clauses.append(rule.column.ilike(f"%{escaped}%", escape="\\"))
        elif rule.operator == "gte":
            clauses.append(rule.column >= rule.value)
        elif rule.operator == "lte":
            clauses.append(rule.column <= rule.value)
        elif rule.operator == "in":
            if not isinstance(rule.value, Sequence) or isinstance(rule.value, str | bytes):
                raise BadRequestError("List filter must be a sequence.")
            if len(rule.value) > 0:
                clauses.append(rule.column.in_(rule.value))
    return clauses
