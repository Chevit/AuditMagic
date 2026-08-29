"""unique_bulk_stock_per_location

Merge duplicate non-serialized item rows per (item_type_id, location_id), then
enforce one row per pair with a partial unique index.

Duplicates were reachable through edit_item location changes and through the
old create_or_merge_item, which merged into a serial-less row at any location.
Merging is a data repair, not a stock movement — the total quantity held is
unchanged, so no Transaction is recorded.

Revision ID: f6g7h
Revises: 989120a6387f
Create Date: 2026-08-29 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6g7h"
down_revision: Union[str, Sequence[str], None] = "989120a6387f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "uq_item_type_location_bulk"


def merge_duplicate_bulk_rows(connection) -> int:
    """Fold every duplicate (item_type_id, location_id) group into its lowest-id row.

    Exposed as a function so it can be tested directly — see
    tests/test_stock_migration.py.

    Returns:
        The number of groups merged.
    """
    duplicates = connection.execute(sa.text("""
            SELECT item_type_id, location_id, MIN(id) AS keep_id, SUM(quantity) AS total
            FROM items
            WHERE serial_number IS NULL AND location_id IS NOT NULL
            GROUP BY item_type_id, location_id
            HAVING COUNT(*) > 1
            """)).fetchall()

    for item_type_id, location_id, keep_id, total in duplicates:
        connection.execute(
            sa.text("UPDATE items SET quantity = :total WHERE id = :keep_id"),
            {"total": total, "keep_id": keep_id},
        )
        connection.execute(
            sa.text("""
                DELETE FROM items
                WHERE serial_number IS NULL
                  AND item_type_id = :item_type_id
                  AND location_id = :location_id
                  AND id != :keep_id
                """),
            {
                "item_type_id": item_type_id,
                "location_id": location_id,
                "keep_id": keep_id,
            },
        )

    return len(duplicates)


def upgrade() -> None:
    merge_duplicate_bulk_rows(op.get_bind())
    op.create_index(
        INDEX_NAME,
        "items",
        ["item_type_id", "location_id"],
        unique=True,
        sqlite_where=sa.text("serial_number IS NULL"),
    )


def downgrade() -> None:
    # The merge cannot be undone: the rows it folded together are gone.
    op.drop_index(INDEX_NAME, table_name="items")
