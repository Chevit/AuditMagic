# Excel Export Design

**Date:** 2026-02-24
**Feature:** Export location inventory and transactions to `.xlsx`

## Overview

Add the ability to export inventory data for the currently selected location to an Excel file. The export produces one mandatory Items sheet and an optional Transactions sheet. Triggered via a new **File** menu in the main window.

## Architecture

Four additions to the project:

| Component | File | Role |
|-----------|------|------|
| `ExportService` | `export_service.py` | Builds the `openpyxl.Workbook` — pure data logic, no UI |
| `ExportOptionsDialog` | `ui_entities/export_options_dialog.py` | Options UI: transaction checkbox + scope radio buttons |
| File menu | `ui_entities/main_window.py` | New "File" menu with "Export to Excel…" action |
| `openpyxl` | `requirements.txt` | New dependency |

## User Flow

1. User selects **File → Export to Excel…**
2. If no items exist at the selected location, show `QMessageBox.warning` and abort.
3. `ExportOptionsDialog` opens — user configures transaction options.
4. User clicks **Export…** — native `QFileDialog.getSaveFileName()` opens with suggested filename `AuditMagic_<LocationName>_<YYYY-MM-DD>.xlsx`.
5. `ExportService.build_workbook(...)` constructs the workbook in memory.
6. `workbook.save(path)` writes the file.
7. `QMessageBox.information` confirms success with the saved path.

The active location in `LocationSelectorWidget` determines scope. "All Locations" exports everything; the Location column identifies each row.

## ExportOptionsDialog

```
┌─────────────────────────────────────────┐
│  Export to Excel                        │
├─────────────────────────────────────────┤
│  Exporting: Warehouse A  (or All)       │
│                                         │
│  ☑ Include transactions                 │
│                                         │
│    ● All transactions for location      │
│    ○ Filtered items only                │
│      (greyed if no search active)       │
│                                         │
│           [ Cancel ]  [ Export… ]       │
└─────────────────────────────────────────┘
```

- Radio buttons enabled only when the checkbox is checked.
- "Filtered items only" disabled when no search filter is active.
- Cancel: silent no-op.

## Sheet Schemas

### Sheet 1: Items

| Column | Source |
|--------|--------|
| Type | `ItemType.name` |
| Sub-type | `ItemType.sub_type` |
| Quantity | `total_quantity` (1 per row for serialized) |
| Serial Number | `serial_number` (blank for non-serialized) |
| Condition | `Item.condition` |
| Location | `Location.name` |

Serialized groups: one row per serial number. Non-serialized: one row with total quantity.

### Sheet 2: Transactions (optional)

| Column | Source |
|--------|--------|
| Date | `Transaction.created_at` (`dd.MM.yyyy HH:mm`) |
| Type | `transaction_type` (ADD/REMOVE/EDIT/TRANSFER) |
| Item Type | `ItemType.name` |
| Sub-type | `ItemType.sub_type` |
| Serial Number | `Transaction.serial_number` |
| Qty Before | `quantity_before` |
| Qty After | `quantity_after` |
| Notes | `Transaction.notes` |
| From Location | `from_location.name` |
| To Location | `to_location.name` |

**Transaction scope** (user's choice):
- *All for location* — OR filter: `location_id OR from_location_id OR to_location_id`
- *Filtered items only* — only transactions for item types visible after active search filter

Both sheets: bold header row + auto-fitted column widths.

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| No items in selected location | `QMessageBox.warning` before export dialog — abort |
| User cancels Save As | Silent no-op |
| File open in Excel (write fails) | `QMessageBox.critical` — "Could not save file. Is it open in another program?" |
| Unexpected exception | `QMessageBox.critical` with message; logged via `logger.py` |

## Dependencies

- `openpyxl` added to `requirements.txt` and bundled via PyInstaller spec.
