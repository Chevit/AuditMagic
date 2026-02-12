"""Rename item notes to details

Revision ID: 5b4692bfcfab
Revises: 251cd8f1299d
Create Date: 2026-02-10 17:12:52.738810

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "5b4692bfcfab"
down_revision: Union[str, Sequence[str], None] = "251cd8f1299d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: rename items.notes to items.details."""
    with op.batch_alter_table("items") as batch_op:
        batch_op.alter_column("notes", new_column_name="details")


def downgrade() -> None:
    """Downgrade schema: rename items.details back to items.notes."""
    with op.batch_alter_table("items") as batch_op:
        batch_op.alter_column("details", new_column_name="notes")
