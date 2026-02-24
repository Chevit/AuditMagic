# Excel Export Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add File → Export to Excel… that writes inventory items (and optionally transactions) for the active location to an `.xlsx` file.

**Architecture:** New `ExportService` (pure data, no UI) builds an `openpyxl.Workbook`; new `ExportOptionsDialog` captures user choices; main window `File` menu triggers the flow. Transactions are loaded via a new `TransactionService.get_for_export` method that has no date-range constraint.

**Tech Stack:** `openpyxl`, PyQt6, existing Repository→Service→UI layers.

---

## Task 1: Add openpyxl dependency

**Files:**
- Modify: `requirements.txt`
- Modify: `AuditMagic.spec`

**Step 1: Add to requirements.txt**

Append after the last line:
```
openpyxl==3.1.5
```

**Step 2: Add hidden import to spec**

In `AuditMagic.spec`, add `'openpyxl'` to `hiddenimports`:
```python
hiddenimports=[
    'sqlalchemy.dialects.sqlite',
    'logging.config',
    'logging.handlers',
    'openpyxl',
],
```

**Step 3: Install**

```bash
pip install openpyxl==3.1.5
```
Expected: `Successfully installed openpyxl-3.1.5`

**Step 4: Verify import**

```bash
python -c "import openpyxl; print(openpyxl.__version__)"
```
Expected: `3.1.5`

**Step 5: Commit**

```bash
git add requirements.txt AuditMagic.spec
git commit -m "feat: add openpyxl dependency for Excel export"
```

---

## Task 2: TransactionRepository.get_for_export + TransactionService.get_for_export

**Files:**
- Modify: `repositories.py` (add method to `TransactionRepository`)
- Modify: `services.py` (add method to `TransactionService`)
- Create: `tests/test_export_transactions.py`

**Step 1: Write the failing test**

Create `tests/test_export_transactions.py`:
```python
"""Tests for TransactionService.get_for_export."""
import os
import sys
import pytest

os.environ.setdefault("AUDITMAGIC_DB", ":memory:")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db import init_database
init_database(":memory:")

from repositories import ItemTypeRepository, ItemRepository, LocationRepository
from services import TransactionService, InventoryService


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    """Each test gets a fresh in-memory database."""
    from db import init_database
    init_database(":memory:")


def _make_location(name="Warehouse"):
    return LocationRepository.create(name)

def _make_type(name="Laptop", serialized=False):
    return ItemTypeRepository.get_or_create(name, "", serialized)

def _add_item(type_id, location_id, qty=5):
    return InventoryService.add_item(
        item_type_name="Laptop", item_sub_type="", quantity=qty,
        location_id=location_id, notes=""
    )


def test_get_for_export_returns_list():
    loc = _make_location()
    _add_item(_make_type().id, loc.id)
    result = TransactionService.get_for_export(location_id=loc.id)
    assert isinstance(result, list)
    assert len(result) >= 1


def test_get_for_export_dict_has_required_keys():
    loc = _make_location()
    _add_item(_make_type().id, loc.id)
    result = TransactionService.get_for_export(location_id=loc.id)
    keys = result[0].keys()
    for k in ("type", "item_type_id", "quantity_before", "quantity_after",
              "notes", "serial_number", "from_location_id", "to_location_id", "created_at"):
        assert k in keys, f"missing key: {k}"


def test_get_for_export_filters_by_location():
    loc_a = _make_location("A")
    loc_b = _make_location("B")
    _add_item(_make_type().id, loc_a.id, qty=3)
    _add_item(_make_type("Monitor").id, loc_b.id, qty=2)
    result_a = TransactionService.get_for_export(location_id=loc_a.id)
    result_b = TransactionService.get_for_export(location_id=loc_b.id)
    # Each should only see their own location's transactions
    assert all(t["location_id"] == loc_a.id for t in result_a)
    assert all(t["location_id"] == loc_b.id for t in result_b)


def test_get_for_export_all_locations_when_none():
    loc_a = _make_location("A")
    loc_b = _make_location("B")
    _add_item(_make_type().id, loc_a.id)
    _add_item(_make_type("Monitor").id, loc_b.id)
    result = TransactionService.get_for_export(location_id=None)
    assert len(result) >= 2


def test_get_for_export_filtered_by_type_ids():
    loc = _make_location()
    t1 = _make_type("Laptop")
    t2 = _make_type("Mouse")
    _add_item(t1.id, loc.id)
    _add_item(t2.id, loc.id)
    result = TransactionService.get_for_export(location_id=None, item_type_ids=[t1.id])
    assert all(t["item_type_id"] == t1.id for t in result)
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_export_transactions.py -v
```
Expected: `ERROR` — `get_for_export` does not exist yet.

**Step 3: Add `TransactionRepository.get_for_export` to `repositories.py`**

Find `TransactionRepository` class. Add this static method after `get_all_by_date_range`:

```python
@staticmethod
def get_for_export(
    location_id: Optional[int] = None,
    item_type_ids: Optional[List[int]] = None,
) -> List[Transaction]:
    """Fetch transactions for export with no date-range constraint.

    Args:
        location_id: If given, returns transactions where location_id,
                     from_location_id, or to_location_id matches.
                     If None, returns all transactions.
        item_type_ids: If given, restricts to these item type IDs.

    Returns:
        Transactions ordered by created_at descending.
    """
    with session_scope() as session:
        q = session.query(Transaction)
        if location_id is not None:
            q = q.filter(
                or_(
                    Transaction.location_id == location_id,
                    Transaction.from_location_id == location_id,
                    Transaction.to_location_id == location_id,
                )
            )
        if item_type_ids is not None:
            q = q.filter(Transaction.item_type_id.in_(item_type_ids))
        q = q.order_by(Transaction.created_at.desc())
        return [_detach_transaction(t) for t in q.all()]
```

**Step 4: Add `TransactionService.get_for_export` to `services.py`**

Inside `TransactionService`, add after `get_all_transactions_by_date_range`:

```python
@staticmethod
def get_for_export(
    location_id: Optional[int] = None,
    item_type_ids: Optional[List[int]] = None,
) -> List[dict]:
    """Get transactions for export — no date range constraint.

    Args:
        location_id: Filter by location (OR across all location columns).
                     None returns all locations.
        item_type_ids: If given, restrict to these item type IDs only.

    Returns:
        List of transaction dictionaries.
    """
    transactions = TransactionRepository.get_for_export(
        location_id=location_id,
        item_type_ids=item_type_ids,
    )
    return [_transaction_to_dict(t) for t in transactions]
```

Also add `Optional` and `List` to the import at the top of `services.py` if not already present (check `from typing import`).

**Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/test_export_transactions.py -v
```
Expected: All 5 tests `PASSED`.

**Step 6: Commit**

```bash
git add repositories.py services.py tests/test_export_transactions.py
git commit -m "feat: add TransactionRepository/Service.get_for_export for unbounded export queries"
```

---

## Task 3: ExportService — Items sheet

**Files:**
- Create: `export_service.py`
- Create: `tests/test_export_service.py`

**Step 1: Write failing tests**

Create `tests/test_export_service.py`:
```python
"""Tests for ExportService."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime
import pytest
from ui_entities.inventory_item import InventoryItem, GroupedInventoryItem


def _make_item(name="Laptop", sub="X1", qty=3, sn=None, loc="Warehouse", cond="Good"):
    return InventoryItem(
        id=1, item_type_id=1, item_type_name=name, item_sub_type=sub,
        is_serialized=sn is not None, quantity=qty, serial_number=sn,
        location_id=1, location_name=loc, condition=cond, details="",
        created_at=datetime.now(), updated_at=datetime.now(),
    )


def _make_grouped(name="Laptop", sub="X1", qty=6, serials=None, loc="Warehouse"):
    serials = serials or []
    return GroupedInventoryItem(
        item_type_id=1, item_type_name=name, item_sub_type=sub,
        is_serialized=bool(serials), details="", total_quantity=qty,
        item_count=len(serials) or 1, serial_numbers=serials, item_ids=[1],
        location_id=1, location_name=loc,
    )


def test_build_workbook_returns_workbook():
    from export_service import ExportService
    wb = ExportService.build_workbook([_make_item()], location_name="Warehouse")
    import openpyxl
    assert isinstance(wb, openpyxl.Workbook)


def test_items_sheet_exists():
    from export_service import ExportService
    wb = ExportService.build_workbook([_make_item()], location_name="Warehouse")
    assert "Items" in wb.sheetnames


def test_items_sheet_has_bold_header():
    from export_service import ExportService
    wb = ExportService.build_workbook([_make_item()], location_name="Warehouse")
    ws = wb["Items"]
    assert ws.cell(1, 1).font.bold is True


def test_items_sheet_header_columns():
    from export_service import ExportService
    wb = ExportService.build_workbook([_make_item()], location_name="Warehouse")
    ws = wb["Items"]
    headers = [ws.cell(1, c).value for c in range(1, 7)]
    assert headers == ["Type", "Sub-type", "Quantity", "Serial Number", "Condition", "Location"]


def test_non_serialized_item_one_row():
    from export_service import ExportService
    item = _make_grouped("Laptop", qty=5)
    wb = ExportService.build_workbook([item], location_name="Warehouse")
    ws = wb["Items"]
    # Row 1 = header, row 2 = data
    assert ws.max_row == 2
    assert ws.cell(2, 3).value == 5  # quantity


def test_serialized_item_one_row_per_serial():
    from export_service import ExportService
    item = _make_grouped("Laptop", serials=["SN1", "SN2", "SN3"])
    wb = ExportService.build_workbook([item], location_name="Warehouse")
    ws = wb["Items"]
    assert ws.max_row == 4  # 1 header + 3 serials


def test_no_transactions_sheet_by_default():
    from export_service import ExportService
    wb = ExportService.build_workbook([_make_item()], location_name="Warehouse")
    assert "Transactions" not in wb.sheetnames
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_export_service.py -v
```
Expected: `ModuleNotFoundError: No module named 'export_service'`

**Step 3: Create `export_service.py`**

```python
"""Excel export service — builds openpyxl workbooks from inventory data."""

from __future__ import annotations

from typing import Dict, List, Optional, Union

import openpyxl
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from ui_entities.inventory_item import GroupedInventoryItem, InventoryItem


class ExportService:
    """Builds Excel workbooks from inventory data. No UI dependencies."""

    # Sheet column headers
    ITEM_HEADERS = ["Type", "Sub-type", "Quantity", "Serial Number", "Condition", "Location"]
    TRANSACTION_HEADERS = [
        "Date", "Type", "Item Type", "Sub-type", "Serial Number",
        "Qty Before", "Qty After", "Notes", "From Location", "To Location",
    ]

    @staticmethod
    def build_workbook(
        items: List[Union[InventoryItem, GroupedInventoryItem]],
        location_name: str,
        transactions: Optional[List[dict]] = None,
        loc_map: Optional[Dict[int, str]] = None,
        type_map: Optional[Dict[int, str]] = None,
    ) -> openpyxl.Workbook:
        """Build a workbook with an Items sheet and optional Transactions sheet.

        Args:
            items: List of InventoryItem or GroupedInventoryItem for the Items sheet.
            location_name: Display name used in the sheet title.
            transactions: Optional list of transaction dicts (from _transaction_to_dict).
            loc_map: Optional {location_id: name} for resolving location IDs in transactions.
            type_map: Optional {item_type_id: display_name} for transaction sheet.

        Returns:
            openpyxl.Workbook ready to be saved.
        """
        wb = openpyxl.Workbook()
        ws_items = wb.active
        ws_items.title = "Items"

        ExportService._write_items_sheet(ws_items, items)

        if transactions is not None:
            ws_tx = wb.create_sheet("Transactions")
            ExportService._write_transactions_sheet(
                ws_tx, transactions, loc_map or {}, type_map or {}
            )

        return wb

    @staticmethod
    def _write_items_sheet(
        ws,
        items: List[Union[InventoryItem, GroupedInventoryItem]],
    ) -> None:
        bold = Font(bold=True)

        # Header row
        for col, header in enumerate(ExportService.ITEM_HEADERS, start=1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = bold

        row = 2
        for item in items:
            if isinstance(item, GroupedInventoryItem) and item.is_serialized:
                # One row per serial number
                for sn in item.serial_numbers:
                    ws.cell(row=row, column=1, value=item.item_type_name)
                    ws.cell(row=row, column=2, value=item.item_sub_type or "")
                    ws.cell(row=row, column=3, value=1)
                    ws.cell(row=row, column=4, value=sn)
                    ws.cell(row=row, column=5, value="")
                    ws.cell(row=row, column=6, value=item.location_name)
                    row += 1
            elif isinstance(item, GroupedInventoryItem):
                ws.cell(row=row, column=1, value=item.item_type_name)
                ws.cell(row=row, column=2, value=item.item_sub_type or "")
                ws.cell(row=row, column=3, value=item.total_quantity)
                ws.cell(row=row, column=4, value="")
                ws.cell(row=row, column=5, value="")
                ws.cell(row=row, column=6, value=item.location_name)
                row += 1
            else:
                # InventoryItem
                ws.cell(row=row, column=1, value=item.item_type_name)
                ws.cell(row=row, column=2, value=item.item_sub_type or "")
                ws.cell(row=row, column=3, value=item.quantity)
                ws.cell(row=row, column=4, value=item.serial_number or "")
                ws.cell(row=row, column=5, value=item.condition or "")
                ws.cell(row=row, column=6, value=item.location_name)
                row += 1

        ExportService._autofit(ws, len(ExportService.ITEM_HEADERS))

    @staticmethod
    def _write_transactions_sheet(
        ws,
        transactions: List[dict],
        loc_map: Dict[int, str],
        type_map: Dict[int, str],
    ) -> None:
        bold = Font(bold=True)

        for col, header in enumerate(ExportService.TRANSACTION_HEADERS, start=1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = bold

        for row, trans in enumerate(transactions, start=2):
            created = trans.get("created_at")
            date_str = created.strftime("%d.%m.%Y %H:%M") if created else ""
            type_name = trans.get("type", "").upper()
            item_type_id = trans.get("item_type_id")
            name_parts = (type_map.get(item_type_id) or str(item_type_id)).split(" - ", 1)
            item_name = name_parts[0]
            item_sub = name_parts[1] if len(name_parts) > 1 else ""
            from_id = trans.get("from_location_id")
            to_id = trans.get("to_location_id")

            ws.cell(row=row, column=1, value=date_str)
            ws.cell(row=row, column=2, value=type_name)
            ws.cell(row=row, column=3, value=item_name)
            ws.cell(row=row, column=4, value=item_sub)
            ws.cell(row=row, column=5, value=trans.get("serial_number") or "")
            ws.cell(row=row, column=6, value=trans.get("quantity_before", ""))
            ws.cell(row=row, column=7, value=trans.get("quantity_after", ""))
            ws.cell(row=row, column=8, value=trans.get("notes") or "")
            ws.cell(row=row, column=9, value=loc_map.get(from_id, "") if from_id else "")
            ws.cell(row=row, column=10, value=loc_map.get(to_id, "") if to_id else "")

        ExportService._autofit(ws, len(ExportService.TRANSACTION_HEADERS))

    @staticmethod
    def _autofit(ws, num_cols: int, min_width: int = 10, max_width: int = 50) -> None:
        """Set column widths based on content."""
        for col in range(1, num_cols + 1):
            max_len = 0
            for cell in ws[get_column_letter(col)]:
                try:
                    max_len = max(max_len, len(str(cell.value or "")))
                except Exception:
                    pass
            ws.column_dimensions[get_column_letter(col)].width = max(
                min_width, min(max_len + 2, max_width)
            )
```

**Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_export_service.py -v
```
Expected: All 7 tests `PASSED`.

**Step 5: Commit**

```bash
git add export_service.py tests/test_export_service.py
git commit -m "feat: add ExportService with Items sheet"
```

---

## Task 4: ExportService — Transactions sheet tests

**Files:**
- Modify: `tests/test_export_service.py`

**Step 1: Add transaction sheet tests**

Append to `tests/test_export_service.py`:
```python
def _make_transaction(type_id=1, tx_type="add", qty_before=0, qty_after=5,
                      notes="init", sn=None, loc_id=1, from_id=None, to_id=None):
    from datetime import timezone
    return {
        "id": 1, "item_type_id": type_id, "type": tx_type,
        "quantity_change": qty_after - qty_before,
        "quantity_before": qty_before, "quantity_after": qty_after,
        "notes": notes, "serial_number": sn,
        "location_id": loc_id, "from_location_id": from_id, "to_location_id": to_id,
        "created_at": datetime(2026, 2, 24, 10, 30, tzinfo=timezone.utc),
    }


def test_transactions_sheet_created_when_passed():
    from export_service import ExportService
    wb = ExportService.build_workbook(
        [_make_item()], "Warehouse",
        transactions=[_make_transaction()],
        loc_map={1: "Warehouse"},
        type_map={1: "Laptop - X1"},
    )
    assert "Transactions" in wb.sheetnames


def test_transactions_sheet_has_bold_header():
    from export_service import ExportService
    wb = ExportService.build_workbook(
        [_make_item()], "Warehouse",
        transactions=[_make_transaction()],
    )
    ws = wb["Transactions"]
    assert ws.cell(1, 1).font.bold is True


def test_transactions_sheet_header_columns():
    from export_service import ExportService
    wb = ExportService.build_workbook(
        [_make_item()], "Warehouse",
        transactions=[_make_transaction()],
    )
    ws = wb["Transactions"]
    headers = [ws.cell(1, c).value for c in range(1, 11)]
    assert headers == [
        "Date", "Type", "Item Type", "Sub-type", "Serial Number",
        "Qty Before", "Qty After", "Notes", "From Location", "To Location",
    ]


def test_transactions_sheet_data_row():
    from export_service import ExportService
    wb = ExportService.build_workbook(
        [_make_item()], "Warehouse",
        transactions=[_make_transaction(type_id=1, tx_type="add", qty_before=0, qty_after=5)],
        loc_map={1: "Warehouse"},
        type_map={1: "Laptop - X1"},
    )
    ws = wb["Transactions"]
    assert ws.cell(2, 2).value == "ADD"
    assert ws.cell(2, 3).value == "Laptop"
    assert ws.cell(2, 4).value == "X1"
    assert ws.cell(2, 6).value == 0
    assert ws.cell(2, 7).value == 5


def test_transactions_location_names_resolved():
    from export_service import ExportService
    tx = _make_transaction(tx_type="transfer", from_id=1, to_id=2)
    wb = ExportService.build_workbook(
        [_make_item()], "Warehouse",
        transactions=[tx],
        loc_map={1: "Warehouse A", 2: "Warehouse B"},
    )
    ws = wb["Transactions"]
    assert ws.cell(2, 9).value == "Warehouse A"
    assert ws.cell(2, 10).value == "Warehouse B"
```

**Step 2: Run tests**

```bash
python -m pytest tests/test_export_service.py -v
```
Expected: All 12 tests `PASSED` (existing 7 + new 5).

**Step 3: Commit**

```bash
git add tests/test_export_service.py
git commit -m "test: add transaction sheet tests for ExportService"
```

---

## Task 5: Translation keys

**Files:**
- Modify: `ui_entities/translations.py`

**Step 1: Add keys to both language blocks**

In the Ukrainian block (`"uk": {`), add after the last `"location.*"` key group:
```python
"export.menu.file": "Файл",
"export.action": "Експортувати в Excel...",
"export.dialog.title": "Експортувати в Excel",
"export.dialog.exporting": "Експортується: {name}",
"export.dialog.include_transactions": "Включити транзакції",
"export.dialog.scope.all": "Усі транзакції для локації",
"export.dialog.scope.filtered": "Лише відфільтровані елементи",
"export.success.title": "Експорт завершено",
"export.success.message": "Файл збережено:\n{path}",
"export.error.no_items": "У вибраній локації немає елементів для експорту.",
"export.filename_default": "AuditMagic_{location}_{date}.xlsx",
```

In the English block (`"en": {`), add the same keys translated:
```python
"export.menu.file": "File",
"export.action": "Export to Excel...",
"export.dialog.title": "Export to Excel",
"export.dialog.exporting": "Exporting: {name}",
"export.dialog.include_transactions": "Include transactions",
"export.dialog.scope.all": "All transactions for location",
"export.dialog.scope.filtered": "Filtered items only",
"export.success.title": "Export Complete",
"export.success.message": "File saved:\n{path}",
"export.error.no_items": "No items in the selected location to export.",
"export.filename_default": "AuditMagic_{location}_{date}.xlsx",
```

**Step 2: Verify**

```bash
python -c "from ui_entities.translations import tr; print(tr('export.action'))"
```
Expected: `Export to Excel...` (or Ukrainian equivalent depending on config).

**Step 3: Commit**

```bash
git add ui_entities/translations.py
git commit -m "feat: add export translation keys"
```

---

## Task 6: ExportOptionsDialog

**Files:**
- Create: `ui_entities/export_options_dialog.py`

**Step 1: Create the dialog**

```python
"""Export options dialog — lets user choose transaction scope before export."""

from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from styles import apply_button_style
from ui_entities.translations import tr


class ExportOptionsDialog(QDialog):
    """Captures export options: whether to include transactions and scope."""

    def __init__(self, location_name: str, has_active_filter: bool = False, parent=None):
        super().__init__(parent)
        self._has_active_filter = has_active_filter
        self.setWindowTitle(tr("export.dialog.title"))
        self.setMinimumWidth(360)
        self._setup_ui(location_name)

    def _setup_ui(self, location_name: str) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Location label
        lbl = QLabel(tr("export.dialog.exporting").format(name=location_name))
        layout.addWidget(lbl)

        # Include transactions checkbox
        self.include_tx_cb = QCheckBox(tr("export.dialog.include_transactions"))
        self.include_tx_cb.toggled.connect(self._on_include_toggled)
        layout.addWidget(self.include_tx_cb)

        # Scope radio buttons (inside an indented container)
        self._scope_container = QWidget()
        scope_layout = QVBoxLayout(self._scope_container)
        scope_layout.setContentsMargins(20, 0, 0, 0)
        scope_layout.setSpacing(4)

        self.radio_all = QRadioButton(tr("export.dialog.scope.all"))
        self.radio_all.setChecked(True)
        self.radio_filtered = QRadioButton(tr("export.dialog.scope.filtered"))
        self.radio_filtered.setEnabled(self._has_active_filter)

        self._scope_group = QButtonGroup(self)
        self._scope_group.addButton(self.radio_all)
        self._scope_group.addButton(self.radio_filtered)

        scope_layout.addWidget(self.radio_all)
        scope_layout.addWidget(self.radio_filtered)
        self._scope_container.setEnabled(False)
        layout.addWidget(self._scope_container)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText(tr("export.action").replace("...", ""))
        apply_button_style(btns.button(QDialogButtonBox.StandardButton.Ok), "primary")
        apply_button_style(btns.button(QDialogButtonBox.StandardButton.Cancel), "secondary")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_include_toggled(self, checked: bool) -> None:
        self._scope_container.setEnabled(checked)

    def include_transactions(self) -> bool:
        return self.include_tx_cb.isChecked()

    def transaction_scope(self) -> str:
        """Returns 'all' or 'filtered'."""
        if self.radio_filtered.isChecked() and self._has_active_filter:
            return "filtered"
        return "all"
```

**Step 2: Smoke-test the import**

```bash
python -c "from ui_entities.export_options_dialog import ExportOptionsDialog; print('OK')"
```
Expected: `OK`

**Step 3: Commit**

```bash
git add ui_entities/export_options_dialog.py
git commit -m "feat: add ExportOptionsDialog"
```

---

## Task 7: File menu + export handler in main_window.py

**Files:**
- Modify: `ui_entities/main_window.py`

### 7a — Find where the menu bar is set up

Search for `menuBar` or `QMenu` in `ui_entities/main_window.py` to find where the Theme menu is added. The File menu goes in the same place, **before** the Theme menu.

### 7b — Add File menu

In the method that sets up menus (search for `theme_menu` or `QMenu`), add before the theme menu setup:

```python
# File menu
file_menu = self.menuBar().addMenu(tr("export.menu.file"))
export_action = file_menu.addAction(tr("export.action"))
export_action.triggered.connect(self._on_export_excel)
```

### 7c — Add the export handler method

Add this private method to `MainWindow`:

```python
def _on_export_excel(self) -> None:
    """Handle File → Export to Excel…"""
    from datetime import date
    import re

    from PyQt6.QtWidgets import QFileDialog, QMessageBox

    from export_service import ExportService
    from services import InventoryService, LocationService, TransactionService
    from ui_entities.export_options_dialog import ExportOptionsDialog

    # Determine current location
    current_loc_id = self._current_location_id  # None means "All Locations"
    if current_loc_id is not None:
        loc = LocationService.get_location_by_id(current_loc_id)
        location_name = loc.name if loc else tr("location.all")
    else:
        location_name = tr("location.all")

    # Guard: no items
    items = self.inventory_model.get_all_items()
    if not items:
        QMessageBox.warning(
            self,
            tr("export.dialog.title"),
            tr("export.error.no_items"),
        )
        return

    # Options dialog
    has_filter = bool(self.search_widget.get_search_text().strip())
    dlg = ExportOptionsDialog(
        location_name=location_name,
        has_active_filter=has_filter,
        parent=self,
    )
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return

    # Build suggested filename
    safe_loc = re.sub(r'[^\w\-]', '_', location_name)
    today = date.today().strftime("%Y-%m-%d")
    suggested = tr("export.filename_default").format(location=safe_loc, date=today)

    # Save As dialog
    path, _ = QFileDialog.getSaveFileName(
        self,
        tr("export.dialog.title"),
        suggested,
        "Excel Files (*.xlsx)",
    )
    if not path:
        return  # user cancelled

    # Load transactions if requested
    transactions = None
    loc_map = None
    type_map = None
    if dlg.include_transactions():
        scope = dlg.transaction_scope()
        if scope == "filtered":
            type_ids = list({item.item_type_id for item in items})
            transactions = TransactionService.get_for_export(
                location_id=current_loc_id, item_type_ids=type_ids
            )
        else:
            transactions = TransactionService.get_for_export(
                location_id=current_loc_id
            )
        loc_map = {loc.id: loc.name for loc in LocationService.get_all_locations()}
        type_map = InventoryService.get_item_type_display_names()

    # Build and save workbook
    try:
        wb = ExportService.build_workbook(
            items=items,
            location_name=location_name,
            transactions=transactions,
            loc_map=loc_map,
            type_map=type_map,
        )
        wb.save(path)
    except PermissionError:
        QMessageBox.critical(
            self,
            tr("export.dialog.title"),
            "Could not save file. Is it open in another program?",
        )
        return
    except Exception as e:
        from logger import logger
        logger.error(f"Export failed: {e}", exc_info=True)
        QMessageBox.critical(self, tr("export.dialog.title"), str(e))
        return

    QMessageBox.information(
        self,
        tr("export.success.title"),
        tr("export.success.message").format(path=path),
    )
```

### 7d — Add `get_all_items()` to InventoryModel

The handler calls `self.inventory_model.get_all_items()`. Open `ui_entities/inventory_model.py` and check what the model's items attribute is named (look for `self._items` or similar). Add:

```python
def get_all_items(self):
    """Return all currently loaded items."""
    return list(self._items)  # replace _items with actual attribute name
```

### 7e — Check `_current_location_id` attribute name

In `main_window.py`, search for `current_location_id` or the attribute that stores the active location. Verify the name used in 7c matches what actually exists in the class.

**Step 1: Verify the app launches without errors**

```bash
python main.py
```
Expected: App opens, File menu visible with "Export to Excel…" item.

**Step 2: Manual smoke test**
1. Add a couple of items
2. File → Export to Excel…
3. Check "Include transactions", select scope
4. Click Export, pick a save path
5. Open the file in Excel or LibreOffice — verify two sheets with correct data

**Step 3: Commit**

```bash
git add ui_entities/main_window.py ui_entities/inventory_model.py
git commit -m "feat: wire File menu and export handler in MainWindow"
```

---

## Task 8: Final integration commit

**Step 1: Run all tests**

```bash
python -m pytest tests/ -v
```
Expected: All tests pass.

**Step 2: Final commit**

```bash
git add -A
git commit -m "feat: Excel export — File > Export to Excel with optional transactions sheet"
```
