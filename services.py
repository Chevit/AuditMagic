"""Service layer for business logic operations."""

from datetime import datetime
from typing import List, Optional, Tuple

from logger import logger
from models import TransactionType
from repositories import ItemRepository, ItemTypeRepository, SearchHistoryRepository, TransactionRepository
from ui_entities.inventory_item import InventoryItem
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
        notes: str = "",
        details: str = ""
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
            notes: Item notes
            details: Type details (description)

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
                notes=notes
            )

            logger.info(f"Item created successfully: id={db_item.id}")
            return InventoryItem.from_db_models(db_item, item_type)
        except Exception as e:
            logger.error(f"Failed to create item: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def create_or_merge_item(
        item_type: str,
        quantity: int,
        sub_type: str = "",
        serial_number: str = "",
        details: str = "",
    ) -> Tuple[InventoryItem, bool]:
        """Create a new item or merge with existing item if fields match.

        If an item with the same item_type, sub_type, serial_number, and details exists,
        the quantity will be added to the existing item and a transaction will be created.

        Args:
            item_type: Type of the item (required)
            quantity: Quantity to add (required)
            sub_type: Sub-type of the item (optional)
            serial_number: Serial number (optional)
            details: Additional details (optional)

        Returns:
            Tuple of (InventoryItem, was_merged: bool).
            was_merged is True if quantity was added to an existing item.
        """
        # Check for existing item with same fields
        existing = ItemRepository.find_by_fields(
            item_type=item_type,
            sub_type=sub_type,
            serial_number=serial_number,
            details=details,
        )

        if existing:
            # Add quantity to existing item (creates transaction)
            updated = ItemRepository.add_quantity(
                item_id=existing.id,
                quantity=quantity,
                notes=tr("transaction.notes.merged"),
            )
            return InventoryItem.from_db_model(updated), True

        # Create new item
        db_item = ItemRepository.create(
            item_type=item_type,
            quantity=quantity,
            sub_type=sub_type,
            serial_number=serial_number,
            details=details,
        )
        return InventoryItem.from_db_model(db_item), False

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
        item_type: str = None,
        sub_type: str = None,
        serial_number: str = None,
        details: str = None,
    ) -> Optional[InventoryItem]:
        """Update an item's properties.

        Args:
            item_id: The item's ID.
            item_type: New item type (optional)
            sub_type: New sub-type (optional)
            serial_number: New serial number (optional)
            details: New details (optional)

        Returns:
            The updated InventoryItem or None if not found.
        """
        db_item = ItemRepository.update(
            item_id=item_id,
            item_type=item_type,
            sub_type=sub_type,
            serial_number=serial_number,
            details=details,
        )
        return InventoryItem.from_db_model(db_item) if db_item else None

    @staticmethod
    def edit_item(
        item_id: int,
        item_type: str,
        quantity: int,
        sub_type: str = "",
        serial_number: str = "",
        details: str = "",
        edit_reason: str = "",
    ) -> Optional[InventoryItem]:
        """Edit an item's properties with full transaction logging.

        DEPRECATED: Use edit_item_hierarchical() for hierarchical model.

        Args:
            item_id: The item's ID.
            item_type: New item type.
            quantity: New quantity.
            sub_type: New sub-type.
            serial_number: New serial number.
            details: New item details.
            edit_reason: Reason for the edit (required).

        Returns:
            The updated InventoryItem or None if not found.
        """
        logger.info(f"Editing item: id={item_id}, reason='{edit_reason}'")
        try:
            db_item = ItemRepository.edit_item(
                item_id=item_id,
                item_type=item_type,
                sub_type=sub_type,
                quantity=quantity,
                serial_number=serial_number,
                details=details,
                edit_reason=edit_reason,
            )
            if db_item:
                logger.info(f"Item edited successfully: id={item_id}")
                return InventoryItem.from_db_model(db_item)
            logger.warning(f"Item not found for edit: id={item_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to edit item: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def edit_item_hierarchical(
        item_id: int,
        type_name: str = None,
        sub_type: str = None,
        quantity: int = None,
        serial_number: str = None,
        location: str = None,
        condition: str = None,
        notes: str = None,
        details: str = None,
        edit_reason: str = "",
    ) -> Optional[InventoryItem]:
        """Edit an item's properties with hierarchical model support.

        For serialized items:
        - Type and sub_type cannot be changed (affects the ItemType definition)
        - Quantity must remain 1
        - Serial number can be updated

        For non-serialized items:
        - Type and sub_type can be changed (creates/uses different ItemType)
        - Quantity can be changed
        - Serial number must remain None

        Args:
            item_id: The item's ID.
            type_name: New type name (only for non-serialized items).
            sub_type: New sub-type (only for non-serialized items).
            quantity: New quantity.
            serial_number: New serial number (only for serialized items).
            location: New location.
            condition: New condition.
            notes: New notes (item-specific).
            details: New details (type-level).
            edit_reason: Reason for the edit (required).

        Returns:
            The updated InventoryItem or None if not found.

        Raises:
            ValueError: If validation fails.
        """
        logger.info(f"Editing item (hierarchical): id={item_id}, reason='{edit_reason}'")
        try:
            # Get current item to check serialization status
            current_item = ItemRepository.get_by_id(item_id)
            if not current_item:
                logger.warning(f"Item not found for edit: id={item_id}")
                return None

            # Get current item type
            from repositories import ItemTypeRepository
            current_type = ItemTypeRepository.get_by_id(current_item.item_type_id)
            if not current_type:
                logger.error(f"ItemType not found: id={current_item.item_type_id}")
                return None

            is_serialized = current_type.is_serialized

            # Validation for serialized items
            if is_serialized:
                if type_name and type_name != current_type.name:
                    raise ValueError("Cannot change type of serialized item")
                if sub_type and sub_type != current_type.sub_type:
                    raise ValueError("Cannot change sub-type of serialized item")
                if quantity and quantity != 1:
                    raise ValueError("Quantity must be 1 for serialized items")
                if serial_number == "":  # Empty string means removing SN
                    raise ValueError("Serial number required for serialized items")

            # Validation for non-serialized items
            else:
                if serial_number:
                    raise ValueError("Serial number not allowed for non-serialized items")
                if quantity and quantity < 1:
                    raise ValueError("Quantity must be at least 1")

            # If type/subtype changed for non-serialized item, get or create new ItemType
            new_type_id = current_item.item_type_id
            if not is_serialized and (type_name or sub_type):
                new_type_name = type_name if type_name else current_type.name
                new_sub_type = sub_type if sub_type is not None else current_type.sub_type
                new_details = details if details is not None else current_type.details

                # Get or create the new ItemType
                new_type = ItemTypeRepository.get_or_create(
                    name=new_type_name,
                    sub_type=new_sub_type,
                    is_serialized=False,  # Non-serialized
                    details=new_details
                )
                new_type_id = new_type.id

            # Update the item
            updated_values = {}
            if new_type_id != current_item.item_type_id:
                updated_values['item_type_id'] = new_type_id
            if quantity is not None:
                updated_values['quantity'] = quantity
            if serial_number is not None:
                updated_values['serial_number'] = serial_number
            if location is not None:
                updated_values['location'] = location
            if condition is not None:
                updated_values['condition'] = condition
            if notes is not None:
                updated_values['notes'] = notes

            # Update item in repository
            db_item = ItemRepository.update_hierarchical(
                item_id=item_id,
                edit_reason=edit_reason,
                **updated_values
            )

            if db_item:
                logger.info(f"Item edited successfully: id={item_id}")
                # Get the updated ItemType
                updated_type = ItemTypeRepository.get_by_id(db_item.item_type_id)
                return InventoryItem.from_db_models(db_item, updated_type)

            logger.warning(f"Item not found after edit: id={item_id}")
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
        return InventoryItem.from_db_model(db_item) if db_item else None

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
        return InventoryItem.from_db_model(db_item) if db_item else None


class SearchService:
    """Service for search operations with autocomplete and history."""

    @staticmethod
    def search(
        query: str, field: str = None, save_to_history: bool = True
    ) -> List[InventoryItem]:
        """Search for items and optionally save to history.

        Args:
            query: Search query string.
            field: Field to search in ('item_type', 'sub_type', 'notes', or None for all).
            save_to_history: Whether to save this search to history.

        Returns:
            List of matching InventoryItem instances.
        """
        if save_to_history and query.strip():
            SearchHistoryRepository.add(query, field)

        db_items = ItemRepository.search(query, field)
        return [InventoryItem.from_db_model(item) for item in db_items]

    @staticmethod
    def get_autocomplete_suggestions(prefix: str, field: str = None) -> List[str]:
        """Get autocomplete suggestions for a search prefix.

        Args:
            prefix: The prefix to search for.
            field: Field to search in ('item_type', 'sub_type', 'notes', or None for all).

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
        start_date: datetime, end_date: datetime, item_id: int = None
    ) -> List[dict]:
        """Get transactions within a date range.

        Args:
            start_date: Start of the date range.
            end_date: End of the date range.
            item_id: Optional item ID to filter by.

        Returns:
            List of transaction dictionaries.
        """
        transactions = TransactionRepository.get_by_date_range(
            start_date, end_date, item_id
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
        "created_at": trans.created_at,
    }
