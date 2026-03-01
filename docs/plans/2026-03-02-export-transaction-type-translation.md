# Export Transaction Type Translation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Translate transaction type values (ADD, REMOVE, EDIT, TRANSFER) to Ukrainian in the Excel export sheet.

**Architecture:** Add a `TRANSACTION_TYPE_LABELS` class-level dict to `ExportService`. Apply it in `_write_transactions_sheet` when writing column 2. The existing test that asserts `"ADD"` must be updated to assert `"Додавання"` (TDD: update test first, then implement).

**Tech Stack:** Python, openpyxl, pytest.

---

### Task 1: Update the failing test and add a TRANSFER translation test

**Files:**
- Modify: `tests/test_export_service.py:128`

**Background:** The existing test at line 128 asserts the raw English value `"ADD"`. After the fix it should assert the Ukrainian value `"Додавання"`. The test at line 137 uses `tx_type="transfer"` but never asserts column 2 — add that assertion too.

**Step 1: Update the existing assertion in `test_transactions_sheet_data_row`**

In `tests/test_export_service.py`, change line 128 from:
```python
assert ws.cell(2, 2).value == "ADD"
```
to:
```python
assert ws.cell(2, 2).value == "Додавання"
```

**Step 2: Add a new test for TRANSFER translation**

Add this test after `test_transactions_location_names_resolved` (end of file):

```python
def test_transactions_type_translated_to_ukrainian():
    """Transaction types must be translated to Ukrainian in the export."""
    cases = [
        ("add",      "Додавання"),
        ("remove",   "Видалення"),
        ("edit",     "Редагування"),
        ("transfer", "Переміщення"),
    ]
    for tx_type, expected_label in cases:
        wb = ExportService.build_workbook(
            [_make_item()], "Warehouse",
            transactions=[_make_transaction(tx_type=tx_type)],
        )
        ws = wb["Транзакції"]
        assert ws.cell(2, 2).value == expected_label, (
            f"Expected '{expected_label}' for type '{tx_type}', "
            f"got '{ws.cell(2, 2).value}'"
        )
```

**Step 3: Run tests to verify they fail**

```bash
cd c:\Users\chevi\PycharmProjects\AuditMagic
.venv\Scripts\python.exe -m pytest tests/test_export_service.py::test_transactions_sheet_data_row tests/test_export_service.py::test_transactions_type_translated_to_ukrainian -v
```

Expected: **2 FAILED** — `AssertionError: assert 'ADD' == 'Додавання'`

---

### Task 2: Implement the translation in ExportService

**Files:**
- Modify: `src/core/export_service.py:16-24` (class body, before `build_workbook`)

**Step 1: Add `TRANSACTION_TYPE_LABELS` dict to the `ExportService` class**

In `src/core/export_service.py`, add this dict directly after the `TRANSACTION_HEADERS` list (after line 24):

```python
TRANSACTION_TYPE_LABELS: Dict[str, str] = {
    "ADD":      "Додавання",
    "REMOVE":   "Видалення",
    "EDIT":     "Редагування",
    "TRANSFER": "Переміщення",
}
```

**Step 2: Apply the translation in `_write_transactions_sheet`**

In `_write_transactions_sheet`, line 120 currently reads:
```python
type_name = trans.get("type", "").upper()
```

Change it to:
```python
raw_type = trans.get("type", "").upper()
type_name = ExportService.TRANSACTION_TYPE_LABELS.get(raw_type, raw_type)
```

The fallback `raw_type` ensures any unknown future type values remain visible rather than going blank.

**Step 3: Run all export tests**

```bash
.venv\Scripts\python.exe -m pytest tests/test_export_service.py -v
```

Expected: **all tests PASS** (the previously failing `test_transactions_sheet_data_row` and `test_transactions_type_translated_to_ukrainian` should now pass).

**Step 4: Commit**

```bash
git add src/core/export_service.py tests/test_export_service.py
git commit -m "fix: translate transaction types to Ukrainian in Excel export"
```
