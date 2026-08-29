# Export Location Filter Fix

**Date:** 2026-05-21
**Status:** Approved

## Problem

When exporting with "Include transactions" checked and a specific location selected, the export produces more transfer rows than the All Transactions dialog shows for the same location.

Root cause: `TransactionRepository.get_for_export` filters by location using an OR across three columns:

```python
or_(
    Transaction.location_id == location_id,
    Transaction.from_location_id == location_id,
    Transaction.to_location_id == location_id,
)
```

TRANSFER operations create two rows per transfer — one with `location_id = from_location_id` (source side) and one with `location_id = to_location_id` (destination side). The OR filter matches both rows for any transfer involving the location, so both appear in the export. The All Transactions dialog uses `Transaction.location_id == location_id` and shows only the single row that belongs to that location.

## Design

Change the location filter in `TransactionRepository.get_for_export` from the OR expression to:

```python
Transaction.location_id == location_id
```

No other files change. The `item_type_ids` filter path is unaffected.

## Files Changed

- `src/core/repositories.py` — `TransactionRepository.get_for_export`: replace OR filter with `Transaction.location_id == location_id`; correct the inaccurate comment that claimed OR behaviour matched AllTransactionsDialog.

## Out of Scope

- Date range filtering in the export dialog
- Changes to `main_window.py`, `services.py`, `export_service.py`, or `ExportOptionsDialog`
