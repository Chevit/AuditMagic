# Remove `notes` from `Item` — Claude Code Instructions

## Goal

Remove the `notes` column from the `Item` model. Notes must live **only on `Transaction`**.

- **Initial item creation** (`AddItemDialog`): replace the removed notes field with an optional "Initial notes" input whose value becomes `transaction_notes` on the first ADD transaction. If empty, fall back to the existing default (`tr("transaction.notes.initial")`).
- **Edit transactions** (`EditItemDialog`): the existing `edit_reason` field already writes to `Transaction.notes` — keep it as-is (required).
- **Add / Remove quantity transactions** (`QuantityDialog`): the existing optional `notes` field already writes to `Transaction.notes` — keep it as-is (optional, empty is fine).

---

## Step 1 — Alembic migration

Create a new migration file in `alembic/versions/`. Name it something like `c3d4e_remove_item_notes.py`.

```python
"""Remove notes column from items table

Revision ID: c3d4e_remove_item_notes
Revises: b2c3d_add_serial_number_to_transactions
Create Date: <today>
"""

from alembic import op
import sqlalchemy as sa

revision = 'c3d4e_remove_item_notes'
down_revision = 'b2c3d_add_serial_number_to_transactions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('items') as batch_op:
        batch_op.drop_column('notes')


def downgrade() -> None:
    with op.batch_alter_table('items') as batch_op:
        batch_op.add_column(sa.Column('notes', sa.Text(), nullable=True))
```

> Batch mode is already required for SQLite — `with op.batch_alter_table(...)` is correct.

---

## Step 2 — `models.py`

**Remove** the `notes` column from `Item`:

```python
# DELETE this line from Item class:
notes = Column(Text, nullable=True)
```

No other changes needed in this file.

---

## Step 3 — `repositories.py`

### 3a — `_detach_item()` helper

Remove `notes` from the copy constructor:

```python
def _detach_item(item: Item) -> Item:
    if item is None:
        return None
    return Item(
        id=item.id,
        item_type_id=item.item_type_id,
        quantity=item.quantity,
        serial_number=item.serial_number,
        location=item.location,
        condition=item.condition,
        # notes REMOVED
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
```

### 3b — `ItemRepository.create()`

Remove the `notes` parameter and its usage:

```python
@staticmethod
def create(
    item_type_id: int,
    quantity: int = 1,
    serial_number: str = None,
    location: str = None,
    condition: str = None,
    # notes parameter REMOVED
    transaction_notes: str = None,
) -> Item:
    ...
    item = Item(
        item_type_id=item_type_id,
        quantity=quantity,
        serial_number=serial_number or None,
        location=location or "",
        condition=condition or "",
        # notes=... REMOVED
    )
```

The `transaction_notes` parameter (and its use in creating the initial `Transaction`) stays unchanged.

### 3c — `ItemRepository.update()`

Remove `notes` parameter and its body logic:

```python
@staticmethod
def update(
    item_id: int,
    serial_number: str = None,
    location: str = None,
    condition: str = None,
    # notes parameter REMOVED
) -> Optional[Item]:
    ...
    # Remove this block entirely:
    # if notes is not None:
    #     item.notes = notes
```

Update the docstring accordingly.

### 3d — `ItemRepository.edit_item()`

Remove `notes` parameter and its usage:

```python
@staticmethod
def edit_item(
    item_id: int,
    item_type_id: int,
    quantity: int,
    serial_number: str,
    location: str,
    condition: str,
    # notes parameter REMOVED
    edit_reason: str,
) -> Optional[Item]:
    ...
    item.location = location or ""
    item.condition = condition or ""
    # item.notes = notes or ""  ← REMOVE this line
```

### 3e — `ItemRepository.search()`

Remove the `notes` field search branch and autocomplete:

In `search()`, remove the `elif field == "notes":` branch and remove `Item.notes.ilike(...)` from the `or_()` in the `else` branch.

In `get_autocomplete_suggestions()`, remove the entire `if field == "notes" or field is None:` block that queries `Item.notes`.

---

## Step 4 — `services.py`

### 4a — `InventoryService.create_item()`

Remove `notes` parameter:

```python
@staticmethod
def create_item(
    item_type_name: str,
    item_sub_type: str = "",
    quantity: int = 1,
    is_serialized: bool = False,
    serial_number: str = None,
    location: str = "",
    condition: str = "",
    # notes parameter REMOVED
    details: str = ""
) -> InventoryItem:
```

Remove `notes=notes` from the `ItemRepository.create(...)` call inside this method.

### 4b — `InventoryService.create_or_merge_item()`

Remove `notes` parameter:

```python
@staticmethod
def create_or_merge_item(
    item_type_name: str,
    quantity: int,
    sub_type: str = "",
    is_serialized: bool = False,
    serial_number: str = "",
    details: str = "",
    location: str = "",
    condition: str = "",
    # notes parameter REMOVED
    transaction_notes: str = "",
) -> Tuple[InventoryItem, bool]:
```

Remove `notes=notes` from all `ItemRepository.create(...)` calls inside this method. The `transaction_notes` argument stays.

### 4c — `InventoryService.update_item()`

Remove `notes` parameter and its pass-through to `ItemRepository.update()`:

```python
@staticmethod
def update_item(
    item_id: int,
    serial_number: str = None,
    location: str = None,
    condition: str = None,
    # notes parameter REMOVED
) -> Optional[InventoryItem]:
```

### 4d — `InventoryService.edit_item()`

Remove `notes` parameter and its pass-through to `ItemRepository.edit_item()`:

```python
@staticmethod
def edit_item(
    item_id: int,
    item_type_name: str,
    sub_type: str = "",
    quantity: int = 1,
    is_serialized: bool = False,
    serial_number: str = "",
    details: str = "",
    location: str = "",
    condition: str = "",
    # notes parameter REMOVED
    edit_reason: str = "",
) -> Optional[InventoryItem]:
```

Remove `notes=notes` from the `ItemRepository.edit_item(...)` call.

---

## Step 5 — `ui_entities/inventory_item.py`

### 5a — `InventoryItem` dataclass

Remove the `notes` field:

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
    location: Optional[str]
    condition: Optional[str]
    # notes field REMOVED
    details: Optional[str]
    created_at: datetime
    updated_at: datetime
```

In `from_db_models()`, remove `notes=item.notes or ""`.

In `to_dict()`, remove the `"notes": self.notes` entry.

### 5b — `GroupedInventoryItem` dataclass

Remove the `notes` compatibility property:

```python
# DELETE this property:
@property
def notes(self) -> str:
    """Grouped items don't have single notes."""
    return ""
```

Remove `"notes": ...` from `to_dict()` if present.

---

## Step 6 — `ui_entities/add_item_dialog.py`

### What to change

The dialog currently has no `notes` UI field, but `InventoryService.create_item()` is called without `transaction_notes`. We need to:

1. **Add an optional "Initial notes" `QTextEdit`** field to the form, labelled with a translation key such as `tr("label.initial_notes")` and placeholder `tr("placeholder.initial_notes")`.
2. Pass its value as `transaction_notes` to the service call.

### UI change (inside `_setup_ui` form section, after the `details` field)

```python
# Initial notes (optional) — stored as transaction notes on first ADD
initial_notes_label = QLabel(tr("label.initial_notes"))
self.initial_notes_edit = QTextEdit()
self.initial_notes_edit.setPlaceholderText(tr("placeholder.initial_notes"))
self.initial_notes_edit.setMaximumHeight(60)
apply_text_edit_style(self.initial_notes_edit)
form_layout.addRow(initial_notes_label, self.initial_notes_edit)
```

### Validation (inside `_on_add_clicked`)

Optionally validate max length (1000 chars) if non-empty — same pattern as details:

```python
initial_notes = self.initial_notes_edit.toPlainText().strip()
if initial_notes:
    valid, error = validate_length(initial_notes, tr("label.initial_notes"), max_length=1000)
    if not valid:
        errors.append(error)
```

### Service call (inside `_on_add_clicked`)

```python
self._result_item = InventoryService.create_item(
    item_type_name=item_type,
    item_sub_type=sub_type,
    quantity=quantity,
    is_serialized=is_serialized,
    serial_number=serial_number if is_serialized else None,
    details=details,
    # no notes= anymore
)
```

Wait — `create_item()` doesn't accept `transaction_notes` yet. You need to thread it through the service, OR call `create_or_merge_item()` instead which already accepts `transaction_notes`. 

**Preferred approach**: Update `InventoryService.create_item()` to accept an optional `transaction_notes: str = ""` and pass it to `ItemRepository.create()`:

```python
# In services.py create_item():
db_item = ItemRepository.create(
    item_type_id=item_type.id,
    quantity=quantity,
    serial_number=serial_number,
    location=location,
    condition=condition,
    transaction_notes=transaction_notes or None,  # None = use default
)
```

Then in `add_item_dialog.py`:

```python
self._result_item = InventoryService.create_item(
    item_type_name=item_type,
    item_sub_type=sub_type,
    quantity=quantity,
    is_serialized=is_serialized,
    serial_number=serial_number if is_serialized else None,
    details=details,
    transaction_notes=initial_notes or None,
)
```

---

## Step 7 — `ui_entities/edit_item_dialog.py`

### Remove `notes` from the InventoryItem built in `_on_save_clicked`

```python
self._result_item = InventoryItem(
    id=self._original_item.id,
    item_type_id=self._original_item.item_type_id,
    item_type_name=item_type,
    item_sub_type=sub_type,
    is_serialized=self._original_item.is_serialized,
    quantity=quantity,
    serial_number=serial_number or None,
    location=self._original_item.location,
    condition=self._original_item.condition,
    # notes=... REMOVED
    details=item_details,
    created_at=self._original_item.created_at,
    updated_at=self._original_item.updated_at,
)
```

### Remove `notes` from `_populate_fields` if it references `item.notes`

Check `_populate_fields()` — if there is a `self.notes_edit` or any reference to `self._original_item.notes`, remove it. The edit dialog currently has no separate `notes` field (only `item_details` and `reason_edit`), so this may already be clean.

### Caller in `main_window.py`

Find where `InventoryService.edit_item()` is called after the `EditItemDialog` is accepted, and remove the `notes=` keyword argument if it was passed. Verify the call signature matches the updated service.

---

## Step 8 — `ui_entities/quantity_dialog.py`

**No changes needed.** The `notes` field in `QuantityDialog` maps to `Transaction.notes` via `add_quantity()` / `remove_quantity()` — this is correct behaviour and must stay.

---

## Step 9 — Translations (`ui_entities/translations.py`)

Add new translation keys for the initial-notes field in `AddItemDialog`. Example:

```python
# English
"label.initial_notes": "Initial Notes",
"placeholder.initial_notes": "Optional notes for the first inventory record…",

# Ukrainian (uk)
"label.initial_notes": "Початкові нотатки",
"placeholder.initial_notes": "Необов'язкові нотатки для першого запису…",
```

Remove any translation keys that referred only to `Item.notes` if they are now unused (e.g. `"label.notes"`, `"placeholder.notes"` — check whether they are still used in `QuantityDialog` first; if so, keep them).

---

## Step 10 — Search widget (`ui_entities/search_widget.py`)

If the search widget exposes a `"notes"` field option in its field selector (dropdown), remove that option — `Item.notes` no longer exists. The `Transaction.notes` field is not searched from the main search widget, so no replacement is needed.

---

## Step 11 — Any other callers

Search the entire project for references to `item.notes`, `.notes =`, `notes=` (as a keyword arg to item-related calls), and `InventoryItem(...notes=...)`. Verify every remaining usage belongs to `Transaction.notes` or `SearchHistory`, not `Item.notes`.

Key files to audit:

- `ui_entities/item_details_dialog.py` — remove display of `item.notes` if present
- `ui_entities/add_serial_number_dialog.py` — check if it passes `notes` to service; remove if so
- `ui_entities/remove_serial_number_dialog.py` — uses `notes` for `delete_by_serial_numbers()` (transaction notes) — keep it
- `ui_entities/main_window.py` — check all service calls

---

## Step 12 — Update `CLAUDE.md`

Apply the following changes to `CLAUDE.md`:

### In the **Data Model** section, update the `Item` entry:

**Before:**
```
- **Item**: `item_type_id` (FK), `quantity`, `serial_number`, `location`, `condition`, `notes`
- ...
- ItemType `details` = type description; Item `notes` = item-specific notes; Transaction `notes` = reason for change
```

**After:**
```
- **Item**: `item_type_id` (FK), `quantity`, `serial_number`, `location`, `condition`
- ...
- ItemType `details` = type description; Transaction `notes` = reason for change (required for EDIT, optional for ADD/REMOVE)
```

### In the **UI Components / AddItemDialog** section (or add a note):

Add:
> **Initial Notes field**: Optional `QTextEdit` whose value is passed as `transaction_notes` to `InventoryService.create_item()`, becoming the notes on the first ADD transaction. If empty, defaults to `tr("transaction.notes.initial")`.

### In the **EditItemDialog** section, remove any mention of item-level notes.

### In the **Key Patterns** section, update or remove the bullet referencing `Item.notes`.

---

## Summary of changes by file

| File | Change |
|------|--------|
| `alembic/versions/c3d4e_remove_item_notes.py` | **New** — drops `items.notes` column |
| `models.py` | Remove `notes` column from `Item` |
| `repositories.py` | Remove `notes` param from `create`, `update`, `edit_item`; remove `notes` from `_detach_item`; remove notes from search/autocomplete |
| `services.py` | Remove `notes` param from `create_item`, `create_or_merge_item`, `update_item`, `edit_item`; add `transaction_notes` pass-through to `create_item` |
| `inventory_item.py` | Remove `notes` field from `InventoryItem`; remove `notes` compat property from `GroupedInventoryItem` |
| `add_item_dialog.py` | Remove `notes` UI (if any); add optional "Initial notes" field → `transaction_notes` |
| `edit_item_dialog.py` | Remove `notes` from constructed `InventoryItem`; no notes field in UI |
| `quantity_dialog.py` | **No change** — `notes` here is transaction notes; correct |
| `translations.py` | Add `label.initial_notes` / `placeholder.initial_notes`; clean up unused item-notes keys |
| `search_widget.py` | Remove `"notes"` from field selector if present |
| `item_details_dialog.py` | Remove display of `item.notes` |
| `main_window.py` | Audit all service calls; remove `notes=` args to item services |
| `CLAUDE.md` | Update Data Model, UI Components, Key Patterns sections |
