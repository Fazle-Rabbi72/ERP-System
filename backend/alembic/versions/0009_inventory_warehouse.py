"""Create Inventory & Warehouse tables (warehouses, products, stock_movements) with RLS.

Revision ID: 0009_inventory_warehouse
Revises: 0008_purchase_bills
Create Date: 2026-11-25 18:55:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.rls import rls_disable_statements, rls_enable_statements

revision: str = "0009_inventory_warehouse"
down_revision: str | None = "0008_purchase_bills"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _audit_columns() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "warehouses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=500), server_default="", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_warehouses"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_warehouses_tenant_code"),
    )
    op.create_index("ix_warehouses_tenant_id", "warehouses", ["tenant_id"])
    op.create_index("ix_warehouses_is_deleted", "warehouses", ["is_deleted"])
    op.create_index("ix_warehouses_code", "warehouses", ["code"])

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=32), server_default="pcs", nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("sale_price", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column(
            "reorder_level", sa.Numeric(18, 3), server_default=sa.text("0.000"), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("description", sa.String(length=500), server_default="", nullable=False),
        *_audit_columns(),
        sa.CheckConstraint(
            "unit_cost >= 0 AND sale_price >= 0 AND reorder_level >= 0",
            name="ck_products_non_negative_product_values",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
        sa.UniqueConstraint("tenant_id", "sku", name="uq_products_tenant_sku"),
    )
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])
    op.create_index("ix_products_is_deleted", "products", ["is_deleted"])
    op.create_index("ix_products_sku", "products", ["sku"])

    op.create_table(
        "stock_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_no", sa.String(length=64), nullable=False),
        sa.Column("movement_date", sa.Date(), nullable=False),
        sa.Column("movement_type", sa.String(length=16), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("reference", sa.String(length=128), server_default="", nullable=False),
        sa.Column("notes", sa.String(length=500), server_default="", nullable=False),
        *_audit_columns(),
        sa.CheckConstraint(
            "movement_type IN ('in', 'out', 'adjustment')",
            name="ck_stock_movements_valid_movement_type",
        ),
        sa.CheckConstraint("quantity <> 0", name="ck_stock_movements_non_zero_movement_quantity"),
        sa.CheckConstraint("unit_cost >= 0", name="ck_stock_movements_non_negative_movement_cost"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_stock_movements_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
            name="fk_stock_movements_warehouse_id_warehouses",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stock_movements"),
        sa.UniqueConstraint(
            "tenant_id", "movement_no", name="uq_stock_movements_tenant_movement_no"
        ),
    )
    op.create_index("ix_stock_movements_tenant_id", "stock_movements", ["tenant_id"])
    op.create_index("ix_stock_movements_is_deleted", "stock_movements", ["is_deleted"])
    op.create_index("ix_stock_movements_movement_no", "stock_movements", ["movement_no"])
    op.create_index("ix_stock_movements_movement_date", "stock_movements", ["movement_date"])
    op.create_index("ix_stock_movements_movement_type", "stock_movements", ["movement_type"])
    op.create_index("ix_stock_movements_product_id", "stock_movements", ["product_id"])
    op.create_index("ix_stock_movements_warehouse_id", "stock_movements", ["warehouse_id"])

    for table in ("warehouses", "products", "stock_movements"):
        for statement in rls_enable_statements(table):
            op.execute(statement)


def downgrade() -> None:
    for table in ("stock_movements", "products", "warehouses"):
        for statement in rls_disable_statements(table):
            op.execute(statement)
    op.drop_table("stock_movements")
    op.drop_table("products")
    op.drop_table("warehouses")
