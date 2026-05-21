# Export Location Filter Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `TransactionRepository.get_for_export` filter by `Transaction.location_id` only, matching the logic used by AllTransactionsDialog.

**Architecture:** Single method change in the repository layer. The OR filter across `location_id / from_location_id / to_location_id` is replaced with a simple equality check on `location_id`. TRANSFER operations already create two rows each carrying their own `location_id`, so the simple filter is sufficient and avoids returning duplicate rows.

**Tech Stack:** Python 3.14, SQLAlchemy, pytest, in-memory SQLite (`AUDITMAGIC_DB=:memory:`)

---

### Task 1: Add a failing test for the TRANSFER duplicate case

**Files:**
- Modify: `tests/test_export_transactions.py`

- [ ] **Step 1: Add the test at the bottom of `tests/test_export_transactions.py`**

```python
def test_get_for_export_transfer_not_duplicated():
    """TRANSFER creates two rows; only the row whose location_id matches should be returned."""
    loc_a = _make_location("TransferA")
    loc_b = _make_location("TransferB")
    # Create a non-serialized item at loc_a
    item = InventoryService.create_item(
        item_type_name="Keyboard",
        item_sub_type="",
        quantity=4,
        location_id=loc_a.id,
        transaction_notes="",
    )
    # Transfer 2 units from loc_a to loc_b (creates two TRANSFER transaction rows)
    InventoryService.transfer_item(
        item_id=item.id,
        quantity=2,
        from_location_id=loc_a.id,
        to_location_id=loc_b.id,
        notes="test transfer",
    )
    result_a = TransactionService.get_for_export(location_id=loc_a.id)
    result_b = TransactionService.get_for_export(location_id=loc_b.id)
    # Every row returned for loc_a must have location_id == loc_a.id
    assert all(t["location_id"] == loc_a.id for t in result_a), (
        "get_for_export returned a row whose location_id != loc_a.id"
    )
    # Every row returned for loc_b must have location_id == loc_b.id
    assert all(t["location_id"] == loc_b.id for t in result_b), (
        "get_for_export returned a row whose location_id != loc_b.id"
    )
```

- [ ] **Step 2: Run the new test to confirm it fails**

```bash
pytest tests/test_export_transactions.py::test_get_for_export_transfer_not_duplicated -v
```

Expected output contains `FAILED` — the OR filter returns destination-side TRANSFER rows where `location_id != loc_a.id`.

---

### Task 2: Fix the OR filter in `TransactionRepository.get_for_export`

**Files:**
- Modify: `src/core/repositories.py:1597-1632`

- [ ] **Step 3: Replace the OR filter with a simple equality check**

In `src/core/repositories.py`, find the `get_for_export` method (~line 1620). Replace:

```python
        if location_id is not None:
            q = q.filter(
                or_(
                    Transaction.location_id == location_id,
                    Transaction.from_location_id == location_id,
                    Transaction.to_location_id == location_id,
                )
            )
```

with:

```python
        if location_id is not None:
            q = q.filter(Transaction.location_id == location_id)
```

- [ ] **Step 4: Update the now-incorrect docstring comment**

In the same method, replace the `Note:` block in the docstring:

```python
        Note:
            TRANSFER operations create two rows (source and destination).  Both rows
            carry the same from_location_id / to_location_id, so when filtering by a
            specific location the OR filter will match both sides.  This is intentional
            and consistent with AllTransactionsDialog — each row represents one side of
            the transfer (outgoing vs incoming) with its own qty_before/after context.
```

with:

```python
        Note:
            TRANSFER operations create two rows (source and destination), each with its
            own location_id.  Filtering by location_id alone is sufficient and matches
            the logic used by AllTransactionsDialog.
```

- [ ] **Step 5: Run the full test suite for export transactions**

```bash
pytest tests/test_export_transactions.py -v
```

Expected: all tests pass, including the new one.

- [ ] **Step 6: Run all tests to check for regressions**

```bash
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add tests/test_export_transactions.py src/core/repositories.py
git commit -m "fix: use location_id equality filter in get_for_export to match AllTransactionsDialog"
```
