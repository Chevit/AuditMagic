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


# ─── InventoryService: mutations ──────────────────────────────────────────────

def test_add_quantity():
    loc = _loc()
    item = _non_ser(loc_id=loc.id, qty=5)
    updated = InventoryService.add_quantity(item.id, 3)
    assert updated.quantity == 8


def test_remove_quantity():
    loc = _loc()
    item = _non_ser(loc_id=loc.id, qty=10)
    updated = InventoryService.remove_quantity(item.id, 4)
    assert updated.quantity == 6


def test_edit_item():
    loc = _loc()
    item = _non_ser("OldType", loc_id=loc.id, qty=5)
    updated = InventoryService.edit_item(
        item_id=item.id,
        item_type_name="NewType",
        sub_type="",
        quantity=8,
        is_serialized=False,
        location_id=loc.id,
        edit_reason="test edit",
    )
    assert updated is not None
    assert updated.item_type_name == "NewType"
    assert updated.quantity == 8


def test_delete_item_returns_true():
    loc = _loc()
    item = _non_ser(loc_id=loc.id)
    assert InventoryService.delete_item(item.id) is True
    assert InventoryService.get_item(item.id) is None


def test_delete_item_missing_returns_false():
    assert InventoryService.delete_item(9999) is False


def test_delete_item_type_returns_true():
    loc = _loc()
    item = _non_ser(loc_id=loc.id)
    type_id = item.item_type_id
    assert InventoryService.delete_item_type(type_id) is True
    assert ItemTypeRepository.get_by_id(type_id) is None


def test_delete_item_type_missing_returns_false():
    assert InventoryService.delete_item_type(9999) is False


def test_delete_items_by_serial_numbers():
    loc = _loc()
    _ser("Laptop", "BULK-001", loc_id=loc.id)
    _ser("Laptop", "BULK-002", loc_id=loc.id)
    count = InventoryService.delete_items_by_serial_numbers(
        ["BULK-001", "BULK-002"], notes="bulk delete"
    )
    assert count == 2


# ─── InventoryService: transfer ───────────────────────────────────────────────

def test_transfer_item():
    loc_a = _loc("A")
    loc_b = _loc("B")
    item = _non_ser(loc_id=loc_a.id, qty=10)
    result = InventoryService.transfer_item(
        item_id=item.id, quantity=5,
        from_location_id=loc_a.id, to_location_id=loc_b.id,
    )
    assert result is True


def test_transfer_serialized_items():
    loc_a = _loc("A")
    loc_b = _loc("B")
    _ser("Laptop", "TR-001", loc_id=loc_a.id)
    count = InventoryService.transfer_serialized_items(
        serial_numbers=["TR-001"],
        from_location_id=loc_a.id,
        to_location_id=loc_b.id,
    )
    assert count == 1


def test_move_all_items_and_delete_non_serialized():
    loc_a = _loc("Source")
    loc_b = _loc("Dest")
    _non_ser(loc_id=loc_a.id, qty=5)
    result = InventoryService.move_all_items_and_delete(loc_a.id, loc_b.id)
    assert result is True
    assert LocationRepository.get_by_id(loc_a.id) is None


def test_move_all_items_and_delete_serialized():
    loc_a = _loc("Source")
    loc_b = _loc("Dest")
    _ser("Laptop", "MV-001", loc_id=loc_a.id)
    InventoryService.move_all_items_and_delete(loc_a.id, loc_b.id)
    assert LocationRepository.get_by_id(loc_a.id) is None
    items = ItemRepository.get_all()
    assert any(i.location_id == loc_b.id for i in items)


def test_move_all_items_and_delete_bad_source_raises():
    loc_b = _loc("Dest")
    with pytest.raises(ValueError):
        InventoryService.move_all_items_and_delete(9999, loc_b.id)


def test_get_locations_for_type():
    loc_a = _loc("A")
    loc_b = _loc("B")
    t = ItemTypeRepository.get_or_create("Laptop", "", True)
    ItemRepository.create_serialized(t.id, "GL-001", loc_a.id)
    ItemRepository.create_serialized(t.id, "GL-002", loc_b.id)
    locs = InventoryService.get_locations_for_type(t.id)
    loc_ids = {l.id for l in locs}
    assert loc_a.id in loc_ids
    assert loc_b.id in loc_ids
