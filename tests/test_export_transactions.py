"""Tests for TransactionService.get_for_export."""
import os
import sys
import pytest

os.environ.setdefault("AUDITMAGIC_DB", ":memory:")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.repositories import ItemTypeRepository, ItemRepository, LocationRepository
from core.services import TransactionService, InventoryService


def _make_location(name="Warehouse"):
    return LocationRepository.create(name)

def _make_type(name="Laptop", serialized=False):
    return ItemTypeRepository.get_or_create(name, "", serialized)

def _add_item(type_id, location_id, qty=5):
    return InventoryService.create_item(
        item_type_name="Laptop", item_sub_type="", quantity=qty,
        location_id=location_id, transaction_notes=""
    )


def test_get_for_export_returns_list():
    loc = _make_location()
    _add_item(_make_type().id, loc.id)
    result = TransactionService.get_for_export(location_id=loc.id)
    assert isinstance(result, list)
    assert len(result) >= 1


def test_get_for_export_dict_has_required_keys():
    loc = _make_location()
    _add_item(_make_type().id, loc.id)
    result = TransactionService.get_for_export(location_id=loc.id)
    keys = result[0].keys()
    for k in ("type", "item_type_id", "quantity_before", "quantity_after",
              "notes", "serial_number", "from_location_id", "to_location_id", "created_at"):
        assert k in keys, f"missing key: {k}"


def test_get_for_export_filters_by_location():
    loc_a = _make_location("A")
    loc_b = _make_location("B")
    InventoryService.create_item(
        item_type_name="Laptop", item_sub_type="", quantity=3,
        location_id=loc_a.id, transaction_notes=""
    )
    InventoryService.create_item(
        item_type_name="Monitor", item_sub_type="", quantity=2,
        location_id=loc_b.id, transaction_notes=""
    )
    result_a = TransactionService.get_for_export(location_id=loc_a.id)
    result_b = TransactionService.get_for_export(location_id=loc_b.id)
    # Each should only see their own location's transactions
    assert all(t["location_id"] == loc_a.id for t in result_a)
    assert all(t["location_id"] == loc_b.id for t in result_b)


def test_get_for_export_all_locations_when_none():
    loc_a = _make_location("A")
    loc_b = _make_location("B")
    InventoryService.create_item(
        item_type_name="Laptop", item_sub_type="", quantity=1,
        location_id=loc_a.id, transaction_notes=""
    )
    InventoryService.create_item(
        item_type_name="Monitor", item_sub_type="", quantity=1,
        location_id=loc_b.id, transaction_notes=""
    )
    result = TransactionService.get_for_export(location_id=None)
    assert len(result) >= 2


def test_get_for_export_filtered_by_type_ids():
    loc = _make_location()
    t1 = _make_type("Laptop")
    t2 = _make_type("Mouse")
    InventoryService.create_item(
        item_type_name="Laptop", item_sub_type="", quantity=1,
        location_id=loc.id, transaction_notes=""
    )
    InventoryService.create_item(
        item_type_name="Mouse", item_sub_type="", quantity=1,
        location_id=loc.id, transaction_notes=""
    )
    result = TransactionService.get_for_export(location_id=None, item_type_ids=[t1.id])
    assert all(t["item_type_id"] == t1.id for t in result)
