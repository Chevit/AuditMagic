"""Service layer for business logic operations."""

from datetime import datetime
from typing import List, Optional, Tuple

from logger import logger
from models import TransactionType
from repositories import ItemRepository, ItemTypeRepository, SearchHistoryRepository, TransactionRepository
from ui_entities.inventory_item import GroupedInventoryItem, InventoryItem
from ui_entities.translations import tr


class InventoryService:
    """Service for inventory management operations."""

    @staticmethod
    def create_item(
        item_type_name: str,
        item_sub_type: str = "",
        quantity: int = 1,
        is_serialized: bool = False,
        serial_number: str = None,
        location: str = "",
        condition: str = "",
        details: str = "",
        transaction_notes: str = "",
    ) -> InventoryItem:
        """Create a new inventory item.

        Args:
            item_type_name: Type name
            item_sub_type: Sub-type name
            quantity: Initial quantity
            is_serialized: Whether this type has serial numbers
            serial_number: Serial number (required if serialized)
            location: Storage location
            condition: Item condition
            details: Type details (description)
            transaction_notes: Optional notes for the initial ADD transaction

        Returns:
            The created InventoryItem.
        """
        logger.info(f"Creating new item: type='{item_type_name}', sub_type='{item_sub_type}', qty={quantity}")
        try:
            # Get or create item type
            item_type = ItemTypeRepository.get_or_create(
                name=item_type_name,
                sub_type=item_sub_type,
                is_serialized=is_serialized,
                details=details
            )

            # Create item instance
            db_item = ItemRepository.create(
                item_type_id=item_type.id,
                quantity=quantity,
                serial_number=serial_number,
                location=location,
                condition=condition,
                transaction_notes=transaction_notes or None,
            )

            logger.info(f"Item created successfully: id={db_item.id}")
            return InventoryItem.from_db_models(db_item, item_type)
        except Exception as e:
            logger.error(f"Failed to create item: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def create_or_merge_item(
        item_type_name: str,
        quantity: int,
        sub_type: str = "",
        is_serialized: bool = False,
        serial_number: str = "",
        details: str = "",
        location: str = "",
        condition: str = "",
        transaction_notes: str = "",
    ) -> Tuple[InventoryItem, bool]:
        """Create a new item or merge with existing item if type matches.

        For non-serialized items: If an item with the same type exists, quantity is added.
        For serialized items: A new item is always created (serial numbers are unique).

        Args:
            item_type_name: Type name of the item (required)
            quantity: Quantity to add (required)
            sub_type: Sub-type of the item (optional)
            is_serialized: Whether items have serial numbers
            serial_number: Serial number (required if serialized)
            details: Type details/description (optional)
            location: Storage location (optional)
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
            details=details
        )

        # For serialized items, always create new (each serial is unique)
        if is_serialized or serial_number:
            db_item = ItemRepository.create(
                item_type_id=item_type.id,
                quantity=1,
                serial_number=serial_number,
                location=location,
                condition=condition,
                transaction_notes=transaction_notes or None,
            )
            return InventoryItem.from_db_models(db_item, item_type), False

        # For non-serialized, check for existing item of same type
        existing = ItemRepository.find_by_type_and_serial(
            item_type_id=item_type.id,
            serial_number=None
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
            location=location,
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
        result = []

        for db_item in db_items:
            item_type = ItemTypeRepository.get_by_id(db_item.item_type_id)
            if item_type:
                result.append(InventoryItem.from_db_models(db_item, item_type))

        return result

    @staticmethod
    def get_all_items_grouped() -> List[GroupedInventoryItem]:
        """Get all inventory items grouped by type.

        Returns items aggregated by ItemType, showing total quantity
        and all serial numbers for each type.

        Returns:
            List of GroupedInventoryItem instances.
        """
        types_with_items = ItemTypeRepository.get_all_with_items()
        result = []

        for item_type, items in types_with_items:
            grouped = GroupedInventoryItem.from_item_type_and_items(item_type, items)
            result.append(grouped)

        return result

    @staticmethod
    def get_serialized_items_grouped() -> List[GroupedInventoryItem]:
        """Get serialized inventory items grouped by type.

        Returns only items belonging to serialized ItemTypes,
        aggregated with their serial numbers.

        Returns:
            List of GroupedInventoryItem instances for serialized types only.
        """
        types_with_items = ItemTypeRepository.get_serialized_with_items()
        result = []

        for item_type, items in types_with_items:
            grouped = GroupedInventoryItem.from_item_type_and_items(item_type, items)
            result.append(grouped)

        return result

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
        location: str = None,
        condition: str = None,
    ) -> Optional[InventoryItem]:
        """Update an item's instance properties.

        Note: To change type-related fields (name, sub_type, details), use edit_item.

        Args:
            item_id: The item's ID.
            serial_number: New serial number (optional)
            location: New location (optional)
            condition: New condition (optional)

        Returns:
            The updated InventoryItem or None if not found.
        """
        db_item = ItemRepository.update(
            item_id=item_id,
            serial_number=serial_number,
            location=location,
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
        location: str = "",
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
            location: Storage location.
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
                details=details
            )

            db_item = ItemRepository.edit_item(
                item_id=item_id,
                item_type_id=item_type.id,
                quantity=quantity,
                serial_number=serial_number,
                location=location,
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
    def delete_items_by_serial_numbers(serial_numbers: List[str], notes: str = "") -> int:
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
        logger.info(f"Deleted {deleted_count} of {len(serial_numbers)} items by serial numbers")
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
        query: str, field: str = None, save_to_history: bool = True
    ) -> List[InventoryItem]:
        """Search for items and optionally save to history.

        Args:
            query: Search query string.
            field: Field to search in ('item_type', 'sub_type', 'details', 'serial_number', or None for all).
            save_to_history: Whether to save this search to history.

        Returns:
            List of matching InventoryItem instances.
        """
        if save_to_history and query.strip():
            SearchHistoryRepository.add(query, field)

        db_items = ItemRepository.search(query, field)
        result = []
        for item in db_items:
            item_type = ItemTypeRepository.get_by_id(item.item_type_id)
            if item_type:
                result.append(InventoryItem.from_db_models(item, item_type))
        return result

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
    def get_item_transactions(item_id: int) -> List[dict]:
        """Get all transactions for an item.

        Args:
            item_id: The item's ID.

        Returns:
            List of transaction dictionaries.
        """
        transactions = TransactionRepository.get_by_item(item_id)
        return [_transaction_to_dict(t) for t in transactions]

    @staticmethod
    def get_transactions_by_date_range(
        start_date: datetime,
        end_date: datetime,
        item_id: int = None,
        item_ids: List[int] = None,
    ) -> List[dict]:
        """Get transactions within a date range.

        Args:
            start_date: Start of the date range.
            end_date: End of the date range.
            item_id: Optional single item ID to filter by.
            item_ids: Optional list of item IDs to filter by (overrides item_id).

        Returns:
            List of transaction dictionaries.
        """
        transactions = TransactionRepository.get_by_date_range(
            start_date, end_date, item_id, item_ids
        )
        return [_transaction_to_dict(t) for t in transactions]

    @staticmethod
    def get_recent_transactions(limit: int = 50, item_id: int = None) -> List[dict]:
        """Get recent transactions.

        Args:
            limit: Maximum number of transactions to return.
            item_id: Optional item ID to filter by.

        Returns:
            List of transaction dictionaries.
        """
        transactions = TransactionRepository.get_recent(limit, item_id)
        return [_transaction_to_dict(t) for t in transactions]


def _transaction_to_dict(trans) -> dict:
    """Convert a Transaction to a dictionary."""
    return {
        "id": trans.id,
        "item_id": trans.item_id,
        "type": trans.transaction_type.value,
        "quantity_change": trans.quantity_change,
        "quantity_before": trans.quantity_before,
        "quantity_after": trans.quantity_after,
        "notes": trans.notes,
        "serial_number": trans.serial_number,
        "created_at": trans.created_at,
    }
