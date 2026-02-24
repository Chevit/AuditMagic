"""Service layer for business logic operations."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from logger import logger
from models import Location
from repositories import (
    ItemRepository,
    ItemTypeRepository,
    LocationRepository,
    SearchHistoryRepository,
    TransactionRepository,
)
from ui_entities.inventory_item import GroupedInventoryItem, InventoryItem
from ui_entities.translations import tr


class LocationService:
    """Service for location management operations."""

    @staticmethod
    def create_location(name: str) -> Location:
        """Create a new location."""
        return LocationRepository.create(name)

    @staticmethod
    def get_location_by_id(location_id: int) -> Optional[Location]:
        """Get location by ID."""
        return LocationRepository.get_by_id(location_id)

    @staticmethod
    def get_location_by_name(name: str) -> Optional[Location]:
        """Get location by exact name."""
        return LocationRepository.get_by_name(name)

    @staticmethod
    def get_all_locations() -> List[Location]:
        """Get all locations ordered by name."""
        return LocationRepository.get_all()

    @staticmethod
    def get_location_count() -> int:
        """Return total number of locations."""
        return LocationRepository.get_count()

    @staticmethod
    def get_item_count(location_id: int) -> int:
        """Return number of items at a location."""
        return LocationRepository.get_item_count(location_id)

    @staticmethod
    def get_all_with_item_counts() -> list:
        """Get all locations with their item counts in a single query."""
        return LocationRepository.get_all_with_item_counts()

    @staticmethod
    def rename_location(location_id: int, new_name: str) -> Optional[Location]:
        """Rename a location."""
        return LocationRepository.rename(location_id, new_name)

    @staticmethod
    def delete_location(location_id: int) -> bool:
        """Delete an empty location. Raises ValueError if it has items."""
        return LocationRepository.delete(location_id)

    @staticmethod
    def get_unassigned_item_count() -> int:
        """Return count of items with location_id IS NULL."""
        return LocationRepository.get_unassigned_item_count()

    @staticmethod
    def assign_all_unassigned_items(location_id: int) -> int:
        """Assign all items with location_id=NULL to the given location."""
        return LocationRepository.assign_all_unassigned(location_id)

    @staticmethod
    def move_all_items_and_delete(from_location_id: int, to_location_id: int) -> bool:
        """Move all items from one location to another, then delete the source location.

        For each item at from_location_id:
          - Non-serialized: calls ItemRepository.transfer_item (handles merge logic).
          - Serialized: calls ItemRepository.transfer_serialized_items.
        Both create TRANSFER transactions for the audit trail.
        After all items are moved, deletes the source location.

        Args:
            from_location_id: Location to empty and delete.
            to_location_id: Destination location.

        Returns:
            True on success.

        Raises:
            ValueError: If either location doesn't exist.
        """
        from_loc = LocationRepository.get_by_id(from_location_id)
        if not from_loc:
            raise ValueError(f"Source location id={from_location_id} not found")
        to_loc = LocationRepository.get_by_id(to_location_id)
        if not to_loc:
            raise ValueError(f"Destination location id={to_location_id} not found")

        notes = tr("transaction.notes.location_deleted_move").format(
            from_loc=from_loc.name
        )

        items = ItemRepository.get_items_at_location(from_location_id)
        for item in items:
            if item.serial_number:
                # Serialized — move in-place by serial number
                ItemRepository.transfer_serialized_items(
                    serial_numbers=[item.serial_number],
                    from_location_id=from_location_id,
                    to_location_id=to_location_id,
                    notes=notes,
                )
            else:
                # Non-serialized — transfer with merge logic
                ItemRepository.transfer_item(
                    item_id=item.id,
                    quantity=item.quantity,
                    from_location_id=from_location_id,
                    to_location_id=to_location_id,
                    notes=notes,
                )

        LocationRepository.delete(from_location_id)
        logger.info(
            f"Service: Moved all items from location '{from_loc.name}' to "
            f"'{to_loc.name}' and deleted source location"
        )
        return True

    @staticmethod
    def get_locations_for_type(item_type_id: int) -> List[Location]:
        """Return the distinct locations that have at least one item of this type.

        Used by TransferDialog to populate the source-location combo when the
        user is in "All Locations" view with a multi-location item.
        """
        items = ItemRepository.get_by_type(item_type_id)
        seen_ids: set = set()
        locs: List[Location] = []
        all_locs = {loc.id: loc for loc in LocationRepository.get_all()}
        for item in items:
            if item.location_id and item.location_id not in seen_ids:
                seen_ids.add(item.location_id)
                if item.location_id in all_locs:
                    locs.append(all_locs[item.location_id])
        return locs


class InventoryService:
    """Service for inventory management operations."""

    @staticmethod
    def create_item(
        item_type_name: str,
        item_sub_type: str = "",
        quantity: int = 1,
        is_serialized: bool = False,
        serial_number: str = None,
        location_id: int = None,
        condition: str = "",
        transaction_notes: str = "",
    ) -> InventoryItem:
        """Create a new inventory item.

        Args:
            item_type_name: Type name
            item_sub_type: Sub-type name
            quantity: Initial quantity
            is_serialized: Whether this type has serial numbers
            serial_number: Serial number (required if serialized)
            location_id: FK to Location
            condition: Item condition
            transaction_notes: Optional notes for the initial ADD transaction

        Returns:
            The created InventoryItem.
        """
        logger.info(
            f"Creating new item: type='{item_type_name}', sub_type='{item_sub_type}', qty={quantity}"
        )
        try:
            # Get or create item type
            item_type = ItemTypeRepository.get_or_create(
                name=item_type_name,
                sub_type=item_sub_type,
                is_serialized=is_serialized,
            )

            # Create item instance
            db_item = ItemRepository.create(
                item_type_id=item_type.id,
                quantity=quantity,
                serial_number=serial_number,
                location_id=location_id,
                condition=condition,
                transaction_notes=transaction_notes or None,
            )

            logger.info(f"Item created successfully: id={db_item.id}")
            return InventoryItem.from_db_models(db_item, item_type)
        except Exception as e:
            logger.error(f"Failed to create item: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def create_serialized_item(
        item_type_name: str,
        item_sub_type: str = "",
        serial_number: str = "",
        location_id: int = None,
        condition: str = "",
        details: str = "",
        notes: str = "",
    ) -> InventoryItem:
        """Create a new serialized inventory item.

        Gets or creates the ItemType (must be serialized=True), then creates
        a new Item via ItemRepository.create_serialized which tracks the full
        group quantity in the transaction (quantity_before = current item count
        for this type, quantity_after = count + 1).

        Notes policy is enforced in the repository:
          - First item of the type: default "initial inventory" text.
          - Subsequent items: caller-supplied notes or "".

        Args:
            item_type_name: Type name.
            item_sub_type: Sub-type (optional).
            serial_number: Unique serial number (required).
            location: Storage location (optional).
            condition: Item condition (optional).
            details: ItemType description (applied only when creating a new type).
            notes: Transaction notes (used for non-first items).

        Returns:
            The created InventoryItem.

        Raises:
            ValueError: If the type already exists as non-serialized, or the
                        serial number is missing or duplicate.
        """
        logger.info(
            f"Creating serialized item: type='{item_type_name}', sn='{serial_number}'"
        )
        try:
            item_type = ItemTypeRepository.get_or_create(
                name=item_type_name,
                sub_type=item_sub_type,
                is_serialized=True,
                details=details,
            )
            db_item = ItemRepository.create_serialized(
                item_type_id=item_type.id,
                serial_number=serial_number,
                location_id=location_id,
                condition=condition,
                notes=notes,
            )
            logger.info(f"Serialized item created: id={db_item.id}")
            return InventoryItem.from_db_models(db_item, item_type)
        except Exception as e:
            logger.error(f"Failed to create serialized item: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def create_or_merge_item(
        item_type_name: str,
        quantity: int,
        sub_type: str = "",
        is_serialized: bool = False,
        serial_number: str = "",
        details: str = "",
        location_id: int = None,
        condition: str = "",
        transaction_notes: str = "",
    ) -> Tuple[InventoryItem, bool]:
        """Create a new item or merge with existing item if type+location matches.

        For non-serialized items: If an item with the same type at the same location
        exists, quantity is added to it (merge).
        For serialized items: A new item is always created (serial numbers are unique).

        Args:
            item_type_name: Type name of the item (required)
            quantity: Quantity to add (required)
            sub_type: Sub-type of the item (optional)
            is_serialized: Whether items have serial numbers
            serial_number: Serial number (required if serialized)
            details: Type details/description (optional)
            location_id: FK to Location (optional)
            condition: Item condition (optional)
            transaction_notes: Custom notes for the ADD transaction (optional)

        Returns:
            Tuple of (InventoryItem, was_merged: bool).
            was_merged is True if quantity was added to an existing item.
        """
        # Get or create item type
        item_type = ItemTypeRepository.get_or_create(
            name=item_type_name,
            sub_type=sub_type,
            is_serialized=is_serialized,
        )

        # For serialized items, always create new (each serial is unique)
        if is_serialized or serial_number:
            db_item = ItemRepository.create(
                item_type_id=item_type.id,
                quantity=1,
                serial_number=serial_number,
                location_id=location_id,
                condition=condition,
                transaction_notes=transaction_notes or None,
            )
            return InventoryItem.from_db_models(db_item, item_type), False

        # For non-serialized, check for existing item of same type at same location
        if location_id is not None:
            existing = ItemRepository.find_non_serialized_at_location(
                item_type_id=item_type.id,
                location_id=location_id,
            )
        else:
            existing = ItemRepository.find_by_type_and_serial(
                item_type_id=item_type.id,
                serial_number=None,
            )

        if existing:
            # Add quantity to existing item (creates transaction)
            updated = ItemRepository.add_quantity(
                item_id=existing.id,
                quantity=quantity,
                notes=tr("transaction.notes.merged"),
            )
            return InventoryItem.from_db_models(updated, item_type), True

        # Create new item
        db_item = ItemRepository.create(
            item_type_id=item_type.id,
            quantity=quantity,
            serial_number=None,
            location_id=location_id,
            condition=condition,
        )
        return InventoryItem.from_db_models(db_item, item_type), False

    @staticmethod
    def get_item(item_id: int) -> Optional[InventoryItem]:
        """Get an item by ID.

        Args:
            item_id: The item's ID.

        Returns:
            The InventoryItem or None if not found.
        """
        db_item = ItemRepository.get_by_id(item_id)
        if not db_item:
            return None

        item_type = ItemTypeRepository.get_by_id(db_item.item_type_id)
        return InventoryItem.from_db_models(db_item, item_type)

    @staticmethod
    def get_all_items() -> List[InventoryItem]:
        """Get all inventory items.

        Returns:
            List of all InventoryItem instances.
        """
        db_items = ItemRepository.get_all()
        if not db_items:
            return []
        type_ids = list({item.item_type_id for item in db_items})
        type_map = ItemTypeRepository.get_by_ids(type_ids)
        return [
            InventoryItem.from_db_models(item, type_map[item.item_type_id])
            for item in db_items
            if item.item_type_id in type_map
        ]

    @staticmethod
    def get_all_items_grouped(location_id: int = None) -> List[GroupedInventoryItem]:
        """Get all inventory items grouped by type, optionally filtered by location.

        Builds a location name map once and passes it to GroupedInventoryItem
        so each row can display the correct location name without N+1 queries.

        Args:
            location_id: Filter items to this location. None = all locations.

        Returns:
            List of GroupedInventoryItem instances.
        """
        types_with_items = ItemTypeRepository.get_all_with_items(
            location_id=location_id
        )
        # Build location map for name resolution (one query for all locations)
        all_locations = LocationRepository.get_all()
        location_map: Dict[int, str] = {loc.id: loc.name for loc in all_locations}
        result = []

        for item_type, items in types_with_items:
            grouped = GroupedInventoryItem.from_item_type_and_items(
                item_type, items, location_map=location_map
            )
            result.append(grouped)

        return result

    @staticmethod
    def get_serialized_items_grouped(
        location_id: int = None,
    ) -> List[GroupedInventoryItem]:
        """Get serialized inventory items grouped by type.

        Returns only items belonging to serialized ItemTypes,
        aggregated with their serial numbers.

        Args:
            location_id: Filter items to this location. None = all locations.

        Returns:
            List of GroupedInventoryItem instances for serialized types only.
        """
        types_with_items = ItemTypeRepository.get_serialized_with_items(
            location_id=location_id
        )
        all_locations = LocationRepository.get_all()
        location_map: Dict[int, str] = {loc.id: loc.name for loc in all_locations}
        result = []

        for item_type, items in types_with_items:
            grouped = GroupedInventoryItem.from_item_type_and_items(
                item_type, items, location_map=location_map
            )
            result.append(grouped)

        return result

    @staticmethod
    def transfer_item(
        item_id: int,
        quantity: int,
        from_location_id: int,
        to_location_id: int,
        notes: str = "",
    ) -> bool:
        """Transfer quantity of a non-serialized item to another location."""
        return ItemRepository.transfer_item(
            item_id=item_id,
            quantity=quantity,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            notes=notes,
        )

    @staticmethod
    def transfer_serialized_items(
        serial_numbers: List[str],
        from_location_id: int,
        to_location_id: int,
        notes: str = "",
    ) -> int:
        """Transfer serialized items (by serial number) to another location."""
        return ItemRepository.transfer_serialized_items(
            serial_numbers=serial_numbers,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            notes=notes,
        )

    @staticmethod
    def get_type_items_at_location(item_type_id: int, location_id: int) -> tuple:
        """Return (total_quantity, sorted_serial_numbers, item_ids) for a type at a location.

        Used by TransferDialog to populate serial checkboxes / qty spinner.
        """
        items = ItemRepository.get_by_type_and_location(item_type_id, location_id)
        total_qty = sum(i.quantity for i in items)
        serials = sorted(i.serial_number for i in items if i.serial_number)
        item_ids = [i.id for i in items]
        return total_qty, serials, item_ids

    @staticmethod
    def get_item_type_display_names() -> dict:
        """Return {item_type_id: display_name} for all item types.

        Used by AllTransactionsDialog to resolve type names in the table.
        """
        types = ItemTypeRepository.get_all()
        return {
            t.id: f"{t.name} — {t.sub_type}" if t.sub_type else t.name for t in types
        }

    @staticmethod
    def get_item_type_names_for_export() -> dict:
        """Return {item_type_id: "Name — SubType"} for use in Excel export.

        Uses an em-dash separator (same as get_item_type_display_names) so that
        ExportService can safely split on " — " without colliding with user-entered
        type names that may contain hyphens.
        """
        types = ItemTypeRepository.get_all()
        return {
            t.id: f"{t.name} \u2014 {t.sub_type}" if t.sub_type else t.name for t in types
        }

    @staticmethod
    def get_item_type_by_name_subtype(name: str, sub_type: str = ""):
        """Return ItemType info for the given name/sub_type, or None.

        Used by the UI to pre-fill serialization state when the user picks an
        existing type. Returns None if the type does not yet exist.

        Args:
            name: Type name
            sub_type: Sub-type name (optional)

        Returns:
            ItemType detached object or None.
        """
        return ItemTypeRepository.get_by_name_and_subtype(name, sub_type)

    @staticmethod
    def get_autocomplete_types(prefix: str = "") -> List[str]:
        """Get autocomplete suggestions for item types.

        Args:
            prefix: Search prefix

        Returns:
            List of matching type names.
        """
        return ItemTypeRepository.get_autocomplete_names(prefix)

    @staticmethod
    def get_autocomplete_subtypes(type_name: str, prefix: str = "") -> List[str]:
        """Get autocomplete suggestions for subtypes.

        Args:
            type_name: The type name
            prefix: Search prefix

        Returns:
            List of matching subtype names.
        """
        return ItemTypeRepository.get_autocomplete_subtypes(type_name, prefix)

    @staticmethod
    def update_item(
        item_id: int,
        serial_number: str = None,
        location_id: int = None,
        condition: str = None,
    ) -> Optional[InventoryItem]:
        """Update an item's instance properties.

        Note: To change type-related fields (name, sub_type, details), use edit_item.

        Args:
            item_id: The item's ID.
            serial_number: New serial number (optional)
            location_id: New Location FK (optional)
            condition: New condition (optional)

        Returns:
            The updated InventoryItem or None if not found.
        """
        db_item = ItemRepository.update(
            item_id=item_id,
            serial_number=serial_number,
            location_id=location_id,
            condition=condition,
        )
        if not db_item:
            return None
        item_type = ItemTypeRepository.get_by_id(db_item.item_type_id)
        return InventoryItem.from_db_models(db_item, item_type)

    @staticmethod
    def edit_item(
        item_id: int,
        item_type_name: str,
        sub_type: str = "",
        quantity: int = 1,
        is_serialized: bool = False,
        serial_number: str = "",
        details: str = "",
        location_id: int = None,
        condition: str = "",
        edit_reason: str = "",
    ) -> Optional[InventoryItem]:
        """Edit an item's properties with full transaction logging.

        Args:
            item_id: The item's ID.
            item_type_name: Type name.
            sub_type: Sub-type name.
            quantity: New quantity.
            is_serialized: Whether type is serialized.
            serial_number: New serial number.
            details: Type details/description.
            location_id: FK to Location.
            condition: Item condition.
            edit_reason: Reason for the edit (required).

        Returns:
            The updated InventoryItem or None if not found.
        """
        logger.info(f"Editing item: id={item_id}, reason='{edit_reason}'")
        try:
            # Get or create the item type
            item_type = ItemTypeRepository.get_or_create(
                name=item_type_name,
                sub_type=sub_type,
                is_serialized=is_serialized,
            )

            db_item = ItemRepository.edit_item(
                item_id=item_id,
                item_type_id=item_type.id,
                quantity=quantity,
                serial_number=serial_number,
                location_id=location_id,
                condition=condition,
                edit_reason=edit_reason,
            )
            if db_item:
                logger.info(f"Item edited successfully: id={item_id}")
                return InventoryItem.from_db_models(db_item, item_type)
            logger.warning(f"Item not found for edit: id={item_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to edit item: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def delete_item_type(type_id: int) -> bool:
        """Delete an ItemType together with all its items and transactions.

        Args:
            type_id: The ItemType ID.

        Returns:
            True if deleted, False if not found.
        """
        logger.info(f"Attempting to delete item type: id={type_id}")
        result = ItemTypeRepository.delete(type_id)
        if result:
            logger.info(f"ItemType deleted successfully: id={type_id}")
        else:
            logger.warning(f"Failed to delete item type (not found): id={type_id}")
        return result

    @staticmethod
    def delete_item(item_id: int) -> bool:
        """Delete an item.

        Args:
            item_id: The item's ID.

        Returns:
            True if deleted, False if not found.
        """
        logger.info(f"Attempting to delete item: id={item_id}")
        result = ItemRepository.delete(item_id)
        if result:
            logger.info(f"Item deleted successfully: id={item_id}")
        else:
            logger.warning(f"Failed to delete item (not found): id={item_id}")
        return result

    @staticmethod
    def delete_items_by_serial_numbers(
        serial_numbers: List[str], notes: str = ""
    ) -> int:
        """Delete items by their serial numbers in a single transaction.

        Args:
            serial_numbers: List of serial numbers to delete.
            notes: Reason/notes for the deletion (for audit trail).

        Returns:
            Number of items deleted.
        """
        if not serial_numbers:
            return 0

        logger.info(f"Deleting {len(serial_numbers)} items by serial numbers")
        deleted_count = ItemRepository.delete_by_serial_numbers(serial_numbers, notes)
        logger.info(
            f"Deleted {deleted_count} of {len(serial_numbers)} items by serial numbers"
        )
        return deleted_count

    @staticmethod
    def add_quantity(
        item_id: int, quantity: int, notes: str = ""
    ) -> Optional[InventoryItem]:
        """Add quantity to an item.

        Args:
            item_id: The item's ID.
            quantity: Quantity to add.
            notes: Transaction notes (optional).

        Returns:
            The updated InventoryItem or None if not found.
        """
        logger.info(f"Adding quantity to item: id={item_id}, quantity={quantity}")
        db_item = ItemRepository.add_quantity(item_id, quantity, notes)
        if not db_item:
            return None
        item_type = ItemTypeRepository.get_by_id(db_item.item_type_id)
        return InventoryItem.from_db_models(db_item, item_type)

    @staticmethod
    def remove_quantity(
        item_id: int, quantity: int, notes: str = ""
    ) -> Optional[InventoryItem]:
        """Remove quantity from an item.

        Args:
            item_id: The item's ID.
            quantity: Quantity to remove.
            notes: Transaction notes (optional).

        Returns:
            The updated InventoryItem or None if not found.

        Raises:
            ValueError: If quantity would go below zero.
        """
        logger.info(f"Removing quantity from item: id={item_id}, quantity={quantity}")
        db_item = ItemRepository.remove_quantity(item_id, quantity, notes)
        if not db_item:
            return None
        item_type = ItemTypeRepository.get_by_id(db_item.item_type_id)
        return InventoryItem.from_db_models(db_item, item_type)


class SearchService:
    """Service for search operations with autocomplete and history."""

    @staticmethod
    def search(
        query: str,
        field: str = None,
        save_to_history: bool = True,
        location_id: int = None,
    ) -> List[InventoryItem]:
        """Search for items and optionally save to history.

        Args:
            query: Search query string.
            field: Field to search in ('item_type', 'sub_type', 'details', 'serial_number', or None for all).
            save_to_history: Whether to save this search to history.
            location_id: Filter results to this location. None = all locations.

        Returns:
            List of matching InventoryItem instances.
        """
        if save_to_history and query.strip():
            SearchHistoryRepository.add(query, field)

        db_items = ItemRepository.search(query, field, location_id=location_id)
        if not db_items:
            return []
        type_ids = list({item.item_type_id for item in db_items})
        type_map = ItemTypeRepository.get_by_ids(type_ids)
        return [
            InventoryItem.from_db_models(item, type_map[item.item_type_id])
            for item in db_items
            if item.item_type_id in type_map
        ]

    @staticmethod
    def get_autocomplete_suggestions(prefix: str, field: str = None) -> List[str]:
        """Get autocomplete suggestions for a search prefix.

        Args:
            prefix: The prefix to search for.
            field: Field to search in ('item_type', 'sub_type', 'details', 'serial_number', or None for all).

        Returns:
            List of unique suggestion strings.
        """
        if not prefix or len(prefix) < 1:
            return []
        return ItemRepository.get_autocomplete_suggestions(prefix, field)

    @staticmethod
    def get_search_history() -> List[Tuple[str, Optional[str]]]:
        """Get recent search history.

        Returns:
            List of tuples (search_query, search_field).
        """
        history = SearchHistoryRepository.get_recent()
        return [(h.search_query, h.search_field) for h in history]

    @staticmethod
    def clear_search_history() -> None:
        """Clear all search history."""
        SearchHistoryRepository.clear()


class TransactionService:
    """Service for transaction history operations."""

    @staticmethod
    def get_transactions_by_type_and_date_range(
        type_id: int,
        start_date: datetime,
        end_date: datetime,
        location_id: int = None,
    ) -> List[dict]:
        """Get transactions for an ItemType within a date range.

        When location_id is supplied only transactions relevant to that
        location are returned (regular transactions by location_id, transfer
        transactions by from_location_id or to_location_id).
        Pass location_id=None to return all transactions regardless of location.

        Args:
            type_id: ItemType ID.
            start_date: Start of the date range.
            end_date: End of the date range.
            location_id: Optional location filter.

        Returns:
            List of transaction dictionaries.
        """
        transactions = TransactionRepository.get_by_type_and_date_range(
            type_id, start_date, end_date, location_id=location_id
        )
        return [
            _transaction_to_dict(t)
            for t in transactions
        ]

    @staticmethod
    def get_recent_transactions(limit: int = 50) -> List[dict]:
        """Get recent transactions.

        Args:
            limit: Maximum number of transactions to return.

        Returns:
            List of transaction dictionaries.
        """
        transactions = TransactionRepository.get_recent(limit)
        return [_transaction_to_dict(t) for t in transactions]

    @staticmethod
    def get_transactions_by_location_and_date_range(
        location_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> List[dict]:
        """Get transactions at a specific location within a date range.

        Filters on Transaction.location_id (historically accurate).

        Args:
            location_id: Location ID.
            start_date: Start of the date range.
            end_date: End of the date range.

        Returns:
            List of transaction dictionaries.
        """
        transactions = TransactionRepository.get_by_location_and_date_range(
            location_id, start_date, end_date
        )
        return [_transaction_to_dict(t) for t in transactions]

    @staticmethod
    def get_all_transactions_by_date_range(
        start_date: datetime,
        end_date: datetime,
    ) -> List[dict]:
        """Get all transactions within a date range (no location filter).

        Args:
            start_date: Start of the date range.
            end_date: End of the date range.

        Returns:
            List of transaction dictionaries.
        """
        transactions = TransactionRepository.get_all_by_date_range(start_date, end_date)
        return [_transaction_to_dict(t) for t in transactions]

    @staticmethod
    def get_for_export(
        location_id: Optional[int] = None,
        item_type_ids: Optional[List[int]] = None,
    ) -> List[dict]:
        """Get transactions for export — no date range constraint.

        Args:
            location_id: Filter by location (OR across all location columns).
                         None returns all locations.
            item_type_ids: If given, restrict to these item type IDs only.

        Returns:
            List of transaction dictionaries.
        """
        transactions = TransactionRepository.get_for_export(
            location_id=location_id,
            item_type_ids=item_type_ids,
        )
        return [_transaction_to_dict(t) for t in transactions]


def _transaction_to_dict(trans) -> dict:
    """Convert a Transaction to a dictionary.

    For TRANSFER transactions, adds a ``transfer_side`` key: ``"source"`` if
    ``trans.location_id`` matches ``from_location_id``, ``"destination"`` if it
    matches ``to_location_id``.  The two TRANSFER records per transfer each
    self-identify their own side via their stored ``location_id``.
    """
    d = {
        "id": trans.id,
        "item_type_id": trans.item_type_id,
        "type": trans.transaction_type.value,
        "quantity_change": trans.quantity_change,
        "quantity_before": trans.quantity_before,
        "quantity_after": trans.quantity_after,
        "notes": trans.notes,
        "serial_number": trans.serial_number,
        "location_id": trans.location_id,
        "from_location_id": trans.from_location_id,
        "to_location_id": trans.to_location_id,
        "created_at": trans.created_at,
    }
    if trans.transaction_type.value == "transfer":
        if trans.from_location_id == trans.location_id:
            d["transfer_side"] = "source"
        elif trans.to_location_id == trans.location_id:
            d["transfer_side"] = "destination"
    return d
