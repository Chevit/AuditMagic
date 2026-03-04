# Add Item Merge on Duplicate Type+Location Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** When adding a non-serialized item whose type+location already exists, show a confirmation popup and merge quantities rather than silently creating a duplicate DB row.

**Architecture:** One new `InventoryService.find_non_serialized_at_location` method wraps the existing repository lookup. `AddItemDialog._on_add_clicked` calls it before saving; on a match it shows a `QMessageBox.question`, routes to `add_quantity` on Yes or shows an informational error on No. New translation keys cover the two popup texts.

**Tech Stack:** Python 3.11+, PyQt6, SQLAlchemy, existing `ItemTypeRepository.get_by_name_and_subtype` + `ItemRepository.find_non_serialized_at_location` (both already exist).

---

### Task 1: Add `InventoryService.find_non_serialized_at_location`

**Files:**
- Modify: `src/core/services.py` (add method just before the `SearchService` class, around line 673)
- Test: `tests/test_services.py`

**Step 1: Write the failing tests**

Open `tests/test_services.py` and add this block at the end of the `# InventoryService: create` section (after the existing `test_create_or_merge_*` tests, before `# InventoryService: query`):

```python
# ─── InventoryService: find_non_serialized_at_location ───────────────────────

def test_find_non_serialized_at_location_returns_item():
    loc = _loc("Storage-A")
    _non_ser("Table", loc_id=loc.id, qty=3)
    result = InventoryService.find_non_serialized_at_location("Table", "", loc.id)
    assert result is not None
    assert result.quantity == 3


def test_find_non_serialized_at_location_returns_none_when_no_type():
    loc = _loc("Storage-B")
    result = InventoryService.find_non_serialized_at_location("NonExistent", "", loc.id)
    assert result is None


def test_find_non_serialized_at_location_returns_none_wrong_location():
    loc1 = _loc("Storage-C")
    loc2 = _loc("Storage-D")
    _non_ser("Chair", loc_id=loc1.id, qty=5)
    result = InventoryService.find_non_serialized_at_location("Chair", "", loc2.id)
    assert result is None


def test_find_non_serialized_at_location_returns_none_for_serialized_type():
    loc = _loc("Storage-E")
    _ser("Laptop", sn="SN-X01", loc_id=loc.id)
    result = InventoryService.find_non_serialized_at_location("Laptop", "", loc.id)
    assert result is None


def test_find_non_serialized_at_location_uses_subtype():
    loc = _loc("Storage-F")
    InventoryService.create_item("Monitor", item_sub_type="4K", quantity=2, location_id=loc.id)
    found = InventoryService.find_non_serialized_at_location("Monitor", "4K", loc.id)
    not_found = InventoryService.find_non_serialized_at_location("Monitor", "HD", loc.id)
    assert found is not None
    assert not_found is None
```

**Step 2: Run to verify they fail**

```bash
cd /c/Users/chevi/PycharmProjects/AuditMagic && .venv/Scripts/python.exe -m pytest tests/test_services.py -k "find_non_serialized" -v 2>&1 | tail -15
```

Expected: 5 FAILED with `AttributeError: type object 'InventoryService' has no attribute 'find_non_serialized_at_location'`

**Step 3: Add the method to `InventoryService`**

In `src/core/services.py`, find the last method of `InventoryService` (the `get_locations_for_type` method, which ends just before `class SearchService:` at line 675). Add the new method immediately before `class SearchService:`:

```python
    @staticmethod
    def find_non_serialized_at_location(
        type_name: str, sub_type: str, location_id: int
    ) -> Optional["InventoryItem"]:
        """Find an existing non-serialized item of the given type at a location.

        Used by AddItemDialog to detect a duplicate before prompting the user.

        Args:
            type_name: ItemType name.
            sub_type: ItemType sub_type (empty string if none).
            location_id: Location to search in.

        Returns:
            InventoryItem if a matching non-serialized item exists, else None.
        """
        item_type = ItemTypeRepository.get_by_name_and_subtype(type_name, sub_type)
        if item_type is None or item_type.is_serialized:
            return None
        db_item = ItemRepository.find_non_serialized_at_location(
            item_type_id=item_type.id,
            location_id=location_id,
        )
        if db_item is None:
            return None
        return InventoryItem.from_db_models(db_item, item_type)
```

Note: `InventoryItem` is already imported at line 15 of services.py. No new imports needed.

**Step 4: Run tests to verify they pass**

```bash
cd /c/Users/chevi/PycharmProjects/AuditMagic && .venv/Scripts/python.exe -m pytest tests/test_services.py -k "find_non_serialized" -v 2>&1 | tail -10
```

Expected: 5 PASSED

**Step 5: Run full suite**

```bash
cd /c/Users/chevi/PycharmProjects/AuditMagic && .venv/Scripts/python.exe -m pytest tests/ -v 2>&1 | tail -5
```

Expected: all tests pass (144+ passed).

**Step 6: Commit**

```bash
cd /c/Users/chevi/PycharmProjects/AuditMagic && git add src/core/services.py tests/test_services.py && git commit -m "feat: add InventoryService.find_non_serialized_at_location"
```

---

### Task 2: Add translation keys

**Files:**
- Modify: `src/ui/translations.py`

**Step 1: Add Ukrainian keys**

In `src/ui/translations.py`, find the Ukrainian `"dialog.add_item.title"` entry (around line 133). After `"dialog.add_item.header": "Додати новий елемент інвентарю",`, add:

```python
            "dialog.add_item.merge.title": "Тип вже існує",
            "dialog.add_item.merge.prompt": "Предмет цього типу вже є на цьому місці. Додати {quantity} од. до наявного запасу?",
            "dialog.add_item.duplicate.title": "Дублікат неможливий",
            "dialog.add_item.duplicate.message": "Неможливо створити дублікат предмета.",
```

**Step 2: Add English keys**

Find the English `"dialog.add_item.title"` entry (around line 363). After `"dialog.add_item.header": "Add New Inventory Item",`, add:

```python
            "dialog.add_item.merge.title": "Type already exists",
            "dialog.add_item.merge.prompt": "An item of this type already exists at this location. Add {quantity} unit(s) to existing stock?",
            "dialog.add_item.duplicate.title": "Cannot create duplicate",
            "dialog.add_item.duplicate.message": "Cannot create duplicate item.",
```

**Step 3: Run translation tests**

```bash
cd /c/Users/chevi/PycharmProjects/AuditMagic && .venv/Scripts/python.exe -m pytest tests/test_translations.py -v 2>&1 | tail -10
```

Expected: all pass.

**Step 4: Commit**

```bash
cd /c/Users/chevi/PycharmProjects/AuditMagic && git add src/ui/translations.py && git commit -m "feat: add merge/duplicate translation keys for AddItemDialog"
```

---

### Task 3: Update `AddItemDialog._on_add_clicked`

**Files:**
- Modify: `src/ui/dialogs/add_item_dialog.py:407-430`

**Step 1: Read the file**

Read `src/ui/dialogs/add_item_dialog.py` lines 407–432 to see the exact current state.

**Step 2: Replace the non-serialized service call block**

Find this block (lines ~411–430 in `_on_add_clicked`, in the `else:` branch after `if is_serialized:`):

```python
            else:
                self._result_item = InventoryService.create_item(
                    item_type_name=item_type,
                    item_sub_type=sub_type,
                    quantity=quantity,
                    is_serialized=False,
                    location_id=location_id,
                    transaction_notes=initial_notes or None,
                )
            logger.info(f"Item created successfully: id={self._result_item.id}")
            self.accept()
```

Replace with:

```python
            else:
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
                        self._result_item = InventoryService.add_quantity(
                            item_id=existing.id,
                            quantity=quantity,
                            notes=initial_notes,
                        )
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
                    transaction_notes=initial_notes or None,
                )
            logger.info(f"Item created successfully: id={self._result_item.id}")
            self.accept()
```

Key notes:
- `location_id` is already retrieved a few lines above (`location_id = self.location_combo.currentData()`) — do not re-add it
- The `return` after the `if existing is not None:` block ensures we don't fall through to `create_item`
- The serialized path (`if is_serialized:` branch above) is unchanged

**Step 3: Run full test suite**

```bash
cd /c/Users/chevi/PycharmProjects/AuditMagic && .venv/Scripts/python.exe -m pytest tests/ -v 2>&1 | tail -5
```

Expected: all tests pass.

**Step 4: Commit**

```bash
cd /c/Users/chevi/PycharmProjects/AuditMagic && git add src/ui/dialogs/add_item_dialog.py && git commit -m "feat: show merge confirmation in AddItemDialog when type+location exists"
```

---

### Task 4: Manual smoke test

Launch the app:

```bash
cd /c/Users/chevi/PycharmProjects/AuditMagic && .venv/Scripts/python.exe src/main.py
```

Verify the following scenarios:

1. **New type, new location** — Add an item with a brand new type. No popup. Item created normally.
2. **Existing type, same location** — Add the same type again at the same location.
   - Popup appears: "An item of this type already exists at this location. Add N unit(s) to existing stock?"
   - Click **Yes** → quantity is summed, single row in inventory.
   - Repeat, click **No** → info popup "Cannot create duplicate item." Dialog stays open.
3. **Existing type, different location** — Add the same type at a *different* location. No popup. New item created for that location.
4. **Serialized type** — Add a serialized item (serial number entered). No merge popup regardless. Item created normally.
