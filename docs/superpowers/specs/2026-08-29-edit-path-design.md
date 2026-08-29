# Edit Path Design

**Date:** 2026-08-29
**Scope:** Split the edit path into the three separate changes it actually makes, and stop
it from being a second, silent way to move stock. Follows
`2026-08-29-stock-addressing-design.md`; terms in `CONTEXT.md`.

---

## Problem

`_on_edit_item` carried the same defect the add/remove/delete paths did, plus two of its
own.

1. **Arbitrary row.** For a grouped non-serialized row it edited `item_ids[0]` — the oldest
   row of the type — and wrote the new *quantity* to it. Under "All Locations" that is
   whichever location the type was first stocked at. For a grouped serialized row it
   resolved the first remaining serial to a row and put type-level edits on it.

2. **Renaming reassigned one row.** `edit_item` passed the new name to
   `ItemTypeRepository.get_or_create` and set that row's `item_type_id` to the result, so
   renaming "Desk" to "Chair" on a grouped row moved one arbitrary row into Chair and left
   the rest as Desk. Nothing in the UI offers this, and the dialog's own conflict check
   blocks the case it half-supports.

3. **A second way to move stock.** The dialog had a location dropdown. Changing it wrote
   `item.location_id` directly with a single EDIT transaction — no TRANSFER record, no
   from/to, and no merge at the destination. `TransferDialog` already moves stock properly,
   including partial quantities. Two mechanisms, one of them wrong.

The serial-number field was also mis-conditioned: `if not self._is_grouped and not
self._is_serialized` showed it for **non-serialized** rows, where a serial number is
invalid under `check_serial_or_quantity`.

---

## Solution

An edit is three separate changes, each going to the thing it belongs to:

| What the user changed | Where it goes |
|---|---|
| name, sub_type, details | the **ItemType** — every Item of it follows |
| quantity | `stock.set_quantity(ref, Quantity(n))` at the ref on screen |
| removed serial numbers | `stock.remove(ref, Serials([...]))` |
| location | **nothing** — moving stock is a transfer |

Edit is an edit; transfer is a transfer. `TransferDialog` is the single way to move stock
and the only one that does partial moves, so the location dropdown comes out. The list's
context menu already offers Transfer.

---

## Changes

### `src/core/stock.py`

`set_quantity(ref, Quantity, notes) -> StockLevel` — set countable stock at a ref exactly,
recording an EDIT transaction. `add` and `remove` express a movement; this expresses a
correction. Raises `MovementMismatch` for a serialized type and `NoStockAtLocation` for an
empty ref.

### `src/core/repositories.py`

`ItemRepository.edit_item(item_id, item_type_id, quantity, serial_number, location_id,
condition, edit_reason)` becomes `set_quantity(item_id, quantity, edit_reason)`. Type,
location and serial no longer change through it, so the collision guard added with the
stock module is deleted: nothing can create a colliding location change any more.

`ItemTypeRepository.update` gains `edit_reason`, recording an EDIT transaction against the
type (no stock moves, so the quantities are zero), and raises if the new name/sub_type is
already taken by another type — previously an `IntegrityError` from
`uq_item_type_name_subtype`.

### `src/core/services.py`

`InventoryService.edit_item` is replaced by `rename_item_type(type_id, name, sub_type,
details, edit_reason)`.

### `src/ui/dialogs/edit_item_dialog.py`

- Location dropdown → read-only label.
- Serial number field → read-only label, shown for a single serialized unit. A unit's
  serial is its identity; correcting one means removing and re-adding the unit, which
  leaves an audit trail.
- Quantity is read-only for a multi-location group: there is no single total to set.

### `src/ui/main_window.py`

`_on_edit_item` calls `rename_item_type`, then `stock.set_quantity` at the ref, then
`stock.remove` for deleted serials grouped by location. No row lookup, no `is_grouped`
branch.

---

## Out of Scope

- Merging one ItemType into another. Removed here as an accident of `get_or_create`; if it
  is wanted it should be an explicit action.
- Editing a unit's condition — not exposed by the dialog today.
- Candidates #2 (ledger) and #4 (session seam).
