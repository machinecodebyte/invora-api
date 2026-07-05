"""Product catalog tables.

Revision ID: 202607050004
Revises: 202607050003
Create Date: 2026-07-05 16:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607050004"
down_revision: str | None = "202607050003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "normalized_name",
            name="uq_product_categories_user_normalized_name",
        ),
    )
    op.create_index(
        op.f("ix_product_categories_user_id"),
        "product_categories",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("normalized_sku", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("selling_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("cost_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["product_categories.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "normalized_sku",
            name="uq_products_user_normalized_sku",
        ),
    )
    op.create_index(
        op.f("ix_products_category_id"),
        "products",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_products_normalized_name"),
        "products",
        ["normalized_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_products_normalized_sku"),
        "products",
        ["normalized_sku"],
        unique=False,
    )
    op.create_index(
        op.f("ix_products_user_id"),
        "products",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_products_user_id"), table_name="products")
    op.drop_index(op.f("ix_products_normalized_sku"), table_name="products")
    op.drop_index(op.f("ix_products_normalized_name"), table_name="products")
    op.drop_index(op.f("ix_products_category_id"), table_name="products")
    op.drop_table("products")
    op.drop_index(
        op.f("ix_product_categories_user_id"),
        table_name="product_categories",
    )
    op.drop_table("product_categories")
