"""Tests for the f6g7h migration: merge duplicate bulk rows, then forbid them."""

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from core.db import session_scope
from core.repositories import ItemRepository, ItemTypeRepository, LocationRepository

MIGRATION = (
    Path(__file__).resolve().parent.parent
    / "alembic"
    / "versions"
    / "f6g7h_unique_bulk_stock_per_location.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("f6g7h_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _drop_index():
    """Return the schema to its pre-migration shape, so duplicates can exist."""
    with session_scope() as session:
        session.execute(text("DROP INDEX IF EXISTS uq_item_type_location_bulk"))


def _bulk_rows(type_id, location_id):
    return [
        row
        for row in ItemRepository.get_by_type_and_location(type_id, location_id)
        if row.serial_number is None
    ]


def test_index_forbids_duplicate_bulk_rows():
    """The invariant is structural, not just enforced in core.stock."""
    loc = LocationRepository.create("W")
    item_type = ItemTypeRepository.get_or_create(name="Desk", is_serialized=False)
    ItemRepository.create(item_type_id=item_type.id, quantity=4, location_id=loc.id)
    with pytest.raises(IntegrityError):
        ItemRepository.create(item_type_id=item_type.id, quantity=6, location_id=loc.id)


def test_index_still_allows_one_row_per_location():
    loc_a = LocationRepository.create("A")
    loc_b = LocationRepository.create("B")
    item_type = ItemTypeRepository.get_or_create(name="Desk", is_serialized=False)
    ItemRepository.create(item_type_id=item_type.id, quantity=4, location_id=loc_a.id)
    ItemRepository.create(item_type_id=item_type.id, quantity=6, location_id=loc_b.id)
    assert len(_bulk_rows(item_type.id, loc_a.id)) == 1
    assert len(_bulk_rows(item_type.id, loc_b.id)) == 1


def test_index_does_not_constrain_serialized_rows():
    loc = LocationRepository.create("W")
    item_type = ItemTypeRepository.get_or_create(name="Laptop", is_serialized=True)
    ItemRepository.create_serialized(item_type.id, "SN-1", location_id=loc.id)
    ItemRepository.create_serialized(item_type.id, "SN-2", location_id=loc.id)
    assert len(ItemRepository.get_by_type_and_location(item_type.id, loc.id)) == 2


def test_merge_folds_duplicates_into_the_lowest_id_row():
    _drop_index()
    loc = LocationRepository.create("W")
    item_type = ItemTypeRepository.get_or_create(name="Desk", is_serialized=False)
    keep = ItemRepository.create(
        item_type_id=item_type.id, quantity=4, location_id=loc.id
    )
    ItemRepository.create(item_type_id=item_type.id, quantity=6, location_id=loc.id)
    ItemRepository.create(item_type_id=item_type.id, quantity=1, location_id=loc.id)
    assert len(_bulk_rows(item_type.id, loc.id)) == 3

    with session_scope() as session:
        merged = _load_migration().merge_duplicate_bulk_rows(session)
    assert merged == 1

    rows = _bulk_rows(item_type.id, loc.id)
    assert len(rows) == 1
    assert rows[0].id == keep.id
    assert rows[0].quantity == 11


def test_merge_leaves_distinct_locations_alone():
    _drop_index()
    loc_a = LocationRepository.create("A")
    loc_b = LocationRepository.create("B")
    item_type = ItemTypeRepository.get_or_create(name="Desk", is_serialized=False)
    ItemRepository.create(item_type_id=item_type.id, quantity=4, location_id=loc_a.id)
    ItemRepository.create(item_type_id=item_type.id, quantity=6, location_id=loc_b.id)

    with session_scope() as session:
        assert _load_migration().merge_duplicate_bulk_rows(session) == 0

    assert _bulk_rows(item_type.id, loc_a.id)[0].quantity == 4
    assert _bulk_rows(item_type.id, loc_b.id)[0].quantity == 6


def test_merge_leaves_serialized_rows_alone():
    _drop_index()
    loc = LocationRepository.create("W")
    item_type = ItemTypeRepository.get_or_create(name="Laptop", is_serialized=True)
    ItemRepository.create_serialized(item_type.id, "SN-1", location_id=loc.id)
    ItemRepository.create_serialized(item_type.id, "SN-2", location_id=loc.id)

    with session_scope() as session:
        assert _load_migration().merge_duplicate_bulk_rows(session) == 0

    assert len(ItemRepository.get_by_type_and_location(item_type.id, loc.id)) == 2
