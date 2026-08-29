# Unit of Work Design

**Date:** 2026-08-29
**Scope:** Make a composed write one transaction, so a failure part-way through leaves
nothing behind. Terms in `CONTEXT.md`.

---

## Problem

Every repository method opens its own `session_scope`, so a service that composes two of
them produced two transactions. `InventoryService.create_serialized_item` gets or creates
the ItemType, then creates the Item — and if the second step fails, the first is already
committed:

```
create_serialized_item("Printer", serial_number="SN-1")   # SN-1 already exists
  -> ItemTypeRepository.get_or_create  -> COMMIT           # "Printer" persisted
  -> ItemRepository.create_serialized  -> IntegrityError
  => an ItemType named "Printer" with no items, and no way for the user to tell why
```

Reproduced before the change and confirmed fixed after. The same shape applied to
`create_item`, to `move_all_items_and_delete` (N transfers then a location deletion), and
to `stock.add` with several serial numbers, where a duplicate in the middle of a batch
left the earlier ones behind.

`stock.remove` had a milder version: the availability check and the write were separate
transactions, so what was checked was not necessarily what was removed.

---

## Solution

`db.unit_of_work()` — a context manager that owns a transaction and lends its session to
every repository call made inside it.

```python
with unit_of_work():
    item_type = ItemTypeRepository.get_or_create(...)
    ItemRepository.create(item_type_id=item_type.id, ...)   # same transaction
```

`session_scope()` becomes reentrant: inside an open unit of work it yields that session and
commits nothing, so the outermost scope owns the commit. The active session is held in a
`ContextVar`, so nesting works and concurrent contexts do not share one.

Wrapped: `create_item`, `create_serialized_item`, `move_all_items_and_delete`, and all four
`stock` operations.

### Why not pass the session as a parameter

The review candidate proposed threading a session through every repository method. That is
54 signatures and every call site, for a benefit that lands on five composed writes, and
each converted signature is a chance to introduce a subtle error. `unit_of_work` puts the
transaction boundary where the decision belongs — the service — without touching a single
repository signature.

The trade-off, stated plainly: the session is ambient rather than an accepted dependency,
so a repository method's transaction membership is not visible in its signature. What is
gained is that the boundary is declared by the code that knows the operation, and that
repository methods keep working unchanged whether or not one is open.

---

## Changes

### `src/core/db.py`

- `_active_session: ContextVar` — the innermost open unit of work's session.
- `session_scope()` joins it when present; unchanged otherwise.
- `unit_of_work()` — opens the session, commits on success, rolls back on any exception,
  and nests by joining.

### `src/core/services.py`, `src/core/stock.py`

Composed writes wrapped. `stock.remove` now checks availability and writes inside one
transaction.

---

## Out of Scope

- Threading sessions through repository signatures.
- The remaining read paths that issue several queries — they are not writes, so a torn read
  is not a correctness problem here.
