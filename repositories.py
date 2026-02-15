"""Repository layer for database operations."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from db import session_scope
from models import Item, Transaction, TransactionType, SearchHistory
from ui_entities.translations import tr
from logger import logger


class ItemRepository:
    """Repository for Item CRUD operations."""

    @staticmethod
    def create(
        item_type: str,
        quantity: int,
        sub_type: str = None,
        serial_number: str = None,
        details: str = None,
    ) -> Item:
        """Create a new item and record the initial transaction.

        Args:
            item_type: Type of the item (required)
            quantity: Initial quantity (required)
            sub_type: Sub-type of the item (optional)
            serial_number: Serial number (optional)
            details: Additional details (optional)

        Returns:
            The created Item instance.
        """
        logger.debug(
            f"Repository: Creating item type='{item_type}', quantity={quantity}"
        )
        with session_scope() as session:
            item = Item(
                item_type=item_type,
                sub_type=sub_type or "",
                quantity=quantity,
                serial_number=serial_number or "",
                details=details or "",
            )
            session.add(item)
            session.flush()  # Get the ID before creating transaction

            # Record initial transaction
            if quantity > 0:
                transaction = Transaction(
                    item_id=item.id,
                    transaction_type=TransactionType.ADD,
                    quantity_change=quantity,
                    quantity_before=0,
                    quantity_after=quantity,
                    notes=notes or tr("transaction.notes.initial"),
                )
                session.add(transaction)

            session.commit()
            # Detach from session before returning
            session.refresh(item)
            logger.debug(f"Repository: Item created with id={item.id}")
            return _detach_item(item)

    @staticmethod
    def get_by_id(item_id: int) -> Optional[Item]:
        """Get an item by its ID.

        Args:
            item_id: The item's ID.

        Returns:
            The Item instance or None if not found.
        """
        with session_scope() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            return _detach_item(item) if item else None

    @staticmethod
    def get_all() -> List[Item]:
        """Get all items.

        Returns:
            List of all Item instances.
        """
        with session_scope() as session:
            items = session.query(Item).order_by(Item.item_type, Item.sub_type).all()
            return [_detach_item(item) for item in items]

    @staticmethod
    def update(
        item_id: int,
        item_type: str = None,
        sub_type: str = None,
        serial_number: str = None,
        details: str = None,
    ) -> Optional[Item]:
        """Update an item's properties (not quantity - use add_quantity/remove_quantity).

        Args:
            item_id: The item's ID.
            item_type: New item type (optional)
            sub_type: New sub-type (optional)
            serial_number: New serial number (optional)
            details: New details (optional)

        Returns:
            The updated Item instance or None if not found.
        """
        with session_scope() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                return None

            if item_type is not None:
                item.item_type = item_type
            if sub_type is not None:
                item.sub_type = sub_type
            if serial_number is not None:
                item.serial_number = serial_number
            if details is not None:
                item.details = details

            session.commit()
            session.refresh(item)
            return _detach_item(item)

    @staticmethod
    def edit_item(
        item_id: int,
        item_type: str,
        sub_type: str,
        quantity: int,
        serial_number: str,
        details: str,
        edit_reason: str,
    ) -> Optional[Item]:
        """Edit an item's properties and quantity, recording all changes as transactions.

        Args:
            item_id: The item's ID.
            item_type: New item type.
            sub_type: New sub-type.
            quantity: New quantity.
            serial_number: New serial number.
            details: New item details.
            edit_reason: Reason for the edit (required, stored in transaction notes).

        Returns:
            The updated Item instance or None if not found.
        """
        with session_scope() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                logger.warning(f"Repository: Item not found for edit: id={item_id}")
                return None

            quantity_before = item.quantity

            # Apply field changes
            item.item_type = item_type
            item.sub_type = sub_type
            item.quantity = quantity
            item.serial_number = serial_number
            item.details = details

            # Record a single EDIT transaction capturing all changes
            quantity_diff = quantity - quantity_before
            edit_transaction = Transaction(
                item_id=item.id,
                transaction_type=TransactionType.EDIT,
                quantity_change=abs(quantity_diff),
                quantity_before=quantity_before,
                quantity_after=quantity,
                notes=edit_reason,
            )
            session.add(edit_transaction)

            session.commit()
            session.refresh(item)
            logger.debug(
                f"Repository: Item edited: id={item_id}, reason='{edit_reason}'"
            )
            return _detach_item(item)

    @staticmethod
    def delete(item_id: int) -> bool:
        """Delete an item and all its transactions.

        Args:
            item_id: The item's ID.

        Returns:
            True if deleted, False if not found.
        """
        with session_scope() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                logger.warning(f"Repository: Item not found for deletion: id={item_id}")
                return False
            session.delete(item)
            logger.debug(f"Repository: Item deleted: id={item_id}")
            return True

    @staticmethod
    def add_quantity(item_id: int, quantity: int, notes: str = None) -> Optional[Item]:
        """Add quantity to an item and record the transaction.

        Args:
            item_id: The item's ID.
            quantity: Quantity to add (must be positive).
            notes: Transaction notes (optional).

        Returns:
            The updated Item instance or None if not found.
        """
        if quantity <= 0:
            raise ValueError("Quantity to add must be positive")

        with session_scope() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                logger.warning(
                    f"Repository: Item not found for add_quantity: id={item_id}"
                )
                return None

            quantity_before = item.quantity
            item.quantity += quantity

            transaction = Transaction(
                item_id=item.id,
                transaction_type=TransactionType.ADD,
                quantity_change=quantity,
                quantity_before=quantity_before,
                quantity_after=item.quantity,
                notes=notes or "",
            )
            session.add(transaction)
            session.commit()
            session.refresh(item)
            logger.debug(
                f"Repository: Added {quantity} to item id={item_id}: {quantity_before} -> {item.quantity}"
            )
            return _detach_item(item)

    @staticmethod
    def remove_quantity(
        item_id: int, quantity: int, notes: str = None
    ) -> Optional[Item]:
        """Remove quantity from an item and record the transaction.

        Args:
            item_id: The item's ID.
            quantity: Quantity to remove (must be positive).
            notes: Transaction notes (optional).

        Returns:
            The updated Item instance or None if not found.

        Raises:
            ValueError: If quantity would go below zero.
        """
        if quantity <= 0:
            raise ValueError("Quantity to remove must be positive")

        with session_scope() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                logger.warning(
                    f"Repository: Item not found for remove_quantity: id={item_id}"
                )
                return None

            if item.quantity < quantity:
                logger.warning(
                    f"Repository: Cannot remove {quantity} from item id={item_id}, only {item.quantity} available"
                )
                raise ValueError(
                    f"Cannot remove {quantity} items. Only {item.quantity} available."
                )

            quantity_before = item.quantity
            item.quantity -= quantity

            transaction = Transaction(
                item_id=item.id,
                transaction_type=TransactionType.REMOVE,
                quantity_change=quantity,
                quantity_before=quantity_before,
                quantity_after=item.quantity,
                notes=notes or "",
            )
            session.add(transaction)
            session.commit()
            session.refresh(item)
            logger.debug(
                f"Repository: Removed {quantity} from item id={item_id}: {quantity_before} -> {item.quantity}"
            )
            return _detach_item(item)

    @staticmethod
    def find_by_fields(
        item_type: str, sub_type: str = "", serial_number: str = "", details: str = ""
    ) -> Optional[Item]:
        """Find an existing item with matching fields (excluding quantity).

        Args:
            item_type: Type of the item.
            sub_type: Sub-type of the item.
            serial_number: Serial number.
            details: Additional details.

        Returns:
            The matching Item instance or None if not found.
        """
        with session_scope() as session:
            item = (
                session.query(Item)
                .filter(
                    Item.item_type == item_type,
                    Item.sub_type == (sub_type or ""),
                    Item.serial_number == (serial_number or ""),
                    Item.details == (details or ""),
                )
                .first()
            )
            return _detach_item(item) if item else None

    @staticmethod
    def search(query: str, field: str = None) -> List[Item]:
        """Search items by query string.

        Args:
            query: Search query string.
            field: Field to search in ('item_type', 'sub_type', 'details', or None for all).

        Returns:
            List of matching Item instances.
        """
        logger.debug(f"Repository: Searching items with query='{query}', field={field}")
        with session_scope() as session:
            search_pattern = f"%{query}%"

            if field == "item_type":
                items = (
                    session.query(Item)
                    .filter(Item.item_type.ilike(search_pattern))
                    .all()
                )
            elif field == "sub_type":
                items = (
                    session.query(Item)
                    .filter(Item.sub_type.ilike(search_pattern))
                    .all()
                )
            elif field == "details":
                items = (
                    session.query(Item).filter(Item.details.ilike(search_pattern)).all()
                )
            else:
                # Search in all fields
                items = (
                    session.query(Item)
                    .filter(
                        or_(
                            Item.item_type.ilike(search_pattern),
                            Item.sub_type.ilike(search_pattern),
                            Item.details.ilike(search_pattern),
                        )
                    )
                    .all()
                )

            return [_detach_item(item) for item in items]

    @staticmethod
    def get_autocomplete_suggestions(
        prefix: str, field: str = None, limit: int = 10
    ) -> List[str]:
        """Get autocomplete suggestions for a search prefix.

        Args:
            prefix: The prefix to search for.
            field: Field to search in ('item_type', 'sub_type', 'details', or None for all).
            limit: Maximum number of suggestions.

        Returns:
            List of unique suggestion strings.
        """
        with session_scope() as session:
            suggestions = set()
            search_pattern = f"{prefix}%"

            if field == "item_type" or field is None:
                types = (
                    session.query(Item.item_type)
                    .filter(Item.item_type.ilike(search_pattern))
                    .distinct()
                    .limit(limit)
                    .all()
                )
                suggestions.update(t[0] for t in types if t[0])

            if field == "sub_type" or field is None:
                sub_types = (
                    session.query(Item.sub_type)
                    .filter(Item.sub_type.ilike(search_pattern))
                    .distinct()
                    .limit(limit)
                    .all()
                )
                suggestions.update(t[0] for t in sub_types if t[0])

            if field == "details" or field is None:
                # For details, extract words that start with the prefix
                details_rows = (
                    session.query(Item.details)
                    .filter(Item.details.ilike(f"%{prefix}%"))
                    .all()
                )
                for (detail,) in details_rows:
                    if detail:
                        words = detail.split()
                        for word in words:
                            if word.lower().startswith(prefix.lower()):
                                suggestions.add(word)

            return sorted(list(suggestions))[:limit]


class TransactionRepository:
    """Repository for Transaction operations."""

    @staticmethod
    def get_by_item(item_id: int) -> List[Transaction]:
        """Get all transactions for an item.

        Args:
            item_id: The item's ID.

        Returns:
            List of Transaction instances ordered by date (newest first).
        """
        with session_scope() as session:
            transactions = (
                session.query(Transaction)
                .filter(Transaction.item_id == item_id)
                .order_by(Transaction.created_at.desc())
                .all()
            )
            return [_detach_transaction(t) for t in transactions]

    @staticmethod
    def get_by_date_range(
        start_date: datetime, end_date: datetime, item_id: int = None
    ) -> List[Transaction]:
        """Get transactions within a date range.

        Args:
            start_date: Start of the date range.
            end_date: End of the date range.
            item_id: Optional item ID to filter by.

        Returns:
            List of Transaction instances ordered by date (newest first).
        """
        with session_scope() as session:
            query = session.query(Transaction).filter(
                Transaction.created_at >= start_date, Transaction.created_at <= end_date
            )

            if item_id is not None:
                query = query.filter(Transaction.item_id == item_id)

            transactions = query.order_by(Transaction.created_at.desc()).all()
            return [_detach_transaction(t) for t in transactions]

    @staticmethod
    def get_recent(limit: int = 50, item_id: int = None) -> List[Transaction]:
        """Get recent transactions.

        Args:
            limit: Maximum number of transactions to return.
            item_id: Optional item ID to filter by.

        Returns:
            List of Transaction instances ordered by date (newest first).
        """
        with session_scope() as session:
            query = session.query(Transaction)

            if item_id is not None:
                query = query.filter(Transaction.item_id == item_id)

            transactions = (
                query.order_by(Transaction.created_at.desc()).limit(limit).all()
            )
            return [_detach_transaction(t) for t in transactions]


class SearchHistoryRepository:
    """Repository for SearchHistory operations."""

    MAX_HISTORY = 5

    @staticmethod
    def add(search_query: str, search_field: str = None) -> SearchHistory:
        """Add a search to history, keeping only the last 5.

        Args:
            search_query: The search query string.
            search_field: The field that was searched (optional).

        Returns:
            The created SearchHistory instance.
        """
        with session_scope() as session:
            # Check if this exact search already exists
            existing = (
                session.query(SearchHistory)
                .filter(
                    SearchHistory.search_query == search_query,
                    SearchHistory.search_field == search_field,
                )
                .first()
            )

            if existing:
                # Update timestamp to move it to the top
                existing.created_at = datetime.now(timezone.utc)
                session.commit()
                return _detach_search_history(existing)

            # Add new search
            history = SearchHistory(
                search_query=search_query, search_field=search_field
            )
            session.add(history)
            session.flush()

            # Keep only the last 5 entries
            all_history = (
                session.query(SearchHistory)
                .order_by(SearchHistory.created_at.desc())
                .all()
            )

            if len(all_history) > SearchHistoryRepository.MAX_HISTORY:
                for old_entry in all_history[SearchHistoryRepository.MAX_HISTORY :]:
                    session.delete(old_entry)

            session.commit()
            return _detach_search_history(history)

    @staticmethod
    def get_recent(limit: int = 5) -> List[SearchHistory]:
        """Get recent search history.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of SearchHistory instances ordered by date (newest first).
        """
        with session_scope() as session:
            history = (
                session.query(SearchHistory)
                .order_by(SearchHistory.created_at.desc())
                .limit(limit)
                .all()
            )
            return [_detach_search_history(h) for h in history]

    @staticmethod
    def clear() -> None:
        """Clear all search history."""
        with session_scope() as session:
            session.query(SearchHistory).delete()


# Helper functions to detach objects from session
def _detach_item(item: Item) -> Item:
    """Create a detached copy of an Item."""
    if item is None:
        return None
    return Item(
        id=item.id,
        item_type=item.item_type,
        sub_type=item.sub_type,
        quantity=item.quantity,
        serial_number=item.serial_number,
        details=item.details,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _detach_transaction(trans: Transaction) -> Transaction:
    """Create a detached copy of a Transaction."""
    if trans is None:
        return None
    return Transaction(
        id=trans.id,
        item_id=trans.item_id,
        transaction_type=trans.transaction_type,
        quantity_change=trans.quantity_change,
        quantity_before=trans.quantity_before,
        quantity_after=trans.quantity_after,
        notes=trans.notes,
        created_at=trans.created_at,
    )


def _detach_search_history(history: SearchHistory) -> SearchHistory:
    """Create a detached copy of a SearchHistory."""
    if history is None:
        return None
    return SearchHistory(
        id=history.id,
        search_query=history.search_query,
        search_field=history.search_field,
        created_at=history.created_at,
    )
