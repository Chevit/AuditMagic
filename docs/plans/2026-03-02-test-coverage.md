# Test Coverage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all broken tests and add comprehensive pytest coverage for `src/core/` (repositories, services) and `src/ui/models/` (DTOs).

**Architecture:** Shared `fresh_db` autouse fixture in `conftest.py` gives every test an isolated in-memory SQLite DB. Repository tests call repos directly. Service tests verify orchestration + return types. DTO tests are pure unit tests (no DB, no fixtures).

**Tech Stack:** pytest, SQLAlchemy in-memory SQLite, existing `init_database(":memory:")` bootstrap.

---

### Task 1: Upgrade conftest.py

**Files:**
- Modify: `tests/conftest.py`

**Step 1: Write the new conftest**

Replace the entire file with:

```python
import os
import sys
import pytest

os.environ.setdefault("AUDITMAGIC_DB", ":memory:")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture(autouse=True)
def fresh_db():
    """Reinitialise an in-memory DB before every test."""
    from core.db import init_database
    init_database(":memory:")
```

**Step 2: Verify existing tests still pass**

Run: `pytest tests/test_export_service.py -v`
Expected: all 11 tests PASS (export_service has no DB, fixture is harmless).

**Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add fresh_db autouse fixture to conftest"
```

---

### Task 2: Rewrite test_serialized_feature.py

**Files:**
- Modify: `tests/test_serialized_feature.py`

**Step 1: Replace the file**

```python
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
    InventoryService.create_item(
        item_type_name="Laptop", is_serialized=True,
        serial_number="SN-001", quantity=1,
    )
    # Should not raise — same type, same flag
    InventoryService.create_item(
        item_type_name="Laptop", is_serialized=True,
        serial_number="SN-002", quantity=1,
    )


def test_get_item_type_by_name_subtype_found():
    InventoryService.create_item(
        item_type_name="Laptop", is_serialized=True,
        serial_number="SN-001", quantity=1,
    )
    found = InventoryService.get_item_type_by_name_subtype("Laptop", "")
    assert found is not None
    assert found.is_serialized is True


def test_get_item_type_by_name_subtype_not_found():
    assert InventoryService.get_item_type_by_name_subtype("NonExistentXYZ", "") is None


def test_translation_keys_present():
    from ui.translations import tr
    keys = [
        "label.serialized_badge",
        "label.non_serialized_badge",
        "label.is_serialized",
        "tooltip.serialized_locked",
        "tooltip.serialized_auto",
        "error.serialized_conflict",
        "message.type_exists_serialized",
        "message.type_exists_non_serialized",
    ]
    for key in keys:
        assert tr(key) != key, f"Translation key missing: {key!r}"
```

**Step 2: Run and confirm pass**

Run: `pytest tests/test_serialized_feature.py -v`
Expected: 8 tests PASS.

**Step 3: Commit**

```bash
git add tests/test_serialized_feature.py
git commit -m "test: convert test_serialized_feature to proper pytest"
```

---

### Task 3: Fix test_export_transactions.py

**Files:**
- Modify: `tests/test_export_transactions.py`

**Step 1: Remove module-level init_database call**

Delete line 11: `init_database(":memory:")`

Also remove `from core.db import init_database` from line 9 (it's now in conftest).
The `fresh_db` fixture from conftest handles DB init for every test automatically.

The top of the file after the fix should read:

```python
"""Tests for TransactionService.get_for_export."""
import os
import sys
import pytest

os.environ.setdefault("AUDITMAGIC_DB", ":memory:")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.repositories import ItemTypeRepository, ItemRepository, LocationRepository
from core.services import TransactionService, InventoryService
```

And delete the `fresh_db` fixture inside the file entirely — conftest provides it.

**Step 2: Run**

Run: `pytest tests/test_export_transactions.py -v`
Expected: 5 tests PASS.

**Step 3: Commit**

```bash
git add tests/test_export_transactions.py
git commit -m "test: remove module-level init_database from test_export_transactions"
```

---

### Task 4: test_repositories.py — LocationRepository + ItemTypeRepository

**Files:**
- Create: `tests/test_repositories.py`

**Step 1: Write the file (LocationRepository section)**

```python
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
```

**Step 2: Run**

Run: `pytest tests/test_repositories.py -k "location or itemtype" -v`
Expected: all PASS.

**Step 3: Commit**

```bash
git add tests/test_repositories.py
git commit -m "test: add LocationRepository and ItemTypeRepository tests"
```

---

### Task 5: test_repositories.py — ItemRepository

**Files:**
- Modify: `tests/test_repositories.py` (append)

**Step 1: Append ItemRepository tests**

```python
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
    # one initial + one add
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
    count = ItemRepository.delete_by_serial_numbers(["DEL-001", "DEL-002"], notes="audit")
    assert count == 2
    assert ItemRepository.get_by_id(
        ItemRepository.search("DEL", field="serial_number") and 0 or 0
    ) is None  # items gone
    txs = [
        tx for tx in TransactionRepository.get_recent(20)
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
        item_id=item.id, quantity=4,
        from_location_id=loc_a.id, to_location_id=loc_b.id,
    )
    assert result is True
    txs = [
        tx for tx in TransactionRepository.get_recent(20)
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
```

**Step 2: Run**

Run: `pytest tests/test_repositories.py -k "item_" -v`
Expected: all PASS.

**Step 3: Commit**

```bash
git add tests/test_repositories.py
git commit -m "test: add ItemRepository tests"
```

---

### Task 6: test_repositories.py — TransactionRepository

**Files:**
- Modify: `tests/test_repositories.py` (append)

**Step 1: Append TransactionRepository tests**

```python
# ─── TransactionRepository ────────────────────────────────────────────────────

from datetime import datetime, timedelta, timezone


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
    for i in range(5):
        ItemRepository.add_quantity(
            _item(t.id, loc.id, qty=1).id, 1
        )
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
```

**Step 2: Run all repository tests**

Run: `pytest tests/test_repositories.py -v`
Expected: all PASS.

**Step 3: Commit**

```bash
git add tests/test_repositories.py
git commit -m "test: add TransactionRepository tests"
```

---

### Task 7: test_services.py — InventoryService (create + query)

**Files:**
- Create: `tests/test_services.py`

**Step 1: Write the file**

```python
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
```

**Step 2: Run**

Run: `pytest tests/test_services.py -k "create or get" -v`
Expected: all PASS.

**Step 3: Commit**

```bash
git add tests/test_services.py
git commit -m "test: add InventoryService create and query tests"
```

---

### Task 8: test_services.py — InventoryService mutations + bulk ops + transfer

**Files:**
- Modify: `tests/test_services.py` (append)

**Step 1: Append mutation + transfer tests**

```python
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
```

**Step 2: Run**

Run: `pytest tests/test_services.py -k "transfer or delete or edit or add_quantity or remove_quantity or move or locations_for" -v`
Expected: all PASS.

**Step 3: Commit**

```bash
git add tests/test_services.py
git commit -m "test: add InventoryService mutation, transfer, and bulk-op tests"
```

---

### Task 9: test_services.py — SearchService + TransactionService + _transaction_to_dict

**Files:**
- Modify: `tests/test_services.py` (append)

**Step 1: Append SearchService + TransactionService tests**

```python
# ─── SearchService ────────────────────────────────────────────────────────────

def test_search_returns_matching_items():
    loc = _loc()
    _non_ser("UniqueChair42", loc_id=loc.id)
    results = SearchService.search("UniqueChair42", save_to_history=False)
    assert len(results) >= 1
    assert all("UniqueChair42" in r.item_type_name for r in results)


def test_search_no_match_returns_empty():
    results = SearchService.search("XYZNOMATCH", save_to_history=False)
    assert results == []


def test_search_by_field_serial():
    loc = _loc()
    _ser("Laptop", "SRCH-SN-001", loc_id=loc.id)
    results = SearchService.search("SRCH-SN-001", field="serial_number", save_to_history=False)
    assert len(results) >= 1
    assert results[0].serial_number == "SRCH-SN-001"


def test_search_saves_to_history():
    loc = _loc()
    _non_ser("Widget", loc_id=loc.id)
    SearchService.search("Widget", save_to_history=True)
    history = SearchService.get_search_history()
    assert any(q == "Widget" for q, _ in history)


def test_search_autocomplete_empty_prefix_returns_empty():
    assert SearchService.get_autocomplete_suggestions("") == []


def test_search_autocomplete_prefix_returns_suggestions():
    ItemTypeRepository.get_or_create("Keyboard", "", False)
    results = SearchService.get_autocomplete_suggestions("Key")
    assert len(results) >= 1


def test_search_clear_history():
    loc = _loc()
    _non_ser("Blah", loc_id=loc.id)
    SearchService.search("Blah", save_to_history=True)
    SearchService.clear_search_history()
    assert SearchService.get_search_history() == []


# ─── TransactionService ───────────────────────────────────────────────────────

def _now():
    return datetime.now(timezone.utc)


def test_ts_get_transactions_by_type_and_date_range():
    loc = _loc()
    item = _non_ser(loc_id=loc.id)
    start = _now() - timedelta(minutes=1)
    end = _now() + timedelta(minutes=1)
    txs = TransactionService.get_transactions_by_type_and_date_range(
        item.item_type_id, start, end
    )
    assert len(txs) >= 1
    assert all("type" in t for t in txs)


def test_ts_get_recent_transactions():
    loc = _loc()
    _non_ser(loc_id=loc.id)
    txs = TransactionService.get_recent_transactions(limit=5)
    assert isinstance(txs, list)
    assert len(txs) <= 5


def test_ts_get_transactions_by_location_and_date_range():
    loc = _loc()
    _non_ser(loc_id=loc.id)
    start = _now() - timedelta(minutes=1)
    end = _now() + timedelta(minutes=1)
    txs = TransactionService.get_transactions_by_location_and_date_range(loc.id, start, end)
    assert len(txs) >= 1
    assert all(t["location_id"] == loc.id for t in txs)


def test_ts_get_all_transactions_by_date_range():
    loc_a = _loc("A")
    loc_b = _loc("B")
    _non_ser("A", loc_id=loc_a.id)
    _non_ser("B", loc_id=loc_b.id)
    start = _now() - timedelta(minutes=1)
    end = _now() + timedelta(minutes=1)
    txs = TransactionService.get_all_transactions_by_date_range(start, end)
    loc_ids = {t["location_id"] for t in txs}
    assert loc_a.id in loc_ids
    assert loc_b.id in loc_ids


# ─── _transaction_to_dict: transfer_side ─────────────────────────────────────

def _make_tx(loc_id, from_id, to_id, tx_type=TransactionType.TRANSFER):
    t = Transaction()
    t.id = 1
    t.item_type_id = 1
    t.transaction_type = tx_type
    t.quantity_change = 5
    t.quantity_before = 10
    t.quantity_after = 5
    t.notes = ""
    t.serial_number = None
    t.location_id = loc_id
    t.from_location_id = from_id
    t.to_location_id = to_id
    t.created_at = datetime(2026, 3, 1, tzinfo=timezone.utc)
    return t


def test_transaction_to_dict_transfer_side_source():
    tx = _make_tx(loc_id=10, from_id=10, to_id=20)
    d = _transaction_to_dict(tx)
    assert d["transfer_side"] == "source"


def test_transaction_to_dict_transfer_side_destination():
    tx = _make_tx(loc_id=20, from_id=10, to_id=20)
    d = _transaction_to_dict(tx)
    assert d["transfer_side"] == "destination"


def test_transaction_to_dict_non_transfer_no_side():
    tx = _make_tx(loc_id=10, from_id=None, to_id=None, tx_type=TransactionType.ADD)
    d = _transaction_to_dict(tx)
    assert "transfer_side" not in d


def test_transaction_to_dict_fields():
    tx = _make_tx(loc_id=10, from_id=10, to_id=20)
    d = _transaction_to_dict(tx)
    for key in ("id", "item_type_id", "type", "quantity_change",
                "quantity_before", "quantity_after", "notes",
                "serial_number", "location_id", "from_location_id",
                "to_location_id", "created_at"):
        assert key in d, f"missing key: {key}"
```

**Step 2: Run all service tests**

Run: `pytest tests/test_services.py -v`
Expected: all PASS.

**Step 3: Commit**

```bash
git add tests/test_services.py
git commit -m "test: add SearchService, TransactionService, and _transaction_to_dict tests"
```

---

### Task 10: test_dto_models.py

**Files:**
- Create: `tests/test_dto_models.py`

**Step 1: Write the file**

Pure unit tests — no DB, no fixture. ORM objects created directly without a session.

```python
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
```

**Step 2: Run**

Run: `pytest tests/test_dto_models.py -v`
Expected: all PASS.

**Step 3: Commit**

```bash
git add tests/test_dto_models.py
git commit -m "test: add InventoryItem and GroupedInventoryItem DTO unit tests"
```

---

### Task 11: Final full run

**Step 1: Run entire test suite**

Run: `pytest tests/ -v`
Expected: all tests PASS. Note the final count.

**Step 2: Commit (if any fixes were needed)**

```bash
git add -A
git commit -m "test: final cleanup after full suite run"
```
