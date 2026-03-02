# Design: Core + DTO Test Coverage (Approach A — Full)

**Date:** 2026-03-02
**Status:** Approved

## Problem

The test suite has three issues:

1. **Gaps** — `src/core/` (repositories, services) and `src/ui/models/` (DTOs) are nearly untested.
2. **Broken style** — `test_serialized_feature.py` uses a script-style `check()` runner with `sys.exit(1)`, which is incompatible with pytest. Module-level side-effects fire at import time.
3. **Boilerplate** — each test file repeats its own DB init; no shared fixture.

## Fix

### 1. Test infrastructure — `conftest.py`

Add a shared `fresh_db` autouse fixture that calls `init_database(":memory:")` before each test. Every test automatically gets an isolated in-memory DB. Removes all per-file init boilerplate.

### 2. Fix existing tests

- **`test_serialized_feature.py`** — full rewrite as proper pytest functions. Each `check()` call becomes a `def test_*` function. Module-level `section()` / `check()` / `sys.exit()` removed. Same logical cases preserved: serialized flag creation, `is_serialized` conflict raises `ValueError`, `get_item_type_by_name_subtype` (found / not found), translation keys present. UI widget tests (require `QApplication`) dropped — belong in a separate UI test pass.
- **`test_export_transactions.py`** — remove module-level `init_database(":memory:")` call (line 11); rely on shared `fresh_db` fixture.
- **`test_export_service.py`** — no changes (no DB).

### 3. `tests/test_repositories.py` (new)

Covers all four repositories directly. Service layer not used — each repository is tested independently.

| Repository | Cases |
|---|---|
| `LocationRepository` | create, get_by_id, get_by_name, get_all (ordered), update (rename), delete, get_count, get_unassigned_item_count, assign_all_unassigned |
| `ItemTypeRepository` | get_or_create (new), get_or_create (idempotent same flag), get_or_create (different flag raises `ValueError`), get_by_id, get_by_ids, get_all, update (rename/details), update raises when items exist + is_serialized changes, delete (cascades), get_by_name_and_subtype (found/not found), get_autocomplete_names, get_all_with_items, get_serialized_with_items |
| `ItemRepository` | create (non-serialized), create_serialized (first item qty_before=0), create_serialized (second item qty_before=1), duplicate serial raises, add_quantity (ADD transaction created), remove_quantity (normal), remove_quantity below zero raises, delete, delete_by_serial_numbers (REMOVE transactions preserved), transfer_item (TRANSFER created), transfer_serialized_items, find_non_serialized_at_location, get_items_at_location, search (by name / by serial) |
| `TransactionRepository` | get_by_type_and_date_range (in-range / out-of-range), get_recent (limit respected), get_by_location_and_date_range, get_all_by_date_range, get_for_export (no filter / by location / by type_ids) |

### 4. `tests/test_services.py` (new)

Covers the three service classes at their own boundary — orchestration logic and return types, not re-testing repository internals.

| Service | Cases |
|---|---|
| `InventoryService` | create_item (returns InventoryItem), create_serialized_item (returns InventoryItem; duplicate serial raises), create_or_merge_item (new → was_merged=False; same type+location → was_merged=True; serialized always new), get_item (found/None), get_all_items, get_all_items_grouped (grouped by type, location filter), get_serialized_items_grouped (serialized types only), add_quantity, remove_quantity, transfer_item (returns True), transfer_serialized_items (returns count), get_type_items_at_location (qty/serials/ids tuple), get_item_type_display_names (with/without sub_type), edit_item (type rename + EDIT transaction), delete_item / delete_item_type (True/False), delete_items_by_serial_numbers (count), move_all_items_and_delete (moves non-serialized + serialized, deletes source, raises on bad IDs), get_locations_for_type |
| `SearchService` | search (match / empty / by field), get_autocomplete_suggestions (empty prefix → []), get_search_history, clear_search_history |
| `TransactionService` | get_transactions_by_type_and_date_range (in-range only), get_recent_transactions (limit), get_transactions_by_location_and_date_range, get_all_transactions_by_date_range, `_transaction_to_dict` transfer_side ("source" / "destination" / absent for non-transfer) |

### 5. `tests/test_dto_models.py` (new)

Pure unit tests — no DB, no fixtures. ORM instances constructed in-memory (not persisted).

| Class | Cases |
|---|---|
| `InventoryItem.from_db_models` | All fields mapped (id, item_type_id, item_type_name, sub_type, is_serialized, quantity, serial_number, location_id, location_name, condition, details, created_at, updated_at), legacy `.location` property returns `location_name`, `is_serialized` reflects the type |
| `GroupedInventoryItem.from_item_type_and_items` | Non-serialized: `total_quantity = item.quantity`, `serial_numbers = []`, `item_count = 1`. Serialized multiple items: `total_quantity = len(items)`, `serial_numbers` populated, `item_ids` list. Legacy compat: `.id` = first item_id, `.quantity` = total_quantity, `.serial_number` = first serial or None. Location name resolved from `location_map`. |

## Files Changed

- Modify: `tests/conftest.py`
- Modify: `tests/test_serialized_feature.py`
- Modify: `tests/test_export_transactions.py`
- Add: `tests/test_repositories.py`
- Add: `tests/test_services.py`
- Add: `tests/test_dto_models.py`

## Constraints

- No changes to production code.
- All tests use in-memory SQLite via `init_database(":memory:")`.
- UI widget tests excluded (require `QApplication`).
- Repository tests do not use the service layer; service tests do not re-test repository internals.
