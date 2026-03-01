"""Pure unit tests for InventoryItem and GroupedInventoryItem DTOs.

No database required. Item and ItemType instances are constructed directly
(not persisted) to test the classmethod and property logic in isolation.
"""
from datetime import datetime, timezone
from core.models import Item, ItemType
from ui.models.inventory_item import InventoryItem, GroupedInventoryItem


# ─── Helpers ──────────────────────────────────────────────────────────────────

_TS = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)


def _make_type(id=1, name="Laptop", sub_type="X1", is_serialized=False, details="A laptop"):
    t = ItemType()
    t.id = id
    t.name = name
    t.sub_type = sub_type
    t.is_serialized = is_serialized
    t.details = details
    return t


def _make_item(id=1, type_id=1, qty=5, sn=None, loc_id=1):
    i = Item()
    i.id = id
    i.item_type_id = type_id
    i.quantity = qty
    i.serial_number = sn
    i.location_id = loc_id
    i.condition = "Good"
    i.created_at = _TS
    i.updated_at = _TS
    return i


# ─── InventoryItem ────────────────────────────────────────────────────────────

def test_inventory_item_from_db_models_fields():
    t = _make_type()
    i = _make_item()
    item = InventoryItem.from_db_models(i, t, location_name="Warehouse")
    assert item.id == 1
    assert item.item_type_id == 1
    assert item.item_type_name == "Laptop"
    assert item.item_sub_type == "X1"
    assert item.is_serialized is False
    assert item.quantity == 5
    assert item.serial_number is None
    assert item.location_id == 1
    assert item.location_name == "Warehouse"
    assert item.condition == "Good"
    assert item.details == "A laptop"
    assert item.created_at == _TS
    assert item.updated_at == _TS


def test_inventory_item_is_serialized_from_type():
    t = _make_type(is_serialized=True)
    i = _make_item(sn="SN-001", qty=1)
    item = InventoryItem.from_db_models(i, t)
    assert item.is_serialized is True


def test_inventory_item_location_property_returns_location_name():
    t = _make_type()
    i = _make_item()
    item = InventoryItem.from_db_models(i, t, location_name="Room A")
    assert item.location == "Room A"


def test_inventory_item_sub_type_none_becomes_empty_string():
    t = _make_type(sub_type=None)
    i = _make_item()
    item = InventoryItem.from_db_models(i, t)
    assert item.item_sub_type == ""


def test_inventory_item_details_none_becomes_empty_string():
    t = _make_type(details=None)
    i = _make_item()
    item = InventoryItem.from_db_models(i, t)
    assert item.details == ""


# ─── GroupedInventoryItem ─────────────────────────────────────────────────────

def test_grouped_non_serialized_single_item():
    t = _make_type(is_serialized=False)
    i = _make_item(qty=7)
    g = GroupedInventoryItem.from_item_type_and_items(t, [i])
    assert g.total_quantity == 7
    assert g.serial_numbers == []
    assert g.item_count == 1
    assert g.item_ids == [1]


def test_grouped_serialized_multiple_items():
    t = _make_type(is_serialized=True)
    items = [
        _make_item(id=1, qty=1, sn="SN-A"),
        _make_item(id=2, qty=1, sn="SN-B"),
        _make_item(id=3, qty=1, sn="SN-C"),
    ]
    g = GroupedInventoryItem.from_item_type_and_items(t, items)
    assert g.total_quantity == 3
    assert g.item_count == 3
    assert sorted(g.serial_numbers) == ["SN-A", "SN-B", "SN-C"]
    assert set(g.item_ids) == {1, 2, 3}


def test_grouped_location_name_from_map():
    t = _make_type()
    i = _make_item(loc_id=42)
    g = GroupedInventoryItem.from_item_type_and_items(
        t, [i], location_map={42: "Server Room"}
    )
    assert g.location_id == 42
    assert g.location_name == "Server Room"
    assert g.is_multi_location is False


def test_grouped_multi_location():
    t = _make_type()
    items = [
        _make_item(id=1, loc_id=1),
        _make_item(id=2, loc_id=2),
    ]
    g = GroupedInventoryItem.from_item_type_and_items(
        t, items, location_map={1: "A", 2: "B"}
    )
    assert g.is_multi_location is True
    assert g.location_id is None
    assert g.location_name == ""


def test_grouped_legacy_id_property():
    t = _make_type()
    g = GroupedInventoryItem.from_item_type_and_items(t, [_make_item(id=99)])
    assert g.id == 99


def test_grouped_legacy_quantity_property():
    t = _make_type()
    g = GroupedInventoryItem.from_item_type_and_items(t, [_make_item(qty=12)])
    assert g.quantity == 12


def test_grouped_legacy_serial_number_first_or_none():
    t = _make_type(is_serialized=True)
    items = [_make_item(id=1, sn="SN-Z"), _make_item(id=2, sn="SN-A")]
    g = GroupedInventoryItem.from_item_type_and_items(t, items)
    # serial_numbers are sorted, so first is "SN-A"
    assert g.serial_number == "SN-A"


def test_grouped_legacy_serial_number_none_when_no_serials():
    t = _make_type(is_serialized=False)
    g = GroupedInventoryItem.from_item_type_and_items(t, [_make_item()])
    assert g.serial_number is None


def test_grouped_legacy_location_property():
    t = _make_type()
    i = _make_item(loc_id=5)
    g = GroupedInventoryItem.from_item_type_and_items(
        t, [i], location_map={5: "Closet"}
    )
    assert g.location == "Closet"
