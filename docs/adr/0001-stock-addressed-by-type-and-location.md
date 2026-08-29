# Stock is addressed by (ItemType, Location), never by Item row id

Every change to Stock — add, remove, delete — is addressed by a `StockRef(item_type_id,
location_id)`. Callers never name an `Item.id`. This exists because the inventory list is
grouped by ItemType while the write path was addressed by row, leaving the UI to guess
which row a user meant: it picked `item_ids[0]`, the oldest row for that type, which under
"All Locations" belongs to whichever Location the type was first stocked at rather than the
one on screen.

For this addressing to be unambiguous, non-serialized Stock holds an invariant: **at most
one Item row per (ItemType, Location)**. It is enforced on every write in `core/stock.py`
and structurally by the `uq_item_type_location_bulk` partial unique index (migration
`f6g7h`), which also merged the duplicates existing databases already held.

## Considered Options

**Keep row addressing and have the UI choose better.** Rejected: the choice is a domain
rule about what a user's "add 5 to this row" means, and it was being made in four untested
Qt slots. Moving it behind the interface is the point.

**Let `edit_item` merge when a location change collides with existing Stock.** Settled by
the edit-path refactor: an edit cannot change a location at all. Moving stock is a
transfer, and `TransferDialog` is the only way to do it — it is also the only one that
supports partial moves. The collision guard this ADR originally described was a holding
position and has been removed; nothing can create a colliding location change now.

**Auto-merge duplicate rows when first touched.** Rejected: repairing data as a side effect
of an unrelated write is not something an audit trail can explain. Duplicates are tolerated
(summed for availability, written to the lowest-id row) until a migration repairs them in
one explicit place.

## Consequences

- Deleting Stock while filtered to a Location removes only that Location's Stock; the
  ItemType and all its Transactions survive. Deleting under "All Locations" still removes
  the whole ItemType, Transactions included.
- Search results identify Stock, not the row that was matched. Acting on a search hit acts
  on the `StockRef`.
