# Implementation Guide: Hierarchical Model - Part 2 (UI & Testing)

> **Continuation of IMPLEMENT_HIERARCHICAL_MODEL.md**

This part covers UI updates, dialog modifications, and comprehensive testing.

---

## Phase 7: Update UI Dialogs (Day 5-6)

### Step 7.1: Update AddItemDialog

**File**: `ui_entities/add_item_dialog.py`

Add imports at top:
```python
from PyQt6.QtWidgets import QCompleter, QCheckBox
from PyQt6.QtCore import QStringListModel, Qt
from services import InventoryService
```

Add to `__init__` method (after existing UI setup):

```python
def __init__(self, parent=None):
    super().__init__(parent)
    # ... existing code ...
    self._setup_autocomplete()
    self._setup_serialization_checkbox()
    self._connect_serialization_signals()
```

Add these NEW methods to the class:

```python
def _setup_autocomplete(self):
    """Setup autocomplete for type and subtype fields."""
    # Type autocomplete
    self.type_completer = QCompleter(self)
    self.type_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    self.type_completer.setFilterMode(Qt.MatchFlag.MatchContains)
    self.type_input.setCompleter(self.type_completer)

    # Subtype autocomplete
    self.subtype_completer = QCompleter(self)
    self.subtype_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    self.subtype_completer.setFilterMode(Qt.MatchFlag.MatchContains)
    self.subtype_input.setCompleter(self.subtype_completer)

    # Update autocomplete on text change
    self.type_input.textChanged.connect(self._update_type_autocomplete)
    self.type_input.textChanged.connect(self._update_subtype_autocomplete)

def _update_type_autocomplete(self, text: str):
    """Update autocomplete suggestions for type."""
    try:
        suggestions = InventoryService.get_autocomplete_types(text)
        model = QStringListModel(suggestions)
        self.type_completer.setModel(model)
    except Exception as e:
        logger.error(f"Failed to load type autocomplete: {e}")

def _update_subtype_autocomplete(self, type_text: str):
    """Update autocomplete suggestions for subtype based on selected type."""
    if not type_text:
        return
    try:
        suggestions = InventoryService.get_autocomplete_subtypes(type_text)
        model = QStringListModel(suggestions)
        self.subtype_completer.setModel(model)
    except Exception as e:
        logger.error(f"Failed to load subtype autocomplete: {e}")

def _setup_serialization_checkbox(self):
    """Add checkbox for serial number tracking."""
    # Create checkbox
    self.serialized_checkbox = QCheckBox(tr("dialog.add.has_serial"))
    self.serialized_checkbox.setToolTip(tr("dialog.add.has_serial.tooltip"))

    # Add to layout (insert before quantity field)
    # Find the row index of quantity field and insert checkbox before it
    # This depends on your specific layout structure
    # Example if using QFormLayout:
    if hasattr(self, 'form_layout'):
        qty_row = None
        for i in range(self.form_layout.rowCount()):
            if self.form_layout.itemAt(i, QFormLayout.ItemRole.FieldRole).widget() == self.quantity_input:
                qty_row = i
                break
        if qty_row is not None:
            self.form_layout.insertRow(qty_row, tr("dialog.add.serialized"), self.serialized_checkbox)

def _connect_serialization_signals(self):
    """Connect serialization checkbox to enable/disable logic."""
    self.serialized_checkbox.stateChanged.connect(self._on_serialization_changed)
    # Initialize state
    self._on_serialization_changed(self.serialized_checkbox.checkState())

def _on_serialization_changed(self, state):
    """Handle serialization checkbox change.

    When checked:
        - Serial number field enabled
        - Quantity field disabled and set to 1
    When unchecked:
        - Serial number field disabled and cleared
        - Quantity field enabled
    """
    is_serialized = (state == Qt.CheckState.Checked)

    if is_serialized:
        # Enable serial number
        self.serial_number_input.setEnabled(True)
        self.serial_number_input.setStyleSheet("")
        apply_input_style(self.serial_number_input)

        # Disable and fix quantity to 1
        self.quantity_input.setEnabled(False)
        self.quantity_input.setValue(1)
        self.quantity_input.setStyleSheet("background-color: #e0e0e0;")
    else:
        # Disable and clear serial number
        self.serial_number_input.setEnabled(False)
        self.serial_number_input.clear()
        self.serial_number_input.setStyleSheet("background-color: #e0e0e0;")

        # Enable quantity
        self.quantity_input.setEnabled(True)
        self.quantity_input.setStyleSheet("")
        apply_input_style(self.quantity_input)
```

Update the `_on_submit` method to pass new parameters:

```python
def _on_submit(self):
    """Submit the form with new hierarchical model."""
    # ... existing validation ...

    try:
        item = InventoryService.create_item(
            item_type_name=item_type,
            item_sub_type=sub_type,
            quantity=quantity,
            is_serialized=self.serialized_checkbox.isChecked(),
            serial_number=serial_number if self.serialized_checkbox.isChecked() else None,
            location="",  # Can add location input field later
            condition="",  # Can add condition input field later
            notes="",
            details=details
        )
        self.accept()
    except ValueError as e:
        QMessageBox.warning(self, tr("error.validation.title"), str(e))
    except Exception as e:
        logger.error(f"Failed to create item: {e}", exc_info=True)
        QMessageBox.critical(self, tr("error.generic.title"), str(e))
```

### Step 7.2: Update ItemDetailsDialog

**File**: `ui_entities/item_details_dialog.py`

Add method to show serial numbers for serialized types:

```python
def _load_item_details(self):
    """Load item details with serial number list for serialized types."""
    item = InventoryService.get_item(self.item_id)
    if not item:
        return

    # Display basic info
    self.name_label.setText(item.display_name)
    self.quantity_label.setText(str(item.quantity))
    self.details_text.setPlainText(item.details)

    # If serialized type, show serial numbers section
    if item.is_serialized:
        self._setup_serial_numbers_section(item)
    else:
        # Hide serial numbers section if exists
        if hasattr(self, 'serial_numbers_widget'):
            self.serial_numbers_widget.setVisible(False)

def _setup_serial_numbers_section(self, item):
    """Setup section showing all serial numbers for this type.

    Args:
        item: InventoryItem instance
    """
    # Get all serial numbers for this type
    from repositories import ItemRepository
    serial_numbers = ItemRepository.get_serial_numbers_for_type(item.item_type_id)

    # Create UI if not exists
    if not hasattr(self, 'serial_numbers_widget'):
        from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QListWidget, QLabel

        self.serial_numbers_widget = QGroupBox(tr("dialog.details.serial_numbers"))
        sn_layout = QVBoxLayout()

        self.serial_count_label = QLabel()
        sn_layout.addWidget(self.serial_count_label)

        self.serial_list = QListWidget()
        self.serial_list.setMaximumHeight(200)
        sn_layout.addWidget(self.serial_list)

        self.serial_numbers_widget.setLayout(sn_layout)

        # Add to main layout
        self.layout().addWidget(self.serial_numbers_widget)

    # Populate list
    self.serial_list.clear()
    for sn in serial_numbers:
        self.serial_list.addItem(sn)

    self.serial_count_label.setText(
        tr("dialog.details.serial_count").format(count=len(serial_numbers))
    )
    self.serial_numbers_widget.setVisible(True)
```

### Step 7.3: Update SearchWidget

**File**: `ui_entities/search_widget.py`

Add "Serial Number" option to search field dropdown:

```python
def _setup_search_fields(self):
    """Setup search field dropdown with serial number option."""
    self.field_combo.clear()
    self.field_combo.addItems([
        tr("search.field.all"),
        tr("search.field.type"),
        tr("search.field.subtype"),
        tr("search.field.serial"),  # NEW
        tr("search.field.location"),  # NEW
        tr("search.field.details")
    ])
```

### Step 7.4: Add Translation Keys

**File**: `ui_entities/translations.py`

Add these new translation keys:

```python
TRANSLATIONS = {
    # ... existing translations ...

    # Add Item Dialog - Serial Number
    "dialog.add.has_serial": {
        "uk": "Має серійний номер",
        "en": "Has Serial Number"
    },
    "dialog.add.has_serial.tooltip": {
        "uk": "Позначте, якщо цей тип товару має унікальні серійні номери. Кількість буде зафіксована на 1.",
        "en": "Check if this item type has unique serial numbers. Quantity will be fixed at 1."
    },
    "dialog.add.serialized": {
        "uk": "Серійний товар",
        "en": "Serialized Item"
    },

    # Item Details - Serial Numbers
    "dialog.details.serial_numbers": {
        "uk": "Серійні номери",
        "en": "Serial Numbers"
    },
    "dialog.details.serial_count": {
        "uk": "Всього серійних номерів: {count}",
        "en": "Total Serial Numbers: {count}"
    },
    "dialog.details.none": {
        "uk": "Немає",
        "en": "None"
    },

    # Search Fields
    "search.field.serial": {
        "uk": "Серійний номер",
        "en": "Serial Number"
    },
    "search.field.location": {
        "uk": "Місцезнаходження",
        "en": "Location"
    },

    # Validation Errors
    "error.serial.required": {
        "uk": "Серійний номер обов'язковий для серійних товарів",
        "en": "Serial number required for serialized items"
    },
    "error.quantity.must_be_one": {
        "uk": "Кількість повинна бути 1 для серійних товарів",
        "en": "Quantity must be 1 for serialized items"
    },
    "error.serial.not_allowed": {
        "uk": "Серійний номер не дозволений для несерійних товарів",
        "en": "Serial number not allowed for non-serialized items"
    },
}
```

---

## Phase 8: Update InventoryModel (Day 6)

### Step 8.1: Update InventoryModel display

**File**: `ui_entities/inventory_model.py`

Update the `data()` method to show new display format:

```python
def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
    """Provide data for model index."""
    if not index.isValid() or index.row() >= len(self._items):
        return None

    item = self._items[index.row()]

    if role == Qt.ItemDataRole.DisplayRole:
        # Use new display_info property
        return item.display_info

    elif role == InventoryItemRole.ItemData:
        return item

    # ... rest of existing roles ...
```

---

## Phase 9: Update Search Functionality (Day 6-7)

### Step 9.1: Update SearchService

**File**: `services.py`

Update the `SearchService.search()` method to handle new fields:

```python
class SearchService:
    """Service for search operations with autocomplete and history."""

    @staticmethod
    def search(
        query: str, field: str = None, save_to_history: bool = True
    ) -> List[InventoryItem]:
        """Search for items and optionally save to history.

        Args:
            query: Search query string.
            field: Field to search in ('item_type', 'sub_type', 'serial', 'location', 'details', or None for all).
            save_to_history: Whether to save this search to history.

        Returns:
            List of matching InventoryItem instances.
        """
        if save_to_history and query.strip():
            SearchHistoryRepository.add(query, field)

        # Map field names
        if field == "serial":
            field = "serial_number"

        # Perform search
        db_items = ItemRepository.search(query, field)

        # Convert to InventoryItems
        result = []
        for db_item in db_items:
            item_type = ItemTypeRepository.get_by_id(db_item.item_type_id)
            if item_type:
                result.append(InventoryItem.from_db_models(db_item, item_type))

        return result
```

### Step 9.2: Update ItemRepository.search()

**File**: `repositories.py`

Update the `ItemRepository.search()` method:

```python
@staticmethod
def search(query: str, field: str = None, limit: int = 100) -> List[Item]:
    """Search items by query string.

    Args:
        query: Search query string.
        field: Field to search ('serial_number', 'location', or None for all).
        limit: Maximum results.

    Returns:
        List of matching Item instances.
    """
    logger.debug(f"Repository: Searching items with query='{query}', field={field}")
    with session_scope() as session:
        search_pattern = f"%{query}%"

        if field == "serial_number":
            items = (
                session.query(Item)
                .filter(Item.serial_number.ilike(search_pattern))
                .limit(limit)
                .all()
            )
        elif field == "location":
            items = (
                session.query(Item)
                .filter(Item.location.ilike(search_pattern))
                .limit(limit)
                .all()
            )
        else:
            # Search in all fields including ItemType
            items = (
                session.query(Item)
                .join(ItemType)
                .filter(
                    or_(
                        ItemType.name.ilike(search_pattern),
                        ItemType.sub_type.ilike(search_pattern),
                        ItemType.details.ilike(search_pattern),
                        Item.serial_number.ilike(search_pattern),
                        Item.location.ilike(search_pattern),
                        Item.notes.ilike(search_pattern)
                    )
                )
                .limit(limit)
                .all()
            )

        return [_detach_item(item) for item in items]
```

---

## Phase 10: Testing (Day 7-8)

### Step 10.1: Create Unit Tests

**File**: `tests/unit/test_item_type_repository.py` (NEW)

```python
"""Unit tests for ItemTypeRepository."""
import pytest
from repositories import ItemTypeRepository


class TestItemTypeRepository:
    """Tests for ItemTypeRepository."""

    def test_create_item_type(self, db_session):
        """Test creating an item type."""
        item_type = ItemTypeRepository.create(
            name="Laptop",
            sub_type="MacBook Pro",
            is_serialized=True,
            details="Apple laptop"
        )

        assert item_type is not None
        assert item_type.id is not None
        assert item_type.name == "Laptop"
        assert item_type.sub_type == "MacBook Pro"
        assert item_type.is_serialized is True

    def test_get_or_create_existing(self, db_session):
        """Test get_or_create returns existing type."""
        # Create first time
        type1 = ItemTypeRepository.create(name="Laptop", sub_type="ThinkPad")

        # Get or create should return existing
        type2 = ItemTypeRepository.get_or_create(name="Laptop", sub_type="ThinkPad")

        assert type1.id == type2.id

    def test_get_or_create_new(self, db_session):
        """Test get_or_create creates new if not exists."""
        item_type = ItemTypeRepository.get_or_create(name="Monitor", sub_type="Dell")

        assert item_type is not None
        assert item_type.name == "Monitor"

    def test_autocomplete_names(self, db_session):
        """Test autocomplete for type names."""
        ItemTypeRepository.create(name="Laptop", sub_type="")
        ItemTypeRepository.create(name="Laser Printer", sub_type="")
        ItemTypeRepository.create(name="Monitor", sub_type="")

        results = ItemTypeRepository.get_autocomplete_names("La")

        assert len(results) == 2
        assert "Laptop" in results
        assert "Laser Printer" in results

    def test_autocomplete_subtypes(self, db_session):
        """Test autocomplete for subtypes."""
        ItemTypeRepository.create(name="Laptop", sub_type="MacBook Pro")
        ItemTypeRepository.create(name="Laptop", sub_type="MacBook Air")
        ItemTypeRepository.create(name="Laptop", sub_type="ThinkPad")

        results = ItemTypeRepository.get_autocomplete_subtypes("Laptop", "Mac")

        assert len(results) == 2
        assert "MacBook Pro" in results
        assert "MacBook Air" in results
```

**File**: `tests/unit/test_hierarchical_items.py` (NEW)

```python
"""Tests for hierarchical item model."""
import pytest
from repositories import ItemTypeRepository, ItemRepository


class TestHierarchicalModel:
    """Test hierarchical ItemType/Item relationship."""

    def test_create_serialized_item(self, db_session):
        """Test creating serialized item."""
        # Create type
        item_type = ItemTypeRepository.create(
            name="Laptop",
            sub_type="MacBook Pro",
            is_serialized=True
        )

        # Create item
        item = ItemRepository.create(
            item_type_id=item_type.id,
            quantity=1,
            serial_number="SN12345"
        )

        assert item.quantity == 1
        assert item.serial_number == "SN12345"
        assert item.item_type_id == item_type.id

    def test_serialized_validation_requires_serial(self, db_session):
        """Test that serialized items require serial number."""
        item_type = ItemTypeRepository.create(
            name="Laptop",
            is_serialized=True
        )

        with pytest.raises(ValueError, match="Serial number required"):
            ItemRepository.create(
                item_type_id=item_type.id,
                quantity=1,
                serial_number=None
            )

    def test_serialized_validation_quantity_one(self, db_session):
        """Test that serialized items must have quantity=1."""
        item_type = ItemTypeRepository.create(
            name="Laptop",
            is_serialized=True
        )

        with pytest.raises(ValueError, match="Quantity must be 1"):
            ItemRepository.create(
                item_type_id=item_type.id,
                quantity=5,
                serial_number="SN12345"
            )

    def test_bulk_item_no_serial(self, db_session):
        """Test that bulk items cannot have serial numbers."""
        item_type = ItemTypeRepository.create(
            name="Cable",
            is_serialized=False
        )

        with pytest.raises(ValueError, match="Serial number not allowed"):
            ItemRepository.create(
                item_type_id=item_type.id,
                quantity=10,
                serial_number="SN12345"
            )

    def test_get_serial_numbers_for_type(self, db_session):
        """Test getting all serial numbers for a type."""
        item_type = ItemTypeRepository.create(
            name="Laptop",
            is_serialized=True
        )

        # Create multiple items
        ItemRepository.create(item_type.id, 1, "SN001")
        ItemRepository.create(item_type.id, 1, "SN002")
        ItemRepository.create(item_type.id, 1, "SN003")

        serial_numbers = ItemRepository.get_serial_numbers_for_type(item_type.id)

        assert len(serial_numbers) == 3
        assert "SN001" in serial_numbers
        assert "SN002" in serial_numbers
        assert "SN003" in serial_numbers

    def test_search_by_serial(self, db_session):
        """Test searching by serial number."""
        item_type = ItemTypeRepository.create(name="Laptop", is_serialized=True)
        item = ItemRepository.create(item_type.id, 1, "SN12345")

        found = ItemRepository.search_by_serial("SN12345")

        assert found is not None
        assert found.id == item.id
        assert found.serial_number == "SN12345"
```

### Step 10.2: Run All Tests

```bash
# Run tests
pytest tests/unit/test_item_type_repository.py -v
pytest tests/unit/test_hierarchical_items.py -v

# Run with coverage
pytest tests/ --cov=repositories --cov=services --cov-report=html

# View coverage report
open htmlcov/index.html  # or your browser
```

### Step 10.3: Manual Testing Checklist

Create test scenarios document:

**File**: `TESTING_CHECKLIST.md`

```markdown
# Hierarchical Model Testing Checklist

## 1. Item Type Creation
- [ ] Create new serialized type (Laptop)
- [ ] Create new bulk type (Cable)
- [ ] Verify types appear in autocomplete
- [ ] Verify unique constraint (can't create duplicate type+subtype)

## 2. Serialized Items
- [ ] Create laptop with serial number
- [ ] Verify quantity is locked to 1
- [ ] Verify serial number is required
- [ ] Try to create with quantity > 1 (should fail)
- [ ] Try to create without serial number (should fail)
- [ ] Create multiple laptops with different serial numbers
- [ ] Verify serial numbers list in details dialog

## 3. Bulk Items
- [ ] Create cables with quantity 50
- [ ] Verify serial number field is disabled
- [ ] Try to add serial number (should fail)
- [ ] Verify quantity can be changed
- [ ] Add/remove quantity works correctly

## 4. Autocomplete
- [ ] Type "Lap" in type field → shows "Laptop"
- [ ] Select "Laptop" → subtype shows suggestions
- [ ] Type "Mac" in subtype → shows "MacBook Pro", "MacBook Air"
- [ ] Autocomplete is case-insensitive

## 5. Search
- [ ] Search by serial number finds correct item
- [ ] Search "all" includes type names
- [ ] Search by location works
- [ ] Search results show correct display format

## 6. Migration
- [ ] Old data migrated correctly
- [ ] All items have correct type_id
- [ ] Serial numbers preserved
- [ ] Quantities preserved
- [ ] Transactions still linked correctly

## 7. Transactions
- [ ] Creating item creates initial transaction
- [ ] Adding quantity creates ADD transaction
- [ ] Removing quantity creates REMOVE transaction
- [ ] Transaction history displays correctly

## 8. Edge Cases
- [ ] Delete type deletes all items (cascade)
- [ ] Duplicate serial numbers rejected
- [ ] Empty/null values handled correctly
- [ ] Unicode characters in names work
- [ ] Very long names/serial numbers handled
```

---

## Phase 11: Update Documentation (Day 8)

### Step 11.1: Update CLAUDE.md

Add to the data model section:

```markdown
## Data Model (Updated: Hierarchical Structure)

### ItemType (Type Definitions)
- **ItemType**: `name`, `sub_type`, `is_serialized`, `details`
- Represents a category/template for items
- One ItemType can have many Items

### Item (Inventory Instances)
- **Item**: `item_type_id` (FK), `quantity`, `serial_number`, `location`, `condition`, `notes`
- Represents actual inventory units
- If serialized: quantity=1, serial_number required
- If not serialized: quantity>0, no serial_number

### Transaction
- **Transaction**: `item_id` (FK), `transaction_type` (ADD/REMOVE/EDIT), `quantity_change`, `notes`
- Tracks all inventory changes with audit trail
```

### Step 11.2: Update IMPROVEMENTS.md

Add completed task to Phase 0 or Phase 1:

```markdown
### Completed: Hierarchical Item Model ✅

- [x] **Implemented ItemType/Item separation**
- [x] **Added serial number validation logic**
- [x] **Added autocomplete for Type/SubType**
- [x] **Added location tracking (string-based)**
- [x] **Migration script preserves all data**
- [x] **Updated all UI dialogs**
- [x] **Comprehensive test coverage**
```

---

## Troubleshooting

### Issue: Migration Fails

**Solution**:
```bash
# Restore backup
cp ~/.local/share/AuditMagic/inventory.db.backup ~/.local/share/AuditMagic/inventory.db

# Check migration script for errors
# Common issues:
# - Wrong revision ID
# - Missing imports
# - SQL syntax errors

# Try downgrade first
alembic downgrade -1

# Then try upgrade again
alembic upgrade head
```

### Issue: Autocomplete Not Working

**Solution**:
- Check QCompleter is properly set up
- Verify InventoryService methods are called
- Check translation keys exist
- Look for errors in console

### Issue: Serial Number Validation Not Working

**Solution**:
- Check ItemType.is_serialized is correctly set
- Verify database constraint is created
- Check ItemRepository.create() validation logic
- Test with pytest

---

## Final Verification

Run this complete test:

```bash
# 1. Database integrity
python -c "
from db import init_database, get_session
from models import ItemType, Item
init_database()
session = get_session()
types = session.query(ItemType).count()
items = session.query(Item).count()
print(f'Types: {types}, Items: {items}')
session.close()
"

# 2. Repository tests
pytest tests/unit/ -v

# 3. Launch app
python main.py

# 4. Manual tests:
# - Create serialized item
# - Create bulk item
# - Test autocomplete
# - Test search
# - View details dialog
# - Add/remove quantity
# - Check transactions
```

---

## Success Criteria

✅ **Phase Complete When:**
1. All unit tests pass
2. Migration runs without errors
3. App launches successfully
4. Can create both serialized and bulk items
5. Autocomplete works for types and subtypes
6. Serial number validation enforces rules
7. Search by serial number works
8. Details dialog shows serial numbers list
9. All existing data preserved
10. No regression in existing functionality

---

## Next Steps (Future Enhancements)

After successful implementation:
1. Add Location table (Phase 2 from proposal)
2. Implement transfer operations
3. Add bulk operations UI
4. Add export with new model
5. Add advanced filtering
6. Performance optimization for large datasets

---

## Estimated Timeline

- **Day 1-2**: Models + Migration (4-8 hours)
- **Day 3-4**: Repositories + DTOs (6-8 hours)
- **Day 4-5**: Services (4-6 hours)
- **Day 5-6**: UI Dialogs (8-10 hours)
- **Day 6-7**: Search + Testing (6-8 hours)
- **Day 7-8**: Integration Testing + Documentation (4-6 hours)

**Total**: 32-46 hours (1-2 weeks calendar time)

---

## Support

If you encounter issues:
1. Check SERIAL_NUMBER_PROPOSAL.md for design decisions
2. Review CLAUDE.md for project conventions
3. Check test files for usage examples
4. Review migration script for data transformations

Good luck with implementation! 🚀
