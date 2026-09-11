# Split Add Item Dialog by Serialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single checkbox-driven `AddItemDialog` with an upfront chooser popup ("With Serial Number" / "Without Serial Number") that opens one of two mode-specific dialogs, each showing only the fields relevant to that mode.

**Architecture:** `main_window._on_add_clicked` opens a new `AddItemChooserDialog`; on accept it opens either `AddSerializedItemDialog` or `AddNonSerializedItemDialog` (both new, replacing `AddItemDialog`). Serialization-conflict detection reuses the existing `has_serialization_conflict()` pure function and `error.serialized_conflict` copy already used by `EditItemDialog`, so a conflict blocks save via the same warning-on-click pattern — no new conflict mechanism. Type/Subtype autocomplete in each dialog is filtered to only that dialog's serialization mode via a new `is_serialized` filter threaded through `ItemTypeRepository` → `InventoryService`.

**Tech Stack:** PyQt6, SQLAlchemy repositories, existing `ui/form_rules.py` validation, `ui/translations.py` i18n.

---

## Reference: decisions from grilling session

1. Chooser: modal, two buttons + Cancel. Cancel → nothing opens.
2. Non-serial dialog: Type, Subtype, Quantity, Initial Notes, Location, existing merge-into-existing-stock prompt. No checkbox, no Serial Number field.
3. Serial dialog: Type, Subtype, Serial Number, Initial Notes, Location. No checkbox, no Quantity widget (always 1, implicit).
4. Same type name+subtype reused with matching serialization = fine. Mismatched serialization = **block save** (existing `has_serialization_conflict` + `error.serialized_conflict`, same pattern as `EditItemDialog._on_save_clicked`: warn on click, don't disable the button preemptively).
5. Autocomplete suggestions filtered per-dialog to only types matching that dialog's mode.
6. Cancel on either mode dialog kills the whole add-item flow (no return to chooser).
7. Live 300ms-debounced Type/Subtype lookup shows info label (match) or conflict block (mismatch) — same debounce pattern as today.
8. Distinct dialog titles per mode (new translation keys).

ADR already recorded: `docs/adr/0001-split-add-item-dialog-by-serialization.md`.

---

## File Structure

- Modify: `src/core/repositories.py` — `ItemTypeRepository.get_autocomplete_names` / `get_autocomplete_subtypes` gain an `is_serialized: Optional[bool] = None` filter.
- Modify: `src/core/services.py` — `InventoryService.get_autocomplete_types` / `get_autocomplete_subtypes` thread the new param through.
- Modify: `src/ui/translations.py` — new keys for the chooser and the two split dialogs.
- Create: `src/ui/dialogs/wrapping_text_edit.py` — `WrappingTextEdit`, extracted from `add_item_dialog.py` (was private, now shared by two dialogs — DRY).
- Create: `src/ui/dialogs/add_item_chooser_dialog.py` — `AddItemChooserDialog`.
- Create: `src/ui/dialogs/add_serialized_item_dialog.py` — `AddSerializedItemDialog`.
- Create: `src/ui/dialogs/add_non_serialized_item_dialog.py` — `AddNonSerializedItemDialog`.
- Modify: `src/ui/main_window.py` — `_on_add_clicked` rewritten to drive chooser → mode dialog; import swap.
- Delete: `src/ui/dialogs/add_item_dialog.py` — fully replaced, no other importer (verified: only `main_window.py:15,604` referenced it).
- Modify: `tests/test_repositories.py`, `tests/test_services.py`, `tests/test_translations.py` — cover the new filter param and new translation keys.

No automated dialog-level tests exist anywhere in this repo today (`AddItemDialog`, `EditItemDialog`, `AddSerialNumberDialog` all go untested at the widget level — only services/repositories/form_rules are unit-tested). This plan follows that convention: the three new/changed dialog files get no pytest coverage; Task 11 is a manual run-through instead.

---

### Task 1: Commit the ADR

**Files:**
- Already created: `docs/adr/0001-split-add-item-dialog-by-serialization.md`

- [ ] **Step 1: Commit it on its own, ahead of the implementation**

```bash
git add docs/adr/0001-split-add-item-dialog-by-serialization.md
git commit -m "docs: add ADR for splitting Add Item dialog by serialization

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Repository — filter `get_autocomplete_names` by serialization

**Files:**
- Modify: `src/core/repositories.py:304-320`
- Test: `tests/test_repositories.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_repositories.py`, right after `test_itemtype_get_autocomplete_names` (currently ending at line 218):

```python
def test_itemtype_get_autocomplete_names_filtered_by_serialization():
    _type("Laptop", serialized=False)
    _type("LaptopDock", serialized=True)
    non_serial_names = ItemTypeRepository.get_autocomplete_names(
        prefix="Lap", is_serialized=False
    )
    serial_names = ItemTypeRepository.get_autocomplete_names(
        prefix="Lap", is_serialized=True
    )
    assert non_serial_names == ["Laptop"]
    assert serial_names == ["LaptopDock"]
    # No filter (default) still returns both, unchanged behavior
    both = ItemTypeRepository.get_autocomplete_names(prefix="Lap")
    assert set(both) == {"Laptop", "LaptopDock"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_repositories.py::test_itemtype_get_autocomplete_names_filtered_by_serialization -v`
Expected: FAIL with `TypeError: get_autocomplete_names() got an unexpected keyword argument 'is_serialized'`

- [ ] **Step 3: Add the filter param**

In `src/core/repositories.py`, replace lines 304-320:

```python
    @staticmethod
    def get_autocomplete_names(
        prefix: str = "", is_serialized: Optional[bool] = None, limit: int = 20
    ) -> List[str]:
        """Get autocomplete suggestions for type names.

        Args:
            prefix: Search prefix (optional)
            is_serialized: When given, only suggest types with this serialization
                state. None (default) suggests across both.
            limit: Maximum number of suggestions

        Returns:
            List of matching type names.
        """
        with session_scope() as session:
            query = session.query(ItemType.name).distinct()
            if prefix:
                query = query.filter(ItemType.name.ilike(f"{prefix}%"))
            if is_serialized is not None:
                query = query.filter(ItemType.is_serialized == is_serialized)
            query = query.order_by(ItemType.name).limit(limit)
            return [row[0] for row in query.all()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_repositories.py::test_itemtype_get_autocomplete_names_filtered_by_serialization -v`
Expected: PASS

- [ ] **Step 5: Run the full repository test file to check nothing else broke**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_repositories.py -v`
Expected: all PASS (including the pre-existing `test_itemtype_get_autocomplete_names`, unaffected since `is_serialized` defaults to `None`)

- [ ] **Step 6: Commit**

```bash
git add src/core/repositories.py tests/test_repositories.py
git commit -m "feat: filter ItemType name autocomplete by serialization

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Repository — filter `get_autocomplete_subtypes` by serialization

**Files:**
- Modify: `src/core/repositories.py:322-349`
- Test: `tests/test_repositories.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_repositories.py`:

```python
def test_itemtype_get_autocomplete_subtypes_filtered_by_serialization():
    _type("Laptop", "Air", serialized=False)
    _type("Laptop", "Pro", serialized=True)
    non_serial = ItemTypeRepository.get_autocomplete_subtypes(
        "Laptop", is_serialized=False
    )
    serial = ItemTypeRepository.get_autocomplete_subtypes(
        "Laptop", is_serialized=True
    )
    assert non_serial == ["Air"]
    assert serial == ["Pro"]
    both = ItemTypeRepository.get_autocomplete_subtypes("Laptop")
    assert set(both) == {"Air", "Pro"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_repositories.py::test_itemtype_get_autocomplete_subtypes_filtered_by_serialization -v`
Expected: FAIL with `TypeError: get_autocomplete_subtypes() got an unexpected keyword argument 'is_serialized'`

- [ ] **Step 3: Add the filter param**

In `src/core/repositories.py`, replace lines 322-349:

```python
    @staticmethod
    def get_autocomplete_subtypes(
        type_name: str,
        prefix: str = "",
        is_serialized: Optional[bool] = None,
        limit: int = 20,
    ) -> List[str]:
        """Get autocomplete suggestions for subtypes given a type name.

        Args:
            type_name: The type name to filter by
            prefix: Search prefix for subtype (optional)
            is_serialized: When given, only suggest subtypes of types with this
                serialization state. None (default) suggests across both.
            limit: Maximum number of suggestions

        Returns:
            List of matching subtype names.
        """
        with session_scope() as session:
            query = (
                session.query(ItemType.sub_type)
                .filter(
                    ItemType.name == type_name,
                    ItemType.sub_type.isnot(None),
                    ItemType.sub_type != "",
                )
                .distinct()
            )
            if prefix:
                query = query.filter(ItemType.sub_type.ilike(f"{prefix}%"))
            if is_serialized is not None:
                query = query.filter(ItemType.is_serialized == is_serialized)
            query = query.order_by(ItemType.sub_type).limit(limit)
            return [row[0] for row in query.all() if row[0]]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_repositories.py::test_itemtype_get_autocomplete_subtypes_filtered_by_serialization -v`
Expected: PASS

- [ ] **Step 5: Run the full repository test file**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_repositories.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/core/repositories.py tests/test_repositories.py
git commit -m "feat: filter ItemType subtype autocomplete by serialization

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Service — thread `is_serialized` through `get_autocomplete_types`

**Files:**
- Modify: `src/core/services.py:385-395`
- Test: `tests/test_services.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_services.py`, right after `test_get_autocomplete_types` (currently ending at line 245):

```python
def test_get_autocomplete_types_filtered_by_serialization():
    ItemTypeRepository.get_or_create("Keyboard", "", False)
    ItemTypeRepository.get_or_create("KeyFob", "", True)
    non_serial = InventoryService.get_autocomplete_types("Key", is_serialized=False)
    serial = InventoryService.get_autocomplete_types("Key", is_serialized=True)
    assert non_serial == ["Keyboard"]
    assert serial == ["KeyFob"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_services.py::test_get_autocomplete_types_filtered_by_serialization -v`
Expected: FAIL with `TypeError: get_autocomplete_types() got an unexpected keyword argument 'is_serialized'`

- [ ] **Step 3: Thread the param through**

In `src/core/services.py`, replace lines 385-395:

```python
    @staticmethod
    def get_autocomplete_types(
        prefix: str = "", is_serialized: Optional[bool] = None
    ) -> List[str]:
        """Get autocomplete suggestions for item types.

        Args:
            prefix: Search prefix
            is_serialized: When given, only suggest types with this
                serialization state. None (default) suggests across both.

        Returns:
            List of matching type names.
        """
        return ItemTypeRepository.get_autocomplete_names(
            prefix, is_serialized=is_serialized
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_services.py::test_get_autocomplete_types_filtered_by_serialization -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/services.py tests/test_services.py
git commit -m "feat: thread is_serialized filter through InventoryService.get_autocomplete_types

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Service — thread `is_serialized` through `get_autocomplete_subtypes`

**Files:**
- Modify: `src/core/services.py:397-408`
- Test: `tests/test_services.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_services.py`:

```python
def test_get_autocomplete_subtypes_filtered_by_serialization():
    ItemTypeRepository.get_or_create("Laptop", "Air", False)
    ItemTypeRepository.get_or_create("Laptop", "Pro", True)
    non_serial = InventoryService.get_autocomplete_subtypes(
        "Laptop", is_serialized=False
    )
    serial = InventoryService.get_autocomplete_subtypes("Laptop", is_serialized=True)
    assert non_serial == ["Air"]
    assert serial == ["Pro"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_services.py::test_get_autocomplete_subtypes_filtered_by_serialization -v`
Expected: FAIL with `TypeError: get_autocomplete_subtypes() got an unexpected keyword argument 'is_serialized'`

- [ ] **Step 3: Thread the param through**

In `src/core/services.py`, replace lines 397-408:

```python
    @staticmethod
    def get_autocomplete_subtypes(
        type_name: str, prefix: str = "", is_serialized: Optional[bool] = None
    ) -> List[str]:
        """Get autocomplete suggestions for subtypes.

        Args:
            type_name: The type name
            prefix: Search prefix
            is_serialized: When given, only suggest subtypes of types with this
                serialization state. None (default) suggests across both.

        Returns:
            List of matching subtype names.
        """
        return ItemTypeRepository.get_autocomplete_subtypes(
            type_name, prefix, is_serialized=is_serialized
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_services.py::test_get_autocomplete_subtypes_filtered_by_serialization -v`
Expected: PASS

- [ ] **Step 5: Run full service + repository suites**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_services.py tests/test_repositories.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/core/services.py tests/test_services.py
git commit -m "feat: thread is_serialized filter through InventoryService.get_autocomplete_subtypes

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Translations — new keys for chooser and split dialogs

**Files:**
- Modify: `src/ui/translations.py:138` (Ukrainian block, after `dialog.add_item.duplicate.message`)
- Modify: `src/ui/translations.py:376` (English block, after `dialog.add_item.duplicate.message`)
- Test: `tests/test_translations.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_translations.py`:

```python
def test_add_item_split_translation_keys_present():
    from ui.translations import tr

    keys = [
        "dialog.add_item_chooser.title",
        "dialog.add_item_chooser.header",
        "button.add_item_chooser.with_serial",
        "button.add_item_chooser.without_serial",
        "dialog.add_serialized_item.title",
        "dialog.add_serialized_item.header",
        "dialog.add_non_serialized_item.title",
        "dialog.add_non_serialized_item.header",
    ]
    for key in keys:
        assert tr(key) != key, f"Translation key missing: {key!r}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_translations.py::test_add_item_split_translation_keys_present -v`
Expected: FAIL — `tr(key)` returns the key itself for the first missing key

- [ ] **Step 3: Add the Ukrainian keys**

In `src/ui/translations.py`, after line 138 (`"dialog.add_item.duplicate.message": "Неможливо створити дублікат предмета.",`), insert:

```python
        "dialog.add_item_chooser.title": "Додати новий елемент",
        "dialog.add_item_chooser.header": "Цей елемент має серійний номер?",
        "button.add_item_chooser.with_serial": "Із серійним номером",
        "button.add_item_chooser.without_serial": "Без серійного номера",
        "dialog.add_serialized_item.title": "Додати серійний елемент",
        "dialog.add_serialized_item.header": "Додати новий серійний елемент",
        "dialog.add_non_serialized_item.title": "Додати елемент",
        "dialog.add_non_serialized_item.header": "Додати новий елемент інвентарю",
```

- [ ] **Step 4: Add the English keys**

In `src/ui/translations.py`, after the English `"dialog.add_item.duplicate.message": "Cannot create duplicate item.",` line, insert:

```python
        "dialog.add_item_chooser.title": "Add New Item",
        "dialog.add_item_chooser.header": "Does this item have a serial number?",
        "button.add_item_chooser.with_serial": "With Serial Number",
        "button.add_item_chooser.without_serial": "Without Serial Number",
        "dialog.add_serialized_item.title": "Add Serialized Item",
        "dialog.add_serialized_item.header": "Add New Serialized Item",
        "dialog.add_non_serialized_item.title": "Add Item",
        "dialog.add_non_serialized_item.header": "Add New Inventory Item",
```

- [ ] **Step 5: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_translations.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/ui/translations.py tests/test_translations.py
git commit -m "feat: add translation keys for split Add Item dialogs

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Extract shared `WrappingTextEdit` widget

**Files:**
- Create: `src/ui/dialogs/wrapping_text_edit.py`
- Modify: `src/ui/dialogs/add_item_dialog.py:38-49` (drop the private copy; this file is deleted in Task 10 anyway, but keep it working until then)

No test — this is a mechanical extraction of an existing, already-in-use private class (`_WrappingTextEdit` in `add_item_dialog.py:38-49`), promoted to shared so both new dialogs (Task 8, Task 9) can use it without duplicating the placeholder word-wrap painter.

- [ ] **Step 1: Create the shared module**

```python
"""QTextEdit that word-wraps its placeholder text.

QTextEdit's built-in placeholder does not wrap, so long placeholder copy gets
clipped. This subclass paints the placeholder itself with word-wrap when the
field is empty.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QTextEdit


class WrappingTextEdit(QTextEdit):
    """QTextEdit whose placeholder text word-wraps instead of clipping."""

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.toPlainText() or not self.placeholderText():
            return
        viewport = self.viewport()
        if viewport is None:
            return
        painter = QPainter(viewport)
        painter.setPen(self.palette().placeholderText().color())
        rect = viewport.rect().adjusted(4, 4, -4, -4)
        painter.drawText(rect, Qt.TextFlag.TextWordWrap, self.placeholderText())
```

- [ ] **Step 2: Point `add_item_dialog.py` at the shared class**

In `src/ui/dialogs/add_item_dialog.py`, delete lines 38-49 (the `_WrappingTextEdit` class body) and its blank lines, add the import, and rename the one use site:

```python
from ui.dialogs.wrapping_text_edit import WrappingTextEdit
```

Then in `_setup_ui`, change:

```python
        self.initial_notes_edit = _WrappingTextEdit()
```

to:

```python
        self.initial_notes_edit = WrappingTextEdit()
```

- [ ] **Step 3: Run LSP diagnostics on the changed file**

Use the LSP `hover`/diagnostics on `src/ui/dialogs/add_item_dialog.py` — confirm no unresolved `_WrappingTextEdit` reference remains and the new import resolves.

- [ ] **Step 4: Run the app-level test suite to confirm nothing imports the old private name**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/ -v`
Expected: all PASS (no test imports `_WrappingTextEdit` — confirmed earlier: no dialog-level tests exist)

- [ ] **Step 5: Commit**

```bash
git add src/ui/dialogs/wrapping_text_edit.py src/ui/dialogs/add_item_dialog.py
git commit -m "refactor: extract WrappingTextEdit into its own module

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 8: `AddItemChooserDialog`

**Files:**
- Create: `src/ui/dialogs/add_item_chooser_dialog.py`

No test — no dialog-level tests exist in this repo (see File Structure note). Verified manually in Task 11.

- [ ] **Step 1: Create the dialog**

```python
"""First step of the Add Item flow: choose serialized vs non-serialized."""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ui.styles import apply_button_style
from ui.translations import tr


class AddItemChooserDialog(QDialog):
    """Asks whether the new item is serialized before opening the right form."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chose_serialized: Optional[bool] = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog.add_item_chooser.title"))
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        header_label = QLabel(tr("dialog.add_item_chooser.header"))
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setWordWrap(True)
        layout.addWidget(header_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        choice_layout = QHBoxLayout()
        choice_layout.setSpacing(10)

        serialized_button = QPushButton(tr("button.add_item_chooser.with_serial"))
        apply_button_style(serialized_button, "primary")
        serialized_button.clicked.connect(self._choose_serialized)
        choice_layout.addWidget(serialized_button)

        non_serialized_button = QPushButton(
            tr("button.add_item_chooser.without_serial")
        )
        apply_button_style(non_serialized_button, "secondary")
        non_serialized_button.clicked.connect(self._choose_non_serialized)
        choice_layout.addWidget(non_serialized_button)

        layout.addLayout(choice_layout)

        cancel_layout = QHBoxLayout()
        cancel_layout.addStretch()
        cancel_button = QPushButton(tr("button.cancel"))
        apply_button_style(cancel_button, "danger")
        cancel_button.clicked.connect(self.reject)
        cancel_layout.addWidget(cancel_button)
        layout.addLayout(cancel_layout)

    def _choose_serialized(self):
        """Record the serialized choice and close."""
        self._chose_serialized = True
        self.accept()

    def _choose_non_serialized(self):
        """Record the non-serialized choice and close."""
        self._chose_serialized = False
        self.accept()

    def is_serialized_chosen(self) -> bool:
        """Return the user's choice. Only meaningful if the dialog was accepted."""
        assert self._chose_serialized is not None
        return self._chose_serialized
```

- [ ] **Step 2: Check LSP diagnostics**

Confirm no unresolved imports or type errors in `src/ui/dialogs/add_item_chooser_dialog.py`.

- [ ] **Step 3: Commit**

```bash
git add src/ui/dialogs/add_item_chooser_dialog.py
git commit -m "feat: add AddItemChooserDialog for the with/without serial choice

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 9: `AddSerializedItemDialog`

**Files:**
- Create: `src/ui/dialogs/add_serialized_item_dialog.py`

No test — no dialog-level tests exist in this repo. Verified manually in Task 11. Reuses `add_item_rules` (called with `quantity_text="1"`, matching the serialized branch's fixed quantity) and `has_serialization_conflict`, both already covered by `tests/test_form_rules.py`.

- [ ] **Step 1: Create the dialog**

```python
"""Dialog for adding a new serialized inventory item (fixed quantity 1)."""

from typing import Optional

from PyQt6.QtCore import QStringListModel, Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.logger import logger
from core.repositories import LocationRepository
from core.services import InventoryService
from ui.dialogs.validation_feedback import show_validation_errors
from ui.dialogs.wrapping_text_edit import WrappingTextEdit
from ui.form_rules import add_item_rules, has_serialization_conflict
from ui.models.inventory_item import InventoryItem
from ui.styles import apply_button_style, apply_combo_box_style, apply_input_style, apply_text_edit_style
from ui.translations import tr
from ui.validators import ItemTypeValidator, SerialNumberValidator


class AddSerializedItemDialog(QDialog):
    """Dialog for adding a new serialized item. Quantity is always 1."""

    def __init__(self, current_location_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self._current_location_id = current_location_id
        self._result_item: Optional[InventoryItem] = None
        self._type_conflict: bool = False
        self._type_debounce_timer = QTimer(self)
        self._type_debounce_timer.setSingleShot(True)
        self._type_debounce_timer.timeout.connect(self._on_type_or_subtype_changed)
        self._setup_ui()
        self._setup_validators()
        self._setup_autocomplete()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog.add_serialized_item.title"))
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        header_label = QLabel(tr("dialog.add_serialized_item.header"))
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        label_font = QFont()
        label_font.setBold(True)

        type_label = QLabel(tr("label.type"))
        type_label.setFont(label_font)
        self.type_edit = QLineEdit()
        self.type_edit.setPlaceholderText(tr("placeholder.type"))
        apply_input_style(self.type_edit)
        form_layout.addRow(type_label, self.type_edit)

        subtype_label = QLabel(tr("label.subtype"))
        self.subtype_edit = QLineEdit()
        self.subtype_edit.setPlaceholderText(tr("placeholder.subtype"))
        apply_input_style(self.subtype_edit)
        form_layout.addRow(subtype_label, self.subtype_edit)

        # Conflict/info status label — red for a serialization conflict,
        # italic secondary color for a plain "type already exists" match.
        self.type_status_label = QLabel("")
        form_layout.addRow("", self.type_status_label)

        serial_label = QLabel(tr("label.serial_number"))
        serial_label.setFont(label_font)
        self.serial_edit = QLineEdit()
        self.serial_edit.setPlaceholderText(tr("placeholder.serial_number"))
        apply_input_style(self.serial_edit)
        form_layout.addRow(serial_label, self.serial_edit)

        initial_notes_label = QLabel(tr("label.initial_notes"))
        self.initial_notes_edit = WrappingTextEdit()
        self.initial_notes_edit.setPlaceholderText(tr("placeholder.initial_notes"))
        self.initial_notes_edit.setMaximumHeight(60)
        apply_text_edit_style(self.initial_notes_edit)
        form_layout.addRow(initial_notes_label, self.initial_notes_edit)

        loc_label = QLabel(tr("location.title"))
        loc_label.setFont(label_font)
        self.location_combo = QComboBox()
        apply_combo_box_style(self.location_combo)
        for loc in LocationRepository.get_all():
            self.location_combo.addItem(loc.name, userData=loc.id)
        if self._current_location_id is not None:
            for i in range(self.location_combo.count()):
                if self.location_combo.itemData(i) == self._current_location_id:
                    self.location_combo.setCurrentIndex(i)
                    break
        form_layout.addRow(loc_label, self.location_combo)

        layout.addLayout(form_layout)
        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton(tr("button.cancel"))
        apply_button_style(cancel_button, "danger")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        add_button = QPushButton(tr("button.add"))
        apply_button_style(add_button, "primary")
        add_button.setDefault(True)
        add_button.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(add_button)

        layout.addLayout(button_layout)

        self.type_edit.setFocus()

    def _setup_validators(self):
        """Set up input validators for form fields."""
        self.type_edit.setValidator(ItemTypeValidator(self))
        self.serial_edit.setValidator(SerialNumberValidator(self))
        logger.debug("Serialized-add form validators configured")

    def _setup_autocomplete(self):
        """Setup autocomplete for type and subtype fields, filtered to serialized types."""
        self.type_completer = QCompleter(self)
        self.type_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.type_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.type_edit.setCompleter(self.type_completer)

        self.subtype_completer = QCompleter(self)
        self.subtype_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.subtype_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.subtype_edit.setCompleter(self.subtype_completer)

        self.type_edit.textChanged.connect(self._update_type_autocomplete)
        self.type_edit.textChanged.connect(self._update_subtype_autocomplete)

        self.type_edit.textChanged.connect(self._restart_type_debounce)
        self.subtype_edit.textChanged.connect(self._restart_type_debounce)

        logger.debug("Serialized-add autocomplete configured")

    def _update_type_autocomplete(self, text: str):
        """Update autocomplete suggestions for type, serialized types only."""
        try:
            suggestions = InventoryService.get_autocomplete_types(
                text, is_serialized=True
            )
            self.type_completer.setModel(QStringListModel(suggestions))
        except Exception as e:
            logger.error(f"Failed to load type autocomplete: {e}")

    def _update_subtype_autocomplete(self, type_text: str):
        """Update autocomplete suggestions for subtype, serialized types only."""
        if not type_text:
            return
        try:
            suggestions = InventoryService.get_autocomplete_subtypes(
                type_text, is_serialized=True
            )
            self.subtype_completer.setModel(QStringListModel(suggestions))
        except Exception as e:
            logger.error(f"Failed to load subtype autocomplete: {e}")

    def _restart_type_debounce(self):
        """Restart 300ms debounce timer for the type/subtype conflict lookup."""
        self._type_debounce_timer.stop()
        self._type_debounce_timer.start(300)

    def _on_type_or_subtype_changed(self):
        """Show a conflict warning or an info match for the typed Type/Subtype.

        A Serialization Conflict (existing type with a different is_serialized)
        blocks the save — see _on_add_clicked. A matching existing type is only
        informational.
        """
        type_name = self.type_edit.text().strip()
        sub_type = self.subtype_edit.text().strip()

        if not type_name:
            self.type_status_label.setText("")
            self._type_conflict = False
            return

        try:
            existing = InventoryService.get_item_type_by_name_subtype(
                type_name, sub_type
            )
        except Exception as e:
            logger.warning(f"Type lookup failed: {e}")
            return

        self._type_conflict = has_serialization_conflict(
            existing_is_serialized=existing.is_serialized if existing else None,
            current_is_serialized=True,
        )
        if self._type_conflict:
            self.type_status_label.setStyleSheet(
                "color: #c62828; font-style: italic;"
            )
            self.type_status_label.setText(
                tr("error.serialized_conflict").format(
                    name=type_name, state=tr("label.non_serialized_badge")
                )
            )
        elif existing is not None:
            self.type_status_label.setStyleSheet("font-style: italic;")
            self.type_status_label.setText(tr("message.type_exists_serialized"))
        else:
            self.type_status_label.setText("")

    def _on_add_clicked(self):
        """Validate and accept the dialog."""
        if self._type_conflict:
            QMessageBox.warning(
                self, tr("message.validation_error"), self.type_status_label.text()
            )
            self.type_edit.setFocus()
            return

        item_type = self.type_edit.text().strip()
        sub_type = self.subtype_edit.text().strip()
        serial_number = self.serial_edit.text().strip()
        initial_notes = self.initial_notes_edit.toPlainText().strip()

        errors = add_item_rules(
            item_type=item_type,
            quantity_text="1",
            serial_number=serial_number,
            initial_notes=initial_notes,
            is_serialized=True,
        )
        if errors:
            show_validation_errors(
                self,
                errors,
                widgets={
                    "type": self.type_edit,
                    "serial": self.serial_edit,
                    "notes": self.initial_notes_edit,
                },
                log_prefix="Serialized-add form",
            )
            return

        logger.info(
            f"Serialized-add form validation passed - creating item: type='{item_type}'"
        )
        location_id = self.location_combo.currentData()

        try:
            self._result_item = InventoryService.create_serialized_item(
                item_type_name=item_type,
                item_sub_type=sub_type,
                serial_number=serial_number,
                location_id=location_id,
                notes=initial_notes or "",
            )
            logger.info(f"Serialized item created successfully: id={self._result_item.id}")
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, tr("message.validation_error"), str(e))
            logger.error(f"Serialized item creation failed with validation error: {e}")
        except Exception as e:
            QMessageBox.critical(
                self,
                tr("error.generic.title"),
                f"{tr('error.generic.message')}\n\n{str(e)}",
            )
            logger.error(f"Serialized item creation failed: {e}", exc_info=True)

    def get_item(self) -> Optional[InventoryItem]:
        """Return the created item, or None if dialog was cancelled."""
        return self._result_item
```

- [ ] **Step 2: Check LSP diagnostics**

Confirm no unresolved imports or type errors in `src/ui/dialogs/add_serialized_item_dialog.py`.

- [ ] **Step 3: Run the full test suite (nothing touches this file yet, but confirms the shared modules it imports are all intact)**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/ -v`
Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add src/ui/dialogs/add_serialized_item_dialog.py
git commit -m "feat: add AddSerializedItemDialog

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 10: `AddNonSerializedItemDialog`

**Files:**
- Create: `src/ui/dialogs/add_non_serialized_item_dialog.py`

No test — no dialog-level tests exist in this repo. Verified manually in Task 11.

- [ ] **Step 1: Create the dialog**

```python
"""Dialog for adding a new non-serialized inventory item (has a quantity)."""

from typing import Optional

from PyQt6.QtCore import QStringListModel, Qt, QTimer
from PyQt6.QtGui import QFont, QIntValidator
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.logger import logger
from core.repositories import LocationRepository
from core.services import InventoryService
from ui.dialogs.validation_feedback import show_validation_errors
from ui.dialogs.wrapping_text_edit import WrappingTextEdit
from ui.form_rules import add_item_rules, has_serialization_conflict
from ui.models.inventory_item import InventoryItem
from ui.styles import apply_button_style, apply_combo_box_style, apply_input_style, apply_text_edit_style
from ui.translations import tr
from ui.validators import ItemTypeValidator


class AddNonSerializedItemDialog(QDialog):
    """Dialog for adding a new non-serialized item with a quantity."""

    def __init__(self, current_location_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self._current_location_id = current_location_id
        self._result_item: Optional[InventoryItem] = None
        self._type_conflict: bool = False
        self._type_debounce_timer = QTimer(self)
        self._type_debounce_timer.setSingleShot(True)
        self._type_debounce_timer.timeout.connect(self._on_type_or_subtype_changed)
        self._setup_ui()
        self._setup_validators()
        self._setup_autocomplete()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog.add_non_serialized_item.title"))
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        header_label = QLabel(tr("dialog.add_non_serialized_item.header"))
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        label_font = QFont()
        label_font.setBold(True)

        type_label = QLabel(tr("label.type"))
        type_label.setFont(label_font)
        self.type_edit = QLineEdit()
        self.type_edit.setPlaceholderText(tr("placeholder.type"))
        apply_input_style(self.type_edit)
        form_layout.addRow(type_label, self.type_edit)

        subtype_label = QLabel(tr("label.subtype"))
        self.subtype_edit = QLineEdit()
        self.subtype_edit.setPlaceholderText(tr("placeholder.subtype"))
        apply_input_style(self.subtype_edit)
        form_layout.addRow(subtype_label, self.subtype_edit)

        # Conflict/info status label — red for a serialization conflict,
        # italic secondary color for a plain "type already exists" match.
        self.type_status_label = QLabel("")
        form_layout.addRow("", self.type_status_label)

        quantity_label = QLabel(tr("label.quantity"))
        quantity_label.setFont(label_font)
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText(tr("placeholder.quantity"))
        quantity_validator = QIntValidator(1, 999999, self)
        self.quantity_input.setValidator(quantity_validator)
        apply_input_style(self.quantity_input, large=True)
        form_layout.addRow(quantity_label, self.quantity_input)

        initial_notes_label = QLabel(tr("label.initial_notes"))
        self.initial_notes_edit = WrappingTextEdit()
        self.initial_notes_edit.setPlaceholderText(tr("placeholder.initial_notes"))
        self.initial_notes_edit.setMaximumHeight(60)
        apply_text_edit_style(self.initial_notes_edit)
        form_layout.addRow(initial_notes_label, self.initial_notes_edit)

        loc_label = QLabel(tr("location.title"))
        loc_label.setFont(label_font)
        self.location_combo = QComboBox()
        apply_combo_box_style(self.location_combo)
        for loc in LocationRepository.get_all():
            self.location_combo.addItem(loc.name, userData=loc.id)
        if self._current_location_id is not None:
            for i in range(self.location_combo.count()):
                if self.location_combo.itemData(i) == self._current_location_id:
                    self.location_combo.setCurrentIndex(i)
                    break
        form_layout.addRow(loc_label, self.location_combo)

        layout.addLayout(form_layout)
        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton(tr("button.cancel"))
        apply_button_style(cancel_button, "danger")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        add_button = QPushButton(tr("button.add"))
        apply_button_style(add_button, "primary")
        add_button.setDefault(True)
        add_button.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(add_button)

        layout.addLayout(button_layout)

        self.type_edit.setFocus()

    def _setup_validators(self):
        """Set up input validators for form fields."""
        self.type_edit.setValidator(ItemTypeValidator(self))
        logger.debug("Non-serialized-add form validators configured")

    def _setup_autocomplete(self):
        """Setup autocomplete for type and subtype fields, filtered to non-serialized types."""
        self.type_completer = QCompleter(self)
        self.type_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.type_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.type_edit.setCompleter(self.type_completer)

        self.subtype_completer = QCompleter(self)
        self.subtype_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.subtype_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.subtype_edit.setCompleter(self.subtype_completer)

        self.type_edit.textChanged.connect(self._update_type_autocomplete)
        self.type_edit.textChanged.connect(self._update_subtype_autocomplete)

        self.type_edit.textChanged.connect(self._restart_type_debounce)
        self.subtype_edit.textChanged.connect(self._restart_type_debounce)

        logger.debug("Non-serialized-add autocomplete configured")

    def _update_type_autocomplete(self, text: str):
        """Update autocomplete suggestions for type, non-serialized types only."""
        try:
            suggestions = InventoryService.get_autocomplete_types(
                text, is_serialized=False
            )
            self.type_completer.setModel(QStringListModel(suggestions))
        except Exception as e:
            logger.error(f"Failed to load type autocomplete: {e}")

    def _update_subtype_autocomplete(self, type_text: str):
        """Update autocomplete suggestions for subtype, non-serialized types only."""
        if not type_text:
            return
        try:
            suggestions = InventoryService.get_autocomplete_subtypes(
                type_text, is_serialized=False
            )
            self.subtype_completer.setModel(QStringListModel(suggestions))
        except Exception as e:
            logger.error(f"Failed to load subtype autocomplete: {e}")

    def _restart_type_debounce(self):
        """Restart 300ms debounce timer for the type/subtype conflict lookup."""
        self._type_debounce_timer.stop()
        self._type_debounce_timer.start(300)

    def _on_type_or_subtype_changed(self):
        """Show a conflict warning or an info match for the typed Type/Subtype.

        A Serialization Conflict (existing type with a different is_serialized)
        blocks the save — see _on_add_clicked. A matching existing type is only
        informational.
        """
        type_name = self.type_edit.text().strip()
        sub_type = self.subtype_edit.text().strip()

        if not type_name:
            self.type_status_label.setText("")
            self._type_conflict = False
            return

        try:
            existing = InventoryService.get_item_type_by_name_subtype(
                type_name, sub_type
            )
        except Exception as e:
            logger.warning(f"Type lookup failed: {e}")
            return

        self._type_conflict = has_serialization_conflict(
            existing_is_serialized=existing.is_serialized if existing else None,
            current_is_serialized=False,
        )
        if self._type_conflict:
            self.type_status_label.setStyleSheet(
                "color: #c62828; font-style: italic;"
            )
            self.type_status_label.setText(
                tr("error.serialized_conflict").format(
                    name=type_name, state=tr("label.serialized_badge")
                )
            )
        elif existing is not None:
            self.type_status_label.setStyleSheet("font-style: italic;")
            self.type_status_label.setText(tr("message.type_exists_non_serialized"))
        else:
            self.type_status_label.setText("")

    def _on_add_clicked(self):
        """Validate and accept the dialog."""
        if self._type_conflict:
            QMessageBox.warning(
                self, tr("message.validation_error"), self.type_status_label.text()
            )
            self.type_edit.setFocus()
            return

        item_type = self.type_edit.text().strip()
        sub_type = self.subtype_edit.text().strip()
        quantity_text = self.quantity_input.text().strip()
        initial_notes = self.initial_notes_edit.toPlainText().strip()

        errors = add_item_rules(
            item_type=item_type,
            quantity_text=quantity_text,
            serial_number="",
            initial_notes=initial_notes,
            is_serialized=False,
        )
        if errors:
            show_validation_errors(
                self,
                errors,
                widgets={
                    "type": self.type_edit,
                    "quantity": self.quantity_input,
                    "notes": self.initial_notes_edit,
                },
                log_prefix="Non-serialized-add form",
            )
            return

        quantity = int(quantity_text)
        logger.info(
            f"Non-serialized-add form validation passed - creating item: "
            f"type='{item_type}', qty={quantity}"
        )
        location_id = self.location_combo.currentData()

        try:
            existing = InventoryService.find_non_serialized_at_location(
                type_name=item_type, sub_type=sub_type, location_id=location_id
            )
            if existing is not None:
                answer = QMessageBox.question(
                    self,
                    tr("dialog.add_item.merge.title"),
                    tr("dialog.add_item.merge.prompt").format(quantity=quantity),
                )
                if answer == QMessageBox.StandardButton.Yes:
                    result = InventoryService.add_quantity(
                        item_id=existing.id,
                        quantity=quantity,
                        notes=initial_notes,
                    )
                    if result is None:
                        QMessageBox.warning(
                            self,
                            tr("error.generic.title"),
                            tr("error.generic.message"),
                        )
                        logger.warning(
                            f"Merge failed: item id={existing.id} not found during add_quantity"
                        )
                        return
                    self._result_item = result
                    logger.info(f"Merged quantity into existing item: id={existing.id}")
                    self.accept()
                else:
                    QMessageBox.information(
                        self,
                        tr("dialog.add_item.duplicate.title"),
                        tr("dialog.add_item.duplicate.message"),
                    )
                return

            self._result_item = InventoryService.create_item(
                item_type_name=item_type,
                item_sub_type=sub_type,
                quantity=quantity,
                is_serialized=False,
                location_id=location_id,
                transaction_notes=initial_notes or "",
            )
            logger.info(f"Item created successfully: id={self._result_item.id}")
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, tr("message.validation_error"), str(e))
            logger.error(f"Item creation failed with validation error: {e}")
        except Exception as e:
            QMessageBox.critical(
                self,
                tr("error.generic.title"),
                f"{tr('error.generic.message')}\n\n{str(e)}",
            )
            logger.error(f"Item creation failed: {e}", exc_info=True)

    def get_item(self) -> Optional[InventoryItem]:
        """Return the created item, or None if dialog was cancelled."""
        return self._result_item
```

- [ ] **Step 2: Check LSP diagnostics**

Confirm no unresolved imports or type errors in `src/ui/dialogs/add_non_serialized_item_dialog.py`.

- [ ] **Step 3: Run the full test suite**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/ -v`
Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add src/ui/dialogs/add_non_serialized_item_dialog.py
git commit -m "feat: add AddNonSerializedItemDialog

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 11: Wire the chooser into `main_window.py`, delete the old dialog

**Files:**
- Modify: `src/ui/main_window.py:15` (import), `src/ui/main_window.py:602-612` (`_on_add_clicked`)
- Delete: `src/ui/dialogs/add_item_dialog.py`
- Delete: `src/ui/dialogs/wrapping_text_edit.py` import there goes away with the file

- [ ] **Step 1: Swap the import**

In `src/ui/main_window.py`, replace line 15:

```python
from ui.dialogs.add_item_dialog import AddItemDialog
```

with (keeping the existing `AddSerialNumberDialog` import on the next line untouched):

```python
from ui.dialogs.add_item_chooser_dialog import AddItemChooserDialog
from ui.dialogs.add_non_serialized_item_dialog import AddNonSerializedItemDialog
from ui.dialogs.add_serialized_item_dialog import AddSerializedItemDialog
```

Run `isort` afterward (Step 5) to place these alphabetically among the existing `ui.dialogs.*` imports.

- [ ] **Step 2: Rewrite `_on_add_clicked`**

In `src/ui/main_window.py`, replace lines 602-612:

```python
    def _on_add_clicked(self):
        """Handle add button click - open add item dialog."""
        dialog = AddItemDialog(
            current_location_id=self._current_location_id, parent=self
        )
        if dialog.exec():
            new_item = dialog.get_item()
            if new_item:
                # Item is already saved by the dialog via InventoryService.create_item
                # Refresh the list to show grouped items correctly
                self._refresh_item_list()
```

with:

```python
    def _on_add_clicked(self):
        """Handle add button click - ask serialized vs non-serialized, then open the matching dialog."""
        chooser = AddItemChooserDialog(parent=self)
        if not chooser.exec():
            return

        if chooser.is_serialized_chosen():
            dialog = AddSerializedItemDialog(
                current_location_id=self._current_location_id, parent=self
            )
        else:
            dialog = AddNonSerializedItemDialog(
                current_location_id=self._current_location_id, parent=self
            )

        if dialog.exec():
            new_item = dialog.get_item()
            if new_item:
                # Item is already saved by the dialog via InventoryService
                # Refresh the list to show grouped items correctly
                self._refresh_item_list()
```

- [ ] **Step 3: Delete the old dialog and its now-unused private widget copy**

```bash
git rm src/ui/dialogs/add_item_dialog.py
```

(`wrapping_text_edit.py` stays — Tasks 9 and 10's dialogs use it.)

- [ ] **Step 4: Check LSP diagnostics on `main_window.py`**

Confirm no unresolved reference to `AddItemDialog` remains anywhere in the file and the three new imports resolve.

- [ ] **Step 5: Format and lint**

```bash
.venv/bin/isort --profile black src/ui/main_window.py src/ui/dialogs/
.venv/bin/black src/ui/main_window.py src/ui/dialogs/
.venv/bin/flake8 --extend-ignore=E203 src/ui/main_window.py src/ui/dialogs/
```

Expected: `black` reports files reformatted if needed (rerun until clean), `flake8` reports nothing.

- [ ] **Step 6: Full test suite + mypy**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/ -v
.venv/bin/mypy src
```

Expected: all tests PASS, mypy clean.

- [ ] **Step 7: Commit**

```bash
git add -A src/ui/main_window.py src/ui/dialogs/
git commit -m "feat: wire Add Item chooser into main window, remove old AddItemDialog

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 12: Manual verification (no automated dialog tests exist for this app)

**Files:** none — this is a run-through, not a code change.

- [ ] **Step 1: Launch the app**

Use the `run` skill (or `python src/main.py`) to launch AuditMagic against a scratch DB.

- [ ] **Step 2: Walk the non-serialized path**

Click "Add New Item" (`main.add_item`) → chooser appears → click "Without Serial Number" → confirm only Type/Subtype/Quantity/Initial Notes/Location show (no Serial Number field, no checkbox) → create a brand-new type → item appears in the list.

- [ ] **Step 3: Walk the serialized path**

Click "Add New Item" → "With Serial Number" → confirm only Type/Subtype/Serial Number/Initial Notes/Location show (no Quantity field) → create a new serialized type → item appears in the list with the serialized badge.

- [ ] **Step 4: Walk the conflict path**

Reopen the chooser, pick the mode opposite of a type created in Step 2 or 3, type that exact Type/Subtype → confirm the red conflict label appears within ~300ms and clicking "Add" shows the warning and does not save.

- [ ] **Step 5: Walk the Cancel paths**

Chooser → Cancel → confirm nothing opens. Chooser → pick a mode → Cancel on the resulting dialog → confirm the whole flow closes (no return to chooser).

- [ ] **Step 6: Switch language and repeat Step 2's chooser screen**

Toggle language to English (or Ukrainian, whichever isn't currently active) via the app's language setting, reopen the chooser, confirm the new titles/button labels render translated, not raw keys.

---

## Self-Review

**Spec coverage** — all 8 grilled decisions map to a task: (1) chooser → Task 8; (2) non-serial fields → Task 10; (3) serial fields → Task 9; (4) conflict blocks save → Tasks 9 & 10's `_on_type_or_subtype_changed`/`_on_add_clicked`; (5) mode-filtered autocomplete → Tasks 2-5, 9, 10; (6) cancel semantics → Task 11's `_on_add_clicked`; (7) live debounced detection → Tasks 9 & 10; (8) distinct titles → Task 6.

**Placeholder scan** — no TBD/"add appropriate handling" left; every code step has complete, runnable code.

**Type consistency** — `get_autocomplete_names(prefix, is_serialized, limit)` (Task 2) matches `ItemTypeRepository.get_autocomplete_names(prefix, is_serialized=...)` calls in Task 4; `get_autocomplete_subtypes(type_name, prefix, is_serialized, limit)` (Task 3) matches Task 5's call shape `get_autocomplete_subtypes(type_name, prefix, is_serialized=...)`. `AddItemChooserDialog.is_serialized_chosen()` (Task 8) matches its only caller in Task 11. `get_item()` on both new dialogs (Tasks 9, 10) matches Task 11's `dialog.get_item()` call, mirroring the old `AddItemDialog.get_item()` contract.
