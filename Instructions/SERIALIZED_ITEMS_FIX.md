# Serialized Items: Context Menu Fix

## Problem

Context menu actions **"Add Quantity"** and **"Remove Quantity"** are dead-ends for serialized items — they show info messages telling the user to go elsewhere. Additionally, the non-serialized grouped item flow has a bug where only `item_ids[0]` is modified while `total_quantity` is displayed.

---

## Step 1: Add Translation Keys

**File:** `ui_entities/translations.py`

Add new keys to both Ukrainian and English dictionaries:

| Key | Ukrainian | English |
|-----|-----------|---------|
| `menu.add_serial_number` | `Додати серійний номер` | `Add Serial Number` |
| `menu.remove_serial_number` | `Видалити серійний номер` | `Remove Serial Number` |
| `dialog.add_serial.title` | `Додати серійний номер` | `Add Serial Number` |
| `dialog.add_serial.header` | `Додати новий серійний номер` | `Add New Serial Number` |
| `dialog.remove_serial.title` | `Видалити серійні номери` | `Remove Serial Numbers` |
| `dialog.remove_serial.header` | `Оберіть серійні номери для видалення` | `Select Serial Numbers to Remove` |
| `dialog.remove_serial.confirm` | `Видалити вибрані ({count})?` | `Delete selected ({count})?` |
| `error.no_serial_selected` | `Оберіть хоча б один серійний номер` | `Select at least one serial number` |
| `error.cannot_delete_all_serials` | `Не можна видалити всі серійні номери. Використовуйте "Видалити" для повного видалення.` | `Cannot delete all serial numbers. Use "Delete" for complete removal.` |
| `label.notes_reason` | `Причина / примітки` | `Reason / Notes` |

Remove the now-unused keys: `message.serialized_use_add_item`, `message.serialized_use_delete`.

---

## Step 2: Create `AddSerialNumberDialog`

**File:** `ui_entities/add_serial_number_dialog.py` (new file)

A streamlined dialog for adding a new serialized item to an existing ItemType.

### UI Layout

```
┌─────────────────────────────────────┐
│   Add Serial Number                 │
│   to: Laptop - ThinkPad X1         │
│─────────────────────────────────────│
│   Serial Number*:  [____________]   │
│   Location:        [____________]   │
│   Condition:       [____________]   │
│   Notes:           [____________]   │
│                                     │
│              [Cancel]  [Add]        │
└─────────────────────────────────────┘
```

### Constructor Parameters

```python
def __init__(
    self,
    item_type_name: str,     # Pre-filled, read-only
    sub_type: str,           # Pre-filled, read-only
    existing_serials: list[str],  # For uniqueness validation
    parent=None
)
```

### Behavior

- Serial number field: required, uses `SerialNumberValidator`, validates not in `existing_serials`
- Location, condition, notes: optional text fields
- On accept: returns serial number and optional fields via getter methods
- Does NOT call the service layer — the caller (main_window) handles creation
- Style all inputs with `apply_input_style()`, buttons with `apply_button_style()`

### Methods

```python
def get_serial_number(self) -> str
def get_location(self) -> str
def get_condition(self) -> str
def get_notes(self) -> str
```

---

## Step 3: Create `RemoveSerialNumberDialog`

**File:** `ui_entities/remove_serial_number_dialog.py` (new file)

A dialog for selecting serial numbers to delete from a grouped serialized item.

### UI Layout

```
┌──────────────────────────────────────────┐
│   Remove Serial Numbers                  │
│   from: Laptop - ThinkPad X1            │
│──────────────────────────────────────────│
│   ☐ SN-001                              │
│   ☐ SN-002                              │
│   ☐ SN-003                              │
│   ☐ SN-004                              │
│──────────────────────────────────────────│
│   Reason / Notes*:  [________________]   │
│                                          │
│   Selected: 0 of 4                       │
│              [Cancel]  [Delete]          │
└──────────────────────────────────────────┘
```

### Constructor Parameters

```python
def __init__(
    self,
    item_type_name: str,
    sub_type: str,
    serial_numbers: list[str],  # All serial numbers in the group
    parent=None
)
```

### Behavior

- Display serial numbers as a scrollable list of checkboxes (using `QScrollArea` + `QCheckBox` widgets)
- "Selected: X of Y" label updates dynamically as checkboxes are toggled
- Notes/reason field: required (for audit trail)
- Validation on accept:
  - At least one serial must be selected
  - Cannot select ALL serials — show `error.cannot_delete_all_serials` message (user should use "Delete" for full removal)
  - Notes must not be empty
- Delete button uses `apply_button_style(button, "danger")`

### Methods

```python
def get_selected_serial_numbers(self) -> list[str]
def get_notes(self) -> str
```

---

## Step 4: Dynamic Context Menu Labels

**File:** `ui_entities/inventory_list_view.py`

### Changes in `_show_context_menu()`

After getting the `item` object, check `item.is_serialized` to set the menu action text:

```python
# Before the menu is built, determine labels
if item.is_serialized:
    add_qty_label = tr("menu.add_serial_number")
    remove_qty_label = tr("menu.remove_serial_number")
else:
    add_qty_label = tr("menu.add_quantity")
    remove_qty_label = tr("menu.remove_quantity")
```

Use these variables when creating `add_qty_action` and `remove_qty_action` (lines 64, 70).

No signal changes needed — the same signals (`add_quantity_requested`, `remove_quantity_requested`) are emitted. The main_window handler already receives the item and can distinguish behavior.

---

## Step 5: Update Main Window Handlers

**File:** `ui_entities/main_window.py`

### 5a. Update `_on_add_quantity()` (line 318)

Replace the `QMessageBox.information` block for serialized items with:

```python
if item.is_serialized:
    item_name = f"{item.item_type} - {item.sub_type}" if item.sub_type else item.item_type
    existing_serials = item.serial_numbers if is_grouped else (
        [item.serial_number] if item.serial_number else []
    )
    dialog = AddSerialNumberDialog(
        item_type_name=item.item_type,
        sub_type=item.sub_type or "",
        existing_serials=existing_serials,
        parent=self
    )
    if dialog.exec():
        try:
            new_item, _ = InventoryService.create_or_merge_item(
                item_type_name=item.item_type,
                sub_type=item.sub_type or "",
                quantity=1,
                is_serialized=True,
                serial_number=dialog.get_serial_number(),
                # location=dialog.get_location(),
                # condition=dialog.get_condition(),
                notes=dialog.get_notes(),
            )
            if new_item:
                self._refresh_item_list()
        except ValueError as e:
            QMessageBox.warning(self, tr("message.validation_error"), str(e))
    return
```

Keep the non-serialized path unchanged.

### 5b. Update `_on_remove_quantity()` (line 345)

Replace the `QMessageBox.information` block for serialized items with:

```python
if item.is_serialized:
    item_name = f"{item.item_type} - {item.sub_type}" if item.sub_type else item.item_type
    serial_numbers = item.serial_numbers if is_grouped else (
        [item.serial_number] if item.serial_number else []
    )
    dialog = RemoveSerialNumberDialog(
        item_type_name=item.item_type,
        sub_type=item.sub_type or "",
        serial_numbers=serial_numbers,
        parent=self
    )
    if dialog.exec():
        try:
            selected = dialog.get_selected_serial_numbers()
            notes = dialog.get_notes()
            deleted_count = InventoryService.delete_items_by_serial_numbers(selected)
            if deleted_count > 0:
                self._refresh_item_list()
        except Exception as e:
            QMessageBox.warning(self, tr("message.validation_error"), str(e))
    return
```

### 5c. Add imports at top of file

```python
from ui_entities.add_serial_number_dialog import AddSerialNumberDialog
from ui_entities.remove_serial_number_dialog import RemoveSerialNumberDialog
```

---

## Step 6: Add Transaction Records for Serial Deletion

**File:** `repositories.py` → `ItemRepository.delete_by_serial_numbers()`

Currently this method deletes items but does NOT create REMOVE transactions. Add a transaction for each deleted serial:

- `transaction_type`: `REMOVE`
- `quantity_change`: 1
- `quantity_before`: 1
- `quantity_after`: 0
- `notes`: passed from the dialog (the reason/notes field)

This requires updating the method signature to accept `notes: str = ""` and creating Transaction records before deletion.

Also update the service layer method `InventoryService.delete_items_by_serial_numbers()` to accept and forward a `notes` parameter. Update the call in Step 5b accordingly:

```python
deleted_count = InventoryService.delete_items_by_serial_numbers(selected, notes)
```

---

## Step 7: Fix Grouped Non-Serialized Item Bug

**File:** `ui_entities/main_window.py`

### Problem

For non-serialized `GroupedInventoryItem`, the code uses `item.item_ids[0]` but displays `item.quantity` (which is `total_quantity` across all items). The QuantityDialog preview shows wrong math.

### Fix

Non-serialized items of the same type should ideally have only one Item row in the database (the `create_or_merge_item` flow already handles this). However, if multiple rows exist (from legacy data or imports), the handler should pass the correct quantity for the targeted item.

**Option A (recommended):** Add a service method to get the actual quantity of `item_ids[0]`:

```python
# In _on_add_quantity / _on_remove_quantity for non-serialized grouped:
target_item_id = item.item_ids[0]
target_item = InventoryService.get_item(target_item_id)
actual_quantity = target_item.quantity if target_item else item.quantity
dialog = QuantityDialog(item_name, actual_quantity, is_add=True, parent=self)
```

**Option B (cleaner long-term):** Add a one-time migration/cleanup that merges all non-serialized items of the same ItemType into a single row. This eliminates the problem at the data level.

---

## Step 8: Update CLAUDE.md

Add the two new dialog classes to the project structure and UI Components sections:

- `ui_entities/add_serial_number_dialog.py` — Add serial number to existing type
- `ui_entities/remove_serial_number_dialog.py` — Remove serial numbers from group

---

## File Change Summary

| File | Action |
|------|--------|
| `ui_entities/translations.py` | Add/remove translation keys |
| `ui_entities/add_serial_number_dialog.py` | **New file** |
| `ui_entities/remove_serial_number_dialog.py` | **New file** |
| `ui_entities/inventory_list_view.py` | Dynamic menu labels |
| `ui_entities/main_window.py` | Replace info messages with dialog flows, add imports |
| `repositories.py` | Add transaction records to `delete_by_serial_numbers()` |
| `services.py` | Add `notes` param to `delete_items_by_serial_numbers()` |
| `CLAUDE.md` | Document new dialogs |

## Implementation Order

1. Translations (Step 1) — no dependencies
2. `AddSerialNumberDialog` (Step 2) — no dependencies
3. `RemoveSerialNumberDialog` (Step 3) — no dependencies
4. Dynamic menu labels (Step 4) — needs Step 1
5. Main window handlers (Step 5) — needs Steps 2, 3
6. Transaction records for deletion (Step 6) — independent
7. Grouped item bug fix (Step 7) — independent
8. Documentation (Step 8) — last
