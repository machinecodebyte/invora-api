"""Inventory tables.

Revision ID: 202607050005
Revises: 202607050004
Create Date: 2026-07-05 18:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607050005"
down_revision: str | None = "202607050004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("current_stock", sa.Numeric(14, 3), nullable=False),
        sa.Column("minimum_stock", sa.Numeric(14, 3), nullable=False),
        sa.Column("safety_stock", sa.Numeric(14, 3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "product_id",
            name="uq_inventory_items_user_product",
        ),
    )
    op.create_index(
        op.f("ix_inventory_items_product_id"),
        "inventory_items",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_items_user_id"),
        "inventory_items",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "inventory_stock_movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
        sa.Column("movement_type", sa.String(length=32), nullable=False),
        sa.Column("quantity_delta", sa.Numeric(14, 3), nullable=False),
        sa.Column("quantity_before", sa.Numeric(14, 3), nullable=False),
        sa.Column("quantity_after", sa.Numeric(14, 3), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("reference_type", sa.String(length=64), nullable=True),
        sa.Column("reference_id", sa.String(length=128), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["inventory_items.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_inventory_stock_movements_inventory_item_id"),
        "inventory_stock_movements",
        ["inventory_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_stock_movements_movement_type"),
        "inventory_stock_movements",
        ["movement_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_stock_movements_occurred_at"),
        "inventory_stock_movements",
        ["occurred_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_stock_movements_product_id"),
        "inventory_stock_movements",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_stock_movements_user_id"),
        "inventory_stock_movements",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_inventory_stock_movements_user_id"),
        table_name="inventory_stock_movements",
    )
    op.drop_index(
        op.f("ix_inventory_stock_movements_product_id"),
        table_name="inventory_stock_movements",
    )
    op.drop_index(
        op.f("ix_inventory_stock_movements_occurred_at"),
        table_name="inventory_stock_movements",
    )
    op.drop_index(
        op.f("ix_inventory_stock_movements_movement_type"),
        table_name="inventory_stock_movements",
    )
    op.drop_index(
        op.f("ix_inventory_stock_movements_inventory_item_id"),
        table_name="inventory_stock_movements",
    )
    op.drop_table("inventory_stock_movements")
    op.drop_index(
        op.f("ix_inventory_items_user_id"),
        table_name="inventory_items",
    )
    op.drop_index(
        op.f("ix_inventory_items_product_id"),
        table_name="inventory_items",
    )
    op.drop_table("inventory_items")
