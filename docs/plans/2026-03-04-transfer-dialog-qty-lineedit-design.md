# Design: Replace QSpinBox with QLineEdit in TransferDialog

**Date:** 2026-03-04

## Problem

`TransferDialog` uses `QSpinBox` for the quantity field in the non-serialized transfer flow. All other dialogs (`AddItemDialog`, `QuantityDialog`) already use `QLineEdit` for quantity input, with comments explicitly noting "QLineEdit instead of QSpinBox for better UX". The spin box also has a manual stylesheet call (`Styles.get_spin_box_style()`) rather than the standard `apply_input_style()` helper, and uses `addStretch()` which prevents the field from filling available space.

## Decision

Replace `QSpinBox` with `QLineEdit` + `PositiveIntValidator` in `TransferDialog`, consistent with the rest of the codebase. Remove `get_spin_box_style()` from `styles.py` as it becomes unused.

## Changes

### `src/ui/dialogs/transfer_dialog.py`

- Remove `QSpinBox` from imports; add `PositiveIntValidator` from `ui.validators`
- Remove `from ui.styles import Styles` (unused after this change)
- Replace `self.qty_spin = QSpinBox()` with `self.qty_spin = QLineEdit("1")`
- Rename attribute to `self.qty_input` to reflect the type
- Apply `apply_input_style(self.qty_input)` instead of manual stylesheet + `setMinimumWidth`
- Attach `PositiveIntValidator(minimum=1, maximum=1)` on creation (placeholder max updated at populate time)
- Remove `qty_row.addStretch()` — `stretch=1` on the field fills remaining space; `avail_label` sits to its right
- In `_populate_content`: call `self._qty_validator.setTop(total_qty)` and `self.qty_input.setText("1")`; remove the `max_qty = max(total_qty, 1)` guard (was only needed by QSpinBox)
- In `_on_accept`: parse `int(self.qty_input.text())` instead of `self.qty_spin.value()`

### `src/ui/styles.py`

- Remove `get_spin_box_style()` — unused after this change

## Validator behaviour

`PositiveIntValidator` (already in `ui/validators.py`) enforces integer input in range `[1, total_qty]` in real time. Accept-time validation still checks for empty/invalid text and falls through to the existing `if not item_ids` guard.
