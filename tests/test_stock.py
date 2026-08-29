"""Tests for core.stock — uses fresh_db fixture from conftest."""

import pytest

from core import stock
from core.models import TransactionType
from core.repositories import (
    ItemRepository,
    ItemTypeRepository,
    LocationRepository,
    TransactionRepository,
)
from core.stock import (
    InsufficientStock,
    MovementMismatch,
    NoStockAtLocation,
    Quantity,
    Serials,
    StockError,
    StockRef,
    UnknownSerials,
)

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _loc(name="Warehouse"):
    return LocationRepository.create(name)


def _type(name="Desk", serialized=False):
    return ItemTypeRepository.get_or_create(name=name, is_serialized=serialized)


def _ref(item_type, location):
    return StockRef(item_type_id=item_type.id, location_id=location.id)


def _rows_at(ref):
    return ItemRepository.get_by_type_and_location(ref.item_type_id, ref.location_id)


def _removals(type_id):
    return [
        tx
        for tx in TransactionRepository.get_recent(50)
        if tx.item_type_id == type_id and tx.transaction_type == TransactionType.REMOVE
    ]


# ─── add ──────────────────────────────────────────────────────────────────────


def test_add_creates_row_when_ref_is_empty():
    ref = _ref(_type(), _loc())
    level = stock.add(ref, Quantity(5))
    assert level.quantity == 5
    assert len(_rows_at(ref)) == 1


def test_add_merges_into_existing_row():
    """The one-row-per-(ItemType, Location) invariant."""
    ref = _ref(_type(), _loc())
    stock.add(ref, Quantity(5))
    level = stock.add(ref, Quantity(3))
    assert level.quantity == 8
    assert len(_rows_at(ref)) == 1


def test_add_serials_creates_one_row_each():
    ref = _ref(_type("Laptop", serialized=True), _loc())
    level = stock.add(ref, Serials(["SN-1", "SN-2"]))
    assert level.quantity == 2
    assert level.serial_numbers == ("SN-1", "SN-2")
    assert len(_rows_at(ref)) == 2


def test_add_quantity_to_serialized_type_raises():
    ref = _ref(_type("Laptop", serialized=True), _loc())
    with pytest.raises(MovementMismatch):
        stock.add(ref, Quantity(3))


def test_add_serials_to_non_serialized_type_raises():
    ref = _ref(_type(), _loc())
    with pytest.raises(MovementMismatch):
        stock.add(ref, Serials(["SN-1"]))


def test_add_at_second_location_leaves_first_untouched():
    item_type = _type()
    ref_a = _ref(item_type, _loc("A"))
    ref_b = _ref(item_type, _loc("B"))
    stock.add(ref_a, Quantity(5))
    stock.add(ref_b, Quantity(2))
    assert stock.add(ref_a, Quantity(1)).quantity == 6
    assert len(_rows_at(ref_b)) == 1


def test_add_to_unknown_item_type_raises():
    with pytest.raises(StockError):
        stock.add(StockRef(item_type_id=9999, location_id=_loc().id), Quantity(1))


# ─── remove ───────────────────────────────────────────────────────────────────


def test_remove_reduces_quantity():
    ref = _ref(_type(), _loc())
    stock.add(ref, Quantity(10))
    level = stock.remove(ref, Quantity(4))
    assert level.quantity == 6


def test_remove_all_deletes_the_row_and_records_removal():
    """check_serial_or_quantity forbids a serial-less row at quantity 0, so
    emptying stock deletes the row — and must still leave an audit record."""
    item_type = _type()
    ref = _ref(item_type, _loc())
    stock.add(ref, Quantity(5))
    level = stock.remove(ref, Quantity(5))
    assert level.is_empty
    assert _rows_at(ref) == []
    assert [tx.quantity_change for tx in _removals(item_type.id)] == [5]


def test_remove_more_than_available_raises():
    ref = _ref(_type(), _loc())
    stock.add(ref, Quantity(3))
    with pytest.raises(InsufficientStock):
        stock.remove(ref, Quantity(4))


def test_remove_from_empty_ref_raises():
    ref = _ref(_type(), _loc())
    with pytest.raises(NoStockAtLocation):
        stock.remove(ref, Quantity(1))


def test_remove_serials_deletes_only_those_rows():
    ref = _ref(_type("Laptop", serialized=True), _loc())
    stock.add(ref, Serials(["SN-1", "SN-2", "SN-3"]))
    level = stock.remove(ref, Serials(["SN-2"]))
    assert level.serial_numbers == ("SN-1", "SN-3")


def test_remove_unknown_serial_raises():
    ref = _ref(_type("Laptop", serialized=True), _loc())
    stock.add(ref, Serials(["SN-1"]))
    with pytest.raises(UnknownSerials):
        stock.remove(ref, Serials(["SN-NOPE"]))


def test_remove_serial_held_at_another_location_raises():
    item_type = _type("Laptop", serialized=True)
    ref_a = _ref(item_type, _loc("A"))
    ref_b = _ref(item_type, _loc("B"))
    stock.add(ref_a, Serials(["SN-A"]))
    stock.add(ref_b, Serials(["SN-B"]))
    with pytest.raises(UnknownSerials):
        stock.remove(ref_b, Serials(["SN-A"]))


# ─── delete ───────────────────────────────────────────────────────────────────


def test_delete_removes_all_stock_at_ref():
    ref = _ref(_type(), _loc())
    stock.add(ref, Quantity(7))
    assert stock.delete(ref) == 7
    assert _rows_at(ref) == []


def test_delete_keeps_item_type_and_transactions():
    item_type = _type()
    ref = _ref(item_type, _loc())
    stock.add(ref, Quantity(4))
    before = len(TransactionRepository.get_recent(50))
    stock.delete(ref)
    assert ItemTypeRepository.get_by_id(item_type.id) is not None
    assert len(TransactionRepository.get_recent(50)) > before


def test_delete_is_scoped_to_one_location():
    item_type = _type()
    ref_a = _ref(item_type, _loc("A"))
    ref_b = _ref(item_type, _loc("B"))
    stock.add(ref_a, Quantity(5))
    stock.add(ref_b, Quantity(3))
    stock.delete(ref_a)
    assert _rows_at(ref_a) == []
    assert sum(row.quantity for row in _rows_at(ref_b)) == 3


def test_delete_serialized_stock_at_one_location():
    item_type = _type("Laptop", serialized=True)
    ref_a = _ref(item_type, _loc("A"))
    ref_b = _ref(item_type, _loc("B"))
    stock.add(ref_a, Serials(["SN-A1", "SN-A2"]))
    stock.add(ref_b, Serials(["SN-B1"]))
    assert stock.delete(ref_a) == 2
    assert _rows_at(ref_a) == []
    assert len(_rows_at(ref_b)) == 1


def test_delete_empty_ref_raises():
    ref = _ref(_type(), _loc())
    with pytest.raises(NoStockAtLocation):
        stock.delete(ref)


# ─── has_stock ────────────────────────────────────────────────────────────────


def test_has_stock():
    ref = _ref(_type(), _loc())
    assert stock.has_stock(ref) is False
    stock.add(ref, Quantity(1))
    assert stock.has_stock(ref) is True


# ─── Tolerance of pre-existing duplicate rows ─────────────────────────────────


def _with_duplicates(qty_a=4, qty_b=6):
    """A ref implemented by two rows — reachable in databases predating the
    invariant, via edit_item location changes."""
    item_type = _type()
    location = _loc()
    ref = _ref(item_type, location)
    ItemRepository.create(
        item_type_id=item_type.id, quantity=qty_a, location_id=location.id
    )
    ItemRepository.create(
        item_type_id=item_type.id, quantity=qty_b, location_id=location.id
    )
    return ref


def test_duplicate_rows_are_summed():
    ref = _with_duplicates(4, 6)
    assert len(_rows_at(ref)) == 2
    assert stock.remove(ref, Quantity(1)).quantity == 9


def test_removal_spills_across_duplicate_rows():
    ref = _with_duplicates(4, 6)
    level = stock.remove(ref, Quantity(7))
    assert level.quantity == 3
    assert len(_rows_at(ref)) == 1


def test_removal_exceeding_summed_duplicates_raises():
    ref = _with_duplicates(4, 6)
    with pytest.raises(InsufficientStock):
        stock.remove(ref, Quantity(11))


def test_add_writes_to_the_lowest_id_row():
    ref = _with_duplicates(4, 6)
    rows_before = sorted(_rows_at(ref), key=lambda r: r.id)
    stock.add(ref, Quantity(2))
    rows_after = {r.id: r.quantity for r in _rows_at(ref)}
    assert rows_after[rows_before[0].id] == 6
    assert rows_after[rows_before[1].id] == 6


# ─── Movement value objects ───────────────────────────────────────────────────


def test_quantity_must_be_positive():
    with pytest.raises(ValueError):
        Quantity(0)


def test_serials_must_not_be_empty():
    with pytest.raises(ValueError):
        Serials([])


def test_serials_must_not_contain_duplicates():
    with pytest.raises(ValueError):
        Serials(["SN-1", "SN-1"])


def test_stock_errors_are_value_errors():
    """The UI catches ValueError; these must keep flowing through it."""
    for error in (
        NoStockAtLocation,
        InsufficientStock,
        UnknownSerials,
        MovementMismatch,
    ):
        assert issubclass(error, ValueError)


# ─── The invariant guard on edit_item ─────────────────────────────────────────


def test_edit_item_refuses_a_colliding_location_change():
    item_type = _type()
    loc_a, loc_b = _loc("A"), _loc("B")
    moving = ItemRepository.create(
        item_type_id=item_type.id, quantity=2, location_id=loc_a.id
    )
    ItemRepository.create(item_type_id=item_type.id, quantity=3, location_id=loc_b.id)
    with pytest.raises(ValueError):
        ItemRepository.edit_item(
            item_id=moving.id,
            item_type_id=item_type.id,
            quantity=2,
            serial_number="",
            location_id=loc_b.id,
            condition="",
            edit_reason="move",
        )


def test_edit_item_allows_a_non_colliding_location_change():
    item_type = _type()
    loc_a, loc_b = _loc("A"), _loc("B")
    moving = ItemRepository.create(
        item_type_id=item_type.id, quantity=2, location_id=loc_a.id
    )
    updated = ItemRepository.edit_item(
        item_id=moving.id,
        item_type_id=item_type.id,
        quantity=2,
        serial_number="",
        location_id=loc_b.id,
        condition="",
        edit_reason="move",
    )
    assert updated.location_id == loc_b.id
