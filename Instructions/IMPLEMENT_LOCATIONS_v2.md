# Feature: Location Management — Multi-Location Inventory with Transfer Support

> **Target project:** AuditMagic (`C:\Users\chevi\PycharmProjects\AuditMagic`)
> **Stack:** Python 3.14 · PyQt6 · SQLAlchemy + SQLite · Alembic · `qt-material`
> **Architecture:** Repository → Service → UI (MVC), custom `QAbstractListModel`, dataclass DTOs
> **Key constraint:** Alembic migrations must use `batch_alter_table` for SQLite compatibility
> **Version:** v3 — incorporates design review feedback + gap analysis fixes

---

## 0. Overview & Scope

Currently, `Item.location` is a free-text string field — there is no `Location` entity. Items are displayed in a single flat list without location awareness. This feature introduces:

1. **Location model** — a first-class `Location` table with FK on `Item`
2. **Location CRUD** — create/rename/delete locations via a management dialog
3. **First-launch wizard** — if no locations exist, force the user to create one before proceeding; all existing items get assigned to it
4. **Location selector** — a dropdown at the top of the main window to filter items by location
5. **Transfer between locations** — context menu action for both serialized and non-serialized items
6. **TRANSFER transaction type** — audit trail for all moves (2 transactions per transfer: one for source, one for destination)
7. **Search scope** — search current location (default) or all locations (checkbox toggle)
8. **Safe deletion** — prevent deleting locations that have items; offer to move items first
9. **Global transaction log** — button at bottom of UI to view all transactions, filterable by location

### Critical Rules
- **Location is mandatory.** Every item must have a `location_id` (NOT NULL after migration).
- **Item.location free-text field is unused** — no data migration needed, just drop the column.
- **ItemTypes are NOT linked to locations.** Only `Item` rows have `location_id`. The same ItemType can have items across many locations.
- **Don't show ItemTypes that have zero items** (existing behavior — maintain it).
- **Transfers create 2 transactions:** one REMOVE-like record at source, one ADD-like record at destination.
- **Non-serialized transfer merges:** If an item of the same type exists at the destination, merge (add quantity) rather than creating a new row.
- **Selected location is persisted** in config and restored on next launch.
- **All transactions carry `location_id`** — ADD/REMOVE/EDIT record the item's location at that moment; TRANSFER records also carry `from_location_id`/`to_location_id`.

---

## 1. Database — New Model & Migration

### 1.1 Add `TRANSFER` to `TransactionType` enum in `models.py`

```python
class TransactionType(enum.Enum):
    ADD = "add"
    REMOVE = "remove"
    EDIT = "edit"
    TRANSFER = "transfer"
```

> **Note:** SQLite stores `SQLEnum` as VARCHAR, so adding this value requires no DB-level ALTER — the Python enum change is sufficient. Add an explicit comment in the migration file to document this.

### 1.2 Create `Location` model in `models.py`

Add **above** the `Item` class:

```python
class Location(Base):
    """Represents a physical storage location."""

    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    items = relationship("Item", back_populates="location_ref")

    def __repr__(self):
        return f"<Location(id={self.id}, name='{self.name}')>"
```

### 1.3 Update `Item` model

Replace the free-text `location` column with a proper FK. Since the old `location` field is unused (empty), we simply drop it and add the FK:

```python
class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_type_id = Column(Integer, ForeignKey("item_types.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    serial_number = Column(String(255), nullable=True, unique=True, index=True)
    # REMOVED: location = Column(String(255), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    condition = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    item_type = relationship("ItemType", back_populates="items")
    location_ref = relationship("Location", back_populates="items")

    # Backward-compat property for any leftover references.
    # WARNING: This returns "" on detached Item objects created by _detach_item()
    # because location_ref is not populated in the detached copy.
    # All new code must use location_id + the location_name field on DTOs instead.
    @property
    def location(self) -> str:
        """Return location name for backward compat (session-bound objects only)."""
        return self.location_ref.name if self.location_ref else ""

    # Keep existing __table_args__ (serial/quantity check constraint)
```

**Note:** `location_id` is `nullable=False` in the final schema. The migration handles this in two steps: add as nullable, populate via first-launch wizard, then the app enforces NOT NULL at creation time (see Section 9.5).

### 1.4 Update `Transaction` model

Add columns for location tracking on **all** transaction types, plus specific from/to fields for transfers:

```python
class Transaction(Base):
    __tablename__ = "transactions"

    # ... existing columns unchanged ...

    # NEW: location context for ALL transaction types.
    # For ADD/REMOVE/EDIT: the item's location at the time of the transaction.
    # For TRANSFER source record: the source location.
    # For TRANSFER destination record: the destination location.
    # This column makes location-filtered queries on AllTransactionsDialog accurate
    # and historically correct (item may be transferred later, but this captures
    # where it was when each event occurred).
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)

    # NEW: transfer-specific columns (populated only for TRANSFER type)
    from_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    to_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)

    # Relationships (read-only references, no back_populates)
    location = relationship("Location", foreign_keys="[Transaction.location_id]")
    from_location = relationship("Location", foreign_keys="[Transaction.from_location_id]")
    to_location = relationship("Location", foreign_keys="[Transaction.to_location_id]")
```

> **Design rationale for `location_id` on all transactions:**
> `AllTransactionsDialog` needs to filter by location. For non-TRANSFER transactions there is no way to reconstruct the item's historical location by joining through `items`, because items can be transferred after the fact. Recording `location_id` at the moment of each transaction is the only historically accurate approach.
>
> For TRANSFER type, both the source and destination transactions carry the same `from_location_id`/`to_location_id`, but each has a different `location_id` (source record: source location; destination record: destination location) — this lets location-specific views show both incoming and outgoing transfers correctly.

### 1.5 Alembic Migration

**Add to `alembic/env.py`** (in both `run_migrations_online` and `run_migrations_offline`):
```python
context.configure(
    # ... existing args ...
    render_as_batch=True  # Required for SQLite ALTER support
)
```

**Generate migration:**
```bash
cd C:\Users\chevi\PycharmProjects\AuditMagic
.venv\Scripts\activate
alembic revision --autogenerate -m "add_locations_table_and_transfer"
```

**Manually edit the generated migration** to use batch operations:

```python
def upgrade():
    # 1. Create locations table
    op.create_table(
        'locations',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
    )

    # 2. Update items table: drop old location, add location_id (nullable first)
    with op.batch_alter_table('items', schema=None) as batch_op:
        batch_op.drop_column('location')
        batch_op.add_column(sa.Column('location_id', sa.Integer, nullable=True))
        batch_op.create_foreign_key('fk_items_location_id', 'locations', ['location_id'], ['id'])
        batch_op.create_index('ix_items_location_id', ['location_id'])

    # 3. Update transactions table: add location columns
    # Note: TransactionType enum needs no DB-level change — SQLite stores it as
    # VARCHAR, so adding TRANSFER to the Python enum is sufficient.
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('location_id', sa.Integer, nullable=True))
        batch_op.add_column(sa.Column('from_location_id', sa.Integer, nullable=True))
        batch_op.add_column(sa.Column('to_location_id', sa.Integer, nullable=True))
        batch_op.create_foreign_key('fk_transactions_location', 'locations', ['location_id'], ['id'])
        batch_op.create_foreign_key('fk_transactions_from_location', 'locations', ['from_location_id'], ['id'])
        batch_op.create_foreign_key('fk_transactions_to_location', 'locations', ['to_location_id'], ['id'])

    # NOTE: location_id on items stays nullable in migration.
    # The app enforces NOT NULL at creation time. The first-launch wizard
    # will create a location and assign all existing items to it before
    # any user interaction.
    # NOTE: location_id on transactions is nullable permanently — historical
    # transactions recorded before this migration have no location context.
```

**Important:** Since `Item.location` is currently unused (empty), no data migration is needed. The column is simply dropped. The first-launch wizard (Step 6.2) handles assigning all existing items to the user's first location.

---

## 2. Repository Layer — `repositories.py`

### 2.1 Add `_detach_location()` helper

```python
def _detach_location(loc: "Location") -> "Location":
    """Create a detached copy of a Location."""
    if loc is None:
        return None
    from models import Location
    return Location(
        id=loc.id,
        name=loc.name,
        description=loc.description,
        created_at=loc.created_at,
        updated_at=loc.updated_at,
    )
```

### 2.2 New `LocationRepository`

```python
class LocationRepository:
    """Repository for Location CRUD operations."""

    @staticmethod
    def create(name: str, description: str = "") -> Location:
        """Create a new location. Raises ValueError if name already exists."""

    @staticmethod
    def get_by_id(location_id: int) -> Optional[Location]:
        """Get location by ID."""

    @staticmethod
    def get_by_name(name: str) -> Optional[Location]:
        """Get location by name (case-insensitive)."""

    @staticmethod
    def get_all() -> List[Location]:
        """Get all locations ordered by name."""

    @staticmethod
    def update(location_id: int, name: str = None, description: str = None) -> Optional[Location]:
        """Update a location. Raises ValueError if new name conflicts."""

    @staticmethod
    def delete(location_id: int) -> bool:
        """Delete a location. Raises ValueError if items exist at this location."""

    @staticmethod
    def get_item_count(location_id: int) -> int:
        """Return count of items at this location."""

    @staticmethod
    def get_count() -> int:
        """Return total number of locations."""
```

> **Design note:** `move_all_items` (moving items from one location to another before deletion) contains non-trivial merge logic for non-serialized items. This logic belongs in the **service layer**, not the repository. Implement it as `LocationService.move_all_items_and_delete()` which orchestrates `ItemRepository` calls directly. See Section 3.1.

### 2.3 Update `_detach_transaction()`

The existing `_detach_transaction()` helper must copy the three new location columns:

```python
def _detach_transaction(trans: Transaction) -> Transaction:
    """Create a detached copy of a Transaction."""
    if trans is None:
        return None
    return Transaction(
        id=trans.id,
        item_type_id=trans.item_type_id,
        transaction_type=trans.transaction_type,
        quantity_change=trans.quantity_change,
        quantity_before=trans.quantity_before,
        quantity_after=trans.quantity_after,
        notes=trans.notes,
        serial_number=trans.serial_number,
        location_id=trans.location_id,              # NEW
        from_location_id=trans.from_location_id,    # NEW
        to_location_id=trans.to_location_id,        # NEW
        created_at=trans.created_at,
    )
```

### 2.4 Update `_detach_item()`

```python
def _detach_item(item: Item) -> Item:
    """Create a detached copy of an Item.

    Note: The detached copy does NOT populate location_ref relationship.
    Do NOT call item.location on detached objects — it returns "".
    Use location_id and resolve location_name at the service/DTO layer instead.
    """
    if item is None:
        return None
    return Item(
        id=item.id,
        item_type_id=item.item_type_id,
        quantity=item.quantity,
        serial_number=item.serial_number,
        location_id=item.location_id,  # CHANGED from location (string)
        condition=item.condition,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
```

### 2.5 Update `ItemRepository.create()`

Change parameter: `location: str = None` → `location_id: int` (required, no default).
Also set `location_id` on the Transaction created within this method:

```python
@staticmethod
def create(
    item_type_id: int,
    quantity: int = 1,
    serial_number: str = None,
    location_id: int,           # CHANGED — mandatory
    condition: str = None,
    transaction_notes: str = None,
) -> Item:
    # ...
    item.location_id = location_id
    # When creating the ADD transaction record:
    transaction = Transaction(
        # ... existing fields ...
        location_id=location_id,  # NEW — record location at time of ADD
    )
```

### 2.6 Update `ItemRepository.create_serialized()`

Change parameter: `location: str = ""` → `location_id: int` (required).
Also populate `location_id` on the TRANSFER/ADD transaction created within this method.

```python
@staticmethod
def create_serialized(
    item_type_id: int,
    serial_number: str,
    location_id: int,            # CHANGED — mandatory
    condition: str = "",
    notes: str = "",
) -> Item:
```

### 2.7 Update `ItemRepository.edit_item()`

Change parameter: `location: str` → `location_id: int`.
Populate `location_id` on the EDIT transaction:

```python
transaction = Transaction(
    # ... existing fields ...
    location_id=location_id,  # NEW — record location at time of EDIT
)
```

### 2.8 Update `ItemRepository.update()`

Change parameter: `location: str = None` → `location_id: int = None`

### 2.9 Add location filter to query methods

#### `ItemRepository.get_all()`
```python
@staticmethod
def get_all(location_id: int = None) -> List[Item]:
    """Get all items, optionally filtered by location."""
    with session_scope() as session:
        query = session.query(Item).order_by(Item.item_type_id, Item.serial_number)
        if location_id is not None:
            query = query.filter(Item.location_id == location_id)
        items = query.all()
        return [_detach_item(item) for item in items]
```

#### `ItemRepository.search()`
Add `location_id: int = None` parameter. When provided, add `.filter(Item.location_id == location_id)`.

#### `ItemRepository.get_autocomplete_suggestions()`
Add `location_id: int = None` parameter. Filter items by location when provided.

#### `ItemTypeRepository._get_types_with_items()`
Add `location_id: int = None` parameter:
```python
@staticmethod
def _get_types_with_items(session, type_filter=None, location_id=None) -> list:
    query = (
        session.query(ItemType, Item)
        .join(Item, Item.item_type_id == ItemType.id)
        .order_by(ItemType.name, ItemType.sub_type, Item.serial_number, Item.id)
    )
    if type_filter is not None:
        query = query.filter(type_filter)
    if location_id is not None:
        query = query.filter(Item.location_id == location_id)
    # ... rest unchanged ...
```

Update `get_all_with_items()` and `get_serialized_with_items()` to accept and pass `location_id`.

### 2.10 New: `ItemRepository.transfer_item()`

```python
@staticmethod
def transfer_item(
    item_id: int,
    to_location_id: int,
    quantity: int = None,  # None = transfer all (for non-serialized)
    notes: str = "",
) -> bool:
    """Transfer a non-serialized item (or partial quantity) to another location.

    Creates TWO TRANSFER transactions:
      1. Source location: quantity decreases
         → location_id=source, from_location_id=source, to_location_id=dest
      2. Destination location: quantity increases
         → location_id=dest, from_location_id=source, to_location_id=dest

    Merge logic: If an item of the same type already exists at the destination,
    add quantity to it. Otherwise, create a new item row.

    If quantity == full amount, update location_id in place (no split needed)
    unless a merge target exists at the destination.

    Returns True on success. Raises ValueError if item not found or invalid quantity.
    """
```

> **Return type change from v1:** The original returned `Optional[Item]` where `None` meant either "item not found" or "fully moved." This is ambiguous. The method now returns `bool` (True on success) and raises `ValueError` on invalid input. The service layer wrapper (`InventoryService.transfer_item()`) handles the bool and exposes it to the UI.

### 2.11 New: `ItemRepository.transfer_serialized_items()`

```python
@staticmethod
def transfer_serialized_items(
    serial_numbers: List[str],
    to_location_id: int,
    notes: str = "",
) -> int:
    """Transfer specific serialized items to another location.

    Creates TWO TRANSFER transactions per item:
      1. Source record: location_id=source, quantity_before=1, quantity_after=0
         from_location_id=source, to_location_id=dest
      2. Destination record: location_id=dest, quantity_before=0, quantity_after=1
         from_location_id=source, to_location_id=dest

    Simply updates each item's location_id.
    Returns count transferred.
    """
```

### 2.12 New: `ItemRepository.find_non_serialized_at_location()`

```python
@staticmethod
def find_non_serialized_at_location(item_type_id: int, location_id: int) -> Optional[Item]:
    """Find the non-serialized item row for a given type at a given location.
    Used for merge-on-transfer logic.
    """
```

### 2.13 Update `add_quantity()`, `remove_quantity()`, `delete_by_serial_numbers()` — set `location_id` on transactions

These three methods create ADD/REMOVE transactions but currently don't set `location_id`. After the location feature, **every transaction must carry `location_id`** so that `AllTransactionsDialog` can filter by location accurately.

#### `ItemRepository.add_quantity()`
Read the item's `location_id` and set it on the ADD transaction:
```python
transaction = Transaction(
    # ... existing fields ...
    location_id=item.location_id,  # NEW — record location at time of ADD
)
```

#### `ItemRepository.remove_quantity()`
Same pattern:
```python
transaction = Transaction(
    # ... existing fields ...
    location_id=item.location_id,  # NEW — record location at time of REMOVE
)
```

#### `ItemRepository.delete_by_serial_numbers()`
This method creates REMOVE transactions for each item before deletion. Set `location_id` on each:
```python
for item in items:
    transaction = Transaction(
        # ... existing fields ...
        location_id=item.location_id,  # NEW — record location at time of REMOVE
    )
```

> **Audit checklist:** After implementing these changes, search the entire `repositories.py` file for `Transaction(` constructor calls and verify **every single one** sets `location_id`. Any missed call will result in transactions with `location_id=NULL` that won't appear in location-filtered views.

### 2.14 New: `TransactionRepository.get_by_location_and_date_range()`

```python
@staticmethod
def get_by_location_and_date_range(
    location_id: int,
    start: datetime,
    end: datetime,
) -> List[Transaction]:
    """Get all transactions for a specific location within a date range.

    Filters on Transaction.location_id, which is set for ALL transaction types
    (ADD/REMOVE/EDIT/TRANSFER). This gives accurate historical results regardless
    of where items have moved since the transaction occurred.
    """
```

```python
@staticmethod
def get_all_by_date_range(start: datetime, end: datetime) -> List[Transaction]:
    """Get all transactions within a date range (no location filter)."""
```

### 2.15 New: `ItemRepository.get_by_type()`

```python
@staticmethod
def get_by_type(item_type_id: int) -> List[Item]:
    """Return all Item rows for a given ItemType, across all locations.

    Used by TransferDialog when opened from the "All Locations" view to
    build a per-location breakdown of items and serial numbers.
    """
    with session_scope() as session:
        items = (
            session.query(Item)
            .filter(Item.item_type_id == item_type_id)
            .order_by(Item.location_id, Item.serial_number)
            .all()
        )
        return [_detach_item(item) for item in items]
```

### 2.16 New: `ItemTypeRepository.get_by_ids()`

```python
@staticmethod
def get_by_ids(type_ids: List[int]) -> Dict[int, "ItemType"]:
    """Batch-fetch ItemTypes by a list of IDs. Returns dict mapping id → detached ItemType.

    Used by AllTransactionsDialog to resolve item_type_id → display name
    without N+1 queries.
    """
    with session_scope() as session:
        types = (
            session.query(ItemType)
            .filter(ItemType.id.in_(type_ids))
            .all()
        )
        return {t.id: _detach_item_type(t) for t in types}
```

---

## 3. Service Layer — `services.py`

### 3.1 New `LocationService`

```python
class LocationService:
    """Service for location management."""

    @staticmethod
    def create_location(name: str, description: str = "") -> "Location":
        """Create a new location. Raises ValueError if name exists."""

    @staticmethod
    def get_all_locations() -> List["Location"]:
        """Get all locations ordered by name."""

    @staticmethod
    def get_location_by_id(location_id: int) -> Optional["Location"]:
        """Get a location by ID."""

    @staticmethod
    def update_location(location_id: int, name: str = None, description: str = None) -> Optional["Location"]:
        """Update a location."""

    @staticmethod
    def delete_location(location_id: int) -> bool:
        """Delete location. Raises ValueError if items exist."""

    @staticmethod
    def can_delete_location(location_id: int) -> Tuple[bool, int]:
        """Check if location can be deleted. Returns (can_delete, item_count)."""

    @staticmethod
    def move_all_items_and_delete(from_location_id: int, to_location_id: int) -> bool:
        """Move all items from source to destination, then delete source location.

        This is intentionally service-layer logic rather than repository logic,
        because the merge step (non-serialized items of the same type at destination)
        requires coordinating multiple ItemRepository calls within one operation.

        Steps:
          1. For each non-serialized item at source:
             a. Check if same type exists at destination → merge (add qty) or create new row
             b. Create 2 TRANSFER transactions (source + destination) for audit trail
          2. For each serialized item at source:
             a. Update location_id to destination
             b. Create 2 TRANSFER transactions per serial number
          3. Delete the source location (now empty)

        MUST create TRANSFER transactions so the user can see why items appeared
        at the destination and where they came from. The transaction notes should
        indicate this was an administrative move due to location deletion, e.g.:
        tr("transaction.notes.location_deleted_move").format(from_loc=..., to_loc=...)
        """

    @staticmethod
    def get_location_count() -> int:
        """Return total number of locations."""

    @staticmethod
    def assign_all_unassigned_items(location_id: int) -> int:
        """Assign all items with location_id=NULL to the given location.
        Used during first-launch wizard. Returns count assigned."""
```

### 3.2 Update `InventoryService`

#### 3.2.1 Update `create_item()` and `create_serialized_item()`
- Replace `location: str = ""` with `location_id: int` (required, no default)
- Pass through to repository

#### 3.2.2 Update `create_or_merge_item()`

> **Verify this method exists in `services.py`** before the implementation step — it is referenced in the plan but not visible in the first 60 lines of the file.

- Replace `location: str = ""` with `location_id: int`
- Merge logic must now use `find_non_serialized_at_location(item_type_id, location_id)` — merge only within the same location, not across locations

#### 3.2.3 Update `edit_item()`
- Replace `location: str = ""` with `location_id: int`

#### 3.2.4 Update `get_all_items_grouped()`
```python
@staticmethod
def get_all_items_grouped(location_id: int = None) -> List[GroupedInventoryItem]:
    """Get all inventory items grouped by type.
    When location_id is provided, only items at that location.
    When location_id is None (all locations), group across all locations.
    """
    # Batch-load all locations upfront to avoid N+1 queries on DTO construction
    location_map = {loc.id: loc.name for loc in LocationRepository.get_all()}
    # Pass location_map to from_item_type_and_items() for location_name resolution
```

#### 3.2.5 New transfer methods
```python
@staticmethod
def transfer_item(
    item_id: int,
    to_location_id: int,
    quantity: int = None,
    notes: str = "",
) -> bool:
    """Transfer non-serialized item. Returns True on success.
    Raises ValueError on invalid input (item not found, bad quantity, etc.)."""

@staticmethod
def transfer_serialized_items(
    serial_numbers: List[str],
    to_location_id: int,
    notes: str = "",
) -> int:
    """Transfer serialized items. Returns count transferred."""
```

### 3.3 Update `SearchService.search()`
- Add `location_id: int = None` parameter
- Pass to `ItemRepository.search()`

### 3.4 Update `_transaction_to_dict()` helper

The `_transaction_to_dict()` function at the bottom of `services.py` converts Transaction objects to dicts for the UI. It must include the three new location columns:

```python
def _transaction_to_dict(trans) -> dict:
    """Convert a Transaction to a dictionary."""
    return {
        "id": trans.id,
        "item_type_id": trans.item_type_id,
        "type": trans.transaction_type.value,
        "quantity_change": trans.quantity_change,
        "quantity_before": trans.quantity_before,
        "quantity_after": trans.quantity_after,
        "notes": trans.notes,
        "serial_number": trans.serial_number,
        "location_id": trans.location_id,                # NEW
        "from_location_id": trans.from_location_id,      # NEW
        "to_location_id": trans.to_location_id,          # NEW
        "created_at": trans.created_at,
    }
```

### 3.5 Update `TransactionService`

```python
@staticmethod
def get_transactions_by_location_and_date_range(
    location_id: int,
    start: datetime,
    end: datetime,
) -> List[Transaction]:
    """Get all transactions for a location within a date range.

    Delegates to TransactionRepository.get_by_location_and_date_range() which
    filters on Transaction.location_id. Because location_id is recorded on ALL
    transaction types at the time they occur, results are historically accurate
    even if items have been transferred since then.
    """

@staticmethod
def get_all_transactions_by_date_range(start: datetime, end: datetime) -> List[Transaction]:
    """Get all transactions within a date range (no location filter)."""
```

---

## 4. DTO Layer — `ui_entities/inventory_item.py`

### 4.1 Update `InventoryItem`

```python
@dataclass
class InventoryItem:
    id: int
    item_type_id: int
    item_type_name: str
    item_sub_type: str
    is_serialized: bool
    quantity: int
    serial_number: Optional[str]
    location_id: int               # CHANGED — was Optional[str] location
    location_name: str             # NEW — resolved name for display
    condition: Optional[str]
    details: Optional[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db_models(cls, item, item_type, location_name: str = ""):
        return cls(
            id=item.id,
            item_type_id=item.item_type_id,
            item_type_name=item_type.name,
            item_sub_type=item_type.sub_type or "",
            is_serialized=item_type.is_serialized,
            quantity=item.quantity,
            serial_number=item.serial_number,
            location_id=item.location_id,
            location_name=location_name,
            condition=item.condition or "",
            details=item_type.details or "",
            created_at=item.created_at,
            updated_at=item.updated_at
        )

    # Keep backward-compat property so existing display_info / UI code still works
    @property
    def location(self) -> str:
        return self.location_name or ""
```

### 4.2 Update `GroupedInventoryItem`

```python
@dataclass
class GroupedInventoryItem:
    item_type_id: int
    item_type_name: str
    item_sub_type: str
    is_serialized: bool
    details: str
    total_quantity: int
    item_count: int
    serial_numbers: List[str] = field(default_factory=list)
    item_ids: List[int] = field(default_factory=list)
    location_id: Optional[int] = None      # NEW — set when filtered to single location
    location_name: str = ""                 # NEW — set when filtered to single location
    is_multi_location: bool = False         # NEW — True when items span multiple locations
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_item_type_and_items(cls, item_type, items: list, location_id: int = None, location_name: str = ""):
        serial_numbers = [item.serial_number for item in items if item.serial_number]
        item_ids = [item.id for item in items]
        total_quantity = sum(item.quantity for item in items)

        # Detect multi-location
        unique_locations = set(item.location_id for item in items if item.location_id)
        is_multi_location = len(unique_locations) > 1

        created_dates = [item.created_at for item in items if item.created_at]
        updated_dates = [item.updated_at for item in items if item.updated_at]

        return cls(
            item_type_id=item_type.id,
            item_type_name=item_type.name,
            item_sub_type=item_type.sub_type or "",
            is_serialized=item_type.is_serialized,
            details=item_type.details or "",
            total_quantity=total_quantity,
            item_count=len(items),
            serial_numbers=sorted(serial_numbers),
            item_ids=item_ids,
            location_id=location_id,
            location_name=location_name,
            is_multi_location=is_multi_location,
            created_at=min(created_dates) if created_dates else None,
            updated_at=max(updated_dates) if updated_dates else None,
        )

    # Keep backward-compat property
    @property
    def location(self) -> str:
        if self.is_multi_location:
            return ""  # Delegate shows "Multiple locations" badge
        return self.location_name or ""
```

> **Important:** `GroupedInventoryItem.serial_numbers` contains **all** serial numbers across all locations when in "All Locations" view (`is_multi_location=True`). Dialogs that show serial numbers to the user (particularly `RemoveSerialNumberDialog`) must filter to only serials at the active location. See Section 5.12.

### 4.3 Location resolution in services

When creating DTOs, the service layer must resolve `location_id` → `location_name`. Do this efficiently with a single batch lookup:

```python
# In InventoryService.get_all_items_grouped():
location_map = {loc.id: loc.name for loc in LocationRepository.get_all()}
# Pass location_name=location_map.get(item.location_id, "") to from_item_type_and_items()
```

---

## 5. UI Layer

### 5.1 New: `LocationSelectorWidget` (`ui_entities/location_selector.py`)

A horizontal bar widget placed at the very top of the main window (above search):

```
[ 📍 Location: [▼ Warehouse A    ] ]  [ ⚙ Manage Locations ]
```

**Implementation details:**
- `QComboBox` with all locations + "All Locations" entry at index 0
  - "All Locations" has user data `None`
  - Each location has user data = `location_id`
- Styled with `apply_combo_box_style()`
- "Manage Locations" `QPushButton` styled with `apply_button_style(..., "secondary")`
- `refresh_locations()` method to reload from DB
- `set_current_location(location_id)` method for restoring from config; pass `None` to select "All Locations"
- `get_current_location_id() -> Optional[int]` — returns None for "All Locations"

**Signals:**
```python
location_changed = pyqtSignal(object)  # int (location_id) or None (all)
manage_requested = pyqtSignal()
```

### 5.2 New: First-Launch Location Dialog (`ui_entities/first_location_dialog.py`)

A **mandatory** modal dialog shown on startup when no locations exist:

```
┌─────────────────────────────────────────────┐
│     Welcome to Inventory Manager!            │
│                                              │
│  Please create your first storage location   │
│  to get started.                             │
│                                              │
│  Location name: [____________________]       │
│  Description:   [____________________]       │
│                               (optional)     │
│                                              │
│                          [Create]            │
└─────────────────────────────────────────────┘
```

**Behavior:**
- Cannot be dismissed (no close button, no Cancel). User MUST create a location.
- On create: creates the location, assigns all existing items (`location_id IS NULL`) to it.
- `get_location_id()` returns the created location ID.
- `self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)`

### 5.3 New: `LocationManagementDialog` (`ui_entities/location_management_dialog.py`)

Modal dialog for CRUD on locations:

```
┌─────────────────────────────────────────────┐
│         Manage Locations                     │
├─────────────────────────────────────────────┤
│  [+ Add Location]                            │
│                                              │
│  ┌─────────────────────────────────────────┐ │
│  │ Warehouse A  (15 items) [Rename][Delete]│ │
│  │ Warehouse B  (3 items)  [Rename][Delete]│ │
│  │ Office       (0 items)  [Rename][Delete]│ │
│  └─────────────────────────────────────────┘ │
│                                              │
│                              [Close]         │
└─────────────────────────────────────────────┘
```

- Show item count next to each location name
- **Add Location:** Small input dialog (name + optional description)
- **Rename Location:** Small input dialog pre-filled with current name
- **Delete Location:**
  - If location has items → warning dialog:
    ```
    "Location 'X' contains N items. Move all items to:"
    [▼ Select destination location]   (excludes the location being deleted)
    [Move & Delete] [Cancel]
    ```
  - If location is empty → simple confirm dialog → delete
  - If only 1 location exists and has items → show error "Cannot delete the only location. Create another location first."
- Dialog emits a signal or sets a flag when locations have changed, so MainWindow can refresh.

### 5.4 New: `TransferDialog` (`ui_entities/transfer_dialog.py`)

Dialog for transferring items between locations:

```
┌─────────────────────────────────────────────┐
│         Transfer Items                       │
├─────────────────────────────────────────────┤
│  Item: Laptop - ThinkPad X1                 │
│  Current Location: Warehouse A               │
│                                              │
│  Destination: [▼ Select location       ]     │
│                                              │
│  ── For non-serialized items: ──             │
│  Quantity to transfer: [___5___]             │
│  (Available: 10)                             │
│                                              │
│  ── For serialized items: ──                 │
│  Select serial numbers to transfer:          │
│  ☑ SN-001                                    │
│  ☐ SN-002                                    │
│  ☑ SN-003                                    │
│  Selected: 2 of 3                            │
│                                              │
│  Notes: [________________________]           │
│                (optional)                    │
│                                              │
│                    [Cancel] [Transfer]        │
└─────────────────────────────────────────────┘
```

**Behavior:**
- Destination dropdown: all locations except the current one.
- **Non-serialized items:** Quantity input (1 to current qty). Uses `QIntValidator`.
- **Serialized items:** Checkbox list of serial numbers **at the current (source) location only** — not all serial numbers of the type. At least one must be selected.
- Notes field (optional) for audit trail.
- On accept: calls `InventoryService.transfer_item()` or `transfer_serialized_items()`.
- Style with existing `apply_*` helpers.

**Edge case — "All Locations" view:**
When user right-clicks a grouped item while "All Locations" is selected, and the item exists in multiple locations:
- Show a **source location dropdown** (pre-populated with the locations where this item type exists) in addition to the destination.
- For serialized items, show serial numbers grouped by their location, filtered to the selected source location.

**Data fetching for per-item location info:**
The `GroupedInventoryItem` DTO contains `item_ids` and `serial_numbers` as flat lists without per-item `location_id`. The `TransferDialog` must call back to the repository to get per-item location data when opened from "All Locations" view:

```python
# In TransferDialog.__init__(), when current_location_id is None (all locations):
items_with_locations = ItemRepository.get_by_type(item.item_type_id)
# Build a dict: {location_id: [list of items/serial_numbers at that location]}
location_groups = defaultdict(list)
for db_item in items_with_locations:
    location_groups[db_item.location_id].append(db_item)

# Populate source location dropdown from location_groups.keys()
# When source location changes, update the serial number list / quantity available
```

For **non-serialized items**: each `location_id` key maps to a single item row with its quantity. The quantity spinner max should update when the source location dropdown changes.

For **serialized items**: each `location_id` key maps to a list of serial numbers. The checkbox list should update to show only serials at the selected source location.

Add `ItemRepository.get_items_by_type_grouped_by_location(type_id: int) -> Dict[int, List[Item]]` helper method for this use case, or reuse `get_by_type()` and group in the dialog.

### 5.5 Update `InventoryListView` — Context Menu

Add new signal and menu action:

```python
# New signal
transfer_requested = pyqtSignal(int, object)

# In _show_context_menu(), add after transactions_action:
transfer_action = QAction(tr("menu.transfer"), self)
transfer_action.triggered.connect(
    lambda: self.transfer_requested.emit(row, item)
)
menu.addAction(transfer_action)
```

### 5.6 Update `MainWindow`

#### 5.6.1 Startup sequence in `__init__()`

The init order is critical. After the location feature, it must be:

```python
def __init__(self):
    super().__init__()
    self._current_location_id: Optional[int] = None  # init early — methods below may read it
    uic.loadUi(resource_path("ui/MainWindow.ui"), self)

    # 1. Initialize database (creates tables if needed)
    init_database()

    # 2. Ensure at least one location exists (may show wizard)
    self._ensure_location_exists()

    # 3. Determine current location (from config or default)
    #    Must run BEFORE _check_unassigned_items, which uses _current_location_id
    self._init_current_location()

    # 4. Check for unassigned items (integrity check)
    self._check_unassigned_items()

    # 5. Set up UI components (location selector, search, list)
    self._setup_ui()
    self._setup_theme_menu()
    self._setup_location_selector()   # NEW — must be before search/list
    self._setup_search_widget()
    self._setup_inventory_list()

    # 6. Set location selector to current location (no signal emission)
    self.location_selector.set_current_location(self._current_location_id)

    # 7. Load data filtered by current location
    self._load_data_from_db()

    # 8. Connect signals, restore window
    self._connect_signals()
    self._restore_window_state()
```

**Key points:**
- `_current_location_id` is declared `None` at the very top of `__init__()` so any method that reads it early gets a safe default
- `_ensure_location_exists()` runs before any UI setup
- `_init_current_location()` runs **before** `_check_unassigned_items()` — the integrity check uses `_current_location_id` to pick the assignment target location
- `_check_unassigned_items()` runs after location is determined, before loading data
- `_setup_location_selector()` creates the widget but doesn't trigger `location_changed` yet
- `set_current_location()` programmatically sets the dropdown (should NOT emit `location_changed` to avoid double-load)
- `_load_data_from_db()` uses `self._current_location_id` to filter

```python
def _ensure_location_exists(self):
    """Show first-location dialog if no locations exist."""
    if LocationService.get_location_count() == 0:
        from ui_entities.first_location_dialog import FirstLocationDialog
        dialog = FirstLocationDialog(self)
        dialog.exec()  # Cannot be dismissed
        LocationService.assign_all_unassigned_items(dialog.get_location_id())

def _init_current_location(self):
    """Determine current location from config or default to first.

    Uses a sentinel value to distinguish three states:
      - Key absent entirely  → first run, default to first location
      - Key present, null    → user had "All Locations" selected
      - Key present, int     → specific location (validate it still exists)

    Requires config.get(key, default) to accept an optional second argument.
    If the current config.py only accepts one argument, add the two-argument
    form before implementing this method (see Step 1 prerequisite).
    """
    _MISSING = object()  # sentinel — distinct from None
    saved_loc = config.get("ui.last_location_id", _MISSING)

    if saved_loc is _MISSING:
        # Key absent entirely — first run after this feature, default to first location
        locations = LocationService.get_all_locations()
        self._current_location_id = locations[0].id if locations else None
    elif saved_loc is None:
        # Key present with null — user explicitly selected "All Locations"
        self._current_location_id = None
    else:
        # Key present with int — validate the location still exists
        if LocationService.get_location_by_id(saved_loc):
            self._current_location_id = saved_loc
        else:
            # Location was deleted — fall back to first available
            locations = LocationService.get_all_locations()
            self._current_location_id = locations[0].id if locations else None
```

#### 5.6.2 Add location selector bar
In `_setup_inventory_list()`:

```python
# Layout order:
# 1. LocationSelectorWidget  (NEW)
# 2. SearchWidget
# 3. InventoryListView
# 4. Bottom bar: [Add Item]  <spacer>  [All Transactions]
```

#### 5.6.3 Track current location

`_current_location_id` is declared at the top of `__init__()` and set by `_init_current_location()`. See **Section 5.6.1** for the complete startup sequence and the full three-case sentinel restore logic.

Save on change:
```python
def _on_location_changed(self, location_id):
    self._current_location_id = location_id
    config.set("ui.last_location_id", location_id)  # None is valid — stores null in JSON
    self._refresh_item_list()
```

#### 5.6.4 Connect signals
```python
self.location_selector.location_changed.connect(self._on_location_changed)
self.location_selector.manage_requested.connect(self._on_manage_locations)
self.inventory_list.transfer_requested.connect(self._on_transfer_item)
```

#### 5.6.5 Update `_refresh_item_list()`
```python
def _refresh_item_list(self):
    self.inventory_model.clear()
    items = InventoryService.get_all_items_grouped(location_id=self._current_location_id)
    for item in items:
        self.inventory_model.add_item(item)
```

#### 5.6.6 `_on_transfer_item(row, item)`
```python
def _on_transfer_item(self, row: int, item):
    current_loc = self._current_location_id
    dialog = TransferDialog(item, current_location_id=current_loc, parent=self)
    if dialog.exec():
        self._refresh_item_list()
```

#### 5.6.7 `_on_manage_locations()`
```python
def _on_manage_locations(self):
    dialog = LocationManagementDialog(self)
    dialog.exec()
    # Refresh location selector and item list
    self.location_selector.refresh_locations()
    # If the current location was deleted, reset to first available location
    if self._current_location_id and not LocationService.get_location_by_id(self._current_location_id):
        locations = LocationService.get_all_locations()
        self._current_location_id = locations[0].id if locations else None
        self.location_selector.set_current_location(self._current_location_id)
        config.set("ui.last_location_id", self._current_location_id)
    self._refresh_item_list()
```

#### 5.6.8 Update `_on_add_clicked()`
Pass `self._current_location_id` to the add dialog:
```python
dialog = AddItemDialog(parent=self, current_location_id=self._current_location_id)
```

**When `_current_location_id` is None ("All Locations" view):**
The dialog opens with no location pre-selected. The location `QComboBox` shows the placeholder text (e.g., "Select location..."). The user **must** select a location before saving — validation rejects the form if no location is selected. The combo's first entry should NOT be "All Locations" (which is only for filtering, not for item creation). Populate only with real locations from `LocationService.get_all_locations()`.

#### 5.6.9 Add "All Transactions" button at bottom
Add next to the "Add Item" button (at the bottom of the layout):

```python
# In the bottom horizontal layout:
self.all_transactions_button = QPushButton(tr("button.all_transactions"))
apply_button_style(self.all_transactions_button, "info")
self.all_transactions_button.clicked.connect(self._on_show_all_transactions)
# Add to the right side of the bottom bar
```

```python
def _on_show_all_transactions(self):
    """Show all transactions dialog, filtered by current location by default."""
    dialog = AllTransactionsDialog(
        current_location_id=self._current_location_id,
        parent=self,
    )
    dialog.exec()
```

### 5.7 New: `AllTransactionsDialog` (`ui_entities/all_transactions_dialog.py`)

A dialog showing all transactions (not filtered by item type), with location filter:

```
┌──────────────────────────────────────────────────────┐
│              All Transactions                         │
├──────────────────────────────────────────────────────┤
│  Location: [▼ Warehouse A    ]                       │
│  Start date: [__________]  End date: [__________]    │
│                                      [Apply Filter]  │
│                                                      │
│  ┌──────────────────────────────────────────────────┐│
│  │ Date     │ Type  │ Item      │ Change │ Notes    ││
│  │──────────│───────│───────────│────────│──────────││
│  │ 23.02.26 │ ADD   │ Laptop X1 │ +5     │ Initial  ││
│  │ 23.02.26 │ TRANS │ Mouse     │ -3     │ To WH B  ││
│  │ 22.02.26 │ EDIT  │ Keyboard  │ 0      │ Fix qty  ││
│  └──────────────────────────────────────────────────┘│
│                                                      │
│                                       [Close]        │
└──────────────────────────────────────────────────────┘
```

- **Location dropdown:** All locations + "All Locations". Default = current location from MainWindow.
- **Date range:** Same pattern as existing `TransactionsDialog`.
- **Table columns:** Date, Type (ADD/REMOVE/EDIT/TRANSFER), Item Type Name, Qty Change, Before, After, Serial Number, Notes, From Location, To Location.
- Show From/To Location columns only when "All Locations" is selected or for TRANSFER type transactions.
- Uses `TransactionService.get_transactions_by_location_and_date_range()` (filters on `Transaction.location_id`) or `get_all_transactions_by_date_range()`.

**Location name resolution for transaction display:**
Transaction dicts contain `location_id`, `from_location_id`, `to_location_id` as integer FKs. The dialog must resolve these to display names. Two approaches:

**Recommended approach — batch lookup in the dialog:**
```python
# In AllTransactionsDialog, after fetching transactions:
self._location_map = {loc.id: loc.name for loc in LocationService.get_all_locations()}

# When populating table rows:
location_name = self._location_map.get(trans["location_id"], "-")
from_loc_name = self._location_map.get(trans["from_location_id"], "-")
to_loc_name = self._location_map.get(trans["to_location_id"], "-")
```

Also resolve `item_type_id` → item type name using `ItemTypeRepository.get_by_ids()` batch lookup:
```python
type_ids = list({t["item_type_id"] for t in transactions})
type_map = ItemTypeRepository.get_by_ids(type_ids)
# Display: type_map[trans["item_type_id"]].display_name
```

Both maps are built once per filter application, not per row. This avoids N+1 queries.

### 5.8 Update `SearchWidget`

Add "Search all locations" checkbox:

```python
# In _setup_ui(), in the search_row, after clear_button:
self.all_locations_checkbox = QCheckBox(tr("search.all_locations"))
self.all_locations_checkbox.setChecked(False)  # Default: current location only
search_row.addWidget(self.all_locations_checkbox)
```

**Signal update** — The simplest approach: keep the existing signal signature and let MainWindow check the checkbox state:

```python
# In MainWindow._on_search():
def _on_search(self, query: str, field: str):
    search_all = self.search_widget.all_locations_checkbox.isChecked()
    location_id = None if search_all else self._current_location_id
    results = SearchService.search(query, field_value, location_id=location_id, save_to_history=False)
    self._display_search_results(results)
```

**Note:** When "All Locations" is already selected in the location dropdown, the checkbox is redundant. Hide or disable it when viewing all locations:
```python
def _on_location_changed(self, location_id):
    # ...
    is_all = location_id is None
    self.search_widget.all_locations_checkbox.setVisible(not is_all)
    if is_all:
        self.search_widget.all_locations_checkbox.setChecked(False)
```

### 5.9 Update `AddItemDialog`

- Constructor: `AddItemDialog(parent=None, current_location_id: int = None)`
- **Add a `QComboBox` for location** populated from `LocationService.get_all_locations()`
- Pre-select `current_location_id` if provided
- If `current_location_id` is None, user must select a location manually
- Location is **required** — validation must check it's selected
- Pass `location_id` to `InventoryService.create_item()` / `create_serialized_item()`

### 5.10 Update `EditItemDialog`

- Constructor: `EditItemDialog(item, parent=None, current_location_id: int = None)`
- Add `QComboBox` for location (pre-selected to item's current location)
- For grouped items:
  - If single location (viewed from specific location): show that location, allow changing (moves all items of the type at this location)
  - If multi-location (viewed from "All Locations"): show read-only "Multiple locations" — editing location per-type doesn't make sense here. Transfer should be used instead.
- Pass `location_id` to `InventoryService.edit_item()`

**Critical — update `_on_save_clicked()` InventoryItem constructor:**
The current code in `_on_save_clicked()` builds an `InventoryItem(...)` directly with `location=self._original_item.location`. After the location feature, `InventoryItem` no longer has a `location` string field — it has `location_id: int` and `location_name: str`. Update the constructor call:

```python
self._result_item = InventoryItem(
    # ... existing fields ...
    location_id=self.location_combo.currentData(),     # NEW — from QComboBox
    location_name=self.location_combo.currentText(),   # NEW — display name
    # REMOVE: location=self._original_item.location,
    condition=self._original_item.condition,
    details=item_details,
    # ...
)
```

Also update `get_item()` callers in `MainWindow._on_edit_item()` to pass `location_id` from the returned InventoryItem to `InventoryService.edit_item()`.

### 5.11 Update `AddSerialNumberDialog`

- Add `QComboBox` for location, pre-selected to current location
- Pass `location_id` back to caller via `get_location_id()` method
- Constructor: `AddSerialNumberDialog(..., current_location_id: int = None)`

### 5.12 Update `RemoveSerialNumberDialog`

- Constructor: `RemoveSerialNumberDialog(..., current_location_id: int = None)`
- When `current_location_id` is provided, show **only** serial numbers at that location, not all serial numbers for the type.
- When invoked from "All Locations" view on a multi-location group: either show a source location picker first, or show all serials grouped by location with location labels.
- This prevents a user viewing Warehouse A from accidentally selecting and deleting a serial that physically lives in Warehouse B.

### 5.13 Update `ItemDetailsDialog`

- Display location name in the details form
- For grouped items:
  - If single location: show location name
  - If multi-location: show breakdown — which serial numbers are at which location
    ```
    Serial Numbers:
      Warehouse A:
        SN-001, SN-002
      Warehouse B:
        SN-003
    ```
- **For serialized items:** Add context menu (right-click) on serial number list items:
  - "Transfer to..." → opens a small dialog to pick destination location → transfers just that one serial

### 5.14 Update `InventoryItemDelegate`

Show location in the item row. Update the 2×2 grid layout to include location info:

**Option A — Add location as a 5th field (below the 2×2 grid) — Recommended:**
- Increase `ROW_HEIGHT` slightly (e.g., 80 → 95)
- Add a row below the grid: `📍 Location: Warehouse A` (or "Multiple locations" badge)

For multi-location items (when viewing "All Locations"):
- Show a small badge: "📍 Multiple locations" in a muted style (similar to serialized badge)
- Badge color: `#1565c0` (blue), theme-independent for consistency

### 5.15 Update `TransactionsDialog`

- Add "From Location" and "To Location" columns for TRANSFER type transactions
- Handle new `TransactionType.TRANSFER` in display logic
- Show location names resolved from `from_location_id` / `to_location_id`

### 5.16 Update `InventoryModel`

Add new roles:

```python
class InventoryItemRole:
    # ... existing roles ...
    LocationId = Qt.ItemDataRole.UserRole + 10
    LocationName = Qt.ItemDataRole.UserRole + 11
    IsMultiLocation = Qt.ItemDataRole.UserRole + 12
```

Return data in `data()`:
```python
if role == InventoryItemRole.LocationId:
    return item.location_id if hasattr(item, 'location_id') else None

if role == InventoryItemRole.LocationName:
    return item.location_name if hasattr(item, 'location_name') else ""

if role == InventoryItemRole.IsMultiLocation:
    if isinstance(item, GroupedInventoryItem):
        return item.is_multi_location
    return False
```

---

## 6. Translations — `ui_entities/translations.py`

Add these keys to **both** Ukrainian and English dictionaries:

```python
# ── Ukrainian ──

# Location management
"location.title": "Місцезнаходження",
"location.all": "Всі місця",
"location.manage": "Керувати",
"location.manage.title": "Керування місцезнаходженнями",
"location.add": "Додати місце",
"location.add.title": "Додати нове місцезнаходження",
"location.rename": "Перейменувати",
"location.rename.title": "Перейменувати місцезнаходження",
"location.delete": "Видалити",
"location.name": "Назва:",
"location.description": "Опис:",
"location.name.placeholder": "Введіть назву місця...",
"location.description.placeholder": "Введіть опис (необов'язково)...",
"location.item_count": "{count} елементів",
"location.delete.has_items": "Місце «{name}» містить {count} елементів. Перемістіть усі елементи до:",
"location.delete.confirm": "Видалити місцезнаходження «{name}»?",
"location.delete.empty_confirm": "Видалити порожнє місцезнаходження «{name}»?",
"location.move_and_delete": "Перемістити та видалити",
"location.error.name_required": "Назва місця обов'язкова",
"location.error.name_exists": "Місце з такою назвою вже існує",
"location.error.cannot_delete": "Неможливо видалити місце з елементами",
"location.error.last_location": "Неможливо видалити єдине місце. Створіть інше місце спочатку.",
"location.multiple": "Декілька місць",

# First launch
"location.first_launch.title": "Ласкаво просимо",
"location.first_launch.message": "Будь ласка, створіть перше місце зберігання, щоб розпочати роботу.",

# Transfer
"menu.transfer": "Перемістити",
"transfer.title": "Переміщення елементів",
"transfer.source": "Поточне місце:",
"transfer.destination": "Місце призначення:",
"transfer.quantity": "Кількість для переміщення:",
"transfer.available": "Доступно: {count}",
"transfer.select_serials": "Оберіть серійні номери для переміщення:",
"transfer.selected_count": "Обрано: {selected} з {total}",
"transfer.notes": "Примітки:",
"transfer.button": "Перемістити",
"transfer.error.no_destination": "Оберіть місце призначення",
"transfer.error.no_quantity": "Вкажіть кількість для переміщення",
"transfer.error.no_serials": "Оберіть хоча б один серійний номер",
"transfer.error.same_location": "Місце призначення збігається з поточним",
"transfer.success": "Успішно переміщено",

# Search
"search.all_locations": "Шукати у всіх місцях",

# All transactions
"button.all_transactions": "Всі транзакції",
"dialog.all_transactions.title": "Всі транзакції",
"dialog.all_transactions.location_filter": "Місцезнаходження:",

# Transaction type
"transaction.type.transfer": "Переміщення",
"transaction.column.from_location": "З місця",
"transaction.column.to_location": "До місця",
"transaction.column.item_type": "Тип\nелемента",

# Transaction notes
"transaction.notes.transfer": "Переміщено з «{from_loc}» до «{to_loc}»",
"transaction.notes.transfer_out": "Переміщено до «{to_loc}»",
"transaction.notes.transfer_in": "Переміщено з «{from_loc}»",
"transaction.notes.location_deleted_move": "Автоматично переміщено: місце «{from_loc}» видалено",

# Unassigned items
"location.unassigned.title": "Непризначені елементи",
"location.unassigned.message": "Знайдено {count} елементів без місцезнаходження. Вони будуть переміщені до «{location}».",


# ── English ──

# Location management
"location.title": "Location",
"location.all": "All Locations",
"location.manage": "Manage",
"location.manage.title": "Manage Locations",
"location.add": "Add Location",
"location.add.title": "Add New Location",
"location.rename": "Rename",
"location.rename.title": "Rename Location",
"location.delete": "Delete",
"location.name": "Name:",
"location.description": "Description:",
"location.name.placeholder": "Enter location name...",
"location.description.placeholder": "Enter description (optional)...",
"location.item_count": "{count} items",
"location.delete.has_items": "Location '{name}' contains {count} items. Move all items to:",
"location.delete.confirm": "Delete location '{name}'?",
"location.delete.empty_confirm": "Delete empty location '{name}'?",
"location.move_and_delete": "Move & Delete",
"location.error.name_required": "Location name is required",
"location.error.name_exists": "A location with this name already exists",
"location.error.cannot_delete": "Cannot delete location with items",
"location.error.last_location": "Cannot delete the only location. Create another location first.",
"location.multiple": "Multiple locations",

# First launch
"location.first_launch.title": "Welcome",
"location.first_launch.message": "Please create your first storage location to get started.",

# Transfer
"menu.transfer": "Transfer",
"transfer.title": "Transfer Items",
"transfer.source": "Current Location:",
"transfer.destination": "Destination:",
"transfer.quantity": "Quantity to transfer:",
"transfer.available": "Available: {count}",
"transfer.select_serials": "Select serial numbers to transfer:",
"transfer.selected_count": "Selected: {selected} of {total}",
"transfer.notes": "Notes:",
"transfer.button": "Transfer",
"transfer.error.no_destination": "Select a destination location",
"transfer.error.no_quantity": "Specify quantity to transfer",
"transfer.error.no_serials": "Select at least one serial number",
"transfer.error.same_location": "Destination is the same as current location",
"transfer.success": "Successfully transferred",

# Search
"search.all_locations": "Search all locations",

# All transactions
"button.all_transactions": "All Transactions",
"dialog.all_transactions.title": "All Transactions",
"dialog.all_transactions.location_filter": "Location:",

# Transaction type
"transaction.type.transfer": "Transfer",
"transaction.column.from_location": "From Location",
"transaction.column.to_location": "To Location",
"transaction.column.item_type": "Item Type",

# Transaction notes
"transaction.notes.transfer": "Transferred from '{from_loc}' to '{to_loc}'",
"transaction.notes.transfer_out": "Transferred to '{to_loc}'",
"transaction.notes.transfer_in": "Transferred from '{from_loc}'",
"transaction.notes.location_deleted_move": "Auto-moved: location '{from_loc}' was deleted",

# Unassigned items
"location.unassigned.title": "Unassigned Items",
"location.unassigned.message": "Found {count} items without a location. They will be moved to '{location}'.",
```

---

## 7. Configuration

Save last selected location in config:
```json
{
  "ui": {
    "last_location_id": 1
  }
}
```

Three distinct states must be handled at startup (see Section 5.6.3 for full logic):

| Stored value | Meaning | Restore to |
|---|---|---|
| Key missing | First run with this feature | First available location |
| `null` | User had "All Locations" selected | "All Locations" |
| Integer | Specific location was selected | Validate exists → that location; else first available |

- On location change: save immediately via `config.set("ui.last_location_id", location_id)` (storing `None` as JSON null is valid)

---

## 8. Implementation Order (Optimized for Claude Code)

Execute steps in this exact order. Each step is independently testable.

### Step 1: Model & Migration

> **Prerequisite — `config.py`:** `_init_current_location()` calls `config.get(key, default)` with a sentinel as the second argument to distinguish "key absent" from "key = null". Ensure `Config.get()` accepts an optional `default` parameter. If it currently only accepts one argument, add the two-argument form now — before Step 6.

1. Update `TransactionType` enum — add `TRANSFER = "transfer"` (no DB ALTER needed for SQLite)
2. Add `Location` model to `models.py`
3. Update `Item` model — replace `location` text column with `location_id` FK; add backward-compat `@property location` with deprecation note
4. Update `Transaction` model — add `location_id`, `from_location_id`, `to_location_id`
5. Add `render_as_batch=True` to `alembic/env.py` (both online and offline functions)
6. Generate Alembic migration: `alembic revision --autogenerate -m "add_locations_table_and_transfer"`
7. Edit migration: use `batch_alter_table`, drop old `location` column, add `location_id` on items (nullable for wizard), add all three location columns on transactions; add explicit comment about SQLite enum VARCHAR
8. Run migration: `alembic upgrade head`
9. Verify DB schema is correct

### Step 2: Repository Layer
1. Add `_detach_location()` helper to `repositories.py`
2. Add `LocationRepository` class (CRUD + item count; no move logic — that lives in service layer)
3. Update `_detach_transaction()` — copy `location_id`, `from_location_id`, `to_location_id` (Section 2.3)
4. Update `_detach_item()` — replace `location` with `location_id`; add doc note about compat property limitation
5. Update `ItemRepository.create()` — `location_id: int` (mandatory); populate `location_id` on ADD transaction
6. Update `ItemRepository.create_serialized()` — `location_id: int`; populate `location_id` on transaction
7. Update `ItemRepository.edit_item()` — `location_id: int`; populate `location_id` on EDIT transaction
8. Update `ItemRepository.update()` — `location_id: int = None`
9. **Update `ItemRepository.add_quantity()`** — set `location_id=item.location_id` on ADD transaction (Section 2.13)
10. **Update `ItemRepository.remove_quantity()`** — set `location_id=item.location_id` on REMOVE transaction (Section 2.13)
11. **Update `ItemRepository.delete_by_serial_numbers()`** — set `location_id=item.location_id` on REMOVE transactions (Section 2.13)
12. Add `location_id` filter to `ItemRepository.get_all()`, `search()`, `get_autocomplete_suggestions()`
13. Add `location_id` filter to `ItemTypeRepository._get_types_with_items()`, `get_all_with_items()`, `get_serialized_with_items()`
14. Add `ItemRepository.find_non_serialized_at_location()`
15. Add `ItemRepository.get_by_type(item_type_id)` — all items for a type across all locations; used by `TransferDialog` in "All Locations" view (Section 2.15)
16. Add `ItemTypeRepository.get_by_ids(type_ids)` — batch-fetch dict for `AllTransactionsDialog` name resolution (Section 2.16)
17. Add `ItemRepository.transfer_item()` — returns `bool`; populates `location_id` + `from/to_location_id` on both transactions
18. Add `ItemRepository.transfer_serialized_items()` — populates `location_id` + `from/to_location_id` on both transactions
19. Add `TransactionRepository.get_by_location_and_date_range()` and `get_all_by_date_range()`
20. **AUDIT:** Search `repositories.py` for all `Transaction(` constructor calls and verify every one sets `location_id`

### Step 3: Service Layer
1. Add `LocationService` class (including `move_all_items_and_delete()` with merge logic + TRANSFER transactions)
2. Update `InventoryService.create_item()` — `location_id` parameter
3. Update `InventoryService.create_serialized_item()` — `location_id` parameter
4. Verify `create_or_merge_item()` exists; update — `location_id` parameter; merge scoped to location
5. Update `InventoryService.edit_item()` — `location_id` parameter
6. Update `InventoryService.get_all_items_grouped()` — `location_id` filter + location name resolution via batch lookup
7. Add `InventoryService.transfer_item()` and `transfer_serialized_items()`
8. Update `SearchService.search()` — `location_id` filter
9. **Update `_transaction_to_dict()`** — add `location_id`, `from_location_id`, `to_location_id` to output dict (Section 3.4)
10. Add `TransactionService.get_transactions_by_location_and_date_range()`
11. Add `TransactionService.get_all_transactions_by_date_range()`

### Step 4: DTO Updates
1. Update `InventoryItem` — add `location_id: int`, `location_name: str`; keep `location` as compat property
2. Update `InventoryItem.from_db_models()` — accept `location_name` parameter
3. Update `GroupedInventoryItem` — add `location_id`, `location_name`, `is_multi_location`
4. Update `GroupedInventoryItem.from_item_type_and_items()` — detect multi-location, accept location params
5. Update all service-layer callers to pass location info when building DTOs

### Step 5: Translations
1. Add all new translation keys from Section 6 to both UK and EN dictionaries in `translations.py`

### Step 6: UI — Location Infrastructure
1. Create `LocationSelectorWidget` (`ui_entities/location_selector.py`)
   - `set_current_location()` must NOT emit `location_changed` (use `blockSignals` or a guard flag) to avoid double-load on startup
2. Create `FirstLocationDialog` (`ui_entities/first_location_dialog.py`)
3. Create `LocationManagementDialog` (`ui_entities/location_management_dialog.py`)
4. Integrate into `MainWindow` following the startup sequence in Section 5.6.1:
   - Declare `self._current_location_id = None` as the first line of `__init__()`
   - Add `_ensure_location_exists()` — runs before any UI setup
   - Add `_init_current_location()` — three-case sentinel restore (missing/null/int); runs **before** `_check_unassigned_items`
   - Add `_check_unassigned_items()` — runs after `_init_current_location()` so `_current_location_id` is valid (Section 9.5.1)
   - Add `_setup_location_selector()` — creates widget, adds above search
   - Set location selector to current location (no signal emission)
   - Update `_load_data_from_db()` to use `self._current_location_id`
   - Update `_refresh_item_list()` to pass `location_id`
   - Connect `location_changed`, `manage_requested` signals
   - Save location on every change via `config.set()`

### Step 7: UI — Transfer Dialog
1. Create `TransferDialog` (`ui_entities/transfer_dialog.py`)
2. Add `transfer_requested` signal to `InventoryListView`
3. Add "Transfer" context menu action in `InventoryListView._show_context_menu()`
4. Wire `_on_transfer_item()` in `MainWindow`

### Step 8: UI — All Transactions Dialog
1. Create `AllTransactionsDialog` (`ui_entities/all_transactions_dialog.py`)
2. Add "All Transactions" button to bottom bar in `MainWindow`
3. Wire `_on_show_all_transactions()` in `MainWindow`

### Step 9: UI — Update Existing Dialogs
1. Update `AddItemDialog` — add location `QComboBox` (mandatory, pre-selected to current; no "All Locations" entry; placeholder "Select location..." when current is None) (Section 5.9)
2. Update `EditItemDialog` — add location `QComboBox`; **update `_on_save_clicked()` InventoryItem constructor** to use `location_id`/`location_name` instead of `location` string (Section 5.10)
3. Update `AddSerialNumberDialog` — add location `QComboBox` (pre-selected to current)
4. Update `RemoveSerialNumberDialog` — filter serial numbers to active location only (Section 5.12)
5. Update `ItemDetailsDialog` — show location name; for multi-location serialized groups show location breakdown; add right-click transfer on serial numbers
6. Update `InventoryItemDelegate` — show location row/badge; show "Multiple locations" badge for multi-location groups
7. Update `InventoryModel` — add `LocationId`, `LocationName`, `IsMultiLocation` roles
8. Update `TransactionsDialog` — show from/to location columns for TRANSFER type; add `TransactionType.TRANSFER` handling
9. Update `SearchWidget` — add "Search all locations" checkbox; hide when "All Locations" is active

### Step 10: Documentation
1. Update `CLAUDE.md`:
   - Add `Location` to Data Model section
   - Add `TRANSFER` to TransactionType
   - Add `location_id` to Transaction model description
   - Add new files to Project Structure
   - Add LocationSelectorWidget, TransferDialog, AllTransactionsDialog to UI Components
   - Document location selector, first-launch wizard, transfer feature, three-case config restore
   - Update Key Patterns section

---

## 9. Key Design Decisions & Edge Cases

### 9.1 Transfer transactions — always create 2 records
For every transfer operation, create **two** Transaction records:
1. **Source transaction:** `TRANSFER` type, `location_id` = source, `quantity_change` = amount moved, `quantity_before`/`quantity_after` = counts at source, `from_location_id` = source, `to_location_id` = destination
2. **Destination transaction:** `TRANSFER` type, `location_id` = destination, `quantity_change` = amount moved, `quantity_before`/`quantity_after` = counts at destination, `from_location_id` = source, `to_location_id` = destination

Setting `location_id` to the respective location on each record ensures that when `AllTransactionsDialog` filters by location, both the outgoing and incoming sides appear correctly for that location.

### 9.2 Non-serialized transfer merge logic
When transferring N units of item type X from location A to location B:
1. Check if a non-serialized item of type X exists at location B
2. **If yes (merge):** Add N to that item's quantity. Reduce source item's quantity by N.
3. **If no (new row):** Create a new Item row at location B with quantity=N. Reduce source by N.

**When source quantity reaches 0 (full transfer):**
- Do **NOT** delete the source item row. Instead, update its `location_id` to the destination.
- If a merge target exists at the destination: add the full quantity to the merge target, then delete the now-empty source row (quantity=0 violates the DB CHECK constraint `quantity > 0`).
- **Correction:** Since the CHECK constraint requires `quantity > 0` for non-serialized items, a 0-quantity row cannot exist. So for full transfer:
  - **With merge target at destination:** Add full qty to destination row. Delete source row (no longer needed).
  - **Without merge target at destination:** Simply update `location_id` on the source row to destination. The row stays, just moves locations. No deletion needed.

**UI behavior:** After transfer, `MainWindow._refresh_item_list()` reloads from DB with the current `location_id` filter. The transferred item naturally disappears from the source location view and appears in the destination location view. No explicit row removal needed in the model.

### 9.3 Grouped items in "All Locations" view
- `GroupedInventoryItem.is_multi_location = True` when items of the same type exist at 2+ locations
- `serial_numbers` contains all serial numbers across all locations — dialogs must filter appropriately
- Delegate shows "📍 Multiple locations" badge (blue, similar to serialized badge)
- Transfer from "All Locations" view: dialog must let user pick source location first, then show only serials at that source location

### 9.4 Delete protection
- Location with items → offer to move to another location (via `LocationService.move_all_items_and_delete()`) → then delete
- Only 1 location exists with items → block deletion, show error
- Empty location → simple confirm → delete
- "All Locations" is virtual, cannot be deleted

### 9.5 First launch / upgrade
- If `LocationRepository.get_count() == 0`: show mandatory first-location dialog
- After creating the location: `LocationService.assign_all_unassigned_items(location_id)` runs `UPDATE items SET location_id = ? WHERE location_id IS NULL`
- This handles both fresh installs and upgrades from before the location feature
- `location_id` on items remains nullable in the DB schema; the app enforces NOT NULL at creation time for all new items

### 9.5.1 Startup integrity check for unassigned items
Every application startup (not just first launch) must run an integrity check:

```python
def _check_unassigned_items(self):
    """Check for items with location_id=NULL and prompt user to assign them."""
    unassigned_count = LocationService.get_unassigned_item_count()
    if unassigned_count == 0:
        return

    # Get current location (or first available)
    target_location = LocationService.get_location_by_id(self._current_location_id)
    if not target_location:
        locations = LocationService.get_all_locations()
        target_location = locations[0] if locations else None
    if not target_location:
        return  # No locations exist — first-launch wizard will handle this

    # Notify user
    reply = QMessageBox.warning(
        self,
        tr("location.unassigned.title"),
        tr("location.unassigned.message").format(
            count=unassigned_count,
            location=target_location.name
        ),
        QMessageBox.StandardButton.Ok,
    )
    # Assign all unassigned items to the target location
    assigned = LocationService.assign_all_unassigned_items(target_location.id)
    logger.info(f"Assigned {assigned} unassigned items to location '{target_location.name}'")
```

This check runs in `MainWindow.__init__()` **after** the first-launch wizard but **before** loading data. It catches items that somehow ended up with `location_id=NULL` (DB corruption, manual edits, bugs). The user sees a clear notification that items were auto-assigned to the current location.

Add to `LocationService`:
```python
@staticmethod
def get_unassigned_item_count() -> int:
    """Return count of items with location_id IS NULL."""
```

### 9.6 `location` backward-compat property on detached Item objects
The `@property location` on the `Item` model accesses `self.location_ref`, which is a lazy-loaded SQLAlchemy relationship. `_detach_item()` creates a plain `Item(...)` without populating this relationship, so `detached_item.location` always returns `""`. This is silent and will not raise an exception.

**This is acceptable** because all new code uses `location_id` from detached items and `location_name` from DTOs. However, any existing code that reads `item.location` expecting a real value will silently receive `""`. Audit call sites of `item.location` during implementation to confirm all consumers have been updated.

### 9.7 `move_all_items_and_delete` is service-layer logic
Moving all items between locations during a delete operation requires merge logic (non-serialized items of the same type at the destination must be merged). This coordination across multiple repository calls belongs in `LocationService.move_all_items_and_delete()`, not in `LocationRepository`. The repository's `delete()` method raises `ValueError` if items exist — the service is responsible for moving them first, then calling `delete()`.

### 9.8 Search behavior
- Default: search within current location
- "Search all locations" checkbox: search across all locations
- When "All Locations" is selected in the dropdown, the checkbox is hidden (redundant)
- Search results show location name for each result

### 9.9 Config persistence — three-case restore
```json
{
  "ui": {
    "last_location_id": 1
  }
}
```

| State | last_location_id | Action on startup |
|---|---|---|
| First run with feature | Key missing | Default to first available location |
| User selected "All Locations" | `null` | Restore "All Locations" |
| User selected specific location | `1` (int) | Validate exists → restore; else fall back to first |

---

## 10. Files Changed Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `models.py` | MODIFY | Add `Location` model, `TRANSFER` enum, update `Item` FK, update `Transaction` with `location_id`/`from_location_id`/`to_location_id` |
| `alembic/env.py` | MODIFY | Add `render_as_batch=True` |
| `alembic/versions/xxx_add_locations.py` | NEW | Migration: create locations table, update items & transactions (all three location columns) |
| `repositories.py` | MODIFY | Add `LocationRepository`, update `ItemRepository` (location params + transaction location_id population), `ItemTypeRepository`, `_detach_*`, `TransactionRepository` |
| `services.py` | MODIFY | Add `LocationService` (with move_all_items_and_delete), update `InventoryService`, `SearchService`, `TransactionService` |
| `ui_entities/inventory_item.py` | MODIFY | Add `location_id`/`location_name`/`is_multi_location` to DTOs |
| `ui_entities/translations.py` | MODIFY | Add ~50 new translation keys (UK + EN) |
| `ui_entities/location_selector.py` | **NEW** | Location dropdown + manage button widget |
| `ui_entities/first_location_dialog.py` | **NEW** | Mandatory first-location creation dialog |
| `ui_entities/location_management_dialog.py` | **NEW** | Location CRUD dialog |
| `ui_entities/transfer_dialog.py` | **NEW** | Transfer items between locations dialog |
| `ui_entities/all_transactions_dialog.py` | **NEW** | All transactions view with location filter |
| `ui_entities/main_window.py` | MODIFY | Integrate location selector, transfer, all-transactions button, three-case config restore |
| `ui_entities/inventory_list_view.py` | MODIFY | Add `transfer_requested` signal and context menu action |
| `ui_entities/inventory_delegate.py` | MODIFY | Show location in item row, multi-location badge |
| `ui_entities/inventory_model.py` | MODIFY | Add location-related data roles |
| `ui_entities/add_item_dialog.py` | MODIFY | Add location `QComboBox` (mandatory) |
| `ui_entities/edit_item_dialog.py` | MODIFY | Add location `QComboBox` |
| `ui_entities/add_serial_number_dialog.py` | MODIFY | Add location `QComboBox` |
| `ui_entities/remove_serial_number_dialog.py` | MODIFY | Filter serial list to active location only |
| `ui_entities/item_details_dialog.py` | MODIFY | Show location; serial transfer context menu; multi-location breakdown |
| `ui_entities/search_widget.py` | MODIFY | Add "Search all locations" checkbox |
| `ui_entities/transactions_dialog.py` | MODIFY | Handle TRANSFER type, show from/to location |
| `CLAUDE.md` | MODIFY | Update documentation |
