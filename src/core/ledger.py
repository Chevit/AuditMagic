"""The audit trail: the one place that decides what a Transaction records.

Every change to Stock leaves a Transaction behind. What `quantity_before` and
`quantity_after` mean was previously decided at each of a dozen construction sites,
which had drifted into three different answers for serialized stock — the global
count of a type, the count at one location, or a flat 1 -> 0.

One rule now: **quantity_before and quantity_after are the stock of that ItemType
held at the transaction's location, before and after the change.** Serialized rows
each hold quantity 1, so summing quantity gives the count either way, and serialized
and non-serialized stock need no special cases.

Every method records a change that has *already happened*: call it after the row
change and after a flush, and it derives the other side of the movement from the
resulting state.
"""

from typing import Optional

from sqlalchemy import func

from core.models import Item, Transaction, TransactionType


class Ledger:
    """Records changes to Stock against an open session."""

    def __init__(self, session):
        self._session = session

    # ── internals ────────────────────────────────────────────────────────────

    def _held(self, item_type_id: int, location_id: Optional[int]) -> int:
        """Stock of this ItemType at this Location, right now."""
        total = (
            self._session.query(func.coalesce(func.sum(Item.quantity), 0))
            .filter(
                Item.item_type_id == item_type_id,
                Item.location_id == location_id,
            )
            .scalar()
        )
        return int(total or 0)

    def _record(self, **fields) -> Transaction:
        transaction = Transaction(**fields)
        self._session.add(transaction)
        return transaction

    # ── interface ────────────────────────────────────────────────────────────

    def added(
        self,
        item_type_id: int,
        location_id: Optional[int],
        count: int,
        serial_number: str = None,
        notes: str = "",
    ) -> Transaction:
        """Record stock arriving. Call after the rows exist."""
        after = self._held(item_type_id, location_id)
        return self._record(
            item_type_id=item_type_id,
            transaction_type=TransactionType.ADD,
            quantity_change=count,
            quantity_before=after - count,
            quantity_after=after,
            serial_number=serial_number,
            notes=notes,
            location_id=location_id,
        )

    def removed(
        self,
        item_type_id: int,
        location_id: Optional[int],
        count: int,
        serial_number: str = None,
        notes: str = "",
    ) -> Transaction:
        """Record stock leaving. Call after the rows are gone."""
        after = self._held(item_type_id, location_id)
        return self._record(
            item_type_id=item_type_id,
            transaction_type=TransactionType.REMOVE,
            quantity_change=count,
            quantity_before=after + count,
            quantity_after=after,
            serial_number=serial_number,
            notes=notes,
            location_id=location_id,
        )

    def corrected(
        self,
        item_type_id: int,
        location_id: Optional[int],
        previous: int,
        notes: str = "",
    ) -> Transaction:
        """Record a correction to the count held. Call after the change."""
        after = self._held(item_type_id, location_id)
        return self._record(
            item_type_id=item_type_id,
            transaction_type=TransactionType.EDIT,
            quantity_change=abs(after - previous),
            quantity_before=previous,
            quantity_after=after,
            notes=notes,
            location_id=location_id,
        )

    def transferred(
        self,
        item_type_id: int,
        from_location_id: int,
        to_location_id: int,
        count: int,
        serial_number: str = None,
        notes: str = "",
    ) -> tuple:
        """Record stock moving between locations. Call after the move.

        Writes the pair of records a transfer needs: one at the source and one at
        the destination, each self-identifying by its own location_id.
        """
        source_after = self._held(item_type_id, from_location_id)
        dest_after = self._held(item_type_id, to_location_id)
        shared = dict(
            item_type_id=item_type_id,
            transaction_type=TransactionType.TRANSFER,
            quantity_change=count,
            serial_number=serial_number,
            notes=notes,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
        )
        source = self._record(
            quantity_before=source_after + count,
            quantity_after=source_after,
            location_id=from_location_id,
            **shared,
        )
        destination = self._record(
            quantity_before=dest_after - count,
            quantity_after=dest_after,
            location_id=to_location_id,
            **shared,
        )
        return source, destination

    def type_edited(self, item_type_id: int, notes: str) -> Transaction:
        """Record an edit to the ItemType itself. No stock moves, so no quantities."""
        return self._record(
            item_type_id=item_type_id,
            transaction_type=TransactionType.EDIT,
            quantity_change=0,
            quantity_before=0,
            quantity_after=0,
            notes=notes,
        )
