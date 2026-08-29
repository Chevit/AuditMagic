# Ledger Design

**Date:** 2026-08-29
**Scope:** Concentrate Transaction construction — twelve hand-written sites across ten
repository methods — into one module that decides what an audit record says. Terms in
`CONTEXT.md`.

---

## Problem

Every write path built its own `Transaction(...)`, each re-deciding what
`quantity_before` and `quantity_after` mean. They had drifted into three different answers
for serialized stock:

| Path | `quantity_before/after` meant |
|---|---|
| `create_serialized` | count of that ItemType **everywhere** |
| `transfer_serialized_items` | count of that ItemType **at that location** |
| `delete_by_serial_numbers` | a flat `1 -> 0`, per unit |

CLAUDE.md documented only the first. So a serialized type's history read as a sequence of
numbers that did not connect: adding a third unit recorded `2 -> 3` counting every
location, removing it recorded `1 -> 0`, and moving it recorded the count at one location.
Nothing in the code held the rule; the rule lived in prose that two of the three sites
contradicted.

`transfer_serialized_items` additionally kept `src_counts` / `dest_counts` dictionaries and
decremented them by hand as it looped, to fake the stepping the database could have told it.

---

## Solution

`core/ledger.py`. One rule, stated once and applied everywhere:

> **`quantity_before` and `quantity_after` are the stock of that ItemType held at the
> transaction's location, before and after the change.**

Serialized rows each hold `quantity = 1`, so summing `quantity` gives a count for
serialized stock and a total for non-serialized stock. One formula, no special cases —
that is where the depth is.

```python
Ledger(session).added(item_type_id, location_id, count, serial_number=None, notes="")
                .removed(...)
                .corrected(item_type_id, location_id, previous, notes="")
                .transferred(item_type_id, from_location_id, to_location_id, count, ...)
                .type_edited(item_type_id, notes)
```

Callers name **what happened**. They no longer compute, or even pass, the before/after
numbers — the ledger reads the resulting state and derives the other side of the movement.

**Ordering is part of the interface:** every method records a change that has already
happened. Call it after the row change and after a flush.

`transferred` writes the pair of records a transfer needs, each self-identifying by its own
`location_id`, so the running counters disappear.

---

## Changes

### `src/core/ledger.py` (new)

The module above.

### `src/core/repositories.py`

All twelve construction sites become ledger calls; `Transaction` is no longer constructed
anywhere in the file. Consequences:

- `create_serialized` no longer counts existing items itself.
- `transfer_serialized_items` loses `src_counts` / `dest_counts` and their hand-stepping.
- `transfer_item` loses `src_qty_before` / `dest_qty_before` and the conditional that
  decided what the source's `quantity_after` should be for a full transfer.
- `delete_non_serialized` and `delete_by_serial_numbers` delete the row first and record
  after. This is safe — `Transaction` has no FK to `Item`, so nothing cascades — and it
  keeps one ordering rule for every caller.

---

## What changes in the data

Two paths now record different numbers than before, both moving *onto* the rule the
majority already followed:

- **Adding a serialized unit** records the count at that location, not across all
  locations. Adding the first laptop at Warehouse B now reads `0 -> 1` even when Warehouse
  A holds ten.
- **Removing a serialized unit** records the count at that location falling by one, not
  `1 -> 0`. Removing two of three units at a location reads `3 -> 2`, `2 -> 1`.

Existing rows are not rewritten: history recorded under the old code keeps whatever it
said. The fields are display-only (transactions dialogs and the Excel export), so nothing
computes against them.

---

## Out of Scope

- Backfilling existing Transaction rows to the new rule.
- Candidate #4, the session seam. `Ledger` takes the session it is given, so it is ready
  for that change without needing it.
