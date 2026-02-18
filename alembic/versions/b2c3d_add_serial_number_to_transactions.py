"""Add serial_number to transactions.

Revision ID: b2c3d
Revises: a1b2c
Create Date: 2026-02-18 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2c3d"
down_revision: Union[str, Sequence[str], None] = "a1b2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add serial_number column to transactions table."""
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.add_column(sa.Column("serial_number", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Remove serial_number column from transactions table."""
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_column("serial_number")
