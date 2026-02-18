"""Add item_type_id to transactions and make item_id nullable

Revision ID: d4e5f_add_item_type_id_to_transactions
Revises: c3d4e_remove_item_notes
Create Date: 2026-02-18
"""

from alembic import op
import sqlalchemy as sa

revision = 'd4e5f_add_item_type_id_to_transactions'
down_revision = 'c3d4e_remove_item_notes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('transactions') as batch_op:
        batch_op.add_column(sa.Column('item_type_id', sa.Integer(), nullable=True))
        batch_op.alter_column('item_id', nullable=True)
        batch_op.create_index('ix_transactions_item_type_id', ['item_type_id'])
        batch_op.create_foreign_key(
            'fk_transactions_item_type_id',
            'item_types',
            ['item_type_id'],
            ['id'],
        )

    # Back-fill item_type_id from the items table for existing transactions
    op.execute("""
        UPDATE transactions
        SET item_type_id = (
            SELECT item_type_id FROM items WHERE items.id = transactions.item_id
        )
        WHERE item_id IS NOT NULL
    """)


def downgrade() -> None:
    with op.batch_alter_table('transactions') as batch_op:
        batch_op.drop_constraint('fk_transactions_item_type_id', type_='foreignkey')
        batch_op.drop_index('ix_transactions_item_type_id')
        batch_op.drop_column('item_type_id')
        batch_op.alter_column('item_id', nullable=False)
