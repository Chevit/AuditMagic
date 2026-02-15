# Serial Number Management & Data Model Improvements

## Current Issues

### Problem 1: Ambiguous Serial Number Handling
**Current Model**:
```python
class Item:
    item_type: str
    sub_type: str
    quantity: int       # Can be > 1
    serial_number: str  # Can be set even when quantity > 1
```

**Issues**:
- One item can have `quantity=5` AND `serial_number="ABC123"` (illogical)
- No way to track multiple serial numbers for the same type
- Cannot list all serial numbers for a given type/subtype
- Mixing bulk items and serialized items in same record

### Problem 2: No Autocomplete
- Users must manually type item types and subtypes
- Risk of typos creating duplicate types ("Laptop" vs "laptop")
- No way to see existing types while creating new items

### Problem 3: Data Redundancy
- Same type/subtype strings repeated across many items
- No referential integrity for types
- Hard to rename a type across all items

---

## Proposed Solutions

### Solution Option A: Minimal Changes (Quick Implementation)

Keep current flat structure, add serial number logic.

#### Changes:
1. Add `is_serialized: bool` column to Item
2. Enforce: `if is_serialized: quantity = 1, serial_number required`
3. Add autocomplete from existing types/subtypes
4. Add "serial_number" search field

**Pros:**
- Quick to implement (1-2 days)
- No complex migration
- Minimal risk

**Cons:**
- Still redundant data
- Multiple rows per type (one row per serial number)
- Harder to manage types as entities

---

### Solution Option B: Hierarchical Model (Recommended)

Restructure to separate Types from Items (instances).

#### New Model:

```python
class ItemType(Base):
    """Represents a type/category of items."""
    __tablename__ = "item_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True, index=True)  # "Laptop"
    sub_type = Column(String(255), nullable=True, index=True)  # "ThinkPad X1"
    is_serialized = Column(Boolean, default=False)  # Whether this type tracks serial numbers
    details = Column(Text, nullable=True)  # Description of this type
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    items = relationship("Item", back_populates="item_type", cascade="all, delete-orphan")

    # Unique constraint on name + sub_type
    __table_args__ = (
        UniqueConstraint('name', 'sub_type', name='uq_item_type_name_subtype'),
    )


class Item(Base):
    """Represents actual inventory items/units."""
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    item_type_id = Column(Integer, ForeignKey("item_types.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)  # Always 1 if serialized
    serial_number = Column(String(255), nullable=True, unique=True)  # Unique if present
    location = Column(String(255), nullable=True)  # Optional: where is this item?
    condition = Column(String(50), nullable=True)  # Optional: new, used, damaged
    notes = Column(Text, nullable=True)  # Notes specific to this instance
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    item_type = relationship("ItemType", back_populates="items")
    transactions = relationship("Transaction", back_populates="item", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint('(serial_number IS NULL AND quantity > 0) OR (serial_number IS NOT NULL AND quantity = 1)',
                       name='check_serial_or_quantity'),
    )
```

#### Data Structure Examples:

**Example 1: Serialized Items (Laptops)**
```
ItemType:
  id=1, name="Laptop", sub_type="ThinkPad X1", is_serialized=True, details="Business laptop"

Items:
  id=1, type_id=1, quantity=1, serial_number="SN001", condition="new"
  id=2, type_id=1, quantity=1, serial_number="SN002", condition="used"
  id=3, type_id=1, quantity=1, serial_number="SN003", condition="new"
```

**Example 2: Bulk Items (Cables)**
```
ItemType:
  id=2, name="Cable", sub_type="USB-C", is_serialized=False, details="USB-C charging cable"

Items:
  id=4, type_id=2, quantity=50, serial_number=NULL, location="Storage A"
  id=5, type_id=2, quantity=25, serial_number=NULL, location="Storage B"
```

---

## Implementation Plan for Option B

### Phase 1: Database Migration

**Step 1: Create New Tables**

File: `alembic/versions/XXXX_add_item_types_table.py`
```python
def upgrade():
    # Create item_types table
    op.create_table(
        'item_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('sub_type', sa.String(255), nullable=True),
        sa.Column('is_serialized', sa.Boolean(), default=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'sub_type', name='uq_item_type_name_subtype')
    )
    op.create_index('ix_item_types_name', 'item_types', ['name'])
    op.create_index('ix_item_types_sub_type', 'item_types', ['sub_type'])

    # Migrate existing data
    # 1. Extract unique type/subtype combinations from items
    connection = op.get_bind()
    result = connection.execute("""
        SELECT DISTINCT item_type, sub_type, details
        FROM items
        ORDER BY item_type, sub_type
    """)

    # 2. Insert into item_types
    for row in result:
        # Determine if serialized based on existing data
        is_serialized = connection.execute("""
            SELECT COUNT(*) > 0 FROM items
            WHERE item_type = ? AND sub_type = ? AND serial_number IS NOT NULL
        """, (row.item_type, row.sub_type)).scalar()

        connection.execute("""
            INSERT INTO item_types (name, sub_type, is_serialized, details, created_at, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (row.item_type, row.sub_type, is_serialized, row.details))

    # 3. Add item_type_id to items table
    op.add_column('items', sa.Column('item_type_id', sa.Integer(), nullable=True))

    # 4. Populate item_type_id
    connection.execute("""
        UPDATE items
        SET item_type_id = (
            SELECT id FROM item_types
            WHERE item_types.name = items.item_type
            AND (item_types.sub_type = items.sub_type OR (item_types.sub_type IS NULL AND items.sub_type IS NULL))
        )
    """)

    # 5. Make item_type_id NOT NULL and add FK
    op.alter_column('items', 'item_type_id', nullable=False)
    op.create_foreign_key('fk_items_item_type_id', 'items', 'item_types', ['item_type_id'], ['id'])

    # 6. Drop old columns
    op.drop_column('items', 'item_type')
    op.drop_column('items', 'sub_type')
    op.drop_column('items', 'details')  # Details now on ItemType

    # 7. Add new optional columns
    op.add_column('items', sa.Column('location', sa.String(255), nullable=True))
    op.add_column('items', sa.Column('condition', sa.String(50), nullable=True))
    op.add_column('items', sa.Column('notes', sa.Text(), nullable=True))

    # 8. Add unique constraint on serial_number
    op.create_unique_constraint('uq_items_serial_number', 'items', ['serial_number'])
```

### Phase 2: Update Models

File: `models.py`
```python
class ItemType(Base):
    """Represents a type/category of items."""
    __tablename__ = "item_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    sub_type = Column(String(255), nullable=True, index=True)
    is_serialized = Column(Boolean, default=False, nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))

    items = relationship("Item", back_populates="item_type", cascade="all, delete-orphan")

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
    def serial_numbers(self) -> list[str]:
        """Get all serial numbers for this type (if serialized)."""
        if not self.is_serialized:
            return []
        return [item.serial_number for item in self.items if item.serial_number]


class Item(Base):
    """Represents actual inventory items/units."""
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    item_type_id = Column(Integer, ForeignKey("item_types.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    serial_number = Column(String(255), nullable=True, unique=True)
    location = Column(String(255), nullable=True)
    condition = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))

    item_type = relationship("ItemType", back_populates="items")
    transactions = relationship("Transaction", back_populates="item", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            '(serial_number IS NULL AND quantity > 0) OR (serial_number IS NOT NULL AND quantity = 1)',
            name='check_serial_or_quantity'
        ),
    )

    def __repr__(self):
        return f"<Item(id={self.id}, type_id={self.item_type_id}, qty={self.quantity}, sn={self.serial_number})>"
```

### Phase 3: Update Repositories

File: `repositories.py` - Add new repository:
```python
class ItemTypeRepository:
    """Repository for ItemType operations."""

    @staticmethod
    def create(name: str, sub_type: str = "", is_serialized: bool = False,
               details: str = "") -> ItemType:
        """Create a new item type."""
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
            return _detach_item_type(item_type)

    @staticmethod
    def get_or_create(name: str, sub_type: str = "", is_serialized: bool = False,
                      details: str = "") -> ItemType:
        """Get existing type or create new one."""
        with session_scope() as session:
            item_type = (
                session.query(ItemType)
                .filter(ItemType.name == name, ItemType.sub_type == (sub_type or ""))
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
    def get_all() -> List[ItemType]:
        """Get all item types."""
        with session_scope() as session:
            types = session.query(ItemType).order_by(ItemType.name, ItemType.sub_type).all()
            return [_detach_item_type(t) for t in types]

    @staticmethod
    def get_by_id(type_id: int) -> Optional[ItemType]:
        """Get item type by ID."""
        with session_scope() as session:
            item_type = session.query(ItemType).filter(ItemType.id == type_id).first()
            return _detach_item_type(item_type) if item_type else None

    @staticmethod
    def get_autocomplete_names(prefix: str = "", limit: int = 10) -> List[str]:
        """Get autocomplete suggestions for type names."""
        with session_scope() as session:
            query = session.query(ItemType.name).distinct()
            if prefix:
                query = query.filter(ItemType.name.ilike(f"{prefix}%"))
            query = query.order_by(ItemType.name).limit(limit)
            return [row[0] for row in query.all()]

    @staticmethod
    def get_autocomplete_subtypes(type_name: str, prefix: str = "", limit: int = 10) -> List[str]:
        """Get autocomplete suggestions for subtypes given a type name."""
        with session_scope() as session:
            query = (
                session.query(ItemType.sub_type)
                .filter(ItemType.name == type_name, ItemType.sub_type.isnot(None))
                .distinct()
            )
            if prefix:
                query = query.filter(ItemType.sub_type.ilike(f"{prefix}%"))
            query = query.order_by(ItemType.sub_type).limit(limit)
            return [row[0] for row in query.all() if row[0]]

    @staticmethod
    def update(type_id: int, name: str = None, sub_type: str = None,
               is_serialized: bool = None, details: str = None) -> Optional[ItemType]:
        """Update an item type."""
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


class ItemRepository:
    """Repository for Item operations."""

    @staticmethod
    def create(item_type_id: int, quantity: int = 1, serial_number: str = None,
               location: str = None, condition: str = None, notes: str = None) -> Item:
        """Create a new item instance."""
        with session_scope() as session:
            # Validate type exists
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
            return _detach_item(item)

    @staticmethod
    def get_by_type(type_id: int) -> List[Item]:
        """Get all items of a specific type."""
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
        """Find item by serial number."""
        with session_scope() as session:
            item = (
                session.query(Item)
                .filter(Item.serial_number == serial_number)
                .first()
            )
            return _detach_item(item) if item else None

    @staticmethod
    def get_serial_numbers_for_type(type_id: int) -> List[str]:
        """Get all serial numbers for a given type."""
        with session_scope() as session:
            results = (
                session.query(Item.serial_number)
                .filter(Item.item_type_id == type_id, Item.serial_number.isnot(None))
                .order_by(Item.serial_number)
                .all()
            )
            return [row[0] for row in results]


def _detach_item_type(item_type: ItemType) -> ItemType:
    """Create detached copy of ItemType."""
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

### Phase 4: Update UI Dialogs

**Add Item Dialog with Autocomplete:**

File: `ui_entities/add_item_dialog.py`
```python
from PyQt6.QtWidgets import QCompleter, QCheckBox
from PyQt6.QtCore import Qt

class AddItemDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_autocomplete()
        self._setup_serialization_logic()

    def _setup_ui(self):
        """Setup UI with checkbox for serialization."""
        # ... existing code ...

        # Add checkbox for serialization
        self.serialized_checkbox = QCheckBox(tr("dialog.add.serialized"))
        self.serialized_checkbox.setToolTip(tr("dialog.add.serialized.tooltip"))
        self.serialized_checkbox.stateChanged.connect(self._on_serialized_changed)

        # Insert checkbox before quantity field
        # ... layout code ...

    def _setup_autocomplete(self):
        """Setup autocomplete for type and subtype fields."""
        # Type autocomplete
        type_completer = QCompleter(self)
        type_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        type_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.type_input.setCompleter(type_completer)
        self.type_input.textChanged.connect(self._update_type_autocomplete)

        # Subtype autocomplete (depends on selected type)
        subtype_completer = QCompleter(self)
        subtype_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        subtype_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.subtype_input.setCompleter(subtype_completer)
        self.type_input.textChanged.connect(self._update_subtype_autocomplete)

    def _update_type_autocomplete(self, text: str):
        """Update autocomplete suggestions for type."""
        suggestions = ItemTypeRepository.get_autocomplete_names(text, limit=20)
        model = QStringListModel(suggestions)
        self.type_input.completer().setModel(model)

    def _update_subtype_autocomplete(self, type_text: str):
        """Update autocomplete suggestions for subtype based on type."""
        if not type_text:
            return
        suggestions = ItemTypeRepository.get_autocomplete_subtypes(type_text, limit=20)
        model = QStringListModel(suggestions)
        self.subtype_input.completer().setModel(model)

    def _setup_serialization_logic(self):
        """Setup logic for serialization checkbox."""
        self._on_serialized_changed(self.serialized_checkbox.checkState())

    def _on_serialized_changed(self, state):
        """Handle serialization checkbox state change."""
        is_serialized = (state == Qt.CheckState.Checked)

        if is_serialized:
            # Enable serial number, disable quantity
            self.serial_number_input.setEnabled(True)
            self.serial_number_input.setStyleSheet("")
            self.quantity_input.setEnabled(False)
            self.quantity_input.setValue(1)
            self.quantity_input.setStyleSheet("background-color: #e0e0e0;")
        else:
            # Disable serial number, enable quantity
            self.serial_number_input.setEnabled(False)
            self.serial_number_input.clear()
            self.serial_number_input.setStyleSheet("background-color: #e0e0e0;")
            self.quantity_input.setEnabled(True)
            self.quantity_input.setStyleSheet("")
```

**Item Details Dialog showing Serial Numbers:**

File: `ui_entities/item_details_dialog.py`
```python
class ItemDetailsDialog(QDialog):
    def __init__(self, item_type_id: int, parent=None):
        super().__init__(parent)
        self.item_type_id = item_type_id
        self._setup_ui()
        self._load_details()

    def _load_details(self):
        """Load item type details and serial numbers."""
        item_type = ItemTypeRepository.get_by_id(self.item_type_id)
        if not item_type:
            return

        # Show basic info
        self.name_label.setText(item_type.name)
        self.subtype_label.setText(item_type.sub_type or tr("dialog.details.none"))
        self.details_text.setPlainText(item_type.details or "")

        # Show total quantity
        total_qty = sum(item.quantity for item in ItemRepository.get_by_type(item_type.id))
        self.quantity_label.setText(str(total_qty))

        # If serialized, show serial numbers list
        if item_type.is_serialized:
            self.serial_numbers_widget.setVisible(True)
            serial_numbers = ItemRepository.get_serial_numbers_for_type(item_type.id)

            # Populate list
            self.serial_list.clear()
            for sn in serial_numbers:
                item = QListWidgetItem(sn)
                self.serial_list.addItem(item)

            self.serial_count_label.setText(
                tr("dialog.details.serial_count").format(count=len(serial_numbers))
            )
        else:
            self.serial_numbers_widget.setVisible(False)
```

**Enhanced Search with Serial Number:**

File: `ui_entities/search_widget.py`
```python
def _setup_search_fields(self):
    """Setup search field dropdown."""
    self.field_combo.addItems([
        tr("search.field.all"),
        tr("search.field.type"),
        tr("search.field.subtype"),
        tr("search.field.serial"),  # NEW
        tr("search.field.details")
    ])
```

File: `repositories.py` - Update search:
```python
@staticmethod
def search(query: str, field: str = None, limit: int = 100) -> List[Item]:
    """Search items by query string."""
    with session_scope() as session:
        search_pattern = f"%{query}%"

        if field == "serial_number":
            # Search by serial number
            items = (
                session.query(Item)
                .filter(Item.serial_number.ilike(search_pattern))
                .limit(limit)
                .all()
            )
        elif field == "item_type":
            # Join with ItemType and search by type name
            items = (
                session.query(Item)
                .join(ItemType)
                .filter(ItemType.name.ilike(search_pattern))
                .limit(limit)
                .all()
            )
        # ... other fields ...

        return [_detach_item(item) for item in items]
```

---

## Comparison: Option A vs Option B

| Aspect | Option A (Minimal) | Option B (Hierarchical) |
|--------|-------------------|------------------------|
| **Implementation Time** | 1-2 days | 1-2 weeks |
| **Migration Complexity** | Low | High |
| **Data Normalization** | Poor (redundant) | Excellent |
| **Type Management** | Hard (scattered) | Easy (centralized) |
| **Serial Number Logic** | Works but awkward | Clean and intuitive |
| **Autocomplete** | Possible | Natural fit |
| **Location Support** | Very hard to add | Already included (location field) |
| **Transfer Operations** | Complex implementation | Natural fit |
| **Queries** | Simple | Need joins |
| **Future Extensibility** | Limited | Excellent |
| **Risk** | Low | Medium |

---

## Future Feature: Location Management & Transfers

### Requirement (Future Implementation)

Support multiple storage locations with the ability to transfer items between locations:
- **Transfer entire type**: Move all items of a type from Location A to Location B
- **Transfer specific quantity**: Move X units of bulk items
- **Transfer specific serial numbers**: Move selected serialized items

### How It Works with Option B (Perfect Fit!)

Option B already includes `location` field on Item model, making this feature natural:

#### Example 1: Bulk Items (Cables)
```
Location: Storage A
  ItemType: Cable USB-C (is_serialized=False)
    ├── Item(qty=50, location="Storage A")

Transfer 20 units to Storage B:
  1. Create new Item(qty=20, location="Storage B", type_id=same)
  2. Update existing Item: qty=50-20=30
  3. Create Transaction for both items
```

#### Example 2: Serialized Items (Laptops)
```
Location: Office Floor 1
  ItemType: Laptop ThinkPad X1 (is_serialized=True)
    ├── Item(qty=1, sn="SN001", location="Floor 1")
    ├── Item(qty=1, sn="SN002", location="Floor 1")
    ├── Item(qty=1, sn="SN003", location="Floor 2")

Transfer SN001 and SN002 to Floor 2:
  1. Update Item where sn="SN001": location="Floor 2"
  2. Update Item where sn="SN002": location="Floor 2"
  3. Create TRANSFER transactions
```

### Implementation Sketch (Future)

**New Models:**
```python
class Location(Base):
    """Storage location."""
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    address = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    items = relationship("Item", back_populates="location")


class Item(Base):
    # ... existing fields ...
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    location = relationship("Location", back_populates="items")


class TransactionType(enum.Enum):
    ADD = "add"
    REMOVE = "remove"
    EDIT = "edit"
    TRANSFER = "transfer"  # NEW


class Transaction(Base):
    # ... existing fields ...
    from_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    to_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
```

**Repository Methods:**
```python
class ItemRepository:
    @staticmethod
    def transfer_bulk(item_id: int, quantity: int,
                     to_location_id: int, notes: str = "") -> Tuple[Item, Item]:
        """Transfer quantity from one location to another."""
        # Split item record or update location
        pass

    @staticmethod
    def transfer_serialized(item_ids: List[int],
                          to_location_id: int, notes: str = "") -> List[Item]:
        """Transfer specific serialized items to new location."""
        # Update location_id for each item
        pass

    @staticmethod
    def transfer_all_type(type_id: int, from_location_id: int,
                         to_location_id: int, notes: str = "") -> List[Item]:
        """Transfer all items of a type from one location to another."""
        pass
```

**UI Features:**
```
- Location selector in Add/Edit Item dialogs
- "Transfer" button in context menu
- Transfer dialog:
  [Source Location] → [Target Location]
  If bulk: [Quantity spinner]
  If serialized: [Multi-select list of serial numbers]
  [Reason/Notes text field]
  [Transfer] [Cancel]

- Inventory view grouping by location (optional)
- Location management dialog (add/edit/delete locations)
```

### Why Option B Handles This Better

| Aspect | Option A (Flat) | Option B (Hierarchical) |
|--------|----------------|------------------------|
| **Location per item** | One location per entire record | Location per Item instance |
| **Bulk transfer** | Complex: update one record | Clean: split or update Item records |
| **Serialized transfer** | Very complex: multiple rows | Simple: update location_id |
| **Transfer all of type** | Query all rows, update each | Query by type_id, update location |
| **Location history** | Hard to track | Transaction log with from/to locations |
| **Reports by location** | Complex grouping | Simple: GROUP BY location_id |

### Database Queries (Option B)

```sql
-- Get all items at a location
SELECT it.name, it.sub_type, SUM(i.quantity) as total
FROM items i
JOIN item_types it ON i.item_type_id = it.id
WHERE i.location_id = ?
GROUP BY it.id;

-- Get serialized items at a location
SELECT it.name, it.sub_type, i.serial_number
FROM items i
JOIN item_types it ON i.item_type_id = it.id
WHERE i.location_id = ? AND i.serial_number IS NOT NULL
ORDER BY it.name, i.serial_number;

-- Transfer history for an item
SELECT t.*, l1.name as from_location, l2.name as to_location
FROM transactions t
LEFT JOIN locations l1 ON t.from_location_id = l1.id
LEFT JOIN locations l2 ON t.to_location_id = l2.id
WHERE t.item_id = ? AND t.transaction_type = 'transfer'
ORDER BY t.created_at DESC;
```

### Migration Path

**Phase 1** (Current proposal): Implement hierarchical model with `location` string field
**Phase 2** (Future): Add Location table, migrate string → foreign key
**Phase 3** (Future): Add transfer functionality

This way, even without the Location table, you can start tracking locations as strings, then upgrade later without another major migration.

---

## Recommendation

**I recommend Option B (Hierarchical Model)** for these reasons:

1. **Logical Separation**: Types are entities, Items are instances
2. **Better Serial Number Handling**: Clear distinction between serialized and bulk items
3. **Autocomplete**: Natural fit with type table
4. **Scalability**: Easy to add type-level attributes (min stock, category, supplier, etc.)
5. **Data Integrity**: No duplicate type names, referential integrity
6. **Future Location Support**: ⭐ Location field already included, ready for future expansion
7. **Transfer Operations**: Clean implementation for future location transfers

1. **Logical Separation**: Types are entities, Items are instances
2. **Better Serial Number Handling**: Clear distinction between serialized and bulk items
3. **Autocomplete**: Natural fit with type table
4. **Scalability**: Easy to add type-level attributes (min stock, category, supplier, etc.)
5. **Data Integrity**: No duplicate type names, referential integrity
6. **Future Features**: Easy to add:
   - Categories (ItemType.category_id)
   - Suppliers per type
   - Reorder points per type
   - Type-specific custom fields

**However**, if time is critical, start with Option A and plan Option B for v2.0.

---

## Next Steps

1. **Review this proposal** and decide: Option A or B?
2. **If Option B**: Create Alembic migration script
3. **Update models, repositories, services**
4. **Update all UI dialogs** with new logic
5. **Add comprehensive tests** for new functionality
6. **Update documentation** (CLAUDE.md, IMPROVEMENTS.md)

Would you like me to implement either option?
