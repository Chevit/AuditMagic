# Design: Translate Transaction Types in Excel Export

**Date:** 2026-03-02
**Status:** Approved

## Problem

Transaction types written to the Excel "Транзакції" sheet appear in English (`ADD`, `REMOVE`, `EDIT`, `TRANSFER`). Ukrainian translations already exist in `translations.py` but are not used by the export service.

## Root Cause

[`src/core/export_service.py:120`](../../src/core/export_service.py#L120) writes the raw DB value directly:

```python
type_name = trans.get("type", "").upper()  # → "ADD", "TRANSFER", etc.
ws.cell(row=row, column=2, value=type_name)
```

## Fix

Add a `TRANSACTION_TYPE_LABELS` dict to `ExportService` and apply it when writing column 2.

```python
TRANSACTION_TYPE_LABELS = {
    "ADD":      "Додавання",
    "REMOVE":   "Видалення",
    "EDIT":     "Редагування",
    "TRANSFER": "Переміщення",
}
```

Fallback: if an unknown type appears, write the raw value rather than leaving it blank.

## Files

- Modify: `src/core/export_service.py`
- Test: `tests/test_export_service.py` (update the existing transaction type assertion)
