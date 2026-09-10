# Form Rules and Target Item Deepening

**Date:** 2026-09-10
**Status:** Approved

## Problem

Two clusters of duplicated logic, both trapped inside Qt classes where no test can reach
them.

### 1. Form validation is written three times

`AddItemDialog._on_add_clicked`, `EditItemDialog._on_save_clicked` and
`QuantityDialog._on_action_clicked` each contain the same shape: an `errors: List[str]`
accumulator, a sequence of calls into `ui/validators.py`, a `QMessageBox.warning` whose
body is `tr("message.fix_errors") + "\n\n" + "\n".join(f"• {e}" ...)`, and a hand-written
`if/elif` chain deciding which widget to focus.

The `QMessageBox` block is character-for-character identical in all three. The pure
helpers it calls (`validate_required_field`, `validate_length`,
`validate_positive_integer`) are already deep and easy to test — but they live in
`ui/validators.py`, which imports PyQt6 for its three `QValidator` subclasses, so nothing
can import them without pulling Qt in. No test currently does.

The debounced Serialization Conflict lookup is duplicated too:
`add_item_dialog.py:305-308` and `edit_item_dialog.py:359-362` are byte-identical apart
from one word of docstring.

The copies have drifted:

| | add | edit | quantity |
|---|---|---|---|
| empty quantity | `"Please enter a quantity value"` | `tr("message.quantity_required")` | `"Please enter a quantity value"` |
| non-numeric quantity | `"Quantity must be a valid number"` | `tr("message.quantity_invalid")` | `"Quantity must be a valid number"` |
| focus priority | type → serial → quantity | type → quantity | quantity |

Plus two more untranslated strings in `quantity_dialog.py`: the
`f"Requested: {quantity}, Available: {...}"` suffix (line 189) and the
`"Enter quantity (e.g., 5)..."` placeholder (line 90).

### 2. Target Item resolution is derived at three call sites, one of them wrong

`main_window.py` decides which Item an operation acts on, separately, in three handlers:

```python
main_window.py:506   item_id = item.item_ids[0] if item.item_ids else None   # guarded
main_window.py:664   target_item_id = item.item_ids[0] if is_grouped else item.id   # unguarded
main_window.py:713   target_item_id = item.item_ids[0] if is_grouped else item.id   # unguarded
```

The two unguarded copies raise `IndexError` when a Grouped Item has an empty `item_ids`.
`GroupedInventoryItem.id` (`inventory_item.py:221-223`) already guards this exact case —
the handlers bypass the DTO's own property to re-derive it by hand.

The same shape repeats for serial numbers (`main_window.py:633-637` and `:685-689`,
identical expressions under different variable names) and for the display name
(`main_window.py:664`, `:713`, `:733`) — the latter duplicating `display_name`, a
property both DTOs already have.

## Design

### `src/ui/form_rules.py` (new, Qt-free)

Holds one entry point per form plus the Serialization Conflict rule. Imports only
`typing`, `dataclasses`, `ui.translations` (itself Qt-free) and `core.logger`.

```python
@dataclass(frozen=True)
class FieldError:
    field: str      # Field key: "type", "quantity", "serial", "details",
                    # "notes", "edit_reason"
    message: str    # Already translated, ready to display
```

Entry points take explicit keyword arguments — plain values, no widgets:

```python
def add_item_rules(*, item_type, quantity_text, serial_number,
                   initial_notes, is_serialized) -> List[FieldError]
def edit_item_rules(*, item_type, quantity_text, serial_number, item_details,
                    edit_reason, is_serialized, remaining_serial_count) -> List[FieldError]
def quantity_rules(*, quantity_text, notes, is_add,
                   current_quantity) -> List[FieldError]
def has_serialization_conflict(*, existing_is_serialized: Optional[bool],
                               current_is_serialized: bool) -> bool
```

The three pure helpers move here from `ui/validators.py`. `validators.py` keeps only
`PositiveIntValidator`, `ItemTypeValidator` and `SerialNumberValidator` — the Qt classes.

Errors are returned in field order; the first error's `field` decides focus.

### `src/ui/dialogs/validation_feedback.py` (new, Qt)

The one Qt-side adapter, replacing three identical blocks:

```python
def show_validation_errors(parent, errors: List[FieldError],
                           widgets: Dict[str, QWidget], log_prefix: str) -> None
```

Shows the `QMessageBox`, logs `f"{log_prefix} validation failed: ..."`, then focuses
`widgets[errors[0].field]` — and calls `selectAll()` when that widget is a `QLineEdit`,
which is what `quantity_dialog` already does.

Each dialog supplies its own field-key → widget map. That map is the only validation
knowledge left in the dialogs.

### Target Item on the DTOs

Both `InventoryItem` and `GroupedInventoryItem` grow the same three members, so callers
stop branching on type:

| member | `InventoryItem` | `GroupedInventoryItem` |
|---|---|---|
| `target_item_id -> Optional[int]` | `self.id` | `item_ids[0] if item_ids else None` |
| `target_serial_numbers -> List[str]` | `[serial_number]` or `[]` | `serial_numbers` |
| `remaining_serial_numbers(deleted) -> List[str]` | filters the above | filters the above |

`main_window.py` handlers then read `item.target_item_id`, `item.target_serial_numbers`
and the existing `item.display_name`, and drop their local derivations. The DB lookup for
a serialized Grouped Item (`ItemRepository.search_by_serial`) stays in `main_window` — it
needs a session; only the choice of *which* serial to look up moves to the DTO.

## Drift Resolution

1. **Quantity messages** — `tr("message.quantity_required")` / `tr("message.quantity_invalid")`
   everywhere. Keys already exist; edit's behaviour wins.
2. **`Requested: / Available:`** — new translation key, `message.not_enough_quantity_detail`.
3. **`"Enter quantity (e.g., 5)..."`** — reuse the existing `placeholder.quantity` key.
4. **Focus** — first error in the returned list. Accepted change: for a serialized add
   with both quantity empty and serial missing, focus lands on quantity rather than
   serial. Unreachable in the UI, since checking "serialized" disables the quantity field
   and sets it to `"1"` (`add_item_dialog.py:287-288`).
5. **Logger prefixes** — preserved via `log_prefix` (`"Form"` / `"Edit form"` / `"Quantity"`).

## Files Changed

- `src/ui/form_rules.py` — new, Qt-free.
- `src/ui/dialogs/validation_feedback.py` — new, Qt adapter.
- `src/ui/validators.py` — the three pure helpers move out; `QValidator` subclasses stay.
- `src/ui/models/inventory_item.py` — Target Item members on both DTOs.
- `src/ui/main_window.py` — handlers use the DTO members; the `IndexError` goes.
- `src/ui/dialogs/add_item_dialog.py`, `edit_item_dialog.py`, `quantity_dialog.py` —
  validation blocks replaced by one rules call plus one adapter call.
- `src/ui/translations.py` — one new key.
- `tests/test_form_rules.py` — new.
- `tests/test_dto_models.py` — Target Item cases, including the empty-`item_ids`
  regression.
- `tests/conftest.py` — default `QT_QPA_PLATFORM` to `offscreen`.

## Out of Scope

- `InventoryService` injection into dialogs. One implementation, no second adapter, so
  the seam would be hypothetical. Dialogs keep the module-level import.
- The service/repository layering (rules living in `ItemRepository`), the `ExportService`
  interface, and the `styles.Colors` re-export layer. Separate work.
- Any change to `core/`.
