"""Sales upload tables.

Revision ID: 202607050006
Revises: 202607050005
Create Date: 2026-07-07 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607050006"
down_revision: str | None = "202607050005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sales_upload_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("accepted_rows", sa.Integer(), nullable=False),
        sa.Column("rejected_rows", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sales_upload_batches_file_hash"),
        "sales_upload_batches",
        ["file_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sales_upload_batches_status"),
        "sales_upload_batches",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sales_upload_batches_user_id"),
        "sales_upload_batches",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "sales_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("upload_batch_id", sa.Uuid(), nullable=True),
        sa.Column("sale_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("channel", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["upload_batch_id"],
            ["sales_upload_batches.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sales_transactions_product_id"),
        "sales_transactions",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sales_transactions_sale_date"),
        "sales_transactions",
        ["sale_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sales_transactions_upload_batch_id"),
        "sales_transactions",
        ["upload_batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sales_transactions_user_id"),
        "sales_transactions",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "sales_upload_rejected_rows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("upload_batch_id", sa.Uuid(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["upload_batch_id"],
            ["sales_upload_batches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sales_upload_rejected_rows_upload_batch_id"),
        "sales_upload_rejected_rows",
        ["upload_batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sales_upload_rejected_rows_user_id"),
        "sales_upload_rejected_rows",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_sales_upload_rejected_rows_user_id"),
        table_name="sales_upload_rejected_rows",
    )
    op.drop_index(
        op.f("ix_sales_upload_rejected_rows_upload_batch_id"),
        table_name="sales_upload_rejected_rows",
    )
    op.drop_table("sales_upload_rejected_rows")
    op.drop_index(
        op.f("ix_sales_transactions_user_id"),
        table_name="sales_transactions",
    )
    op.drop_index(
        op.f("ix_sales_transactions_upload_batch_id"),
        table_name="sales_transactions",
    )
    op.drop_index(
        op.f("ix_sales_transactions_sale_date"),
        table_name="sales_transactions",
    )
    op.drop_index(
        op.f("ix_sales_transactions_product_id"),
        table_name="sales_transactions",
    )
    op.drop_table("sales_transactions")
    op.drop_index(
        op.f("ix_sales_upload_batches_user_id"),
        table_name="sales_upload_batches",
    )
    op.drop_index(
        op.f("ix_sales_upload_batches_status"),
        table_name="sales_upload_batches",
    )
    op.drop_index(
        op.f("ix_sales_upload_batches_file_hash"),
        table_name="sales_upload_batches",
    )
    op.drop_table("sales_upload_batches")
