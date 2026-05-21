# Search Result Location Name Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `SearchService.search` resolve location names so exported Items sheets and list-view search results always show the correct location.

**Architecture:** Add a single `LocationRepository.get_all()` call inside `SearchService.search` after the existing `ItemTypeRepository.get_by_ids` call, build a `loc_map`, and pass `location_name` to each `InventoryItem.from_db_models` call. No other files change.

**Tech Stack:** Python 3.14, SQLAlchemy, pytest, in-memory SQLite (`AUDITMAGIC_DB=:memory:`)

---

### Task 1: Add a failing test for location name resolution in search results

**Files:**
- Modify: `tests/test_services.py` (append after the existing `SearchService` test block, ~line 435)

- [ ] **Step 1: Add the test at the bottom of `tests/test_services.py`**

```python
def test_search_result_has_location_name():
    loc = _loc("SearchLocTest")
    _non_ser("LocNameItem", loc_id=loc.id)
    results = SearchService.search("LocNameItem", save_to_history=False)
    assert len(results) >= 1
    assert results[0].location_name == "SearchLocTest"


def test_search_result_location_name_empty_when_no_location():
    _non_ser("NoLocItem", loc_id=None)
    results = SearchService.search("NoLocItem", save_to_history=False)
    assert len(results) >= 1
    assert results[0].location_name == ""
```

- [ ] **Step 2: Run the new tests to confirm they fail**

```bash
python3 -m pytest tests/test_services.py::test_search_result_has_location_name tests/test_services.py::test_search_result_location_name_empty_when_no_location -v
```

Expected: both `FAILED` — `location_name` is currently always `""`.

---

### Task 2: Fix `SearchService.search` to resolve location names

**Files:**
- Modify: `src/core/services.py:698-731`

- [ ] **Step 3: Update `SearchService.search` to build a `loc_map` and pass `location_name`**

Replace the body of `SearchService.search` from the `db_items` fetch to the return statement (~lines 722–731 of `src/core/services.py`):

```python
        db_items = ItemRepository.search(query, field, location_id=location_id)
        if not db_items:
            return []
        type_ids = list({item.item_type_id for item in db_items})
        type_map = ItemTypeRepository.get_by_ids(type_ids)
        all_locations = LocationRepository.get_all()
        loc_map = {loc.id: loc.name for loc in all_locations}
        return [
            InventoryItem.from_db_models(
                item,
                type_map[item.item_type_id],
                location_name=loc_map.get(item.location_id, ""),
            )
            for item in db_items
            if item.item_type_id in type_map
        ]
```

`LocationRepository` is already imported at the top of `services.py` — no import changes needed.

- [ ] **Step 4: Run the new tests to confirm they pass**

```bash
python3 -m pytest tests/test_services.py::test_search_result_has_location_name tests/test_services.py::test_search_result_location_name_empty_when_no_location -v
```

Expected: both `PASSED`.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
python3 -m pytest tests/ -v
```

Expected: all tests pass (161+ depending on count at time of execution).

- [ ] **Step 6: Commit**

```bash
git add tests/test_services.py src/core/services.py
git commit -m "fix: resolve location names in SearchService.search results"
```
