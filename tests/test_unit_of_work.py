"""Tests for transaction atomicity — uses fresh_db fixture from conftest."""

import pytest

from core import stock
from core.db import unit_of_work
from core.repositories import ItemRepository, ItemTypeRepository, LocationRepository
from core.services import InventoryService
from core.stock import Quantity, Serials, StockRef

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _loc(name="Warehouse"):
    return LocationRepository.create(name)


def _held(item_type_id, location_id):
    rows = ItemRepository.get_by_type_and_location(item_type_id, location_id)
    return sum(row.quantity for row in rows)


# ─── Composed writes are one transaction ─────────────────────────────────────


def test_failed_serialized_create_leaves_no_orphan_type():
    """get_or_create then create_serialized: the type must not outlive the failure."""
    loc = _loc()
    InventoryService.create_serialized_item(
        "Laptop", serial_number="SN-1", location_id=loc.id
    )
    with pytest.raises(Exception):
        # New type, serial already taken — the item insert fails after the type
        InventoryService.create_serialized_item(
            "Printer", serial_number="SN-1", location_id=loc.id
        )
    assert ItemTypeRepository.get_by_name_and_subtype("Printer") is None


def test_failed_create_item_leaves_no_orphan_type():
    loc = _loc()
    with pytest.raises(Exception):
        # A serialized type cannot be created through the non-serialized path
        InventoryService.create_item(
            item_type_name="Ghost",
            quantity=1,
            is_serialized=True,
            serial_number=None,
            location_id=loc.id,
        )
    assert ItemTypeRepository.get_by_name_and_subtype("Ghost") is None


def test_a_failed_serial_batch_adds_none_of_it():
    """A duplicate part-way through a batch must not leave the earlier serials."""
    item_type = ItemTypeRepository.get_or_create(name="Laptop", is_serialized=True)
    loc_a, loc_b = _loc("A"), _loc("B")
    stock.add(StockRef(item_type.id, loc_a.id), Serials(["SN-9"]))

    with pytest.raises(Exception):
        stock.add(StockRef(item_type.id, loc_b.id), Serials(["SN-1", "SN-2", "SN-9"]))

    assert _held(item_type.id, loc_b.id) == 0


def test_successful_serial_batch_still_lands():
    item_type = ItemTypeRepository.get_or_create(name="Laptop", is_serialized=True)
    ref = StockRef(item_type.id, _loc().id)
    assert stock.add(ref, Serials(["SN-1", "SN-2"])).quantity == 2


# ─── unit_of_work itself ─────────────────────────────────────────────────────


def test_unit_of_work_rolls_back_on_error():
    loc = _loc()
    item_type = ItemTypeRepository.get_or_create(name="Desk", is_serialized=False)
    with pytest.raises(RuntimeError):
        with unit_of_work():
            ItemRepository.create(
                item_type_id=item_type.id, quantity=5, location_id=loc.id
            )
            raise RuntimeError("something went wrong afterwards")
    assert _held(item_type.id, loc.id) == 0


def test_unit_of_work_commits_on_success():
    loc = _loc()
    item_type = ItemTypeRepository.get_or_create(name="Desk", is_serialized=False)
    with unit_of_work():
        ItemRepository.create(item_type_id=item_type.id, quantity=5, location_id=loc.id)
    assert _held(item_type.id, loc.id) == 5


def test_nested_units_join_the_outer_transaction():
    """A nested unit must not commit early — the outer failure still rolls back."""
    loc = _loc()
    item_type = ItemTypeRepository.get_or_create(name="Desk", is_serialized=False)
    with pytest.raises(RuntimeError):
        with unit_of_work():
            stock.add(StockRef(item_type.id, loc.id), Quantity(4))
            raise RuntimeError("outer failure after a nested unit of work")
    assert _held(item_type.id, loc.id) == 0


def test_repository_calls_outside_a_unit_still_commit():
    """The default path is unchanged: one call, one transaction."""
    loc = _loc()
    item_type = ItemTypeRepository.get_or_create(name="Desk", is_serialized=False)
    ItemRepository.create(item_type_id=item_type.id, quantity=3, location_id=loc.id)
    assert _held(item_type.id, loc.id) == 3
