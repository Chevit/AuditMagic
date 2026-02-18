"""Repository layer for database operations."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from db import session_scope
from logger import logger
from models import Item, ItemType, SearchHistory, Transaction, TransactionType
from ui_entities.translations import tr


class ItemTypeRepository:
    """Repository for ItemType CRUD operations."""

    @staticmethod
    def create(
        name: str,
        sub_type: str = "",
        is_serialized: bool = False,
        details: str = ""
    ) -> ItemType:
        """Create a new item type.

        Args:
            name: Type name (required)
            sub_type: Sub-type name (optional)
            is_serialized: Whether items of this type have serial numbers
            details: Description of this type

        Returns:
            The created ItemType instance.
        """
        logger.debug(f"Repository: Creating item type name='{name}', sub_type='{sub_type}'")
        with session_scope() as session:
            item_type = ItemType(
                name=name,
                sub_type=sub_type or "",
                is_serialized=is_serialized,
                details=details or ""
            )
            session.add(item_type)
            session.flush()
            session.refresh(item_type)
            logger.debug(f"Repository: ItemType created with id={item_type.id}")
            return _detach_item_type(item_type)

    @staticmethod
    def get_or_create(
        name: str,
        sub_type: str = "",
        is_serialized: bool = False,
        details: str = ""
    ) -> ItemType:
        """Get existing type or create new one.

        Args:
            name: Type name
            sub_type: Sub-type name
            is_serialized: Whether serialized
            details: Type description

        Returns:
            Existing or newly created ItemType.
        """
        with session_scope() as session:
            # Try to find existing
            item_type = (
                session.query(ItemType)
                .filter(
                    ItemType.name == name,
                    ItemType.sub_type == (sub_type or "")
                )
                .first()
            )

            if item_type:
                return _detach_item_type(item_type)

            # Create new
            item_type = ItemType(
                name=name,
                sub_type=sub_type or "",
                is_serialized=is_serialized,
                details=details or ""
            )
            session.add(item_type)
            session.flush()
            session.refresh(item_type)
            return _detach_item_type(item_type)

    @staticmethod
    def get_by_id(type_id: int) -> Optional[ItemType]:
        """Get item type by ID.

        Args:
            type_id: The type's ID.

        Returns:
            ItemType instance or None if not found.
        """
        with session_scope() as session:
            item_type = session.query(ItemType).filter(ItemType.id == type_id).first()
            return _detach_item_type(item_type) if item_type else None

    @staticmethod
    def get_all() -> List[ItemType]:
        """Get all item types.

        Returns:
            List of all ItemType instances.
        """
        with session_scope() as session:
            types = session.query(ItemType).order_by(ItemType.name, ItemType.sub_type).all()
            return [_detach_item_type(t) for t in types]

    @staticmethod
    def get_autocomplete_names(prefix: str = "", limit: int = 20) -> List[str]:
        """Get autocomplete suggestions for type names.

        Args:
            prefix: Search prefix (optional)
            limit: Maximum number of suggestions

        Returns:
            List of matching type names.
        """
        with session_scope() as session:
            query = session.query(ItemType.name).distinct()
            if prefix:
                query = query.filter(ItemType.name.ilike(f"{prefix}%"))
            query = query.order_by(ItemType.name).limit(limit)
            return [row[0] for row in query.all()]

    @staticmethod
    def get_autocomplete_subtypes(
        type_name: str,
        prefix: str = "",
        limit: int = 20
    ) -> List[str]:
        """Get autocomplete suggestions for subtypes given a type name.

        Args:
            type_name: The type name to filter by
            prefix: Search prefix for subtype (optional)
            limit: Maximum number of suggestions

        Returns:
            List of matching subtype names.
        """
        with session_scope() as session:
            query = (
                session.query(ItemType.sub_type)
                .filter(
                    ItemType.name == type_name,
                    ItemType.sub_type.isnot(None),
                    ItemType.sub_type != ""
                )
                .distinct()
            )
            if prefix:
                query = query.filter(ItemType.sub_type.ilike(f"{prefix}%"))
            query = query.order_by(ItemType.sub_type).limit(limit)
            return [row[0] for row in query.all() if row[0]]

    @staticmethod
    def update(
        type_id: int,
        name: str = None,
        sub_type: str = None,
        is_serialized: bool = None,
        details: str = None
    ) -> Optional[ItemType]:
        """Update an item type.

        Args:
            type_id: Type ID
            name: New name (optional)
            sub_type: New sub-type (optional)
            is_serialized: New serialized status (optional)
            details: New details (optional)

        Returns:
            Updated ItemType or None if not found.
        """
        with session_scope() as session:
            item_type = session.query(ItemType).filter(ItemType.id == type_id).first()
            if not item_type:
                return None

            if name is not None:
                item_type.name = name
            if sub_type is not None:
                item_type.sub_type = sub_type
            if is_serialized is not None:
                item_type.is_serialized = is_serialized
            if details is not None:
                item_type.details = details

            session.flush()
            session.refresh(item_type)
            return _detach_item_type(item_type)

    @staticmethod
    def delete(type_id: int) -> bool:
        """Delete an item type and all its items.

        Args:
            type_id: Type ID

        Returns:
            True if deleted, False if not found.
        """
        with session_scope() as session:
            item_type = session.query(ItemType).filter(ItemType.id == type_id).first()
            if not item_type:
                return False
            session.delete(item_type)  # Cascade will delete items too
            return True

    @staticmethod
    def search(query: str, limit: int = 100) -> List[ItemType]:
        """Search item types by name or subtype.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching ItemType instances.
        """
        with session_scope() as session:
            search_pattern = f"%{query}%"
            types = (
                session.query(ItemType)
                .filter(
                    or_(
                        ItemType.name.ilike(search_pattern),
                        ItemType.sub_type.ilike(search_pattern)
                    )
                )
                .order_by(ItemType.name, ItemType.sub_type)
                .limit(limit)
                .all()
            )
            return [_detach_item_type(t) for t in types]

    @staticmethod
    def get_all_with_items() -> list:
        """Get all item types with their items for grouped display.

        Returns:
            List of tuples (ItemType, List[Item]) for each type that has items.
        """
        with session_scope() as session:
            # Get all types that have at least one item
            types_with_items = (
                session.query(ItemType)
                .join(Item)
                .order_by(ItemType.name, ItemType.sub_type)
                .all()
            )

            result = []
            for item_type in types_with_items:
                # Get all items for this type
                items = (
                    session.query(Item)
                    .filter(Item.item_type_id == item_type.id)
                    .order_by(Item.serial_number, Item.id)
                    .all()
                )
                # Detach both type and items
                detached_type = _detach_item_type(item_type)
                detached_items = [_detach_item(item) for item in items]
                result.append((detached_type, detached_items))

            return result

    @staticmethod
    def get_serialized_with_items() -> list:
        """Get all serialized item types with their items.

        Returns:
            List of tuples (ItemType, List[Item]) for each serialized type that has items.
        """
        with session_scope() as session:
            types_with_items = (
                session.query(ItemType)
                .join(Item)
                .filter(ItemType.is_serialized.is_(True))
                .order_by(ItemType.name, ItemType.sub_type)
                .all()
            )

            result = []
            for item_type in types_with_items:
                items = (
                    session.query(Item)
                    .filter(Item.item_type_id == item_type.id)
                    .order_by(Item.serial_number, Item.id)
                    .all()
                )
                detached_type = _detach_item_type(item_type)
                detached_items = [_detach_item(item) for item in items]
                result.append((detached_type, detached_items))

            return result


class ItemRepository:
    """Repository for Item CRUD operations."""

    @staticmethod
    def create(
        item_type_id: int,
        quantity: int = 1,
        serial_number: str = None,
        location: str = None,
        condition: str = None,
        notes: str = None
    ) -> Item:
        """Create a new item instance.

        Args:
            item_type_id: FK to ItemType
            quantity: Quantity (must be 1 if serialized)
            serial_number: Serial number (required if type is serialized)
            location: Storage location
            condition: Item condition
            notes: Additional notes

        Returns:
            The created Item instance.

        Raises:
            ValueError: If validation fails
        """
        logger.debug(f"Repository: Creating item for type_id={item_type_id}, qty={quantity}")

        with session_scope() as session:
            # Validate type exists and get serialization status
            item_type = session.query(ItemType).filter(ItemType.id == item_type_id).first()
            if not item_type:
                raise ValueError(f"ItemType with id {item_type_id} not found")

            # Validate serialization rules
            if item_type.is_serialized:
                if not serial_number:
                    raise ValueError("Serial number required for serialized items")
                if quantity != 1:
                    raise ValueError("Quantity must be 1 for serialized items")
            else:
                if serial_number:
                    raise ValueError("Serial number not allowed for non-serialized items")
                if quantity < 1:
                    raise ValueError("Quantity must be at least 1")

            item = Item(
                item_type_id=item_type_id,
                quantity=quantity,
                serial_number=serial_number or None,
                location=location or "",
                condition=condition or "",
                notes=notes or ""
            )
            session.add(item)
            session.flush()

            # Create initial transaction
            if quantity > 0:
                transaction = Transaction(
                    item_id=item.id,
                    transaction_type=TransactionType.ADD,
                    quantity_change=quantity,
                    quantity_before=0,
                    quantity_after=quantity,
                    notes=tr("transaction.notes.initial")
                )
                session.add(transaction)

            session.flush()
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
            items = session.query(Item).order_by(Item.item_type_id, Item.serial_number).all()
            return [_detach_item(item) for item in items]

    @staticmethod
    def update(
        item_id: int,
        serial_number: str = None,
        location: str = None,
        condition: str = None,
        notes: str = None,
    ) -> Optional[Item]:
        """Update an item's properties (not quantity - use add_quantity/remove_quantity).

        Note: To change type-related fields (name, sub_type, details), use edit_item
        which handles ItemType changes properly.

        Args:
            item_id: The item's ID.
            serial_number: New serial number (optional)
            location: New location (optional)
            condition: New condition (optional)
            notes: New notes (optional)

        Returns:
            The updated Item instance or None if not found.
        """
        with session_scope() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                return None

            if serial_number is not None:
                item.serial_number = serial_number or None
            if location is not None:
                item.location = location
            if condition is not None:
                item.condition = condition
            if notes is not None:
                item.notes = notes

            session.commit()
            session.refresh(item)
            return _detach_item(item)

    @staticmethod
    def edit_item(
        item_id: int,
        item_type_id: int,
        quantity: int,
        serial_number: str,
        location: str,
        condition: str,
        notes: str,
        edit_reason: str,
    ) -> Optional[Item]:
        """Edit an item's properties and quantity, recording all changes as transactions.

        Note: To change type-related fields (name, sub_type, details), first get or create
        the appropriate ItemType and pass its ID here.

        Args:
            item_id: The item's ID.
            item_type_id: New ItemType ID (can change the type).
            quantity: New quantity.
            serial_number: New serial number (or empty string for none).
            location: New location.
            condition: New condition.
            notes: New item notes.
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
            item.item_type_id = item_type_id
            item.quantity = quantity
            item.serial_number = serial_number or None
            item.location = location or ""
            item.condition = condition or ""
            item.notes = notes or ""

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
    def find_by_type_and_serial(
        item_type_id: int, serial_number: str = None
    ) -> Optional[Item]:
        """Find an existing item by type ID and serial number.

        Args:
            item_type_id: The ItemType ID.
            serial_number: Serial number (optional).

        Returns:
            The matching Item instance or None if not found.
        """
        with session_scope() as session:
            query = session.query(Item).filter(Item.item_type_id == item_type_id)

            if serial_number:
                query = query.filter(Item.serial_number == serial_number)
            else:
                # For non-serialized items, find one without serial number
                query = query.filter(Item.serial_number.is_(None))

            item = query.first()
            return _detach_item(item) if item else None

    @staticmethod
    def search(query: str, field: str = None) -> List[Item]:
        """Search items by query string.

        Args:
            query: Search query string.
            field: Field to search in ('item_type', 'sub_type', 'details', 'serial_number', 'notes', or None for all).

        Returns:
            List of matching Item instances.
        """
        logger.debug(f"Repository: Searching items with query='{query}', field={field}")
        with session_scope() as session:
            search_pattern = f"%{query}%"

            # Join Item with ItemType for searching type-related fields
            base_query = session.query(Item).join(ItemType)

            if field == "item_type":
                items = base_query.filter(ItemType.name.ilike(search_pattern)).all()
            elif field == "sub_type":
                items = base_query.filter(ItemType.sub_type.ilike(search_pattern)).all()
            elif field == "details":
                items = base_query.filter(ItemType.details.ilike(search_pattern)).all()
            elif field == "serial_number":
                items = (
                    session.query(Item)
                    .filter(Item.serial_number.ilike(search_pattern))
                    .all()
                )
            elif field == "notes":
                items = (
                    session.query(Item)
                    .filter(Item.notes.ilike(search_pattern))
                    .all()
                )
            else:
                # Search in all relevant fields
                items = (
                    base_query.filter(
                        or_(
                            ItemType.name.ilike(search_pattern),
                            ItemType.sub_type.ilike(search_pattern),
                            ItemType.details.ilike(search_pattern),
                            Item.serial_number.ilike(search_pattern),
                            Item.notes.ilike(search_pattern),
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
            field: Field to search in ('item_type', 'sub_type', 'details', 'serial_number', 'notes', or None for all).
            limit: Maximum number of suggestions.

        Returns:
            List of unique suggestion strings.
        """
        with session_scope() as session:
            suggestions = set()
            search_pattern = f"{prefix}%"

            if field == "item_type" or field is None:
                types = (
                    session.query(ItemType.name)
                    .filter(ItemType.name.ilike(search_pattern))
                    .distinct()
                    .limit(limit)
                    .all()
                )
                suggestions.update(t[0] for t in types if t[0])

            if field == "sub_type" or field is None:
                sub_types = (
                    session.query(ItemType.sub_type)
                    .filter(ItemType.sub_type.ilike(search_pattern))
                    .distinct()
                    .limit(limit)
                    .all()
                )
                suggestions.update(t[0] for t in sub_types if t[0])

            if field == "details" or field is None:
                # For details, extract words that start with the prefix
                details_rows = (
                    session.query(ItemType.details)
                    .filter(ItemType.details.ilike(f"%{prefix}%"))
                    .all()
                )
                for (detail,) in details_rows:
                    if detail:
                        words = detail.split()
                        for word in words:
                            if word.lower().startswith(prefix.lower()):
                                suggestions.add(word)

            if field == "serial_number" or field is None:
                serials = (
                    session.query(Item.serial_number)
                    .filter(
                        Item.serial_number.isnot(None),
                        Item.serial_number.ilike(search_pattern)
                    )
                    .distinct()
                    .limit(limit)
                    .all()
                )
                suggestions.update(s[0] for s in serials if s[0])

            if field == "notes" or field is None:
                # For notes, extract words that start with the prefix
                notes_rows = (
                    session.query(Item.notes)
                    .filter(Item.notes.ilike(f"%{prefix}%"))
                    .all()
                )
                for (note,) in notes_rows:
                    if note:
                        words = note.split()
                        for word in words:
                            if word.lower().startswith(prefix.lower()):
                                suggestions.add(word)

            return sorted(list(suggestions))[:limit]

    @staticmethod
    def get_by_type(type_id: int) -> List[Item]:
        """Get all items of a specific type.

        Args:
            type_id: ItemType ID

        Returns:
            List of Item instances.
        """
        with session_scope() as session:
            items = (
                session.query(Item)
                .filter(Item.item_type_id == type_id)
                .order_by(Item.serial_number, Item.location)
                .all()
            )
            return [_detach_item(item) for item in items]

    @staticmethod
    def search_by_serial(serial_number: str) -> Optional[Item]:
        """Find item by serial number.

        Args:
            serial_number: Serial number to search for

        Returns:
            Item instance or None.
        """
        with session_scope() as session:
            item = (
                session.query(Item)
                .filter(Item.serial_number == serial_number)
                .first()
            )
            return _detach_item(item) if item else None

    @staticmethod
    def get_serial_numbers_for_type(type_id: int) -> List[str]:
        """Get all serial numbers for a given type.

        Args:
            type_id: ItemType ID

        Returns:
            List of serial numbers.
        """
        with session_scope() as session:
            results = (
                session.query(Item.serial_number)
                .filter(
                    Item.item_type_id == type_id,
                    Item.serial_number.isnot(None),
                    Item.serial_number != ""
                )
                .order_by(Item.serial_number)
                .all()
            )
            return [row[0] for row in results if row[0]]

    @staticmethod
    def delete_by_serial_numbers(serial_numbers: List[str]) -> int:
        """Delete items by their serial numbers in a single transaction.

        Args:
            serial_numbers: List of serial numbers to delete.

        Returns:
            Number of items deleted.
        """
        if not serial_numbers:
            return 0

        with session_scope() as session:
            items = (
                session.query(Item)
                .filter(Item.serial_number.in_(serial_numbers))
                .all()
            )
            count = len(items)
            for item in items:
                session.delete(item)
            logger.debug(f"Repository: Bulk deleted {count} items by serial numbers")
            return count

    @staticmethod
    def get_items_at_location(location: str) -> List[Item]:
        """Get all items at a specific location.

        Args:
            location: Location name

        Returns:
            List of Item instances.
        """
        with session_scope() as session:
            items = (
                session.query(Item)
                .filter(Item.location == location)
                .order_by(Item.item_type_id, Item.serial_number)
                .all()
            )
            return [_detach_item(item) for item in items]


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
        item_type_id=item.item_type_id,
        quantity=item.quantity,
        serial_number=item.serial_number,
        location=item.location,
        condition=item.condition,
        notes=item.notes,
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


def _detach_item_type(item_type: ItemType) -> ItemType:
    """Create a detached copy of an ItemType."""
    if item_type is None:
        return None
    return ItemType(
        id=item_type.id,
        name=item_type.name,
        sub_type=item_type.sub_type,
        is_serialized=item_type.is_serialized,
        details=item_type.details,
        created_at=item_type.created_at,
        updated_at=item_type.updated_at
    )
