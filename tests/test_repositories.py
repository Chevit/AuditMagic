"""Tests for repository layer — runs against in-memory SQLite via fresh_db fixture."""

from datetime import datetime, timedelta, timezone

import pytest

from core.models import TransactionType
from core.repositories import (ItemRepository, ItemTypeRepository,
                               LocationRepository, TransactionRepository)

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


# ─── ItemRepository ───────────────────────────────────────────────────────────


def test_item_create_non_serialized():
    loc = _loc()
    t = _type()
    item = _item(t.id, loc.id, qty=10)
    assert item.id is not None
    assert item.quantity == 10
    assert item.serial_number is None


def test_item_create_serialized():
    loc = _loc()
    t = ItemTypeRepository.get_or_create("Laptop", "", True)
    item = _serial(t.id, loc.id, "SN-001")
    assert item.quantity == 1
    assert item.serial_number == "SN-001"


def test_item_create_serialized_first_item_qty_before_zero():
    loc = _loc()
    t = ItemTypeRepository.get_or_create("Laptop", "", True)
    _serial(t.id, loc.id, "SN-001")
    txs = TransactionRepository.get_recent(10)
    add_tx = next(tx for tx in txs if tx.transaction_type == TransactionType.ADD)
    assert add_tx.quantity_before == 0
    assert add_tx.quantity_after == 1


def test_item_create_serialized_second_item_qty_before_one():
    loc = _loc()
    t = ItemTypeRepository.get_or_create("Laptop", "", True)
    _serial(t.id, loc.id, "SN-001")
    _serial(t.id, loc.id, "SN-002")
    txs = TransactionRepository.get_recent(10)
    add_txs = sorted(
        [tx for tx in txs if tx.transaction_type == TransactionType.ADD],
        key=lambda x: x.quantity_before,
    )
    assert add_txs[0].quantity_before == 0
    assert add_txs[1].quantity_before == 1


def test_item_create_duplicate_serial_raises():
    loc = _loc()
    t = ItemTypeRepository.get_or_create("Laptop", "", True)
    _serial(t.id, loc.id, "SN-DUP")
    with pytest.raises(Exception):
        _serial(t.id, loc.id, "SN-DUP")


def test_item_get_by_id():
    loc = _loc()
    t = _type()
    item = _item(t.id, loc.id)
    found = ItemRepository.get_by_id(item.id)
    assert found is not None
    assert found.id == item.id


def test_item_get_by_id_missing():
    assert ItemRepository.get_by_id(9999) is None


def test_item_get_all():
    loc = _loc()
    t = _type()
    _item(t.id, loc.id)
    items = ItemRepository.get_all()
    assert len(items) >= 1


def test_item_add_quantity():
    loc = _loc()
    t = _type()
    item = _item(t.id, loc.id, qty=5)
    updated = ItemRepository.add_quantity(item.id, 3)
    assert updated.quantity == 8


def test_item_add_quantity_creates_transaction():
    loc = _loc()
    t = _type()
    item = _item(t.id, loc.id, qty=5)
    ItemRepository.add_quantity(item.id, 3)
    txs = TransactionRepository.get_recent(10)
    add_txs = [tx for tx in txs if tx.transaction_type == TransactionType.ADD]
    # one initial ADD (from create) + one more ADD (from add_quantity)
    assert len(add_txs) == 2


def test_item_remove_quantity():
    loc = _loc()
    t = _type()
    item = _item(t.id, loc.id, qty=10)
    updated = ItemRepository.remove_quantity(item.id, 4)
    assert updated.quantity == 6


def test_item_remove_quantity_below_zero_raises():
    loc = _loc()
    t = _type()
    item = _item(t.id, loc.id, qty=3)
    with pytest.raises(ValueError):
        ItemRepository.remove_quantity(item.id, 10)


def test_item_delete():
    loc = _loc()
    t = _type()
    item = _item(t.id, loc.id)
    assert ItemRepository.delete(item.id) is True
    assert ItemRepository.get_by_id(item.id) is None


def test_item_delete_missing_returns_false():
    assert ItemRepository.delete(9999) is False


def test_item_delete_by_serial_numbers_creates_remove_transactions():
    loc = _loc()
    t = ItemTypeRepository.get_or_create("Laptop", "", True)
    _serial(t.id, loc.id, "DEL-001")
    _serial(t.id, loc.id, "DEL-002")
    count = ItemRepository.delete_by_serial_numbers(
        ["DEL-001", "DEL-002"], notes="audit"
    )
    assert count == 2
    # Items should be gone
    assert ItemRepository.search("DEL-001", field="serial_number") == []
    # REMOVE transactions should still exist (audit trail preserved)
    txs = [
        tx
        for tx in TransactionRepository.get_recent(20)
        if tx.transaction_type == TransactionType.REMOVE
    ]
    assert len(txs) == 2
    assert all(tx.notes == "audit" for tx in txs)


def test_item_transfer_item_creates_transfer_transactions():
    loc_a = _loc("A")
    loc_b = _loc("B")
    t = _type()
    item = _item(t.id, loc_a.id, qty=10)
    result = ItemRepository.transfer_item(
        item_id=item.id,
        quantity=4,
        from_location_id=loc_a.id,
        to_location_id=loc_b.id,
    )
    assert result is True
    txs = [
        tx
        for tx in TransactionRepository.get_recent(20)
        if tx.transaction_type == TransactionType.TRANSFER
    ]
    assert len(txs) == 2
    loc_ids = {tx.location_id for tx in txs}
    assert loc_a.id in loc_ids
    assert loc_b.id in loc_ids


def test_item_transfer_serialized_items():
    loc_a = _loc("A")
    loc_b = _loc("B")
    t = ItemTypeRepository.get_or_create("Laptop", "", True)
    _serial(t.id, loc_a.id, "TR-001")
    count = ItemRepository.transfer_serialized_items(
        serial_numbers=["TR-001"],
        from_location_id=loc_a.id,
        to_location_id=loc_b.id,
    )
    assert count == 1
    moved = ItemRepository.search("TR-001", field="serial_number")
    assert moved[0].location_id == loc_b.id


def test_item_find_non_serialized_at_location():
    loc = _loc()
    t = _type()
    _item(t.id, loc.id, qty=5)
    found = ItemRepository.find_non_serialized_at_location(t.id, loc.id)
    assert found is not None
    assert found.serial_number is None


def test_item_search_by_type_name():
    loc = _loc()
    t = _type("UniqueMonitor")
    _item(t.id, loc.id)
    results = ItemRepository.search("UniqueMonitor", field="item_type")
    assert len(results) == 1


def test_item_search_by_serial():
    loc = _loc()
    t = ItemTypeRepository.get_or_create("Laptop", "", True)
    _serial(t.id, loc.id, "FIND-ME-123")
    results = ItemRepository.search("FIND-ME-123", field="serial_number")
    assert len(results) == 1
    assert results[0].serial_number == "FIND-ME-123"


# ─── TransactionRepository ────────────────────────────────────────────────────


def _now():
    return datetime.now(timezone.utc)


def test_transaction_get_by_type_and_date_range_in_range():
    loc = _loc()
    t = _type()
    _item(t.id, loc.id, qty=5)
    start = _now() - timedelta(minutes=1)
    end = _now() + timedelta(minutes=1)
    txs = TransactionRepository.get_by_type_and_date_range(t.id, start, end)
    assert len(txs) >= 1


def test_transaction_get_by_type_and_date_range_out_of_range():
    loc = _loc()
    t = _type()
    _item(t.id, loc.id, qty=5)
    past_start = _now() - timedelta(days=2)
    past_end = _now() - timedelta(days=1)
    txs = TransactionRepository.get_by_type_and_date_range(t.id, past_start, past_end)
    assert len(txs) == 0


def test_transaction_get_recent_limit():
    loc = _loc()
    t = _type()
    for _ in range(5):
        item = _item(t.id, loc.id, qty=1)
        ItemRepository.add_quantity(item.id, 1)
    txs = TransactionRepository.get_recent(limit=3)
    assert len(txs) <= 3


def test_transaction_get_by_location_and_date_range():
    loc = _loc()
    t = _type()
    _item(t.id, loc.id, qty=5)
    start = _now() - timedelta(minutes=1)
    end = _now() + timedelta(minutes=1)
    txs = TransactionRepository.get_by_location_and_date_range(loc.id, start, end)
    assert len(txs) >= 1
    assert all(tx.location_id == loc.id for tx in txs)


def test_transaction_get_all_by_date_range():
    loc_a = _loc("A")
    loc_b = _loc("B")
    t = _type()
    _item(t.id, loc_a.id)
    _item(t.id, loc_b.id)
    start = _now() - timedelta(minutes=1)
    end = _now() + timedelta(minutes=1)
    txs = TransactionRepository.get_all_by_date_range(start, end)
    loc_ids = {tx.location_id for tx in txs}
    assert loc_a.id in loc_ids
    assert loc_b.id in loc_ids


def test_transaction_get_for_export_no_filter():
    loc = _loc()
    t = _type()
    _item(t.id, loc.id)
    txs = TransactionRepository.get_for_export()
    assert len(txs) >= 1


def test_transaction_get_for_export_by_location():
    loc_a = _loc("A")
    loc_b = _loc("B")
    t = _type()
    _item(t.id, loc_a.id)
    _item(t.id, loc_b.id)
    txs = TransactionRepository.get_for_export(location_id=loc_a.id)
    assert all(
        tx.location_id == loc_a.id
        or tx.from_location_id == loc_a.id
        or tx.to_location_id == loc_a.id
        for tx in txs
    )


def test_transaction_get_for_export_by_type_ids():
    loc = _loc()
    t1 = _type("A")
    t2 = _type("B")
    _item(t1.id, loc.id)
    _item(t2.id, loc.id)
    txs = TransactionRepository.get_for_export(item_type_ids=[t1.id])
    assert all(tx.item_type_id == t1.id for tx in txs)
