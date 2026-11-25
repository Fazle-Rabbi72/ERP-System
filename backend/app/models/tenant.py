"""Tenant model (one company/organisation in cloud or the single tenant in on-prem)."""

from sqlalchemy import Boolean, CheckConstraint, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBaseModel


class Tenant(TenantBaseModel):
    """Represents a tenant company.

    Inherits `TenantBaseModel` with the invariant `tenant_id = id` so that the
    same RLS policy applies uniformly to every table in the database.
    """

    __tablename__ = "tenants"
    __table_args__ = (CheckConstraint("tenant_id = id", name="self_tenant_id"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
