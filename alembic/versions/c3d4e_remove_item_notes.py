"""Remove notes column from items table

Revision ID: c3d4e_remove_item_notes
Revises: b2c3d_add_serial_number_to_transactions
Create Date: 2026-02-18
"""

from alembic import op
import sqlalchemy as sa

revision = 'c3d4e_remove_item_notes'
down_revision = 'b2c3d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('items') as batch_op:
        batch_op.drop_column('notes')


def downgrade() -> None:
    with op.batch_alter_table('items') as batch_op:
        batch_op.add_column(sa.Column('notes', sa.Text(), nullable=True))
