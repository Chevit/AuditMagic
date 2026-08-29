# Search Result Location Name Resolution

**Date:** 2026-05-21
**Status:** Approved

## Problem

`SearchService.search` returns `InventoryItem` objects with `location_name=""` because it calls `InventoryItem.from_db_models(item, item_type)` without resolving the location name. This causes two symptoms:

1. **Export bug:** When exporting with "Include transactions" + "Filtered items only", the Items sheet has an empty Warehouse column for every row — the items come from the search-filtered model which holds the unresolved DTOs.
2. **List view bug:** Search results never show `@ Location` in the item's `display_info`, even though the normal (non-search) view does.

## Design

Add location name resolution to `SearchService.search` in `src/core/services.py`.

After fetching `db_items` and building `type_map`, build a `loc_map`:

```python
all_locations = LocationRepository.get_all()
loc_map = {loc.id: loc.name for loc in all_locations}
```

Then pass `location_name` when constructing each DTO:

```python
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

`LocationRepository.get_all()` is the same call already used by `get_all_items_grouped` and other service methods — same pattern, one extra query per search.

## Files Changed

- `src/core/services.py` — `SearchService.search`: add `loc_map` build and pass `location_name` to `from_db_models`.

## Out of Scope

- Changes to `main_window.py`, `export_service.py`, or any DTO class.
- `SearchService.get_autocomplete_suggestions` and `get_search_history` are unaffected.
