"""Initial schema (squashed baseline).

Revision ID: a1b2c
Revises:
Create Date: 2026-02-15 21:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create full initial schema."""
    op.create_table(
        "item_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sub_type", sa.String(length=255), nullable=True),
        sa.Column("is_serialized", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "sub_type", name="uq_item_type_name_subtype"),
    )
    op.create_index("ix_item_types_name", "item_types", ["name"], unique=False)
    op.create_index("ix_item_types_sub_type", "item_types", ["sub_type"], unique=False)

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_type_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("serial_number", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("condition", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "(serial_number IS NULL AND quantity > 0) OR (serial_number IS NOT NULL AND quantity = 1)",
            name="check_serial_or_quantity",
        ),
        sa.ForeignKeyConstraint(["item_type_id"], ["item_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("serial_number", name="uq_items_serial_number"),
    )
    op.create_index("ix_items_item_type_id", "items", ["item_type_id"], unique=False)
    op.create_index("ix_items_serial_number", "items", ["serial_number"], unique=False)

    op.create_table(
        "search_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("search_query", sa.String(length=255), nullable=False),
        sa.Column("search_field", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column(
            "transaction_type",
            sa.Enum("ADD", "REMOVE", "EDIT", name="transactiontype"),
            nullable=False,
        ),
        sa.Column("quantity_change", sa.Integer(), nullable=False),
        sa.Column("quantity_before", sa.Integer(), nullable=False),
        sa.Column("quantity_after", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_created_at", "transactions", ["created_at"], unique=False)


def downgrade() -> None:
    """Drop full schema."""
    op.drop_index("ix_transactions_created_at", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("search_history")
    op.drop_index("ix_items_serial_number", table_name="items")
    op.drop_index("ix_items_item_type_id", table_name="items")
    op.drop_table("items")
    op.drop_index("ix_item_types_sub_type", table_name="item_types")
    op.drop_index("ix_item_types_name", table_name="item_types")
    op.drop_table("item_types")
