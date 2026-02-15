"""add_hierarchical_item_model

Revision ID: a1b2c3d4e5f6
Revises: 251cd8f1299d
Create Date: 2026-02-15 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union

# revision identifiers, used by Alembic
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '251cd8f1299d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate from flat Item model to hierarchical ItemType/Item model."""

    # Get database connection for data migration
    connection = op.get_bind()

    # ===== STEP 1: Create item_types table =====
    op.create_table(
        'item_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('sub_type', sa.String(255), nullable=True),
        sa.Column('is_serialized', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'sub_type', name='uq_item_type_name_subtype')
    )
    op.create_index('ix_item_types_name', 'item_types', ['name'])
    op.create_index('ix_item_types_sub_type', 'item_types', ['sub_type'])

    # ===== STEP 2: Check if there's existing data to migrate =====
    result = connection.execute(sa.text("SELECT COUNT(*) FROM items")).scalar()

    if result > 0:
        # There's existing data - perform data migration
        print(f"Found {result} existing items, performing data migration...")

        # Extract unique type/subtype combinations
        existing_types = connection.execute(sa.text("""
            SELECT DISTINCT
                item_type,
                sub_type,
                details,
                MIN(created_at) as earliest_created
            FROM items
            GROUP BY item_type, sub_type, details
            ORDER BY item_type, sub_type
        """))

        type_id_map = {}  # Maps (item_type, sub_type) -> type_id

        for row in existing_types:
            item_type = row.item_type
            sub_type = row.sub_type or ""
            details = row.details or ""
            created_at = row.earliest_created

            # Determine if this type should be serialized
            # (if any items have non-empty serial numbers)
            has_serials = connection.execute(sa.text("""
                SELECT COUNT(*) > 0
                FROM items
                WHERE item_type = :item_type
                  AND (sub_type = :sub_type OR (sub_type IS NULL AND :sub_type = ''))
                  AND serial_number IS NOT NULL
                  AND serial_number != ''
            """), {
                'item_type': item_type,
                'sub_type': sub_type
            }).scalar()

            # Insert into item_types
            result_insert = connection.execute(sa.text("""
                INSERT INTO item_types (name, sub_type, is_serialized, details, created_at, updated_at)
                VALUES (:name, :sub_type, :is_serialized, :details, :created_at, :updated_at)
            """), {
                'name': item_type,
                'sub_type': sub_type if sub_type else None,
                'is_serialized': 1 if has_serials else 0,
                'details': details,
                'created_at': created_at,
                'updated_at': created_at
            })

            # Get the ID of inserted type
            type_id = connection.execute(sa.text("""
                SELECT id FROM item_types
                WHERE name = :name
                  AND (sub_type = :sub_type OR (sub_type IS NULL AND :sub_type IS NULL))
            """), {
                'name': item_type,
                'sub_type': sub_type if sub_type else None
            }).scalar()

            type_id_map[(item_type, sub_type)] = type_id

        print(f"Created {len(type_id_map)} item types")

        # ===== STEP 3: Rename old items to items_old =====
        op.rename_table('items', 'items_old')

        # ===== STEP 4: Create new items table =====
        op.create_table(
            'items',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('item_type_id', sa.Integer(), nullable=False),
            sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('serial_number', sa.String(255), nullable=True),
            sa.Column('location', sa.String(255), nullable=True),
            sa.Column('condition', sa.String(50), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['item_type_id'], ['item_types.id']),
            sa.UniqueConstraint('serial_number', name='uq_items_serial_number'),
            sa.CheckConstraint(
                '(serial_number IS NULL AND quantity > 0) OR (serial_number IS NOT NULL AND quantity = 1)',
                name='check_serial_or_quantity'
            )
        )
        op.create_index('ix_items_item_type_id', 'items', ['item_type_id'])
        op.create_index('ix_items_serial_number', 'items', ['serial_number'])

        # ===== STEP 5: Migrate data from items_old to items =====
        old_items = connection.execute(sa.text("""
            SELECT id, item_type, sub_type, quantity, serial_number, created_at, updated_at
            FROM items_old
        """))

        for old_item in old_items:
            item_type = old_item.item_type
            sub_type = old_item.sub_type or ""
            type_id = type_id_map.get((item_type, sub_type))

            if not type_id:
                print(f"WARNING: No type_id found for {item_type}/{sub_type}, skipping item {old_item.id}")
                continue

            # Insert into new items table
            connection.execute(sa.text("""
                INSERT INTO items (id, item_type_id, quantity, serial_number, location, condition, notes, created_at, updated_at)
                VALUES (:id, :item_type_id, :quantity, :serial_number, NULL, NULL, NULL, :created_at, :updated_at)
            """), {
                'id': old_item.id,
                'item_type_id': type_id,
                'quantity': old_item.quantity,
                'serial_number': old_item.serial_number if old_item.serial_number and old_item.serial_number != '' else None,
                'created_at': old_item.created_at,
                'updated_at': old_item.updated_at
            })

        # ===== STEP 6: Drop old items table =====
        op.drop_table('items_old')

        print("Migration completed successfully!")
    else:
        # No existing data - just create new schema
        print("No existing data, creating fresh schema...")

        # Rename old table
        op.rename_table('items', 'items_old')

        # Create new items table
        op.create_table(
            'items',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('item_type_id', sa.Integer(), nullable=False),
            sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('serial_number', sa.String(255), nullable=True),
            sa.Column('location', sa.String(255), nullable=True),
            sa.Column('condition', sa.String(50), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['item_type_id'], ['item_types.id']),
            sa.UniqueConstraint('serial_number', name='uq_items_serial_number'),
            sa.CheckConstraint(
                '(serial_number IS NULL AND quantity > 0) OR (serial_number IS NOT NULL AND quantity = 1)',
                name='check_serial_or_quantity'
            )
        )
        op.create_index('ix_items_item_type_id', 'items', ['item_type_id'])
        op.create_index('ix_items_serial_number', 'items', ['serial_number'])

        # Drop old table
        op.drop_table('items_old')

        print("Fresh schema created successfully!")


def downgrade() -> None:
    """Revert to flat Item model."""
    connection = op.get_bind()

    # Create old items structure
    op.create_table(
        'items_old',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_type', sa.String(255), nullable=False),
        sa.Column('sub_type', sa.String(255), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('serial_number', sa.String(255), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Migrate data back
    items = connection.execute(sa.text("""
        SELECT i.id, it.name, it.sub_type, i.quantity, i.serial_number, it.details, i.created_at, i.updated_at
        FROM items i
        JOIN item_types it ON i.item_type_id = it.id
    """))

    for item in items:
        connection.execute(sa.text("""
            INSERT INTO items_old (id, item_type, sub_type, quantity, serial_number, details, created_at, updated_at)
            VALUES (:id, :item_type, :sub_type, :quantity, :serial_number, :details, :created_at, :updated_at)
        """), {
            'id': item.id,
            'item_type': item.name,
            'sub_type': item.sub_type,
            'quantity': item.quantity,
            'serial_number': item.serial_number,
            'details': item.details,
            'created_at': item.created_at,
            'updated_at': item.updated_at
        })

    # Drop new tables
    op.drop_table('items')
    op.drop_table('item_types')

    # Rename old back to items
    op.rename_table('items_old', 'items')
