"""Tests for repository layer — runs against in-memory SQLite via fresh_db fixture."""
import pytest
from core.repositories import (
    ItemRepository,
    ItemTypeRepository,
    LocationRepository,
    TransactionRepository,
)
from core.models import TransactionType


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _loc(name="Warehouse"):
    return LocationRepository.create(name)


def _type(name="Laptop", sub="", serialized=False):
    return ItemTypeRepository.get_or_create(name, sub, serialized)


def _item(type_id, loc_id, qty=5):
    return ItemRepository.create(item_type_id=type_id, quantity=qty, location_id=loc_id)


def _serial(type_id, loc_id, sn="SN-001"):
    return ItemRepository.create_serialized(
        item_type_id=type_id, serial_number=sn, location_id=loc_id
    )


# ─── LocationRepository ───────────────────────────────────────────────────────

def test_location_create():
    loc = _loc("Room A")
    assert loc.id is not None
    assert loc.name == "Room A"


def test_location_get_by_id():
    loc = _loc("Room A")
    found = LocationRepository.get_by_id(loc.id)
    assert found is not None
    assert found.name == "Room A"


def test_location_get_by_id_missing_returns_none():
    assert LocationRepository.get_by_id(9999) is None


def test_location_get_by_name():
    _loc("Room A")
    found = LocationRepository.get_by_name("Room A")
    assert found is not None


def test_location_get_by_name_missing_returns_none():
    assert LocationRepository.get_by_name("NoSuchRoom") is None


def test_location_get_all_ordered():
    _loc("Zebra")
    _loc("Alpha")
    names = [l.name for l in LocationRepository.get_all()]
    assert names == sorted(names)


def test_location_get_count():
    assert LocationRepository.get_count() == 0
    _loc("A")
    _loc("B")
    assert LocationRepository.get_count() == 2


def test_location_rename():
    loc = _loc("Old Name")
    renamed = LocationRepository.rename(loc.id, "New Name")
    assert renamed.name == "New Name"
    assert LocationRepository.get_by_id(loc.id).name == "New Name"


def test_location_delete_empty():
    loc = _loc("Empty")
    assert LocationRepository.delete(loc.id) is True
    assert LocationRepository.get_by_id(loc.id) is None


def test_location_delete_with_items_raises():
    loc = _loc()
    t = _type()
    _item(t.id, loc.id)
    with pytest.raises(ValueError):
        LocationRepository.delete(loc.id)


def test_location_delete_missing_returns_false():
    assert LocationRepository.delete(9999) is False


def test_location_get_unassigned_item_count():
    t = _type()
    # Create item without location
    ItemRepository.create(item_type_id=t.id, quantity=3, location_id=None)
    assert LocationRepository.get_unassigned_item_count() == 1


def test_location_assign_all_unassigned():
    loc = _loc()
    t = _type()
    ItemRepository.create(item_type_id=t.id, quantity=3, location_id=None)
    count = LocationRepository.assign_all_unassigned(loc.id)
    assert count == 1
    assert LocationRepository.get_unassigned_item_count() == 0


# ─── ItemTypeRepository ───────────────────────────────────────────────────────

def test_itemtype_get_or_create_new():
    t = ItemTypeRepository.get_or_create("Widget", "Small", False)
    assert t.id is not None
    assert t.name == "Widget"
    assert t.sub_type == "Small"
    assert t.is_serialized is False


def test_itemtype_get_or_create_idempotent():
    t1 = ItemTypeRepository.get_or_create("Widget", "", False)
    t2 = ItemTypeRepository.get_or_create("Widget", "", False)
    assert t1.id == t2.id


def test_itemtype_get_or_create_conflict_raises():
    ItemTypeRepository.get_or_create("Widget", "", True)
    with pytest.raises(ValueError):
        ItemTypeRepository.get_or_create("Widget", "", False)


def test_itemtype_get_by_id():
    t = _type("Screen")
    found = ItemTypeRepository.get_by_id(t.id)
    assert found is not None
    assert found.name == "Screen"


def test_itemtype_get_by_id_missing():
    assert ItemTypeRepository.get_by_id(9999) is None


def test_itemtype_get_by_ids():
    t1 = _type("A")
    t2 = _type("B")
    mapping = ItemTypeRepository.get_by_ids([t1.id, t2.id])
    assert set(mapping.keys()) == {t1.id, t2.id}


def test_itemtype_get_all():
    _type("Beta")
    _type("Alpha")
    types = ItemTypeRepository.get_all()
    assert len(types) >= 2
    names = [t.name for t in types]
    assert names == sorted(names)


def test_itemtype_update_name():
    t = _type("OldName")
    updated = ItemTypeRepository.update(t.id, name="NewName")
    assert updated.name == "NewName"


def test_itemtype_update_is_serialized_without_items():
    t = _type("Gadget", serialized=False)
    updated = ItemTypeRepository.update(t.id, is_serialized=True)
    assert updated.is_serialized is True


def test_itemtype_update_is_serialized_with_items_raises():
    loc = _loc()
    t = _type("Gadget", serialized=False)
    _item(t.id, loc.id)
    with pytest.raises(ValueError):
        ItemTypeRepository.update(t.id, is_serialized=True)


def test_itemtype_delete_cascades():
    loc = _loc()
    t = _type("ToDelete")
    _item(t.id, loc.id)
    assert ItemTypeRepository.delete(t.id) is True
    assert ItemTypeRepository.get_by_id(t.id) is None
    assert ItemRepository.get_all() == []


def test_itemtype_delete_missing_returns_false():
    assert ItemTypeRepository.delete(9999) is False


def test_itemtype_get_by_name_and_subtype_found():
    t = _type("Laptop", "X1")
    found = ItemTypeRepository.get_by_name_and_subtype("Laptop", "X1")
    assert found is not None
    assert found.id == t.id


def test_itemtype_get_by_name_and_subtype_not_found():
    assert ItemTypeRepository.get_by_name_and_subtype("NoSuch", "") is None


def test_itemtype_get_autocomplete_names():
    _type("Laptop")
    _type("LaptopPro")
    _type("Monitor")
    names = ItemTypeRepository.get_autocomplete_names(prefix="Lap")
    assert "Laptop" in names
    assert "LaptopPro" in names
    assert "Monitor" not in names


def test_itemtype_get_all_with_items():
    loc = _loc()
    t = _type("Laptop")
    _item(t.id, loc.id, qty=3)
    results = ItemTypeRepository.get_all_with_items()
    assert len(results) == 1
    item_type, items = results[0]
    assert item_type.name == "Laptop"
    assert len(items) == 1


def test_itemtype_get_serialized_with_items():
    loc = _loc()
    ser_type = ItemTypeRepository.get_or_create("Serial", "", True)
    non_ser_type = _type("Bulk")
    _serial(ser_type.id, loc.id, "SN-X")
    _item(non_ser_type.id, loc.id)
    results = ItemTypeRepository.get_serialized_with_items()
    type_names = [r[0].name for r in results]
    assert "Serial" in type_names
    assert "Bulk" not in type_names
