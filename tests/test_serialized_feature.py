"""Tests for is_serialized immutability (replaces the old script-style runner)."""
import pytest
from core.services import InventoryService


def test_create_serialized_item_flag():
    item = InventoryService.create_item(
        item_type_name="Laptop", is_serialized=True,
        serial_number="SN-001", quantity=1,
    )
    assert item.is_serialized is True


def test_create_non_serialized_item_flag():
    item = InventoryService.create_item(
        item_type_name="Desk", is_serialized=False, quantity=5,
    )
    assert item.is_serialized is False


def test_conflict_serialized_to_non_raises():
    InventoryService.create_item(
        item_type_name="Laptop", is_serialized=True,
        serial_number="SN-001", quantity=1,
    )
    with pytest.raises(ValueError):
        InventoryService.create_item(
            item_type_name="Laptop", is_serialized=False, quantity=3,
        )


def test_conflict_non_to_serialized_raises():
    InventoryService.create_item(
        item_type_name="Desk", is_serialized=False, quantity=5,
    )
    with pytest.raises(ValueError):
        InventoryService.create_item(
            item_type_name="Desk", is_serialized=True,
            serial_number="SN-DESK-01", quantity=1,
        )


def test_same_type_same_flag_idempotent():
    item1 = InventoryService.create_item(
        item_type_name="Laptop", is_serialized=True,
        serial_number="SN-001", quantity=1,
    )
    # Should not raise — same type, same flag
    item2 = InventoryService.create_item(
        item_type_name="Laptop", is_serialized=True,
        serial_number="SN-002", quantity=1,
    )
    assert item1.item_type_id == item2.item_type_id


def test_get_item_type_by_name_subtype_found():
    InventoryService.create_item(
        item_type_name="Laptop", is_serialized=True,
        serial_number="SN-001", quantity=1,
    )
    found = InventoryService.get_item_type_by_name_subtype("Laptop", "")
    assert found is not None
    assert found.name == "Laptop"
    assert found.is_serialized is True


def test_get_item_type_by_name_subtype_not_found():
    assert InventoryService.get_item_type_by_name_subtype("NonExistentXYZ", "") is None

