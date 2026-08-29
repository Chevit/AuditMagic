"""Tests for the audit trail's one rule — uses fresh_db fixture from conftest."""

from core import stock
from core.models import TransactionType
from core.repositories import (
    ItemRepository,
    ItemTypeRepository,
    LocationRepository,
    TransactionRepository,
)
from core.stock import Quantity, Serials, StockRef

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _loc(name="Warehouse"):
    return LocationRepository.create(name)


def _type(name="Desk", serialized=False):
    return ItemTypeRepository.get_or_create(name=name, is_serialized=serialized)


def _txs(kind=None, location_id=None):
    rows = TransactionRepository.get_recent(100)
    if kind is not None:
        rows = [t for t in rows if t.transaction_type == kind]
    if location_id is not None:
        rows = [t for t in rows if t.location_id == location_id]
    return sorted(rows, key=lambda t: t.id)


def _steps(kind=None, location_id=None):
    return [(t.quantity_before, t.quantity_after) for t in _txs(kind, location_id)]


# ─── The rule: before/after are the stock held at that location ───────────────


def test_bulk_add_and_remove_track_the_location():
    ref = StockRef(_type().id, _loc().id)
    stock.add(ref, Quantity(5))
    stock.add(ref, Quantity(3))
    stock.remove(ref, Quantity(2))
    assert _steps(TransactionType.ADD) == [(0, 5), (5, 8)]
    assert _steps(TransactionType.REMOVE) == [(8, 6)]


def test_serialized_add_counts_stock_at_that_location_only():
    """Previously counted every item of the type, at any location."""
    item_type = _type("Laptop", serialized=True)
    loc_a, loc_b = _loc("A"), _loc("B")
    stock.add(StockRef(item_type.id, loc_a.id), Serials(["A-1", "A-2"]))
    stock.add(StockRef(item_type.id, loc_b.id), Serials(["B-1"]))

    assert _steps(TransactionType.ADD, loc_a.id) == [(0, 1), (1, 2)]
    # B holds none of this type yet, however many A holds
    assert _steps(TransactionType.ADD, loc_b.id) == [(0, 1)]


def test_serialized_remove_counts_stock_at_that_location():
    """Previously recorded a flat 1 -> 0 for every serial removed."""
    item_type = _type("Laptop", serialized=True)
    ref = StockRef(item_type.id, _loc().id)
    stock.add(ref, Serials(["SN-1", "SN-2", "SN-3"]))
    stock.remove(ref, Serials(["SN-1", "SN-2"]))
    assert _steps(TransactionType.REMOVE) == [(3, 2), (2, 1)]


def test_deleting_all_stock_at_a_location_records_the_drop_to_zero():
    ref = StockRef(_type().id, _loc().id)
    stock.add(ref, Quantity(6))
    stock.delete(ref, "closing")
    assert _steps(TransactionType.REMOVE) == [(6, 0)]


def test_correction_records_both_sides():
    ref = StockRef(_type().id, _loc().id)
    stock.add(ref, Quantity(5))
    stock.set_quantity(ref, Quantity(2), "recount")
    edits = _txs(TransactionType.EDIT)
    assert [(t.quantity_before, t.quantity_after) for t in edits] == [(5, 2)]
    assert edits[0].quantity_change == 3


# ─── Transfers: a pair of records, each true for its own location ────────────


def test_bulk_transfer_records_both_sides():
    item_type = _type()
    loc_a, loc_b = _loc("A"), _loc("B")
    stock.add(StockRef(item_type.id, loc_a.id), Quantity(10))
    stock.add(StockRef(item_type.id, loc_b.id), Quantity(2))
    ItemRepository.transfer_item(
        item_id=ItemRepository.get_by_type_and_location(item_type.id, loc_a.id)[0].id,
        quantity=4,
        from_location_id=loc_a.id,
        to_location_id=loc_b.id,
    )
    assert _steps(TransactionType.TRANSFER, loc_a.id) == [(10, 6)]
    assert _steps(TransactionType.TRANSFER, loc_b.id) == [(2, 6)]


def test_full_bulk_transfer_empties_the_source():
    item_type = _type()
    loc_a, loc_b = _loc("A"), _loc("B")
    stock.add(StockRef(item_type.id, loc_a.id), Quantity(5))
    ItemRepository.transfer_item(
        item_id=ItemRepository.get_by_type_and_location(item_type.id, loc_a.id)[0].id,
        quantity=5,
        from_location_id=loc_a.id,
        to_location_id=loc_b.id,
    )
    assert _steps(TransactionType.TRANSFER, loc_a.id) == [(5, 0)]
    assert _steps(TransactionType.TRANSFER, loc_b.id) == [(0, 5)]


def test_serialized_transfer_steps_one_unit_at_a_time():
    item_type = _type("Laptop", serialized=True)
    loc_a, loc_b = _loc("A"), _loc("B")
    stock.add(StockRef(item_type.id, loc_a.id), Serials(["SN-1", "SN-2", "SN-3"]))
    ItemRepository.transfer_serialized_items(
        serial_numbers=["SN-1", "SN-2"],
        from_location_id=loc_a.id,
        to_location_id=loc_b.id,
    )
    assert _steps(TransactionType.TRANSFER, loc_a.id) == [(3, 2), (2, 1)]
    assert _steps(TransactionType.TRANSFER, loc_b.id) == [(0, 1), (1, 2)]


# ─── Type-level edits ─────────────────────────────────────────────────────────


def test_type_edit_moves_no_stock():
    item_type = _type()
    stock.add(StockRef(item_type.id, _loc().id), Quantity(5))
    ItemTypeRepository.update(item_type.id, name="Standing Desk", edit_reason="renamed")
    edit = _txs(TransactionType.EDIT)[0]
    assert (edit.quantity_before, edit.quantity_after, edit.quantity_change) == (
        0,
        0,
        0,
    )
    assert edit.location_id is None
    assert edit.notes == "renamed"


# ─── Every movement leaves a record ──────────────────────────────────────────


def test_every_stock_operation_is_recorded():
    item_type = _type()
    ref = StockRef(item_type.id, _loc().id)
    stock.add(ref, Quantity(5))
    stock.remove(ref, Quantity(1))
    stock.set_quantity(ref, Quantity(10))
    stock.delete(ref)
    kinds = [t.transaction_type for t in _txs()]
    assert kinds == [
        TransactionType.ADD,
        TransactionType.REMOVE,
        TransactionType.EDIT,
        TransactionType.REMOVE,
    ]
