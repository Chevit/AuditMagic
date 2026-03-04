# Core Layer Cleanup — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove duplication in `repositories.py` and `services.py` by replacing 5 `_detach_*` boilerplate helpers with a single generic one, merging one duplicate method, and deleting `LocationService` (pure pass-throughs).

**Architecture:** Three independent changes in bottom-up order: (1) `repositories.py` detach helpers → single `_detach()` using `make_transient`; (2) `services.py` duplicate display-name method removed; (3) `LocationService` deleted, two logic methods moved to `InventoryService`, all UI callers updated to use `LocationRepository` directly. No method signatures change on any public class.

**Tech Stack:** Python 3.14, SQLAlchemy (make_transient), pytest.

---

### Task 1: Replace `_detach_*` helpers with a single `_detach`

**Files:**
- Modify: `src/core/repositories.py`

This task only touches `repositories.py`. The five type-specific helpers at the bottom of the file (lines 1713–1790) are replaced by one generic function. All ~40 call sites in the same file are updated.

**Step 1: Add the generic `_detach` helper and the `make_transient` import**

At the top of `src/core/repositories.py`, the existing imports end with:

```python
from sqlalchemy import delete as sql_delete, func, or_
```

Add `make_transient` to it:

```python
from sqlalchemy import delete as sql_delete, func, or_
from sqlalchemy.orm import make_transient
```

**Step 2: Replace the five `_detach_*` functions at the bottom of the file**

The current block (lines 1713–1790) reads:

```python
# Helper functions to detach objects from session
def _detach_location(loc: Location) -> Location:
    ...

def _detach_item(item: Item) -> Item:
    ...

def _detach_transaction(trans: Transaction) -> Transaction:
    ...

def _detach_search_history(history: SearchHistory) -> SearchHistory:
    ...

def _detach_item_type(item_type: ItemType) -> ItemType:
    ...
```

Replace the entire block with:

```python
# ---------------------------------------------------------------------------
# Session-detachment helper
# ---------------------------------------------------------------------------

def _detach(obj):
    """Detach *obj* from its session so callers can use it after session.close().

    All already-loaded column values remain accessible.
    Returns None unchanged.
    """
    if obj is None:
        return None
    make_transient(obj)
    return obj
```

**Step 3: Replace every call site in the file**

Run a bulk find-and-replace for each old name → `_detach`. The mapping is:

| Old call | New call |
|---|---|
| `_detach_location(x)` | `_detach(x)` |
| `_detach_item(x)` | `_detach(x)` |
| `_detach_item_type(x)` | `_detach(x)` |
| `_detach_transaction(x)` | `_detach(x)` |
| `_detach_search_history(x)` | `_detach(x)` |

Example before/after (same pattern everywhere):

```python
# Before
return _detach_location(loc)

# After
return _detach(loc)
```

```python
# Before
return [_detach_item(item) for item in items]

# After
return [_detach(item) for item in items]
```

```python
# Before
return {t.id: _detach_item_type(t) for t in types}

# After
return {t.id: _detach(t) for t in types}
```

**Step 4: Run the full test suite**

```bash
.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: **all tests PASS**.

**Step 5: Commit**

```bash
git add src/core/repositories.py
git commit -m "refactor: replace _detach_* helpers with single generic _detach"
```

---

### Task 2: Remove duplicate `get_item_type_names_for_export`

**Files:**
- Modify: `src/core/services.py`
- Modify: `src/ui/main_window.py`

`get_item_type_display_names` and `get_item_type_names_for_export` have identical bodies. Remove `get_item_type_names_for_export` and update its one caller.

**Step 1: Delete `get_item_type_names_for_export` from `services.py`**

In `src/core/services.py`, find and delete the entire method (approximately lines 502–513):

```python
@staticmethod
def get_item_type_names_for_export() -> dict:
    """Return {item_type_id: "Name — SubType"} for use in Excel export.

    Uses an em-dash separator (same as get_item_type_display_names) so that
    ExportService can safely split on " — " without colliding with user-entered
    type names that may contain hyphens.
    """
    types = ItemTypeRepository.get_all()
    return {
        t.id: f"{t.name} \u2014 {t.sub_type}" if t.sub_type else t.name for t in types
    }
```

**Step 2: Update the call site in `main_window.py`**

In `src/ui/main_window.py` line 169, change:

```python
type_map = InventoryService.get_item_type_names_for_export()
```

to:

```python
type_map = InventoryService.get_item_type_display_names()
```

**Step 3: Run the full test suite**

```bash
.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: **all tests PASS**.

**Step 4: Commit**

```bash
git add src/core/services.py src/ui/main_window.py
git commit -m "refactor: remove duplicate get_item_type_names_for_export"
```

---

### Task 3: Delete `LocationService` — move logic methods to `InventoryService`

**Files:**
- Modify: `src/core/services.py`
- Modify: `src/ui/main_window.py`
- Modify: `src/ui/dialogs/add_item_dialog.py`
- Modify: `src/ui/dialogs/add_serial_number_dialog.py`
- Modify: `src/ui/dialogs/all_transactions_dialog.py`
- Modify: `src/ui/dialogs/edit_item_dialog.py`
- Modify: `src/ui/dialogs/first_location_dialog.py`
- Modify: `src/ui/dialogs/location_management_dialog.py`
- Modify: `src/ui/dialogs/transactions_dialog.py`
- Modify: `src/ui/dialogs/transfer_dialog.py`
- Modify: `src/ui/widgets/location_selector.py`

This task has no logic changes — only call site migrations. The two methods with real business logic (`move_all_items_and_delete`, `get_locations_for_type`) move to `InventoryService`. All 9 pure pass-through methods are replaced by direct `LocationRepository` calls.

**Step 1: Move `move_all_items_and_delete` and `get_locations_for_type` to `InventoryService`**

In `src/core/services.py`, cut the bodies of both methods from `LocationService` and add them at the end of `InventoryService` (before the last method or right before the module-level `_transaction_to_dict` function).

The method bodies are unchanged — they already call `LocationRepository` and `ItemRepository` directly:

```python
# Add to InventoryService:

@staticmethod
def move_all_items_and_delete(from_location_id: int, to_location_id: int) -> bool:
    """Move all items from one location to another, then delete the source location.

    For each item at from_location_id:
      - Non-serialized: calls ItemRepository.transfer_item (handles merge logic).
      - Serialized: calls ItemRepository.transfer_serialized_items.
    Both create TRANSFER transactions for the audit trail.
    After all items are moved, deletes the source location.

    Args:
        from_location_id: Location to empty and delete.
        to_location_id: Destination location.

    Returns:
        True on success.

    Raises:
        ValueError: If either location doesn't exist.
    """
    from_loc = LocationRepository.get_by_id(from_location_id)
    if not from_loc:
        raise ValueError(f"Source location id={from_location_id} not found")
    to_loc = LocationRepository.get_by_id(to_location_id)
    if not to_loc:
        raise ValueError(f"Destination location id={to_location_id} not found")

    notes = tr("transaction.notes.location_deleted_move").format(
        from_loc=from_loc.name
    )

    items = ItemRepository.get_items_at_location(from_location_id)
    for item in items:
        if item.serial_number:
            ItemRepository.transfer_serialized_items(
                serial_numbers=[item.serial_number],
                from_location_id=from_location_id,
                to_location_id=to_location_id,
                notes=notes,
            )
        else:
            ItemRepository.transfer_item(
                item_id=item.id,
                quantity=item.quantity,
                from_location_id=from_location_id,
                to_location_id=to_location_id,
                notes=notes,
            )

    LocationRepository.delete(from_location_id)
    logger.info(
        f"Service: Moved all items from location '{from_loc.name}' to "
        f"'{to_loc.name}' and deleted source location"
    )
    return True

@staticmethod
def get_locations_for_type(item_type_id: int) -> List[Location]:
    """Return the distinct locations that have at least one item of this type.

    Used by TransferDialog to populate the source-location combo when the
    user is in "All Locations" view with a multi-location item.
    """
    items = ItemRepository.get_by_type(item_type_id)
    seen_ids: set = set()
    locs: List[Location] = []
    all_locs = {loc.id: loc for loc in LocationRepository.get_all()}
    for item in items:
        if item.location_id and item.location_id not in seen_ids:
            seen_ids.add(item.location_id)
            if item.location_id in all_locs:
                locs.append(all_locs[item.location_id])
    return locs
```

**Step 2: Delete the entire `LocationService` class from `services.py`**

Delete the entire class body (lines 19–151 approximately — from `class LocationService:` through the end of `get_locations_for_type`).

**Step 3: Update imports in `services.py`**

`services.py` currently imports `Location` from `core.models` for the `LocationService` type hints. `InventoryService` also uses `Location` in the two moved methods. Verify `Location` is still in the import at the top:

```python
from core.models import Location
```

It should already be there — `InventoryService` uses `Location` in its return types. No change needed if it's present.

**Step 4: Update all UI file imports**

For each file below, replace `LocationService` with `LocationRepository` in the import line, and replace every `LocationService.XYZ(...)` call with `LocationRepository.XYZ(...)` using the mapping table below.

**Mapping table** (old → new):

| `LocationService` method | `LocationRepository` method |
|---|---|
| `create_location(name)` | `create(name)` |
| `get_location_by_id(id)` | `get_by_id(id)` |
| `get_location_by_name(name)` | `get_by_name(name)` |
| `get_all_locations()` | `get_all()` |
| `get_location_count()` | `get_count()` |
| `get_item_count(loc_id)` | `get_item_count(loc_id)` |
| `get_all_with_item_counts()` | `get_all_with_item_counts()` |
| `rename_location(id, name)` | `rename(id, name)` |
| `delete_location(id)` | `delete(id)` |
| `get_unassigned_item_count()` | `get_unassigned_item_count()` |
| `assign_all_unassigned_items(id)` | `assign_all_unassigned(id)` |
| `move_all_items_and_delete(f, t)` | `InventoryService.move_all_items_and_delete(f, t)` |
| `get_locations_for_type(id)` | `InventoryService.get_locations_for_type(id)` |

**`src/ui/main_window.py`**

Change import line 22:
```python
# Before
from core.services import InventoryService, LocationService, SearchService, TransactionService

# After
from core.services import InventoryService, SearchService, TransactionService
from core.repositories import LocationRepository
```

Change the inline import at line 109:
```python
# Before
from core.services import InventoryService, LocationService, TransactionService

# After
from core.services import InventoryService, TransactionService
from core.repositories import LocationRepository
```

Then replace all `LocationService.` calls in this file:
- `LocationService.get_location_by_id(...)` → `LocationRepository.get_by_id(...)`
- `LocationService.get_all_locations()` → `LocationRepository.get_all()`
- `LocationService.get_location_count()` → `LocationRepository.get_count()`
- `LocationService.get_unassigned_item_count()` → `LocationRepository.get_unassigned_item_count()`
- `LocationService.assign_all_unassigned_items(...)` → `LocationRepository.assign_all_unassigned(...)`

**`src/ui/dialogs/add_item_dialog.py`**

```python
# Before
from core.services import InventoryService, LocationService

# After
from core.services import InventoryService
from core.repositories import LocationRepository
```

Replace: `LocationService.get_all_locations()` → `LocationRepository.get_all()`

**`src/ui/dialogs/add_serial_number_dialog.py`**

```python
# Before
from core.services import LocationService

# After
from core.repositories import LocationRepository
```

Replace: `LocationService.get_all_locations()` → `LocationRepository.get_all()`

**`src/ui/dialogs/all_transactions_dialog.py`**

```python
# Before
from core.services import InventoryService, LocationService, TransactionService

# After
from core.services import InventoryService, TransactionService
from core.repositories import LocationRepository
```

Replace:
- `LocationService.get_all_locations()` → `LocationRepository.get_all()`

**`src/ui/dialogs/edit_item_dialog.py`**

```python
# Before
from core.services import InventoryService, LocationService

# After
from core.services import InventoryService
from core.repositories import LocationRepository
```

Replace: `LocationService.get_all_locations()` → `LocationRepository.get_all()`

**`src/ui/dialogs/first_location_dialog.py`**

```python
# Before
from core.services import LocationService

# After
from core.repositories import LocationRepository
```

Replace:
- `LocationService.get_location_by_name(name)` → `LocationRepository.get_by_name(name)`
- `LocationService.create_location(name=name)` → `LocationRepository.create(name)`

**`src/ui/dialogs/location_management_dialog.py`**

```python
# Before
from core.services import LocationService

# After
from core.services import InventoryService
from core.repositories import LocationRepository
```

Replace:
- `LocationService.get_all_with_item_counts()` → `LocationRepository.get_all_with_item_counts()`
- `LocationService.get_location_by_name(name)` → `LocationRepository.get_by_name(name)`
- `LocationService.create_location(name)` → `LocationRepository.create(name)`
- `LocationService.rename_location(loc_id, new_name)` → `LocationRepository.rename(loc_id, new_name)`
- `LocationService.get_all_locations()` → `LocationRepository.get_all()`
- `LocationService.get_item_count(loc_id)` → `LocationRepository.get_item_count(loc_id)`
- `LocationService.delete_location(loc_id)` → `LocationRepository.delete(loc_id)`
- `LocationService.move_all_items_and_delete(loc_id, dest_id)` → `InventoryService.move_all_items_and_delete(loc_id, dest_id)`

**`src/ui/dialogs/transactions_dialog.py`**

```python
# Before
from core.services import LocationService

# After
from core.repositories import LocationRepository
```

Replace: `LocationService.get_all_locations()` → `LocationRepository.get_all()`

**`src/ui/dialogs/transfer_dialog.py`**

```python
# Before
from core.services import InventoryService, LocationService

# After
from core.services import InventoryService
from core.repositories import LocationRepository
```

Replace:
- `LocationService.get_all_locations()` → `LocationRepository.get_all()`
- `LocationService.get_locations_for_type(...)` → `InventoryService.get_locations_for_type(...)`

**`src/ui/widgets/location_selector.py`**

```python
# Before
from core.services import LocationService

# After
from core.repositories import LocationRepository
```

Replace: `LocationService.get_all_locations()` → `LocationRepository.get_all()`

**Step 5: Run the full test suite**

```bash
.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: **all tests PASS**.

**Step 6: Commit**

```bash
git add src/core/services.py \
        src/ui/main_window.py \
        src/ui/dialogs/add_item_dialog.py \
        src/ui/dialogs/add_serial_number_dialog.py \
        src/ui/dialogs/all_transactions_dialog.py \
        src/ui/dialogs/edit_item_dialog.py \
        src/ui/dialogs/first_location_dialog.py \
        src/ui/dialogs/location_management_dialog.py \
        src/ui/dialogs/transactions_dialog.py \
        src/ui/dialogs/transfer_dialog.py \
        src/ui/widgets/location_selector.py
git commit -m "refactor: delete LocationService, callers use LocationRepository directly"
```
