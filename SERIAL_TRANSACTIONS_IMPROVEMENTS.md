# Serial Number Transactions — Remaining Improvements

## Current State

The core serial number flow is implemented and working:
- `AddSerialNumberDialog` and `RemoveSerialNumberDialog` exist and function correctly
- Context menu shows dynamic labels ("Add Serial Number" / "Remove Serial Number") for serialized items
- `ItemRepository.delete_by_serial_numbers()` already creates REMOVE transactions with notes
- `ItemRepository.create()` already creates an initial ADD transaction for new items
- `InventoryService.delete_items_by_serial_numbers()` accepts and forwards a `notes` parameter

Three issues remain, all related to transaction completeness and visibility.

---

## Issue 1: Edit Dialog Doesn't Pass Notes When Deleting Serials

**File:** `ui_entities/main_window.py`, line 250

**Problem:** When a user deletes serial numbers through the Edit dialog, the `edit_notes` variable (captured from dialog on line 195) is available but not passed to the service:

```python
# Current (line 250):
deleted_count = InventoryService.delete_items_by_serial_numbers(deleted_serials)

# Should be:
deleted_count = InventoryService.delete_items_by_serial_numbers(deleted_serials, edit_notes)
```

**Impact:** REMOVE transactions created during edit have empty notes — the audit trail loses the reason for deletion even though the user typed one into the "Edit reason" field.

**Fix:** Pass `edit_notes` as the second argument on line 250. One-line change, no new logic needed.

---

## Issue 2: Transactions Dialog Only Shows First Item's History

**File:** `ui_entities/main_window.py`, lines 424–436

**Problem:** When viewing transactions for a grouped serialized item, only transactions for `item_ids[0]` are shown:

```python
item_id = item.item_ids[0] if is_grouped else item.id
dialog = TransactionsDialog(item_id=item_id, ...)
```

For a serialized group with 5 serial numbers, the user only sees the transaction history of the first serial. Transactions for the other 4 serials (including their ADD on creation and any REMOVE on deletion) are invisible.

**Fix — two parts:**

### 2a. Support multiple item IDs in TransactionsDialog

Update `TransactionsDialog.__init__()` to accept an optional `item_ids: list[int]` parameter alongside the existing `item_id: int`. When `item_ids` is provided, fetch transactions for all of them.

**File:** `ui_entities/transactions_dialog.py`

- Add `item_ids` parameter to constructor
- Store as `self._item_ids`
- When loading transactions, if `_item_ids` is set, call the service for each ID and merge results (sorted by date)
- Add a "Serial Number" column to the table so the user can distinguish which serial each transaction belongs to

### 2b. Support multiple item IDs in the service/repository layer

**File:** `services.py` — `TransactionService.get_transactions_by_date_range()`

- Add an `item_ids: list[int] = None` parameter
- When provided, query transactions for all given IDs in a single query (`Transaction.item_id.in_(item_ids)`)

**File:** `repositories.py` — `TransactionRepository.get_by_date_range()`

- Same change: accept `item_ids` list, use `IN` clause

### 2c. Update main_window to pass all item IDs

**File:** `ui_entities/main_window.py`, `_on_show_transactions()`

```python
# Current:
item_id = item.item_ids[0] if is_grouped else item.id

# Updated:
if is_grouped:
    dialog = TransactionsDialog(
        item_ids=item.item_ids,
        item_name=item_name,
        parent=self
    )
else:
    dialog = TransactionsDialog(
        item_id=item.id,
        item_name=item_name,
        parent=self
    )
```

---

## Issue 3: Deleted Serial Transactions Become Orphaned

**Problem:** When a serialized item is deleted, its `Item` row is removed from the database. The REMOVE transaction references the now-deleted `item_id`. This means:

- The transaction record still exists but the associated Item is gone
- If `TransactionsDialog` queries by `item_id`, these "ghost" transactions are found but have no serial number context
- The transaction table cannot display which serial number the transaction belonged to

**Fix — store serial number directly on the Transaction:**

### 3a. Add `serial_number` column to Transaction model

**File:** `models.py`

Add a nullable `serial_number` column to the `Transaction` table:

```python
serial_number = Column(String(255), nullable=True)
```

### 3b. Create Alembic migration

Generate and apply a migration to add the column:

```bash
alembic revision --autogenerate -m "add serial_number to transactions"
alembic upgrade head
```

Use batch mode for SQLite compatibility (as per project conventions).

### 3c. Populate serial_number when creating transactions

**File:** `repositories.py`

Update these methods to store the serial number on the transaction:

- `ItemRepository.create()` — set `serial_number` from the item's serial when creating the initial ADD transaction
- `ItemRepository.delete_by_serial_numbers()` — set `serial_number` from each item's serial when creating REMOVE transactions
- `ItemRepository.add_quantity()` — leave as `None` (non-serialized items)
- `ItemRepository.remove_quantity()` — leave as `None` (non-serialized items)

### 3d. Display serial number in TransactionsDialog

**File:** `ui_entities/transactions_dialog.py`

Add a "Serial Number" column to the transaction table. Show the value from `transaction.serial_number` when present, or "—" for non-serialized item transactions.

---

## File Change Summary

| File | Change | Issue |
|------|--------|-------|
| `ui_entities/main_window.py` (line 250) | Pass `edit_notes` to `delete_items_by_serial_numbers()` | #1 |
| `ui_entities/main_window.py` (`_on_show_transactions`) | Pass all `item_ids` for grouped items | #2 |
| `ui_entities/transactions_dialog.py` | Accept `item_ids` list, add Serial Number column | #2, #3 |
| `services.py` (`TransactionService`) | Support `item_ids` list in query methods | #2 |
| `repositories.py` (`TransactionRepository`) | Support `item_ids` list in `get_by_date_range()` | #2 |
| `models.py` | Add `serial_number` column to `Transaction` | #3 |
| `alembic/versions/` | New migration for `serial_number` column | #3 |
| `repositories.py` (`ItemRepository`) | Store serial number on ADD/REMOVE transactions | #3 |

## Implementation Order

1. **Issue 1** — one-line fix, no dependencies, immediate impact on audit trail
2. **Issue 3a–3c** — model + migration + repository changes (do before Issue 2 so the serial column exists)
3. **Issue 2** — service + dialog + main_window changes (depends on Issue 3 for serial display)
4. **Issue 3d** — display serial in transactions table (depends on Issues 2 and 3)
