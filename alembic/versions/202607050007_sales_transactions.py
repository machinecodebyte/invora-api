"""Sales transaction management fields.

Revision ID: 202607050007
Revises: 202607050006
Create Date: 2026-07-07 13:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607050007"
down_revision: str | None = "202607050006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sales_transactions",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sales_transactions",
        sa.Column("deleted_reason", sa.String(length=1000), nullable=True),
    )
    op.create_index(
        op.f("ix_sales_transactions_source"),
        "sales_transactions",
        ["source"],
        unique=False,
    )
    op.create_index(
        "ix_sales_transactions_user_sale_date",
        "sales_transactions",
        ["user_id", "sale_date"],
        unique=False,
    )
    op.create_index(
        "ix_sales_transactions_user_product_sale_date",
        "sales_transactions",
        ["user_id", "product_id", "sale_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_sales_transactions_user_product_sale_date",
        table_name="sales_transactions",
    )
    op.drop_index(
        "ix_sales_transactions_user_sale_date",
        table_name="sales_transactions",
    )
    op.drop_index(
        op.f("ix_sales_transactions_source"),
        table_name="sales_transactions",
    )
    op.drop_column("sales_transactions", "deleted_reason")
    op.drop_column("sales_transactions", "deleted_at")
