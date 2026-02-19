# Feature: ItemType `is_serialized` — Lock, Enforce, and Surface in All CRUD Flows

> **Target project:** AuditMagic (`C:\Users\chevi\PycharmProjects\AuditMagic`)
> **Stack:** Python 3.11 · PyQt6 · SQLAlchemy + SQLite · Alembic · `qt-material`
> **Architecture:** Repository → Service → UI (MVC), custom `QAbstractListModel`, dataclass DTOs

---

## 0. Overview

`ItemType.is_serialized` is a **permanent, immutable property** set at type-creation time.
It must be:
1. **Saved correctly** when a brand-new `ItemType` is created.
2. **Locked** — impossible to change once the type has any `Item` rows.
3. **Enforced** in `repositories.py` so conflicting requests raise clear errors.
4. **Surfaced** in every CRUD dialog and in the list-view delegate.

The following bugs exist today and must be fixed:

| # | File | Bug |
|---|------|-----|
| 1 | `repositories.py` → `ItemTypeRepository.get_or_create` | When an existing type is found, the caller's `is_serialized` is silently ignored — no conflict check, no error. |
| 2 | `ui_entities/add_item_dialog.py` | When a user types a type name that **already exists**, the `Serialized` checkbox is not synced to the existing type's state, so the form can submit a conflicting value. |
| 3 | `ui_entities/edit_item_dialog.py` | `is_serialized` is never shown or editable — the user has no visual indication; the field is not guarded against type-change renames. |
| 4 | `ui_entities/item_details_dialog.py` | `is_serialized` is never displayed. |
| 5 | `ui_entities/inventory_delegate.py` | No serialized badge in the list-view. |
| 6 | `services.py` → `InventoryService.edit_item` | Passes `is_serialized` directly to `get_or_create` when editing — could create a new type with the wrong flag. |

---

## 1. Repository Layer — `repositories.py`

### 1.1 `ItemTypeRepository.get_or_create` — enforce serialized consistency

Replace the current implementation:

```python
@staticmethod
def get_or_create(
    name: str,
    sub_type: str = "",
    is_serialized: bool = False,
    details: str = ""
) -> ItemType:
```

New logic (keep the signature unchanged):

```python
with session_scope() as session:
    item_type = (
        session.query(ItemType)
        .filter(
            ItemType.name == name,
            ItemType.sub_type == (sub_type or "")
        )
        .first()
    )

    if item_type:
        # ── Conflict guard ──────────────────────────────────────────────
        if item_type.is_serialized != is_serialized:
            existing_state = "serialized" if item_type.is_serialized else "non-serialized"
            requested_state = "serialized" if is_serialized else "non-serialized"
            raise ValueError(
                f"ItemType '{name}' (sub_type='{sub_type}') already exists as "
                f"{existing_state}. Cannot use it as {requested_state}. "
                f"Choose a different name/sub-type or keep the same serialization mode."
            )
        return _detach_item_type(item_type)

    # ── Brand-new type ───────────────────────────────────────────────────
    item_type = ItemType(
        name=name,
        sub_type=sub_type or "",
        is_serialized=is_serialized,
        details=details or ""
    )
    session.add(item_type)
    session.flush()
    session.refresh(item_type)
    return _detach_item_type(item_type)
```

### 1.2 `ItemTypeRepository.update` — block `is_serialized` changes when items exist

Inside the `update` method, add this guard before applying `is_serialized`:

```python
if is_serialized is not None and item_type.is_serialized != is_serialized:
    # Check whether any items exist for this type
    item_count = session.query(Item).filter(Item.item_type_id == type_id).count()
    if item_count > 0:
        raise ValueError(
            f"Cannot change is_serialized for '{item_type.name}': "
            f"{item_count} item(s) already exist. Delete all items first."
        )
    item_type.is_serialized = is_serialized
```

### 1.3 Add `ItemTypeRepository.get_by_name_and_subtype` helper (new public method)

This is needed by the UI to look up an existing type while the user is typing:

```python
@staticmethod
def get_by_name_and_subtype(name: str, sub_type: str = "") -> Optional[ItemType]:
    """Return an existing ItemType for the given name/sub_type, or None."""
    with session_scope() as session:
        item_type = (
            session.query(ItemType)
            .filter(
                ItemType.name == name,
                ItemType.sub_type == (sub_type or "")
            )
            .first()
        )
        return _detach_item_type(item_type) if item_type else None
```

---

## 2. Service Layer — `services.py`

### 2.1 Add `get_item_type_by_name_subtype` to `InventoryService`

```python
@staticmethod
def get_item_type_by_name_subtype(name: str, sub_type: str = ""):
    """Return ItemType info for the given name/sub_type, or None.

    Used by UI to pre-fill serialization state when the user picks an existing type.

    Returns:
        ItemType ORM detached object or None.
    """
    return ItemTypeRepository.get_by_name_and_subtype(name, sub_type)
```

### 2.2 `InventoryService.edit_item` — pass `is_serialized` from existing type

Inside `edit_item`, after calling `ItemTypeRepository.get_or_create`, use the **returned** type's `is_serialized` (not the caller's argument) when building the result.
The current code already does this implicitly, but add a comment and make it explicit:

```python
# Always use the authoritative is_serialized from the DB, not the caller's hint.
item_type = ItemTypeRepository.get_or_create(
    name=item_type_name,
    sub_type=sub_type,
    is_serialized=is_serialized,   # conflict guard in repo will raise if wrong
    details=details
)
```

No logic change needed here — the repo guard is sufficient.

---

## 3. Translations — `ui_entities/translations.py`

Add the following keys to **both** `Language.UKRAINIAN` and `Language.ENGLISH` dictionaries:

```python
# ── UKRAINIAN ──────────────────────────────────────────────────────────────────
"label.serialized_badge": "Серійний",
"label.non_serialized_badge": "Не серійний",
"label.is_serialized": "Тип серійний:",
"tooltip.serialized_locked": "Серіалізація заблокована після створення типу.",
"tooltip.serialized_auto": "Автоматично встановлено з існуючого типу",
"error.serialized_conflict": "Тип '{name}' вже існує як {state}. Оберіть інше ім'я або підтип.",
"message.type_exists_serialized": "Знайдено існуючий тип (серійний) — прапорець заблоковано.",
"message.type_exists_non_serialized": "Знайдено існуючий тип (не серійний) — прапорець заблоковано.",

# ── ENGLISH ────────────────────────────────────────────────────────────────────
"label.serialized_badge": "Serialized",
"label.non_serialized_badge": "Non-serialized",
"label.is_serialized": "Is Serialized:",
"tooltip.serialized_locked": "Serialization is locked after the type is created.",
"tooltip.serialized_auto": "Auto-set from existing type",
"error.serialized_conflict": "Type '{name}' already exists as {state}. Choose a different name or sub-type.",
"message.type_exists_serialized": "Existing type found (serialized) — checkbox locked.",
"message.type_exists_non_serialized": "Existing type found (non-serialized) — checkbox locked.",
```

---

## 4. Add Dialog — `ui_entities/add_item_dialog.py`

### Goal
When the user types a type name (and optionally sub-type) that **already exists in the DB**, the `Serialized` checkbox must:
- Be **automatically set** to match the existing type's state.
- Be **disabled** (read-only) with a tooltip explaining why.
- Show an inline status label like *"Existing type found (serialized) — checkbox locked."*

When the type name is cleared or points to a non-existing type, restore the checkbox to editable.

### Changes

#### A) Add inline status label to the form, below the serialized checkbox row

In `_setup_ui`, right after `form_layout.addRow(serialized_label, self.serialized_checkbox)`:

```python
# Status label for type-lookup feedback
self.type_status_label = QLabel("")
self.type_status_label.setStyleSheet(f"color: {Colors.get_text_secondary()}; font-style: italic;")
form_layout.addRow("", self.type_status_label)
```

#### B) Wire up type/subtype change → existing-type lookup

In `_setup_autocomplete`, add:

```python
self.type_edit.textChanged.connect(self._on_type_or_subtype_changed)
self.subtype_edit.textChanged.connect(self._on_type_or_subtype_changed)
```

#### C) Add `_on_type_or_subtype_changed` method

```python
def _on_type_or_subtype_changed(self):
    """Check if the current type/subtype combination already exists.

    If it does, lock the serialized checkbox to the existing type's state.
    """
    type_name = self.type_edit.text().strip()
    sub_type = self.subtype_edit.text().strip()

    if not type_name:
        self._unlock_serialized_checkbox()
        self.type_status_label.setText("")
        return

    try:
        existing = InventoryService.get_item_type_by_name_subtype(type_name, sub_type)
    except Exception as e:
        logger.warning(f"Type lookup failed: {e}")
        return

    if existing is not None:
        # Lock checkbox to existing type's state
        self.serialized_checkbox.setChecked(existing.is_serialized)
        self.serialized_checkbox.setEnabled(False)
        self.serialized_checkbox.setToolTip(tr("tooltip.serialized_locked"))
        if existing.is_serialized:
            self.type_status_label.setText(tr("message.type_exists_serialized"))
        else:
            self.type_status_label.setText(tr("message.type_exists_non_serialized"))
        # Trigger serialization logic to update dependent fields
        self._on_serialization_changed(self.serialized_checkbox.checkState())
    else:
        self._unlock_serialized_checkbox()
        self.type_status_label.setText("")

def _unlock_serialized_checkbox(self):
    """Re-enable the serialized checkbox for a new type."""
    self.serialized_checkbox.setEnabled(True)
    self.serialized_checkbox.setToolTip(tr("tooltip.has_serial"))
```

#### D) Update `_setup_serialization_logic`

Also connect `_on_type_or_subtype_changed` at init so it runs once on load (in case fields are pre-filled):

```python
def _setup_serialization_logic(self):
    self.serialized_checkbox.checkStateChanged.connect(self._on_serialization_changed)
    self._on_serialization_changed(self.serialized_checkbox.checkState())
    # Run initial type lookup (fields may be pre-filled)
    self._on_type_or_subtype_changed()
    logger.debug("Serialization logic configured")
```

---

## 5. Edit Dialog — `ui_entities/edit_item_dialog.py`

### Goal
The edit dialog must:
1. Show whether the item's type is serialized as a **read-only field** in the form.
2. Guard against type renames that would conflict with an existing type's `is_serialized` — detect conflict early (on type/subtype change) and show an error label, also block saving.

### Changes

#### A) Add read-only `is_serialized` display row in `_setup_ui`

After the `subtype_edit` row:

```python
# Serialized indicator (read-only)
is_serial_label = QLabel(tr("label.is_serialized"))
is_serial_label.setFont(label_font)
self._serialized_value_label = QLabel(
    tr("label.serialized_badge") if self._is_serialized else tr("label.non_serialized_badge")
)
# Color-code the badge
badge_color = "#2e7d32" if self._is_serialized else "#757575"   # green / grey
self._serialized_value_label.setStyleSheet(
    f"color: {badge_color}; font-weight: bold; padding: 2px 6px; "
    f"border: 1px solid {badge_color}; border-radius: 3px;"
)
self._serialized_value_label.setToolTip(tr("tooltip.serialized_locked"))
form_layout.addRow(is_serial_label, self._serialized_value_label)
```

#### B) Add a conflict-status label below the subtype row

```python
self.edit_type_status_label = QLabel("")
self.edit_type_status_label.setStyleSheet(f"color: #c62828; font-style: italic;")  # red
form_layout.addRow("", self.edit_type_status_label)
```

#### C) Wire up type/subtype changes

In `_setup_validators`, add:

```python
self.type_edit.textChanged.connect(self._on_edit_type_changed)
self.subtype_edit.textChanged.connect(self._on_edit_type_changed)
```

#### D) Add `_on_edit_type_changed` method

```python
def _on_edit_type_changed(self):
    """Warn if the new type name/subtype maps to a type with different is_serialized."""
    type_name = self.type_edit.text().strip()
    sub_type = self.subtype_edit.text().strip()

    if not type_name:
        self.edit_type_status_label.setText("")
        self._type_conflict = False
        return

    try:
        existing = InventoryService.get_item_type_by_name_subtype(type_name, sub_type)
    except Exception as e:
        logger.warning(f"Type lookup in edit dialog failed: {e}")
        return

    if existing is not None and existing.is_serialized != self._is_serialized:
        conflict_state = tr("label.serialized_badge") if existing.is_serialized else tr("label.non_serialized_badge")
        self.edit_type_status_label.setText(
            tr("error.serialized_conflict").format(name=type_name, state=conflict_state)
        )
        self._type_conflict = True
    else:
        self.edit_type_status_label.setText("")
        self._type_conflict = False
```

#### E) Initialise `_type_conflict` flag

In `__init__`, after `self._deleted_serial_numbers: List[str] = []`, add:

```python
self._type_conflict: bool = False
```

#### F) Block save on conflict

In `_on_save_clicked`, before the first validation block, add:

```python
if self._type_conflict:
    QMessageBox.warning(
        self,
        tr("message.validation_error"),
        self.edit_type_status_label.text(),
    )
    self.type_edit.setFocus()
    return
```

---

## 6. Details Dialog — `ui_entities/item_details_dialog.py`

Add a serialized row to the details form, right after the sub-type row:

```python
# Serialized
serialized_label = QLabel(tr("label.is_serialized"))
serialized_label.setFont(label_font)
is_ser = self._item.is_serialized
badge_text = tr("label.serialized_badge") if is_ser else tr("label.non_serialized_badge")
badge_color = "#2e7d32" if is_ser else "#757575"
serialized_value = QLabel(badge_text)
serialized_value.setFont(value_font)
serialized_value.setStyleSheet(
    f"color: {badge_color}; font-weight: bold; padding: 2px 6px; "
    f"border: 1px solid {badge_color}; border-radius: 3px;"
)
form_layout.addRow(serialized_label, serialized_value)
```

---

## 7. List-view Delegate — `ui_entities/inventory_delegate.py`

### Goal
Render a small colored pill/badge (`Serialized` | `Non-serialized`) in the list item,
visible at a glance.

### Changes

Open `inventory_delegate.py`. Locate the `paint` method.

After the item's main display text is drawn, add a badge in the top-right area of the item rect:

```python
# ── Serialized badge ────────────────────────────────────────────────────────
is_serialized = getattr(item_data, 'is_serialized', False)
badge_text = tr("label.serialized_badge") if is_serialized else tr("label.non_serialized_badge")
badge_color = QColor("#2e7d32") if is_serialized else QColor("#757575")   # green / grey

badge_font = QFont(painter.font())
badge_font.setPointSize(max(badge_font.pointSize() - 2, 7))
badge_font.setBold(True)
fm = QFontMetrics(badge_font)
badge_rect = fm.boundingRect(badge_text).adjusted(-4, -2, 4, 2)

# Position: right side, vertically centred in top half of row
badge_rect.moveRight(option.rect.right() - 8)
badge_rect.moveTop(option.rect.top() + 6)

# Draw pill background
painter.save()
painter.setFont(badge_font)
painter.setPen(Qt.PenStyle.NoPen)
painter.setBrush(badge_color)
painter.setRenderHint(QPainter.RenderHint.Antialiasing)
painter.drawRoundedRect(badge_rect, 3, 3)

# Draw text
painter.setPen(QColor("#ffffff"))
painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)
painter.restore()
```

**Required imports** (add if not present):

```python
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PyQt6.QtCore import Qt
from ui_entities.translations import tr
```

---

## 8. Required Alembic Migration

`is_serialized` column already exists in the model and presumably in the DB (it was added in a prior migration).
**No new migration is needed** unless you verify with:

```bash
cd C:\Users\chevi\PycharmProjects\AuditMagic
.venv\Scripts\activate
alembic current
alembic check
```

If `alembic check` shows a pending migration for `is_serialized`, generate and apply it:

```bash
alembic revision --autogenerate -m "ensure_is_serialized_not_null"
alembic upgrade head
```

---

## 9. Testing Checklist (Manual)

After implementing all changes, verify:

### 9.1 Create — New type (Add Dialog)
- [ ] Check "Serialized" → serial number field appears, quantity locked to 1. Save. Confirm `ItemType.is_serialized = True` in DB.
- [ ] Uncheck "Serialized" → serial field hidden, quantity editable. Save. Confirm `ItemType.is_serialized = False` in DB.
- [ ] Type a name that **already exists as serialized** → checkbox auto-checks, is disabled, status label appears.
- [ ] Type a name that **already exists as non-serialized** → checkbox auto-unchecks, is disabled, status label appears.
- [ ] Clear the name → checkbox re-enables.

### 9.2 Edit Dialog
- [ ] Open edit for a **serialized** item → green "Serialized" badge visible, read-only.
- [ ] Open edit for a **non-serialized** item → grey "Non-serialized" badge visible, read-only.
- [ ] Rename type to an existing type **with same `is_serialized`** → no conflict label. Save succeeds.
- [ ] Rename type to an existing type **with different `is_serialized`** → red conflict label appears. Save button shows error and is blocked.

### 9.3 Details Dialog
- [ ] Open details for serialized item → "Is Serialized: Serialized" row visible with green badge.
- [ ] Open details for non-serialized item → "Is Serialized: Non-serialized" row visible with grey badge.

### 9.4 List View
- [ ] Serialized items show green "Serialized" pill top-right.
- [ ] Non-serialized items show grey "Non-serialized" pill top-right.

### 9.5 Conflict via Service (edge case)
- [ ] Call `InventoryService.create_item(item_type_name="Laptop", is_serialized=True)` when "Laptop" already exists as non-serialized → `ValueError` raised with clear message, shown in QMessageBox.

---

## 10. Code-Quality Reminders

- Format all changed files with **Black** before committing.
- Add docstrings to every new public method.
- Use `tr()` for all user-visible strings — never hardcode English in the UI layer.
- Follow the existing `Colors.get_*()` helpers for theme-aware colors instead of hardcoding hex values where possible. The green/grey badge colors above are intentionally fixed (not theme-dependent) for accessibility contrast — this is acceptable.
- `is_serialized` must **never** be exposed as an editable field in any dialog once the type exists.

---

## 11. File Change Summary

| File | Change |
|------|--------|
| `repositories.py` | `get_or_create` conflict guard; `update` immutability guard; new `get_by_name_and_subtype` |
| `services.py` | New `get_item_type_by_name_subtype` method |
| `ui_entities/translations.py` | 8 new translation keys in both languages |
| `ui_entities/add_item_dialog.py` | Type-lookup hook, inline status label, `_on_type_or_subtype_changed`, `_unlock_serialized_checkbox` |
| `ui_entities/edit_item_dialog.py` | Read-only serialized badge, conflict detection label, `_on_edit_type_changed`, `_type_conflict` guard |
| `ui_entities/item_details_dialog.py` | Serialized badge row added to form |
| `ui_entities/inventory_delegate.py` | Serialized pill badge in `paint` |
