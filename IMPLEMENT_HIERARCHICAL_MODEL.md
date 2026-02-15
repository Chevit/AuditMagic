# Implementation Guide: Hierarchical Item Model (Option B)

> **Purpose**: Step-by-step instructions for Claude Code to implement the hierarchical ItemType/Item model with serial number support, autocomplete, and location tracking.

## Overview

This guide implements Option B from SERIAL_NUMBER_PROPOSAL.md:
- Separate `ItemType` table (types/categories)
- `Item` table (actual inventory instances)
- Serial number logic with validation
- Autocomplete for Type/SubType
- Location tracking (string-based, ready for future expansion)

**Estimated Time**: 1-2 weeks
**Complexity**: High (major refactor)
**Risk**: Medium (requires careful data migration)

---

## Prerequisites

Before starting:
1. ✅ Complete Phase 0: Code Cleanup (IMPROVEMENTS.md)
2. ✅ Backup current database
3. ✅ Ensure all existing tests pass (if any)
4. ✅ Create a new git branch: `git checkout -b feature/hierarchical-model`

---

## Phase 1: Create New Models (Day 1)

### Step 1.1: Update models.py

**File**: `models.py`

Add these imports at the top:
```python
from sqlalchemy import Boolean, UniqueConstraint, CheckConstraint
```

Add the new `ItemType` model BEFORE the `Item` model:

```python
class ItemType(Base):
    """Represents a type/category of items.

    This is the template/definition for items (e.g., "Laptop ThinkPad X1").
    Actual inventory instances are stored in the Item table.
    """
    __tablename__ = "item_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    sub_type = Column(String(255), nullable=True, index=True)
    is_serialized = Column(Boolean, default=False, nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    items = relationship("Item", back_populates="item_type", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('name', 'sub_type', name='uq_item_type_name_subtype'),
    )

    def __repr__(self):
        return f"<ItemType(id={self.id}, name='{self.name}', sub_type='{self.sub_type}', serialized={self.is_serialized})>"

    @property
    def total_quantity(self) -> int:
        """Get total quantity across all items of this type."""
        return sum(item.quantity for item in self.items)

    @property
    def serial_numbers(self) -> list:
        """Get all serial numbers for this type (if serialized)."""
        if not self.is_serialized:
            return []
        return [item.serial_number for item in self.items if item.serial_number]

    @property
    def display_name(self) -> str:
        """Get display name with subtype if present."""
        if self.sub_type:
            return f"{self.name} - {self.sub_type}"
        return self.name
```

Replace the existing `Item` model with this NEW version:

```python
class Item(Base):
    """Represents actual inventory items/units.

    This is an instance of an ItemType (e.g., one specific laptop with serial number ABC123).
    For non-serialized items, one row can represent multiple units (quantity > 1).
    For serialized items, one row = one unit (quantity must = 1).
    """
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_type_id = Column(Integer, ForeignKey("item_types.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    serial_number = Column(String(255), nullable=True, unique=True, index=True)
    location = Column(String(255), nullable=True)
    condition = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    item_type = relationship("ItemType", back_populates="items")
    transactions = relationship("Transaction", back_populates="item", cascade="all, delete-orphan")

    # Constraints: Either bulk (no SN, qty > 0) OR serialized (has SN, qty = 1)
    __table_args__ = (
        CheckConstraint(
            '(serial_number IS NULL AND quantity > 0) OR (serial_number IS NOT NULL AND quantity = 1)',
            name='check_serial_or_quantity'
        ),
    )

    def __repr__(self):
        return f"<Item(id={self.id}, type_id={self.item_type_id}, qty={self.quantity}, sn={self.serial_number})>"

    @property
    def display_name(self) -> str:
        """Get display name from item type."""
        return self.item_type.display_name if self.item_type else f"Type #{self.item_type_id}"
```

**Testing**:
```bash
# Verify no syntax errors
python -c "from models import ItemType, Item; print('Models loaded successfully')"
```

---

## Phase 2: Create Migration Script (Day 1-2)

### Step 2.1: Create Alembic Migration

**Command**:
```bash
alembic revision -m "add_hierarchical_item_model"
```

This creates a new file in `alembic/versions/`. Open it and replace with this content:

**File**: `alembic/versions/XXXX_add_hierarchical_item_model.py`

```python
"""add_hierarchical_item_model

Revision ID: XXXX
Revises: YYYY
Create Date: 2026-XX-XX
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Boolean


# revision identifiers
revision = 'XXXX'  # Will be auto-generated
down_revision = 'YYYY'  # Previous migration ID
branch_labels = None
depends_on = None


def upgrade():
    """Migrate from flat Item model to hierarchical ItemType/Item model."""

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

    # ===== STEP 2: Extract unique types from items and populate item_types =====
    connection = op.get_bind()

    # Get unique type/subtype combinations
    result = connection.execute(sa.text("""
        SELECT DISTINCT
            item_type,
            sub_type,
            details,
            MIN(created_at) as earliest_created
        FROM items
        GROUP BY item_type, sub_type
        ORDER BY item_type, sub_type
    """))

    type_id_map = {}  # Maps (item_type, sub_type) -> type_id

    for row in result:
        item_type = row.item_type
        sub_type = row.sub_type or ""
        details = row.details or ""
        created_at = row.earliest_created

        # Determine if this type should be serialized
        # (if any items have serial numbers)
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
        result = connection.execute(sa.text("""
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

    # ===== STEP 3: Create new items table structure =====
    # Rename old items to items_old
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

    # ===== STEP 4: Migrate data from items_old to items =====
    # Get all old items
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
            'serial_number': old_item.serial_number if old_item.serial_number else None,
            'created_at': old_item.created_at,
            'updated_at': old_item.updated_at
        })

    # ===== STEP 5: Update transactions table to reference new items =====
    # (Transactions still reference items by ID, which we preserved)
    # Just verify the foreign key still works

    # ===== STEP 6: Drop old items table =====
    op.drop_table('items_old')

    print("Migration completed successfully!")
    print(f"Created {len(type_id_map)} item types")


def downgrade():
    """Revert to flat Item model."""
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
    connection = op.get_bind()
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
```

### Step 2.2: Test Migration (with backup!)

**CRITICAL: Backup first!**
```bash
# Backup database
cp ~/.local/share/AuditMagic/inventory.db ~/.local/share/AuditMagic/inventory.db.backup

# Run migration
alembic upgrade head

# Verify
python -c "
from db import init_database
from sqlalchemy import inspect
init_database()
from db import get_engine
inspector = inspect(get_engine())
print('Tables:', inspector.get_table_names())
print('ItemTypes columns:', [c['name'] for c in inspector.get_columns('item_types')])
print('Items columns:', [c['name'] for c in inspector.get_columns('items')])
"

# If successful, test app
python main.py
```

**If migration fails**:
```bash
# Restore backup
cp ~/.local/share/AuditMagic/inventory.db.backup ~/.local/share/AuditMagic/inventory.db
# Fix migration script and try again
```

---

## Phase 3: Create ItemTypeRepository (Day 2-3)

### Step 3.1: Add ItemTypeRepository to repositories.py

**File**: `repositories.py`

Add this NEW repository class BEFORE the `ItemRepository` class:

```python
class ItemTypeRepository:
    """Repository for ItemType CRUD operations."""

    @staticmethod
    def create(
        name: str,
        sub_type: str = "",
        is_serialized: bool = False,
        details: str = ""
    ) -> ItemType:
        """Create a new item type.

        Args:
            name: Type name (required)
            sub_type: Sub-type name (optional)
            is_serialized: Whether items of this type have serial numbers
            details: Description of this type

        Returns:
            The created ItemType instance.
        """
        logger.debug(f"Repository: Creating item type name='{name}', sub_type='{sub_type}'")
        with session_scope() as session:
            item_type = ItemType(
                name=name,
                sub_type=sub_type or "",
                is_serialized=is_serialized,
                details=details or ""
            )
            session.add(item_type)
            session.flush()
            session.refresh(item_type)
            logger.debug(f"Repository: ItemType created with id={item_type.id}")
            return _detach_item_type(item_type)

    @staticmethod
    def get_or_create(
        name: str,
        sub_type: str = "",
        is_serialized: bool = False,
        details: str = ""
    ) -> ItemType:
        """Get existing type or create new one.

        Args:
            name: Type name
            sub_type: Sub-type name
            is_serialized: Whether serialized
            details: Type description

        Returns:
            Existing or newly created ItemType.
        """
        with session_scope() as session:
            # Try to find existing
            item_type = (
                session.query(ItemType)
                .filter(
                    ItemType.name == name,
                    ItemType.sub_type == (sub_type or "")
                )
                .first()
            )

            if item_type:
                return _detach_item_type(item_type)

            # Create new
            item_type = ItemType(
                name=name,
                sub_type=sub_type or "",
                is_serialized=is_serialized,
                details=details or ""
            )
            session.add(item_type)
            session.flush()
            session.refresh(item_type)
            return _detach_item_type(item_type)

    @staticmethod
    def get_by_id(type_id: int) -> Optional[ItemType]:
        """Get item type by ID.

        Args:
            type_id: The type's ID.

        Returns:
            ItemType instance or None if not found.
        """
        with session_scope() as session:
            item_type = session.query(ItemType).filter(ItemType.id == type_id).first()
            return _detach_item_type(item_type) if item_type else None

    @staticmethod
    def get_all() -> List[ItemType]:
        """Get all item types.

        Returns:
            List of all ItemType instances.
        """
        with session_scope() as session:
            types = session.query(ItemType).order_by(ItemType.name, ItemType.sub_type).all()
            return [_detach_item_type(t) for t in types]

    @staticmethod
    def get_autocomplete_names(prefix: str = "", limit: int = 20) -> List[str]:
        """Get autocomplete suggestions for type names.

        Args:
            prefix: Search prefix (optional)
            limit: Maximum number of suggestions

        Returns:
            List of matching type names.
        """
        with session_scope() as session:
            query = session.query(ItemType.name).distinct()
            if prefix:
                query = query.filter(ItemType.name.ilike(f"{prefix}%"))
            query = query.order_by(ItemType.name).limit(limit)
            return [row[0] for row in query.all()]

    @staticmethod
    def get_autocomplete_subtypes(
        type_name: str,
        prefix: str = "",
        limit: int = 20
    ) -> List[str]:
        """Get autocomplete suggestions for subtypes given a type name.

        Args:
            type_name: The type name to filter by
            prefix: Search prefix for subtype (optional)
            limit: Maximum number of suggestions

        Returns:
            List of matching subtype names.
        """
        with session_scope() as session:
            query = (
                session.query(ItemType.sub_type)
                .filter(
                    ItemType.name == type_name,
                    ItemType.sub_type.isnot(None),
                    ItemType.sub_type != ""
                )
                .distinct()
            )
            if prefix:
                query = query.filter(ItemType.sub_type.ilike(f"{prefix}%"))
            query = query.order_by(ItemType.sub_type).limit(limit)
            return [row[0] for row in query.all() if row[0]]

    @staticmethod
    def update(
        type_id: int,
        name: str = None,
        sub_type: str = None,
        is_serialized: bool = None,
        details: str = None
    ) -> Optional[ItemType]:
        """Update an item type.

        Args:
            type_id: Type ID
            name: New name (optional)
            sub_type: New sub-type (optional)
            is_serialized: New serialized status (optional)
            details: New details (optional)

        Returns:
            Updated ItemType or None if not found.
        """
        with session_scope() as session:
            item_type = session.query(ItemType).filter(ItemType.id == type_id).first()
            if not item_type:
                return None

            if name is not None:
                item_type.name = name
            if sub_type is not None:
                item_type.sub_type = sub_type
            if is_serialized is not None:
                item_type.is_serialized = is_serialized
            if details is not None:
                item_type.details = details

            session.flush()
            session.refresh(item_type)
            return _detach_item_type(item_type)

    @staticmethod
    def delete(type_id: int) -> bool:
        """Delete an item type and all its items.

        Args:
            type_id: Type ID

        Returns:
            True if deleted, False if not found.
        """
        with session_scope() as session:
            item_type = session.query(ItemType).filter(ItemType.id == type_id).first()
            if not item_type:
                return False
            session.delete(item_type)  # Cascade will delete items too
            return True

    @staticmethod
    def search(query: str, limit: int = 100) -> List[ItemType]:
        """Search item types by name or subtype.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching ItemType instances.
        """
        with session_scope() as session:
            search_pattern = f"%{query}%"
            types = (
                session.query(ItemType)
                .filter(
                    or_(
                        ItemType.name.ilike(search_pattern),
                        ItemType.sub_type.ilike(search_pattern)
                    )
                )
                .order_by(ItemType.name, ItemType.sub_type)
                .limit(limit)
                .all()
            )
            return [_detach_item_type(t) for t in types]
```

### Step 3.2: Add detach helper function

Add this function at the END of `repositories.py` (after existing detach functions):

```python
def _detach_item_type(item_type: ItemType) -> ItemType:
    """Create a detached copy of an ItemType."""
    if item_type is None:
        return None
    return ItemType(
        id=item_type.id,
        name=item_type.name,
        sub_type=item_type.sub_type,
        is_serialized=item_type.is_serialized,
        details=item_type.details,
        created_at=item_type.created_at,
        updated_at=item_type.updated_at
    )
```

### Step 3.3: Add import at top of repositories.py

Add to imports:
```python
from models import Item, Transaction, TransactionType, SearchHistory, ItemType
```

**Testing**:
```bash
python -c "
from repositories import ItemTypeRepository
# Test create
t = ItemTypeRepository.create('Test Laptop', 'MacBook Pro', is_serialized=True)
print(f'Created type: {t.id} - {t.name}')
# Test autocomplete
names = ItemTypeRepository.get_autocomplete_names('Test')
print(f'Autocomplete results: {names}')
"
```

---

## Phase 4: Update ItemRepository (Day 3-4)

### Step 4.1: Replace ItemRepository.create()

**File**: `repositories.py`

Find the `ItemRepository.create()` method and REPLACE it with:

```python
@staticmethod
def create(
    item_type_id: int,
    quantity: int = 1,
    serial_number: str = None,
    location: str = None,
    condition: str = None,
    notes: str = None
) -> Item:
    """Create a new item instance.

    Args:
        item_type_id: FK to ItemType
        quantity: Quantity (must be 1 if serialized)
        serial_number: Serial number (required if type is serialized)
        location: Storage location
        condition: Item condition
        notes: Additional notes

    Returns:
        The created Item instance.

    Raises:
        ValueError: If validation fails
    """
    logger.debug(f"Repository: Creating item for type_id={item_type_id}, qty={quantity}")

    with session_scope() as session:
        # Validate type exists and get serialization status
        item_type = session.query(ItemType).filter(ItemType.id == item_type_id).first()
        if not item_type:
            raise ValueError(f"ItemType with id {item_type_id} not found")

        # Validate serialization rules
        if item_type.is_serialized:
            if not serial_number:
                raise ValueError("Serial number required for serialized items")
            if quantity != 1:
                raise ValueError("Quantity must be 1 for serialized items")
        else:
            if serial_number:
                raise ValueError("Serial number not allowed for non-serialized items")
            if quantity < 1:
                raise ValueError("Quantity must be at least 1")

        item = Item(
            item_type_id=item_type_id,
            quantity=quantity,
            serial_number=serial_number or None,
            location=location or "",
            condition=condition or "",
            notes=notes or ""
        )
        session.add(item)
        session.flush()

        # Create initial transaction
        if quantity > 0:
            transaction = Transaction(
                item_id=item.id,
                transaction_type=TransactionType.ADD,
                quantity_change=quantity,
                quantity_before=0,
                quantity_after=quantity,
                notes=tr("transaction.notes.initial")
            )
            session.add(transaction)

        session.flush()
        session.refresh(item)
        logger.debug(f"Repository: Item created with id={item.id}")
        return _detach_item(item)
```

### Step 4.2: Update _detach_item() helper

Find the `_detach_item()` function and REPLACE it with:

```python
def _detach_item(item: Item) -> Item:
    """Create a detached copy of an Item."""
    if item is None:
        return None
    return Item(
        id=item.id,
        item_type_id=item.item_type_id,
        quantity=item.quantity,
        serial_number=item.serial_number,
        location=item.location,
        condition=item.condition,
        notes=item.notes,
        created_at=item.created_at,
        updated_at=item.updated_at
    )
```

### Step 4.3: Add new helper methods to ItemRepository

Add these methods to `ItemRepository` class:

```python
@staticmethod
def get_by_type(type_id: int) -> List[Item]:
    """Get all items of a specific type.

    Args:
        type_id: ItemType ID

    Returns:
        List of Item instances.
    """
    with session_scope() as session:
        items = (
            session.query(Item)
            .filter(Item.item_type_id == type_id)
            .order_by(Item.serial_number, Item.location)
            .all()
        )
        return [_detach_item(item) for item in items]

@staticmethod
def search_by_serial(serial_number: str) -> Optional[Item]:
    """Find item by serial number.

    Args:
        serial_number: Serial number to search for

    Returns:
        Item instance or None.
    """
    with session_scope() as session:
        item = (
            session.query(Item)
            .filter(Item.serial_number == serial_number)
            .first()
        )
        return _detach_item(item) if item else None

@staticmethod
def get_serial_numbers_for_type(type_id: int) -> List[str]:
    """Get all serial numbers for a given type.

    Args:
        type_id: ItemType ID

    Returns:
        List of serial numbers.
    """
    with session_scope() as session:
        results = (
            session.query(Item.serial_number)
            .filter(
                Item.item_type_id == type_id,
                Item.serial_number.isnot(None)
            )
            .order_by(Item.serial_number)
            .all()
        )
        return [row[0] for row in results]

@staticmethod
def get_items_at_location(location: str) -> List[Item]:
    """Get all items at a specific location.

    Args:
        location: Location name

    Returns:
        List of Item instances.
    """
    with session_scope() as session:
        items = (
            session.query(Item)
            .filter(Item.location == location)
            .order_by(Item.item_type_id, Item.serial_number)
            .all()
        )
        return [_detach_item(item) for item in items]
```

**Testing**:
```bash
python -c "
from repositories import ItemTypeRepository, ItemRepository

# Create type
t = ItemTypeRepository.create('Test Item', 'Model X', is_serialized=True)

# Create serialized item
item = ItemRepository.create(t.id, quantity=1, serial_number='SN12345')
print(f'Created item: {item.id} with SN: {item.serial_number}')

# Get serial numbers for type
sns = ItemRepository.get_serial_numbers_for_type(t.id)
print(f'Serial numbers: {sns}')
"
```

---

## Phase 5: Update InventoryItem DTO (Day 4)

### Step 5.1: Update InventoryItem dataclass

**File**: `ui_entities/inventory_item.py`

REPLACE the entire class with:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class InventoryItem:
    """Data Transfer Object for inventory items in UI layer."""

    id: int
    item_type_id: int
    item_type_name: str  # From ItemType.name
    item_sub_type: str  # From ItemType.sub_type
    is_serialized: bool  # From ItemType.is_serialized
    quantity: int
    serial_number: Optional[str]
    location: Optional[str]
    condition: Optional[str]
    notes: Optional[str]
    details: Optional[str]  # From ItemType.details
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db_models(cls, item, item_type):
        """Create InventoryItem from Item and ItemType models.

        Args:
            item: Item model instance
            item_type: ItemType model instance

        Returns:
            InventoryItem instance.
        """
        return cls(
            id=item.id,
            item_type_id=item.item_type_id,
            item_type_name=item_type.name,
            item_sub_type=item_type.sub_type or "",
            is_serialized=item_type.is_serialized,
            quantity=item.quantity,
            serial_number=item.serial_number,
            location=item.location or "",
            condition=item.condition or "",
            notes=item.notes or "",
            details=item_type.details or "",
            created_at=item.created_at,
            updated_at=item.updated_at
        )

    @property
    def display_name(self) -> str:
        """Get formatted display name."""
        if self.item_sub_type:
            return f"{self.item_type_name} - {self.item_sub_type}"
        return self.item_type_name

    @property
    def display_info(self) -> str:
        """Get detailed display info for list view."""
        parts = [self.display_name]
        if self.serial_number:
            parts.append(f"SN: {self.serial_number}")
        else:
            parts.append(f"Qty: {self.quantity}")
        if self.location:
            parts.append(f"@ {self.location}")
        return " | ".join(parts)
```

---

## Phase 6: Update Services (Day 4-5)

### Step 6.1: Update InventoryService

**File**: `services.py`

Add import at top:
```python
from repositories import ItemRepository, TransactionRepository, SearchHistoryRepository, ItemTypeRepository
```

REPLACE `InventoryService` methods with these updated versions:

```python
class InventoryService:
    """Service for inventory management operations."""

    @staticmethod
    def create_item(
        item_type_name: str,
        item_sub_type: str = "",
        quantity: int = 1,
        is_serialized: bool = False,
        serial_number: str = None,
        location: str = "",
        condition: str = "",
        notes: str = "",
        details: str = ""
    ) -> InventoryItem:
        """Create a new inventory item.

        Args:
            item_type_name: Type name
            item_sub_type: Sub-type name
            quantity: Initial quantity
            is_serialized: Whether this type has serial numbers
            serial_number: Serial number (required if serialized)
            location: Storage location
            condition: Item condition
            notes: Item notes
            details: Type details (description)

        Returns:
            The created InventoryItem.
        """
        logger.info(f"Creating new item: type='{item_type_name}', sub_type='{item_sub_type}', qty={quantity}")
        try:
            # Get or create item type
            item_type = ItemTypeRepository.get_or_create(
                name=item_type_name,
                sub_type=item_sub_type,
                is_serialized=is_serialized,
                details=details
            )

            # Create item instance
            db_item = ItemRepository.create(
                item_type_id=item_type.id,
                quantity=quantity,
                serial_number=serial_number,
                location=location,
                condition=condition,
                notes=notes
            )

            logger.info(f"Item created successfully: id={db_item.id}")
            return InventoryItem.from_db_models(db_item, item_type)
        except Exception as e:
            logger.error(f"Failed to create item: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def get_item(item_id: int) -> Optional[InventoryItem]:
        """Get an item by ID.

        Args:
            item_id: The item's ID.

        Returns:
            The InventoryItem or None if not found.
        """
        db_item = ItemRepository.get_by_id(item_id)
        if not db_item:
            return None

        item_type = ItemTypeRepository.get_by_id(db_item.item_type_id)
        return InventoryItem.from_db_models(db_item, item_type)

    @staticmethod
    def get_all_items() -> List[InventoryItem]:
        """Get all inventory items.

        Returns:
            List of all InventoryItem instances.
        """
        db_items = ItemRepository.get_all()
        result = []

        for db_item in db_items:
            item_type = ItemTypeRepository.get_by_id(db_item.item_type_id)
            if item_type:
                result.append(InventoryItem.from_db_models(db_item, item_type))

        return result

    @staticmethod
    def get_autocomplete_types(prefix: str = "") -> List[str]:
        """Get autocomplete suggestions for item types.

        Args:
            prefix: Search prefix

        Returns:
            List of matching type names.
        """
        return ItemTypeRepository.get_autocomplete_names(prefix)

    @staticmethod
    def get_autocomplete_subtypes(type_name: str, prefix: str = "") -> List[str]:
        """Get autocomplete suggestions for subtypes.

        Args:
            type_name: The type name
            prefix: Search prefix

        Returns:
            List of matching subtype names.
        """
        return ItemTypeRepository.get_autocomplete_subtypes(type_name, prefix)
```

Continue this in a second message due to length...

**Files Modified Summary**:
- ✅ models.py
- ✅ repositories.py
- ✅ ui_entities/inventory_item.py
- ✅ services.py (partial)

**Next Steps**:
- Complete services.py updates
- Update UI dialogs
- Add translation keys
- Test thoroughly

Would you like me to continue with the remaining steps?
