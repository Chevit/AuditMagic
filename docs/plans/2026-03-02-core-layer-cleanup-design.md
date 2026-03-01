# Design: Core Layer Cleanup (Approach B — Moderate)

**Date:** 2026-03-02
**Status:** Approved

## Problem

`repositories.py` and `services.py` have three categories of duplication/inconsistency:

1. **`_detach_*` boilerplate** — 5 module-level functions (~80 lines) that each manually recreate an ORM object by copying every field. Same pattern repeated for `Location`, `Item`, `ItemType`, `Transaction`, `SearchHistory`.

2. **Duplicate display-name method** — `InventoryService.get_item_type_display_names` and `InventoryService.get_item_type_names_for_export` have identical bodies: `{t.id: f"{t.name} — {t.sub_type}" if t.sub_type else t.name for t in ItemTypeRepository.get_all()}`.

3. **`LocationService` thin wrappers** — 9 of 11 methods are pure 1-line delegations to `LocationRepository`. The service adds no logic for these. Two methods (`move_all_items_and_delete`, `get_locations_for_type`) do have real multi-repo orchestration logic.

## Fix

### 1. Replace `_detach_*` with a single generic `_detach` helper

**Before:** 5 functions × ~15 lines = ~80 lines of manual field copying.

**After:** One generic helper using SQLAlchemy's `make_transient`:

```python
from sqlalchemy.orm import make_transient

def _detach(obj):
    """Detach obj from its session so it's safe to use after session.close()."""
    if obj is None:
        return None
    make_transient(obj)
    return obj
```

`make_transient` strips all session-tracking state from the object in-place; all already-loaded column values remain accessible. Since every query in this codebase loads columns eagerly (no lazy relationships are accessed post-session), this is a safe drop-in replacement.

All call sites change from `return _detach_location(loc)` → `return _detach(loc)`, etc.

### 2. Merge duplicate display-name methods

Delete `get_item_type_names_for_export`. It is identical to `get_item_type_display_names`.

Update the single caller (`src/ui/main_window.py:169`) to call `get_item_type_display_names`.

### 3. Delete `LocationService`, relocate logic methods

Delete `LocationService` from `services.py`.

- The 9 pure pass-throughs are deleted entirely; UI callers switch to `LocationRepository` directly.
- `move_all_items_and_delete` moves to `InventoryService` (it already orchestrates `ItemRepository`, `LocationRepository`, and transactions — same pattern as other `InventoryService` methods).
- `get_locations_for_type` moves to `InventoryService` for the same reason.

UI files that currently import `LocationService` will import `LocationRepository` instead (for the simple queries) and `InventoryService` (for the two relocated logic methods).

## Files

- Modify: `src/core/repositories.py` — remove 5 `_detach_*`, add `_detach`
- Modify: `src/core/services.py` — delete `LocationService`, delete `get_item_type_names_for_export`, add 2 methods to `InventoryService`
- Modify: `src/ui/main_window.py` — update 1 call site + update location imports
- Modify: `src/ui/dialogs/add_item_dialog.py` — update location imports
- Modify: `src/ui/dialogs/add_serial_number_dialog.py` — update location imports
- Modify: `src/ui/dialogs/all_transactions_dialog.py` — update location imports + 1 call site
- Modify: `src/ui/dialogs/edit_item_dialog.py` — update location imports
- Modify: `src/ui/dialogs/first_location_dialog.py` — update location imports
- Modify: `src/ui/dialogs/location_management_dialog.py` — update location imports
- Modify: `src/ui/dialogs/transactions_dialog.py` — update location imports
- Modify: `src/ui/dialogs/transfer_dialog.py` — update location imports
- Modify: `src/ui/widgets/location_selector.py` — update location imports
- Test: `tests/` — update any imports that reference `LocationService`

## Constraints

- No changes to any method signatures on `InventoryService` or any repository.
- No changes to the database layer.
- All existing tests must pass after the refactor.
