"""drop_location_description

Revision ID: 989120a6387f
Revises: 2a7de58569a0
Create Date: 2026-02-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '989120a6387f'
down_revision: Union[str, Sequence[str], None] = '2a7de58569a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('locations') as batch_op:
        batch_op.drop_column('description')


def downgrade() -> None:
    with op.batch_alter_table('locations') as batch_op:
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
