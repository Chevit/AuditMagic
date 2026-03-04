# TransferDialog QSpinBox → QLineEdit Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the `QSpinBox` quantity field in `TransferDialog` with a `QLineEdit` + `PositiveIntValidator`, matching the pattern used by every other quantity field in the codebase.

**Architecture:** Two files change. `styles.py` loses `get_spin_box_style()` (unused after this). `transfer_dialog.py` swaps its `QSpinBox` for a `QLineEdit`, applies the standard `apply_input_style()` helper, attaches `PositiveIntValidator` with `top` updated dynamically to `total_qty`, removes the trailing `addStretch()` so the field fills remaining space, and updates accept-time parsing.

**Tech Stack:** PyQt6, `PositiveIntValidator` (`src/ui/validators.py`), `apply_input_style` (`src/ui/styles.py`)

---

### Task 1: Remove `get_spin_box_style()` from styles.py

**Files:**
- Modify: `src/ui/styles.py:243-263`

**Step 1: Delete the method**

In `src/ui/styles.py`, remove the entire `get_spin_box_style` static method (lines 243–263):

```python
    @staticmethod
    def get_spin_box_style() -> str:
        """Get QSpinBox stylesheet with theme-aware colors and dimensions."""
        return f"""
            QSpinBox {{
                padding: 5px;
                border: {Dimensions.BORDER_WIDTH}px solid {Colors.get_border_default()};
                border-radius: {Dimensions.get_border_radius()}px;
                background-color: {Colors.get_bg_default()};
                color: {Colors.get_main_color()};
                font-size: {Dimensions.get_font_size()}px;
                mib-width: 100px;
            }}
            QSpinBox:focus {{
                border: {Dimensions.BORDER_WIDTH}px solid {Colors.get_border_focus()};
            }}
            QSpinBox:disabled {{
                background-color: {Colors.get_bg_disabled()};
                color: {Colors.get_text_disabled()};
            }}
        """
```

**Step 2: Run existing tests**

```bash
pytest tests/ -v
```

Expected: all tests pass (this method had no callers outside transfer_dialog which we haven't changed yet).

**Step 3: Commit**

```bash
git add src/ui/styles.py
git commit -m "refactor: remove unused get_spin_box_style from Styles"
```

---

### Task 2: Update imports in transfer_dialog.py

**Files:**
- Modify: `src/ui/dialogs/transfer_dialog.py:1-26`

**Step 1: Remove `QSpinBox` from the PyQt6 import block and `Styles` from the styles import**

Current imports (lines 7–25):
```python
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
```

Remove `QSpinBox` from that block. `QLineEdit` is already imported.

Current line 5:
```python
from ui.styles import Styles
```
Delete this line entirely.

**Step 2: Add `PositiveIntValidator` import**

After the existing `from ui.styles import apply_button_style, apply_combo_box_style, apply_input_style` line, add:

```python
from ui.validators import PositiveIntValidator
```

**Step 3: Run existing tests**

```bash
pytest tests/ -v
```

Expected: all pass (dialog isn't instantiated by tests).

**Step 4: Commit**

```bash
git add src/ui/dialogs/transfer_dialog.py
git commit -m "refactor: update transfer_dialog imports for QLineEdit migration"
```

---

### Task 3: Replace QSpinBox with QLineEdit in `_setup_ui`

**Files:**
- Modify: `src/ui/dialogs/transfer_dialog.py:112-125`

**Step 1: Replace the qty block**

Current code (lines 112–125):
```python
        else:
            qty_row_title = QHBoxLayout()
            qty_row_title.addWidget(QLabel(tr("transfer.quantity")))
            layout.addLayout(qty_row_title)
            qty_row = QHBoxLayout()
            self.qty_spin = QSpinBox()
            self.qty_spin.setMinimum(1)
            self.qty_spin.setMinimumWidth(150)
            self.qty_spin.setStyleSheet(Styles.get_spin_box_style())
            qty_row.addWidget(self.qty_spin, stretch=1)
            self.avail_label = QLabel("")
            qty_row.addWidget(self.avail_label)
            qty_row.addStretch()
            layout.addLayout(qty_row)
```

Replace with:
```python
        else:
            qty_row_title = QHBoxLayout()
            qty_row_title.addWidget(QLabel(tr("transfer.quantity")))
            layout.addLayout(qty_row_title)
            qty_row = QHBoxLayout()
            self.qty_input = QLineEdit("1")
            apply_input_style(self.qty_input)
            self._qty_validator = PositiveIntValidator(minimum=1, maximum=1)
            self.qty_input.setValidator(self._qty_validator)
            qty_row.addWidget(self.qty_input, stretch=1)
            self.avail_label = QLabel("")
            qty_row.addWidget(self.avail_label)
            layout.addLayout(qty_row)
```

Key changes:
- `QSpinBox` → `QLineEdit("1")` (pre-filled with "1")
- `apply_input_style()` replaces manual stylesheet + setMinimumWidth
- `PositiveIntValidator` attached (max=1 is a placeholder; updated in `_populate_content`)
- `qty_row.addStretch()` removed — `stretch=1` on the field fills remaining space
- Attribute renamed `qty_spin` → `qty_input`

**Step 2: Run existing tests**

```bash
pytest tests/ -v
```

Expected: all pass.

**Step 3: Commit**

```bash
git add src/ui/dialogs/transfer_dialog.py
git commit -m "refactor: replace QSpinBox with QLineEdit in TransferDialog setup"
```

---

### Task 4: Update `_populate_content` to drive the validator

**Files:**
- Modify: `src/ui/dialogs/transfer_dialog.py:200-204`

**Step 1: Replace the non-serialized branch**

Current code (lines 200–204):
```python
        else:
            max_qty = max(total_qty, 1)
            self.qty_spin.setMaximum(max_qty)
            self.qty_spin.setValue(1)
            self.avail_label.setText(tr("transfer.available").format(count=total_qty))
```

Replace with:
```python
        else:
            self._qty_validator.setTop(total_qty)
            self.qty_input.setText("1")
            self.avail_label.setText(tr("transfer.available").format(count=total_qty))
```

Key changes:
- `max(total_qty, 1)` guard removed — `setTop` accepts 0 and the accept-time guard handles zero stock
- `.setMaximum` / `.setValue` replaced by `.setTop` / `.setText`

**Step 2: Run existing tests**

```bash
pytest tests/ -v
```

Expected: all pass.

**Step 3: Commit**

```bash
git add src/ui/dialogs/transfer_dialog.py
git commit -m "refactor: update _populate_content to use QLineEdit validator"
```

---

### Task 5: Update `_on_accept` to parse text

**Files:**
- Modify: `src/ui/dialogs/transfer_dialog.py:257-260`

**Step 1: Replace qty read**

Current code (lines 257–260):
```python
            else:
                quantity = self.qty_spin.value()
                if quantity <= 0:
                    self.error_label.setText(tr("transfer.error.no_quantity"))
                    self.error_label.show()
                    return
```

Replace with:
```python
            else:
                text = self.qty_input.text().strip()
                if not text or not text.isdigit():
                    self.error_label.setText(tr("transfer.error.no_quantity"))
                    self.error_label.show()
                    return
                quantity = int(text)
                if quantity <= 0:
                    self.error_label.setText(tr("transfer.error.no_quantity"))
                    self.error_label.show()
                    return
```

**Step 2: Run existing tests**

```bash
pytest tests/ -v
```

Expected: all pass.

**Step 3: Commit**

```bash
git add src/ui/dialogs/transfer_dialog.py
git commit -m "refactor: update _on_accept to parse QLineEdit text for quantity"
```

---

### Task 6: Manual smoke test

Launch the app and open a transfer dialog on a non-serialized item:

```bash
python src/main.py
```

Verify:
1. Quantity field looks like a standard input (same style as Notes field above it)
2. Field pre-filled with `"1"`, shows available count label to its right
3. Field expands to fill row width (no extra gap after the available label)
4. Typing non-numeric characters is blocked by the validator
5. Entering a value above `total_qty` is blocked
6. Transfer completes successfully

---
