# Design: Add Item Merge on Duplicate Type+Location

**Date:** 2026-03-04

## Problem

`AddItemDialog` always calls `InventoryService.create_item()`, which creates a new DB row for every submission. If a non-serialized item of the same type+subtype already exists at the selected location, the user ends up with duplicate rows for the same type instead of consolidated stock.

## Decision

Before saving, check whether a non-serialized item of the same type+subtype already exists at the selected location. If it does, ask for confirmation. On "Yes", add quantity to the existing item. On "No", show an informational message and leave the dialog open.

## Flow

```
User clicks Add
  → validation passes
  → [non-serialized path]
      → InventoryService.find_non_serialized_at_location(type, sub_type, location_id)
          → item found?
              YES → QMessageBox.question "Same type exists. Add N unit(s) to existing stock?"
                      → Yes: InventoryService.add_quantity(item.id, qty, notes) → accept()
                      → No:  QMessageBox.information "Cannot create duplicate item." (stay open)
              NO  → InventoryService.create_item(...) → accept()  [unchanged]
```

Serialized path is unchanged — each serial number is unique, no merge logic applies.

## Changes

### `src/core/services.py`

Add one new static method to `InventoryService`:

```python
@staticmethod
def find_non_serialized_at_location(
    type_name: str, sub_type: str, location_id: int
) -> Optional[InventoryItem]:
    """Find an existing non-serialized item of the given type at a location.

    Returns the InventoryItem if found, None otherwise.
    Returns None if the type does not exist or is serialized.
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

### `src/ui/dialogs/add_item_dialog.py`

In `_on_add_clicked`, replace the non-serialized service call block with:

```python
else:
    location_id = self.location_combo.currentData()
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
            self.accept()
        else:
            QMessageBox.information(
                self,
                tr("dialog.add_item.duplicate.title"),
                tr("dialog.add_item.duplicate.message"),
            )
    else:
        self._result_item = InventoryService.create_item(
            item_type_name=item_type,
            item_sub_type=sub_type,
            quantity=quantity,
            is_serialized=False,
            location_id=location_id,
            transaction_notes=initial_notes or None,
        )
        self.accept()
```

### `src/ui/translations.py`

Add translation keys (Ukrainian + English fallback):

| Key | Ukrainian | English fallback |
|---|---|---|
| `dialog.add_item.merge.title` | "Тип вже існує" | "Type already exists" |
| `dialog.add_item.merge.prompt` | "Предмет цього типу вже є на цьому місці. Додати {quantity} од. до наявного запасу?" | "An item of this type already exists at this location. Add {quantity} unit(s) to existing stock?" |
| `dialog.add_item.duplicate.title` | "Дублікат неможливий" | "Cannot create duplicate" |
| `dialog.add_item.duplicate.message` | "Неможливо створити дублікат предмета." | "Cannot create duplicate item." |

## What does NOT change

- `create_item`, `create_or_merge_item`, `create_serialized_item` — untouched
- Serialized add flow — untouched
- `ItemRepository.find_non_serialized_at_location` — already exists, no changes needed
- `ItemTypeRepository.get_by_name_and_subtype` — already exists, no changes needed
