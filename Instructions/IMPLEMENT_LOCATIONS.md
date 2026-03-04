# Feature: Location Management — Multi-Location Inventory with Transfer Support

> **Target project:** AuditMagic (`C:\Users\chevi\PycharmProjects\AuditMagic`)
> **Stack:** Python 3.14 · PyQt6 · SQLAlchemy + SQLite · Alembic · `qt-material`
> **Architecture:** Repository → Service → UI (MVC), custom `QAbstractListModel`, dataclass DTOs
> **Key constraint:** Alembic migrations must use `batch_alter_table` for SQLite compatibility

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

    # Backward-compat property for any leftover references
    @property
    def location(self) -> str:
        """Return location name for backward compat."""
        return self.location_ref.name if self.location_ref else ""

    # Keep existing __table_args__ (serial/quantity check constraint)
```

**Note:** `location_id` is `nullable=False` in the final schema. The migration must handle this in two steps: add as nullable, populate, then alter to NOT NULL.

### 1.4 Update `Transaction` model

Add columns for transfer tracking:

```python
class Transaction(Base):
    __tablename__ = "transactions"

    # ... existing columns unchanged ...

    # NEW columns for transfer audit trail
    from_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    to_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)

    # Relationships (read-only references, no back_populates)
    from_location = relationship("Location", foreign_keys="[Transaction.from_location_id]")
    to_location = relationship("Location", foreign_keys="[Transaction.to_location_id]")
```

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

    # 3. Update transactions table: add from/to location columns
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('from_location_id', sa.Integer, nullable=True))
        batch_op.add_column(sa.Column('to_location_id', sa.Integer, nullable=True))
        batch_op.create_foreign_key('fk_transactions_from_location', 'locations', ['from_location_id'], ['id'])
        batch_op.create_foreign_key('fk_transactions_to_location', 'locations', ['to_location_id'], ['id'])

    # NOTE: location_id stays nullable in migration.
    # The app enforces NOT NULL at creation time. The first-launch wizard
    # will create a location and assign all existing items to it before
    # any user interaction. Making the column NOT NULL in the DB after
    # the wizard runs would require a second migration — instead, we
    # enforce it at the application level.
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
    def move_all_items(from_location_id: int, to_location_id: int) -> int:
        """Move all items from one location to another.
        For non-serialized items: merge with existing items of the same type at destination.
        Returns total count of items affected."""

    @staticmethod
    def get_count() -> int:
        """Return total number of locations."""
```

### 2.3 Update `_detach_item()`

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
        location_id=item.location_id,  # CHANGED from location
        condition=item.condition,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
```

### 2.4 Update `ItemRepository.create()`

Change parameter: `location: str = None` → `location_id: int`  (required, no default)

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
```

Set `item.location_id = location_id` instead of `item.location = location`.

### 2.5 Update `ItemRepository.create_serialized()`

Change parameter: `location: str = ""` → `location_id: int`  (required)

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

### 2.6 Update `ItemRepository.edit_item()`

Change parameter: `location: str` → `location_id: int`

### 2.7 Update `ItemRepository.update()`

Change parameter: `location: str = None` → `location_id: int = None`

### 2.8 Add location filter to query methods

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

### 2.9 New: `ItemRepository.transfer_item()`

```python
@staticmethod
def transfer_item(
    item_id: int,
    to_location_id: int,
    quantity: int = None,  # None = transfer all (for non-serialized)
    notes: str = "",
) -> Optional[Item]:
    """Transfer a non-serialized item (or partial quantity) to another location.

    Creates TWO TRANSFER transactions:
      1. Source location: quantity decreases
      2. Destination location: quantity increases

    Merge logic: If an item of the same type already exists at the destination,
    add quantity to it. Otherwise, create a new item row.

    If quantity == full amount, update location_id in place (no split needed)
    unless a merge target exists at the destination.

    Returns the source item (updated) or None if fully moved.
    """
```

### 2.10 New: `ItemRepository.transfer_serialized_items()`

```python
@staticmethod
def transfer_serialized_items(
    serial_numbers: List[str],
    to_location_id: int,
    notes: str = "",
) -> int:
    """Transfer specific serialized items to another location.

    Creates TWO TRANSFER transactions per item:
      1. Source location: quantity_before=1, quantity_after=0 (item leaves)
      2. Destination location: quantity_before=0, quantity_after=1 (item arrives)

    Simply updates each item's location_id.
    Returns count transferred.
    """
```

### 2.11 New: `ItemRepository.find_non_serialized_at_location()`

```python
@staticmethod
def find_non_serialized_at_location(item_type_id: int, location_id: int) -> Optional[Item]:
    """Find the non-serialized item row for a given type at a given location.
    Used for merge-on-transfer logic.
    """
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
        """Move all items to destination, then delete source location.
        Handles merge for non-serialized items."""

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
- Replace `location: str = ""` with `location_id: int`
- Merge logic: `find_non_serialized_at_location(item_type_id, location_id)`

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
    """Transfer non-serialized item. Returns True on success."""

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

### 3.4 Update `TransactionService`
- Add method: `get_transactions_by_location_and_date_range(location_id, start, end)`
- Add method: `get_all_transactions_by_date_range(start, end)` (no location filter)

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

    # Keep backward-compat property
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

### 4.3 Location resolution in services

When creating DTOs, the service layer must resolve `location_id` → `location_name`. Do this efficiently with a batch lookup:

```python
# In InventoryService.get_all_items_grouped():
location_map = {loc.id: loc.name for loc in LocationRepository.get_all()}
# Pass location_name to from_item_type_and_items()
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
  - "All Locations" has user data `0` (or `None`)
  - Each location has user data = `location_id`
- Styled with `apply_combo_box_style()`
- "Manage Locations" `QPushButton` styled with `apply_button_style(..., "secondary")`
- `refresh_locations()` method to reload from DB
- `set_current_location(location_id)` method for restoring from config
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
- Returns the created location ID.
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
- **Serialized items:** Checkbox list of serial numbers at the current location. At least one must be selected.
- Notes field (optional) for audit trail.
- On accept: calls `InventoryService.transfer_item()` or `transfer_serialized_items()`.
- Style with existing `apply_*` helpers.

**Edge case — "All Locations" view:**
When user right-clicks a grouped item while "All Locations" is selected, and the item exists in multiple locations:
- The transfer dialog should show a **source location dropdown** (pre-populated with the locations where this item type exists) in addition to the destination.
- For serialized items, show serial numbers grouped by their location.

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

#### 5.6.1 First-launch check
In `__init__()`, after `init_database()` and before `_setup_ui()`:

```python
# Ensure at least one location exists
self._ensure_location_exists()
```

```python
def _ensure_location_exists(self):
    """Show first-location dialog if no locations exist."""
    if LocationService.get_location_count() == 0:
        from ui_entities.first_location_dialog import FirstLocationDialog
        dialog = FirstLocationDialog(self)
        dialog.exec()  # Cannot be dismissed
        # Assign all existing unassigned items
        LocationService.assign_all_unassigned_items(dialog.get_location_id())
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
```python
self._current_location_id: Optional[int] = None  # None = all locations
```

Restore from config on startup:
```python
saved_loc = config.get("ui.last_location_id")
if saved_loc is not None:
    self._current_location_id = saved_loc
    self.location_selector.set_current_location(saved_loc)
```

Save on change:
```python
def _on_location_changed(self, location_id):
    self._current_location_id = location_id
    config.set("ui.last_location_id", location_id)
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
    # If the current location was deleted, reset to "All Locations"
    if self._current_location_id and not LocationService.get_location_by_id(self._current_location_id):
        self._current_location_id = None
        self.location_selector.set_current_location(None)
    self._refresh_item_list()
```

#### 5.6.8 Update `_on_add_clicked()`
Pass `self._current_location_id` to the add dialog:
```python
dialog = AddItemDialog(parent=self, current_location_id=self._current_location_id)
```

If `_current_location_id` is None (all locations), the dialog should let the user pick a location.

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
- Uses `TransactionService` methods.

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
- Replace free-text location field (if any — currently location is not in AddItemDialog form, it goes through the service with `location=""`)
- **Add a `QComboBox` for location** populated from `LocationService.get_all_locations()`
- Pre-select `current_location_id` if provided
- If `current_location_id` is None, user must select a location manually
- Location is **required** — validation must check it's selected
- Pass `location_id` to `InventoryService.create_item()` / `create_serialized_item()`

### 5.10 Update `EditItemDialog`

- Add `QComboBox` for location (pre-selected to item's current location)
- For grouped items:
  - If single location (viewed from specific location): show that location, allow changing (moves all items of the type at this location)
  - If multi-location (viewed from "All Locations"): show read-only "Multiple locations" — editing location per-type doesn't make sense here. Transfer should be used instead.
- Pass `location_id` to `InventoryService.edit_item()`

### 5.11 Update `AddSerialNumberDialog`

- Add `QComboBox` for location, pre-selected to current location
- Pass `location_id` back to caller via `get_location_id()` method
- Constructor: `AddSerialNumberDialog(..., current_location_id: int = None)`

### 5.12 Update `ItemDetailsDialog`

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

### 5.13 Update `InventoryItemDelegate`

Show location in the item row. Update the 2×2 grid layout to include location info:

**Option A — Add location as a 5th field (below the 2×2 grid):**
- Increase `ROW_HEIGHT` slightly (e.g., 80 → 95)
- Add a row below the grid: `📍 Location: Warehouse A` (or "Multiple locations" badge)

**Option B — Replace one of the existing grid cells:**
- The "Серійний номер:" row at position (1,1) can be moved/combined
- Use the freed space for location

**Recommended: Option A** — Keep all existing info, add location as a subtle line at the bottom of each row.

For multi-location items (when viewing "All Locations"):
- Show a small badge: "📍 Multiple locations" in a muted style (similar to serialized badge)
- Badge color: `#1565c0` (blue) or similar, theme-independent for consistency

### 5.14 Update `TransactionsDialog`

- Add "From Location" and "To Location" columns for TRANSFER type transactions
- Handle new `TransactionType.TRANSFER` in display logic
- Show location names resolved from `from_location_id` / `to_location_id`

### 5.15 Update `InventoryModel`

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

- On startup: read `ui.last_location_id`, validate it still exists, set in selector
- On location change: save immediately via `config.set("ui.last_location_id", location_id)`
- If saved location was deleted: fall back to first available location (not "All Locations", since the user likely wants to see a specific one)

---

## 8. Implementation Order (Optimized for Claude Code)

Execute steps in this exact order. Each step is independently testable.

### Step 1: Model & Migration
1. Update `TransactionType` enum — add `TRANSFER = "transfer"`
2. Add `Location` model to `models.py`
3. Update `Item` model — replace `location` text column with `location_id` FK
4. Update `Transaction` model — add `from_location_id`, `to_location_id`
5. Add `render_as_batch=True` to `alembic/env.py` (both online and offline functions)
6. Generate Alembic migration: `alembic revision --autogenerate -m "add_locations_table_and_transfer"`
7. Edit migration: use `batch_alter_table`, drop old `location` column, add `location_id` (nullable for now)
8. Run migration: `alembic upgrade head`
9. Verify DB schema is correct

### Step 2: Repository Layer
1. Add `_detach_location()` helper to `repositories.py`
2. Add `LocationRepository` class (full CRUD + item count + move all items)
3. Update `_detach_item()` — replace `location` with `location_id`
4. Update `ItemRepository.create()` — `location_id: int` parameter (mandatory)
5. Update `ItemRepository.create_serialized()` — `location_id: int` parameter
6. Update `ItemRepository.edit_item()` — `location_id: int` parameter
7. Update `ItemRepository.update()` — `location_id: int = None` parameter
8. Add `location_id` filter to `ItemRepository.get_all()`, `search()`, `get_autocomplete_suggestions()`
9. Add `location_id` filter to `ItemTypeRepository._get_types_with_items()`, `get_all_with_items()`, `get_serialized_with_items()`
10. Add `ItemRepository.find_non_serialized_at_location()`
11. Add `ItemRepository.transfer_item()`
12. Add `ItemRepository.transfer_serialized_items()`

### Step 3: Service Layer
1. Add `LocationService` class
2. Update `InventoryService.create_item()` — `location_id` parameter
3. Update `InventoryService.create_serialized_item()` — `location_id` parameter
4. Update `InventoryService.create_or_merge_item()` — `location_id` parameter
5. Update `InventoryService.edit_item()` — `location_id` parameter
6. Update `InventoryService.get_all_items_grouped()` — `location_id` filter + location name resolution
7. Add `InventoryService.transfer_item()` and `transfer_serialized_items()`
8. Update `SearchService.search()` — `location_id` filter
9. Add `TransactionService.get_transactions_by_location_and_date_range()`
10. Add `TransactionService.get_all_transactions_by_date_range()`

### Step 4: DTO Updates
1. Update `InventoryItem` — add `location_id: int`, `location_name: str`, remove old `location`
2. Update `InventoryItem.from_db_models()` — accept `location_name` parameter
3. Update `GroupedInventoryItem` — add `location_id`, `location_name`, `is_multi_location`
4. Update `GroupedInventoryItem.from_item_type_and_items()` — detect multi-location, accept location params
5. Update all service-layer callers to pass location info when building DTOs

### Step 5: Translations
1. Add all new translation keys from Section 6 to both UK and EN dictionaries in `translations.py`

### Step 6: UI — Location Infrastructure
1. Create `LocationSelectorWidget` (`ui_entities/location_selector.py`)
2. Create `FirstLocationDialog` (`ui_entities/first_location_dialog.py`)
3. Create `LocationManagementDialog` (`ui_entities/location_management_dialog.py`)
4. Integrate into `MainWindow`:
   - Add first-launch check in `__init__` (before `_setup_ui`)
   - Add `LocationSelectorWidget` above search
   - Connect `location_changed` and `manage_requested` signals
   - Add `_current_location_id` tracking
   - Update `_refresh_item_list()` to pass `location_id`
   - Save/restore last location in config

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
1. Update `AddItemDialog` — add location `QComboBox` (mandatory, pre-selected to current)
2. Update `EditItemDialog` — add location `QComboBox` (pre-selected to item's location; read-only "Multiple" for multi-location groups)
3. Update `AddSerialNumberDialog` — add location `QComboBox` (pre-selected to current)
4. Update `ItemDetailsDialog` — show location name; for multi-location serialized groups show location breakdown; add right-click transfer on serial numbers
5. Update `InventoryItemDelegate` — show location row/badge; show "Multiple locations" badge for multi-location groups
6. Update `InventoryModel` — add `LocationId`, `LocationName`, `IsMultiLocation` roles
7. Update `TransactionsDialog` — show from/to location columns for TRANSFER type; add `TransactionType.TRANSFER` handling
8. Update `SearchWidget` — add "Search all locations" checkbox; hide when "All Locations" is active

### Step 10: Documentation
1. Update `CLAUDE.md`:
   - Add `Location` to Data Model section
   - Add `TRANSFER` to TransactionType
   - Add new files to Project Structure
   - Add LocationSelectorWidget, TransferDialog, AllTransactionsDialog to UI Components
   - Document location selector, first-launch wizard, transfer feature
   - Update Key Patterns section

---

## 9. Key Design Decisions & Edge Cases

### 9.1 Transfer transactions — always create 2 records
For every transfer operation, create **two** Transaction records:
1. **Source transaction:** `TRANSFER` type, `quantity_change` = amount moved, `quantity_before` / `quantity_after` = counts at source location, `from_location_id` = source, `to_location_id` = destination
2. **Destination transaction:** `TRANSFER` type, `quantity_change` = amount moved, `quantity_before` / `quantity_after` = counts at destination location, `from_location_id` = source, `to_location_id` = destination

This ensures that when viewing transactions filtered by a single location, both the outgoing and incoming transfers appear correctly.

### 9.2 Non-serialized transfer merge logic
When transferring N units of item type X from location A to location B:
1. Check if a non-serialized item of type X exists at location B
2. **If yes:** Add N to that item's quantity (merge). Reduce source item's quantity by N. If source reaches 0, delete the source item row.
3. **If no:** Create a new Item row at location B with quantity=N. Reduce source by N. If source reaches 0, delete source row.

### 9.3 Grouped items in "All Locations" view
- `GroupedInventoryItem.is_multi_location = True` when items of the same type exist at 2+ locations
- Delegate shows "📍 Multiple locations" badge (blue, similar to serialized badge)
- Transfer from "All Locations" view: dialog must let user pick source location first
- Location column in delegate: show location name for single-location items, badge for multi-location

### 9.4 Delete protection
- Location with items → offer to move to another location → then delete
- Only 1 location exists with items → block deletion, show error
- Empty location → simple confirm → delete
- "All Locations" is virtual, cannot be deleted

### 9.5 First launch / upgrade
- If `LocationRepository.get_count() == 0`: show mandatory first-location dialog
- After creating the location: `UPDATE items SET location_id = ? WHERE location_id IS NULL`
- This handles both fresh installs and upgrades from before the location feature

### 9.6 Search behavior
- Default: search within current location
- "Search all locations" checkbox: search across all locations
- When "All Locations" is selected in the dropdown, the checkbox is hidden (redundant)
- Search results show location name for each result

### 9.7 Config persistence
```json
{
  "ui": {
    "last_location_id": 1
  }
}
```
- Saved on every location change
- On startup: validate the saved ID still exists; fall back to first location if not

---

## 10. Files Changed Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `models.py` | MODIFY | Add `Location` model, `TRANSFER` enum, update `Item` FK, update `Transaction` FKs |
| `alembic/env.py` | MODIFY | Add `render_as_batch=True` |
| `alembic/versions/xxx_add_locations.py` | NEW | Migration: create locations table, update items & transactions |
| `repositories.py` | MODIFY | Add `LocationRepository`, update `ItemRepository`, `ItemTypeRepository`, `_detach_*` |
| `services.py` | MODIFY | Add `LocationService`, update `InventoryService`, `SearchService`, `TransactionService` |
| `ui_entities/inventory_item.py` | MODIFY | Add location fields to `InventoryItem` and `GroupedInventoryItem` |
| `ui_entities/translations.py` | MODIFY | Add ~50 new translation keys (UK + EN) |
| `ui_entities/location_selector.py` | **NEW** | Location dropdown + manage button widget |
| `ui_entities/first_location_dialog.py` | **NEW** | Mandatory first-location creation dialog |
| `ui_entities/location_management_dialog.py` | **NEW** | Location CRUD dialog |
| `ui_entities/transfer_dialog.py` | **NEW** | Transfer items between locations dialog |
| `ui_entities/all_transactions_dialog.py` | **NEW** | All transactions view with location filter |
| `ui_entities/main_window.py` | MODIFY | Integrate location selector, transfer, all-transactions button |
| `ui_entities/inventory_list_view.py` | MODIFY | Add `transfer_requested` signal and context menu action |
| `ui_entities/inventory_delegate.py` | MODIFY | Show location in item row, multi-location badge |
| `ui_entities/inventory_model.py` | MODIFY | Add location-related data roles |
| `ui_entities/add_item_dialog.py` | MODIFY | Add location `QComboBox` (mandatory) |
| `ui_entities/edit_item_dialog.py` | MODIFY | Add location `QComboBox` |
| `ui_entities/add_serial_number_dialog.py` | MODIFY | Add location `QComboBox` |
| `ui_entities/item_details_dialog.py` | MODIFY | Show location; serial transfer context menu |
| `ui_entities/search_widget.py` | MODIFY | Add "Search all locations" checkbox |
| `ui_entities/transactions_dialog.py` | MODIFY | Handle TRANSFER type, show from/to location |
| `CLAUDE.md` | MODIFY | Update documentation |
