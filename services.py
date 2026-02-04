"""Service layer for business logic operations."""
from datetime import datetime
from typing import List, Optional, Tuple

from models import TransactionType
from repositories import ItemRepository, TransactionRepository, SearchHistoryRepository
from ui_entities.inventory_item import InventoryItem


class InventoryService:
    """Service for inventory management operations."""

    @staticmethod
    def create_item(item_type: str, quantity: int, sub_type: str = "",
                    serial_number: str = "", notes: str = "") -> InventoryItem:
        """Create a new inventory item.

        Args:
            item_type: Type of the item (required)
            quantity: Initial quantity (required)
            sub_type: Sub-type of the item (optional)
            serial_number: Serial number (optional)
            notes: Additional notes (optional)

        Returns:
            The created InventoryItem.
        """
        db_item = ItemRepository.create(
            item_type=item_type,
            quantity=quantity,
            sub_type=sub_type,
            serial_number=serial_number,
            notes=notes
        )
        return InventoryItem.from_db_model(db_item)

    @staticmethod
    def get_item(item_id: int) -> Optional[InventoryItem]:
        """Get an item by ID.

        Args:
            item_id: The item's ID.

        Returns:
            The InventoryItem or None if not found.
        """
        db_item = ItemRepository.get_by_id(item_id)
        return InventoryItem.from_db_model(db_item) if db_item else None

    @staticmethod
    def get_all_items() -> List[InventoryItem]:
        """Get all inventory items.

        Returns:
            List of all InventoryItem instances.
        """
        db_items = ItemRepository.get_all()
        return [InventoryItem.from_db_model(item) for item in db_items]

    @staticmethod
    def update_item(item_id: int, item_type: str = None, sub_type: str = None,
                    serial_number: str = None, notes: str = None) -> Optional[InventoryItem]:
        """Update an item's properties.

        Args:
            item_id: The item's ID.
            item_type: New item type (optional)
            sub_type: New sub-type (optional)
            serial_number: New serial number (optional)
            notes: New notes (optional)

        Returns:
            The updated InventoryItem or None if not found.
        """
        db_item = ItemRepository.update(
            item_id=item_id,
            item_type=item_type,
            sub_type=sub_type,
            serial_number=serial_number,
            notes=notes
        )
        return InventoryItem.from_db_model(db_item) if db_item else None

    @staticmethod
    def delete_item(item_id: int) -> bool:
        """Delete an item.

        Args:
            item_id: The item's ID.

        Returns:
            True if deleted, False if not found.
        """
        return ItemRepository.delete(item_id)

    @staticmethod
    def add_quantity(item_id: int, quantity: int, notes: str = "") -> Optional[InventoryItem]:
        """Add quantity to an item.

        Args:
            item_id: The item's ID.
            quantity: Quantity to add.
            notes: Transaction notes (optional).

        Returns:
            The updated InventoryItem or None if not found.
        """
        db_item = ItemRepository.add_quantity(item_id, quantity, notes)
        return InventoryItem.from_db_model(db_item) if db_item else None

    @staticmethod
    def remove_quantity(item_id: int, quantity: int, notes: str = "") -> Optional[InventoryItem]:
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
        db_item = ItemRepository.remove_quantity(item_id, quantity, notes)
        return InventoryItem.from_db_model(db_item) if db_item else None


class SearchService:
    """Service for search operations with autocomplete and history."""

    @staticmethod
    def search(query: str, field: str = None, save_to_history: bool = True) -> List[InventoryItem]:
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
    def get_transactions_by_date_range(start_date: datetime, end_date: datetime,
                                       item_id: int = None) -> List[dict]:
        """Get transactions within a date range.

        Args:
            start_date: Start of the date range.
            end_date: End of the date range.
            item_id: Optional item ID to filter by.

        Returns:
            List of transaction dictionaries.
        """
        transactions = TransactionRepository.get_by_date_range(start_date, end_date, item_id)
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
        'id': trans.id,
        'item_id': trans.item_id,
        'type': trans.transaction_type.value,
        'quantity_change': trans.quantity_change,
        'quantity_before': trans.quantity_before,
        'quantity_after': trans.quantity_after,
        'notes': trans.notes,
        'created_at': trans.created_at
    }
