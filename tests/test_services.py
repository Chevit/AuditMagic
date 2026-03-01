"""Tests for service layer — uses fresh_db fixture from conftest."""
import pytest
from datetime import datetime, timedelta, timezone
from core.services import InventoryService, SearchService, TransactionService, _transaction_to_dict
from core.repositories import LocationRepository, ItemTypeRepository, ItemRepository
from core.models import TransactionType, Transaction


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _loc(name="Warehouse"):
    return LocationRepository.create(name)


def _non_ser(name="Desk", loc_id=None, qty=5):
    return InventoryService.create_item(
        item_type_name=name, is_serialized=False,
        quantity=qty, location_id=loc_id,
    )


def _ser(name="Laptop", sn="SN-001", loc_id=None):
    return InventoryService.create_serialized_item(
        item_type_name=name, serial_number=sn, location_id=loc_id,
    )


# ─── InventoryService: create ─────────────────────────────────────────────────

def test_create_item_returns_inventory_item():
    from ui.models.inventory_item import InventoryItem
    loc = _loc()
    item = _non_ser(loc_id=loc.id)
    assert isinstance(item, InventoryItem)
    assert item.item_type_name == "Desk"
    assert item.quantity == 5


def test_create_serialized_item_returns_inventory_item():
    from ui.models.inventory_item import InventoryItem
    loc = _loc()
    item = _ser(loc_id=loc.id)
    assert isinstance(item, InventoryItem)
    assert item.serial_number == "SN-001"
    assert item.is_serialized is True


def test_create_serialized_duplicate_serial_raises():
    loc = _loc()
    _ser(loc_id=loc.id, sn="DUP-001")
    with pytest.raises(Exception):
        _ser(loc_id=loc.id, sn="DUP-001")


def test_create_or_merge_new_item_not_merged():
    loc = _loc()
    item, merged = InventoryService.create_or_merge_item(
        item_type_name="Chair", quantity=3, location_id=loc.id,
    )
    assert merged is False
    assert item.quantity == 3


def test_create_or_merge_existing_merges():
    loc = _loc()
    InventoryService.create_or_merge_item(
        item_type_name="Chair", quantity=3, location_id=loc.id,
    )
    item2, merged = InventoryService.create_or_merge_item(
        item_type_name="Chair", quantity=4, location_id=loc.id,
    )
    assert merged is True
    assert item2.quantity == 7


def test_create_or_merge_serialized_always_new():
    loc = _loc()
    item1, m1 = InventoryService.create_or_merge_item(
        item_type_name="Laptop", quantity=1, is_serialized=True,
        serial_number="SN-A", location_id=loc.id,
    )
    item2, m2 = InventoryService.create_or_merge_item(
        item_type_name="Laptop", quantity=1, is_serialized=True,
        serial_number="SN-B", location_id=loc.id,
    )
    assert m1 is False
    assert m2 is False
    assert item1.serial_number != item2.serial_number


# ─── InventoryService: query ──────────────────────────────────────────────────

def test_get_item_found():
    loc = _loc()
    created = _non_ser(loc_id=loc.id)
    found = InventoryService.get_item(created.id)
    assert found is not None
    assert found.id == created.id


def test_get_item_not_found():
    assert InventoryService.get_item(9999) is None


def test_get_all_items():
    loc = _loc()
    _non_ser("A", loc_id=loc.id)
    _non_ser("B", loc_id=loc.id)
    items = InventoryService.get_all_items()
    assert len(items) >= 2


def test_get_all_items_grouped():
    from ui.models.inventory_item import GroupedInventoryItem
    loc = _loc()
    _non_ser("Desk", loc_id=loc.id, qty=3)
    _non_ser("Chair", loc_id=loc.id, qty=7)
    grouped = InventoryService.get_all_items_grouped()
    assert all(isinstance(g, GroupedInventoryItem) for g in grouped)
    names = {g.item_type_name for g in grouped}
    assert "Desk" in names
    assert "Chair" in names


def test_get_all_items_grouped_location_filter():
    loc_a = _loc("A")
    loc_b = _loc("B")
    _non_ser("DeskA", loc_id=loc_a.id)
    _non_ser("DeskB", loc_id=loc_b.id)
    grouped_a = InventoryService.get_all_items_grouped(location_id=loc_a.id)
    names = {g.item_type_name for g in grouped_a}
    assert "DeskA" in names
    assert "DeskB" not in names


def test_get_serialized_items_grouped_only_serialized():
    from ui.models.inventory_item import GroupedInventoryItem
    loc = _loc()
    _ser("Laptop", sn="SN-001", loc_id=loc.id)
    _non_ser("Desk", loc_id=loc.id)
    grouped = InventoryService.get_serialized_items_grouped()
    names = {g.item_type_name for g in grouped}
    assert "Laptop" in names
    assert "Desk" not in names


def test_get_type_items_at_location():
    loc = _loc()
    t = ItemTypeRepository.get_or_create("Laptop", "", True)
    ItemRepository.create_serialized(t.id, "SN-X", loc.id)
    ItemRepository.create_serialized(t.id, "SN-Y", loc.id)
    qty, serials, ids = InventoryService.get_type_items_at_location(t.id, loc.id)
    assert qty == 2
    assert set(serials) == {"SN-X", "SN-Y"}
    assert len(ids) == 2


def test_get_item_type_display_names_with_subtype():
    ItemTypeRepository.get_or_create("Laptop", "X1", False)
    names = InventoryService.get_item_type_display_names()
    assert any("Laptop" in v and "X1" in v for v in names.values())


def test_get_item_type_display_names_without_subtype():
    ItemTypeRepository.get_or_create("Desk", "", False)
    names = InventoryService.get_item_type_display_names()
    assert any(v == "Desk" for v in names.values())


def test_get_autocomplete_types():
    ItemTypeRepository.get_or_create("Keyboard", "", False)
    results = InventoryService.get_autocomplete_types("Key")
    assert "Keyboard" in results


def test_get_autocomplete_subtypes():
    ItemTypeRepository.get_or_create("Laptop", "Pro", False)
    results = InventoryService.get_autocomplete_subtypes("Laptop", "P")
    assert "Pro" in results
