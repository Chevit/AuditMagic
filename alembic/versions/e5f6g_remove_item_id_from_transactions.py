"""Remove item_id from transactions and make item_type_id NOT NULL

Revision ID: e5f6g_remove_item_id_from_transactions
Revises: d4e5f_add_item_type_id_to_transactions
Create Date: 2026-02-18

Transactions are now related to ItemType, not Item.
The item_type_id column becomes the sole required FK.
"""

from alembic import op
import sqlalchemy as sa

revision = 'e5f6g_remove_item_id_from_transactions'
down_revision = 'd4e5f_add_item_type_id_to_transactions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove orphaned transaction rows that have no item_type_id
    # (can happen if item was deleted before the item_type_id back-fill ran)
    op.execute("DELETE FROM transactions WHERE item_type_id IS NULL")

    with op.batch_alter_table('transactions') as batch_op:
        batch_op.drop_column('item_id')
        batch_op.alter_column('item_type_id', nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('transactions') as batch_op:
        batch_op.alter_column('item_type_id', nullable=True)
        batch_op.add_column(sa.Column('item_id', sa.Integer(), nullable=True))
