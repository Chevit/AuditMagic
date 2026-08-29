# Stock Addressing Design

**Date:** 2026-08-29
**Scope:** Introduce `core/stock.py`, a module that addresses inventory changes by
`StockRef(item_type_id, location_id)` instead of `Item.id`, and move the add-quantity,
remove-quantity and delete paths onto it. Terms used here are defined in `CONTEXT.md`;
the addressing decision is recorded in `docs/adr/0001-stock-addressed-by-type-and-location.md`.

---

## Problem

The inventory list is grouped by ItemType (`GroupedInventoryItem`), but every write is
addressed by `Item.id`. The gap is closed inside four Qt slots in `main_window.py`, which
pick the row themselves:

```python
target_item_id = item.item_ids[0] if is_grouped else item.id
```

`_get_types_with_items` orders by `ItemType.name, sub_type, Item.serial_number, Item.id`,
so `item_ids[0]` is the **oldest** row of that type. When the location filter is "All
Locations", that row belongs to whichever Location the type was first stocked at — not the
one the user is looking at. Adding 5 units to a row showing 12 at Warehouse B can add them
at Warehouse A.

Three further defects sit on the same paths:

1. **`_on_delete_item`** calls `delete_item_type` for any grouped row, deleting every
   Location's Stock — and every Transaction for that type — while the user is filtered to
   one Location.
2. **`ItemRepository.delete:825`** records no Transaction, so deleting non-serialized Stock
   makes it vanish with no audit record. Its docstring claims to delete "all its
   transactions", which is impossible: `Transaction` has no `item_id`, only `item_type_id`.
3. **`main_window.py:473`** imports `ItemRepository` directly, reaching past the service
   seam to resolve a serial number to a row id.

None of the four slots is covered by a test.

---

## Solution

A new module, `core/stock.py`, owning the write path for Stock. Callers name *what stock*;
the module decides which Item rows implement it.

```python
StockRef(item_type_id: int, location_id: int)

Quantity(count: int)          # Movement for non-serialized Stock
Serials(numbers: list[str])   # Movement for serialized Stock

add(ref, movement, notes="") -> StockLevel
remove(ref, movement, notes="") -> StockLevel
delete(ref, notes="") -> int          # removes all Stock at this ref, returns units removed
has_stock(ref) -> bool

StockLevel(ref, quantity: int, serial_numbers: list[str])
```

The serialized/non-serialized branch lives inside the implementation. `core/stock.py`
imports no UI DTOs — unlike `services.py`, which imports `ui.models.inventory_item`.

**Writes go through the existing `ItemRepository`.** The session-per-repository-call
structure and the scattered `Transaction` construction are separate problems; this change
moves addressing only.

### Errors

Defined in `core/stock.py`, all subclassing `ValueError` so existing `except ValueError`
blocks in the UI keep working unchanged:

- `NoStockAtLocation` — the ref holds nothing
- `InsufficientStock` — removal exceeds what the ref holds
- `UnknownSerials` — one or more serials are not at that Location

Tests assert on the exception type. Message text is translated, so asserting on strings
would be asserting on `translations.py`.

### The one-row invariant

Non-serialized Stock holds **at most one Item row per (ItemType, Location)**. `add`
enforces it: it merges into the existing row rather than creating a second.

Duplicates are reachable in existing databases via two paths:

- `ItemRepository.edit_item:763` sets `item.location_id` with no merge check.
- `InventoryService.create_or_merge_item` with `location_id=None` falls back to
  `find_by_type_and_serial(type, None)`, merging into a serial-less row at *any* Location.

Until the migration lands, `stock` **tolerates** duplicates: it sums across all rows for a
ref when checking availability, and writes to the lowest-id row. It does not silently
repair them.

---

## Changes

### `src/core/stock.py` (new)

The module above. Internally:

- `add` with `Quantity`: find the row for the ref; `ItemRepository.add_quantity` if it
  exists, `ItemRepository.create` otherwise.
- `add` with `Serials`: `ItemRepository.create_serialized` per serial.
- `remove` with `Quantity`: `ItemRepository.remove_quantity` on the canonical row, after
  checking the summed availability across the ref.
- `remove` with `Serials`: `ItemRepository.delete_by_serial_numbers`, after checking every
  serial is at that Location.
- `delete`: writes a REMOVE Transaction for the Stock at the ref, then deletes its rows —
  the `delete_by_serial_numbers` pattern extended to non-serialized Stock. The ItemType and
  all Transactions survive.

### `src/core/repositories.py`

`edit_item` gains a guard: a location change that would collide with existing non-serialized
Stock of the same type raises rather than creating a duplicate. This is a holding position,
not the edit-path design — see the ADR.

Fix the stale `ItemRepository.delete` docstring (it does not delete Transactions).

### `src/ui/main_window.py`

`_on_add_quantity`, `_on_remove_quantity`, `_on_delete_item` build a `StockRef` and call
`stock`. The `isinstance(item, GroupedInventoryItem)` branch and the `item_ids[0]` pick go
away, as does the direct `ItemRepository` import.

`_on_delete_item` gains two confirmation messages: Stock at one Location versus the whole
ItemType with its Transactions.

`_on_edit_item` is unchanged.

### `src/ui/dialogs/quantity_dialog.py`

Add a location combo, matching `AddSerialNumberDialog`:

- **Add**: all Locations, pre-selected to the current Location.
- **Remove**: only Locations holding Stock of this type, via the existing
  `InventoryService.get_locations_for_type` — the same rule `TransferDialog` uses.

Disabled when only one Location is possible.

### `src/ui/dialogs/add_item_dialog.py`

The merge prompt stays, as a typo check. It calls `stock.has_stock(ref)` for the boolean
and `stock.add(ref, Quantity(n))` on Yes, instead of resolving a row id through
`find_non_serialized_at_location` and calling `add_quantity(existing.id)`.

### `src/core/services.py`

Remove `add_quantity`, `remove_quantity`, `delete_item`, and `create_or_merge_item` — the
last has no production callers, only five tests. Narrow `find_non_serialized_at_location`
to `stock.has_stock`. `delete_item_type` stays; it backs the "All Locations" delete.

### Tests

- Rewrite `test_services.py:257,264` (add/remove by `item.id`) and `:67-108`
  (`create_or_merge_item`) against `stock`. They are replaced, not kept alongside.
- `test_repositories.py:317-349` stay — they cover the row primitive, which `stock` still
  uses.
- New: multi-location refs, the merge invariant, tolerance of pre-existing duplicates,
  location-scoped delete preserving Transactions, REMOVE recorded for non-serialized
  deletion, `edit_item`'s collision guard, and each error type.

---

## Out of Scope

- **The edit path.** `_on_edit_item` conflates editing an ItemType with editing an Item and
  picks an arbitrary row to carry both. Deferred; `edit_item` gets only the collision guard.
- **The Alembic migration** adding a partial unique index on `(item_type_id, location_id)`
  where `serial_number IS NULL`, and merging existing duplicates. Follows once the module
  enforces the invariant.
- **The session seam.** Repositories keep opening their own `session_scope`, so a composed
  write is still several transactions.
- **Transaction construction**, still hand-built at ten sites in `repositories.py`.

---

## Delivery

1. `docs:` this spec, `CONTEXT.md`, ADR 0001.
2. `feat:` `core/stock.py` and its tests. Nothing calls it yet.
3. `feat:` UI rewiring — the three slots, `QuantityDialog`, `AddItemDialog`.
4. `refactor:` remove the superseded service methods and rewrite their tests.
