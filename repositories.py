"""Repository layer for database operations."""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import delete as sql_delete, func, or_
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
        details: str = "",
    ) -> ItemType:
        """Get existing type or create new one.

        Raises ValueError if the existing type's is_serialized conflicts with
        the requested value — serialization mode is immutable once set.

        Args:
            name: Type name
            sub_type: Sub-type name
            is_serialized: Whether serialized
            details: Type description (applied only when creating a new type)

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
                # Conflict guard — is_serialized is immutable after creation
                if item_type.is_serialized != is_serialized:
                    existing_state = "serialized" if item_type.is_serialized else "non-serialized"
                    requested_state = "serialized" if is_serialized else "non-serialized"
                    raise ValueError(
                        f"ItemType '{name}' (sub_type='{sub_type}') already exists as "
                        f"{existing_state}. Cannot use it as {requested_state}. "
                        f"Choose a different name/sub-type or keep the same serialization mode."
                    )
                return _detach_item_type(item_type)

            # Create new
            item_type = ItemType(
                name=name,
                sub_type=sub_type or "",
                is_serialized=is_serialized,
                details=details or "",
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
    def get_by_name_and_subtype(name: str, sub_type: str = "") -> Optional[ItemType]:
        """Return an existing ItemType for the given name/sub_type, or None.

        Used by the UI to look up the existing type while the user is typing,
        so the serialization state can be pre-filled and locked.

        Args:
            name: Type name
            sub_type: Sub-type name (optional)

        Returns:
            Existing ItemType or None if not found.
        """
        with session_scope() as session:
            item_type = (
                session.query(ItemType)
                .filter(
                    ItemType.name == name,
                    ItemType.sub_type == (sub_type or "")
                )
                .first()
            )
            return _detach_item_type(item_type) if item_type else None

    @staticmethod
    def get_by_ids(type_ids: List[int]) -> Dict[int, "ItemType"]:
        """Batch-fetch ItemTypes by IDs in a single query.

        Args:
            type_ids: List of ItemType IDs to fetch.

        Returns:
            Dict mapping id → ItemType for each found type.
        """
        if not type_ids:
            return {}
        with session_scope() as session:
            types = session.query(ItemType).filter(ItemType.id.in_(type_ids)).all()
            return {t.id: _detach_item_type(t) for t in types}

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
            if is_serialized is not None and item_type.is_serialized != is_serialized:
                item_count = session.query(Item).filter(Item.item_type_id == type_id).count()
                if item_count > 0:
                    raise ValueError(
                        f"Cannot change is_serialized for '{item_type.name}': "
                        f"{item_count} item(s) already exist. Delete all items first."
                    )
                item_type.is_serialized = is_serialized
            if details is not None:
                item_type.details = details

            session.flush()
            session.refresh(item_type)
            return _detach_item_type(item_type)

    @staticmethod
    def delete(type_id: int) -> bool:
        """Delete an item type together with all its items and transactions.

        Deletion order:
          1. Transaction records for this type (item_type_id NOT NULL — must go first).
          2. Item records (handled by ORM cascade from ItemType).
          3. The ItemType itself.

        Args:
            type_id: Type ID

        Returns:
            True if deleted, False if not found.
        """
        with session_scope() as session:
            item_type = session.query(ItemType).filter(ItemType.id == type_id).first()
            if not item_type:
                logger.warning(f"Repository: ItemType not found for deletion: id={type_id}")
                return False

            # 1. Delete transactions (FK item_type_id NOT NULL — no ORM cascade)
            session.execute(sql_delete(Transaction).where(Transaction.item_type_id == type_id))
            session.flush()

            # 2+3. Delete items + item type (ORM cascade="all, delete-orphan" handles items)
            session.delete(item_type)
            logger.debug(f"Repository: ItemType deleted: id={type_id}, name='{item_type.name}'")
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
    def _get_types_with_items(session, type_filter=None) -> list:
        """Shared helper to query item types with their items.

        Args:
            session: Database session.
            type_filter: Optional SQLAlchemy filter clause to apply to the ItemType query.

        Returns:
            List of tuples (ItemType, List[Item]) for each matching type that has items.
        """
        query = (
            session.query(ItemType, Item)
            .join(Item, Item.item_type_id == ItemType.id)
            .order_by(ItemType.name, ItemType.sub_type, Item.serial_number, Item.id)
        )
        if type_filter is not None:
            query = query.filter(type_filter)
        rows = query.all()

        seen: dict = {}
        order: list = []
        for item_type, item in rows:
            if item_type.id not in seen:
                seen[item_type.id] = (item_type, [])
                order.append(item_type.id)
            seen[item_type.id][1].append(item)

        return [
            (_detach_item_type(seen[tid][0]), [_detach_item(i) for i in seen[tid][1]])
            for tid in order
        ]

    @staticmethod
    def get_all_with_items() -> list:
        """Get all item types with their items for grouped display.

        Returns:
            List of tuples (ItemType, List[Item]) for each type that has items.
        """
        with session_scope() as session:
            return ItemTypeRepository._get_types_with_items(session)

    @staticmethod
    def get_serialized_with_items() -> list:
        """Get all serialized item types with their items.

        Returns:
            List of tuples (ItemType, List[Item]) for each serialized type that has items.
        """
        with session_scope() as session:
            return ItemTypeRepository._get_types_with_items(
                session, ItemType.is_serialized.is_(True)
            )


class ItemRepository:
    """Repository for Item CRUD operations."""

    @staticmethod
    def create(
        item_type_id: int,
        quantity: int = 1,
        serial_number: str = None,
        location: str = None,
        condition: str = None,
        transaction_notes: str = None,
    ) -> Item:
        """Create a new item instance.

        Args:
            item_type_id: FK to ItemType
            quantity: Quantity (must be 1 if serialized)
            serial_number: Serial number (required if type is serialized)
            location: Storage location
            condition: Item condition
            transaction_notes: Custom notes for the initial ADD transaction
                (defaults to "Initial inventory" translation)

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
            )
            session.add(item)
            session.flush()

            # Create initial transaction
            if quantity > 0:
                transaction = Transaction(
                    item_type_id=item_type_id,
                    transaction_type=TransactionType.ADD,
                    quantity_change=quantity,
                    quantity_before=0,
                    quantity_after=quantity,
                    serial_number=serial_number or None,
                    notes=transaction_notes or tr("transaction.notes.initial"),
                )
                session.add(transaction)

            session.flush()
            session.refresh(item)
            logger.debug(f"Repository: Item created with id={item.id}")
            return _detach_item(item)

    @staticmethod
    def create_serialized(
        item_type_id: int,
        serial_number: str,
        location: str = "",
        condition: str = "",
        notes: str = "",
    ) -> Item:
        """Create a new serialized item with grouped-quantity-aware transactions.

        The ADD transaction records the group size before and after adding this
        unit, so the history correctly reflects the full type inventory moving
        from N to N+1.

        Notes policy:
          - First item of the type (existing_count == 0): always uses the
            default "initial inventory" translation, ignoring caller notes.
          - Subsequent items: uses caller-supplied notes, or "" if empty.

        Args:
            item_type_id: FK to ItemType (must be is_serialized=True).
            serial_number: Unique serial number (required).
            location: Storage location (optional).
            condition: Item condition (optional).
            notes: Transaction notes for non-first items (optional).

        Returns:
            The created Item instance.

        Raises:
            ValueError: If the type is not serialized, serial number is
                        missing, or serial number already exists.
        """
        if not serial_number:
            raise ValueError("Serial number is required for serialized items")

        with session_scope() as session:
            item_type = session.query(ItemType).filter(ItemType.id == item_type_id).first()
            if not item_type:
                raise ValueError(f"ItemType with id {item_type_id} not found")
            if not item_type.is_serialized:
                raise ValueError(
                    f"ItemType '{item_type.name}' is not serialized; use create() instead"
                )

            # Count existing items so the transaction reflects the group quantity
            existing_count = (
                session.query(func.count(Item.id))
                .filter(Item.item_type_id == item_type_id)
                .scalar()
            ) or 0

            item = Item(
                item_type_id=item_type_id,
                quantity=1,
                serial_number=serial_number,
                location=location or "",
                condition=condition or "",
            )
            session.add(item)
            session.flush()

            # First item of a type always gets the default note
            transaction_notes = (
                tr("transaction.notes.initial")
                if existing_count == 0
                else (notes or "")
            )

            transaction = Transaction(
                item_type_id=item_type_id,
                transaction_type=TransactionType.ADD,
                quantity_change=1,
                quantity_before=existing_count,
                quantity_after=existing_count + 1,
                serial_number=serial_number,
                notes=transaction_notes,
            )
            session.add(transaction)
            session.flush()
            session.refresh(item)
            logger.debug(
                f"Repository: Serialized item created: id={item.id}, sn={serial_number!r}, "
                f"group qty {existing_count} -> {existing_count + 1}"
            )
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
    ) -> Optional[Item]:
        """Update an item's properties (not quantity - use add_quantity/remove_quantity).

        Note: To change type-related fields (name, sub_type, details), use edit_item
        which handles ItemType changes properly.

        Args:
            item_id: The item's ID.
            serial_number: New serial number (optional)
            location: New location (optional)
            condition: New condition (optional)

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

            session.flush()
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

            # Record a single EDIT transaction capturing all changes
            quantity_diff = quantity - quantity_before
            edit_transaction = Transaction(
                item_type_id=item_type_id,
                transaction_type=TransactionType.EDIT,
                quantity_change=abs(quantity_diff),
                quantity_before=quantity_before,
                quantity_after=quantity,
                notes=edit_reason,
            )
            session.add(edit_transaction)

            session.flush()
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
                item_type_id=item.item_type_id,
                transaction_type=TransactionType.ADD,
                quantity_change=quantity,
                quantity_before=quantity_before,
                quantity_after=item.quantity,
                notes=notes or "",
            )
            session.add(transaction)
            session.flush()
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
                item_type_id=item.item_type_id,
                transaction_type=TransactionType.REMOVE,
                quantity_change=quantity,
                quantity_before=quantity_before,
                quantity_after=item.quantity,
                notes=notes or "",
            )
            session.add(transaction)
            session.flush()
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
    def search(query: str, field: str = None, limit: int = 200) -> List[Item]:
        """Search items by query string.

        Args:
            query: Search query string.
            field: Field to search in ('item_type', 'sub_type', 'details', 'serial_number', or None for all).
            limit: Maximum number of results to return.

        Returns:
            List of matching Item instances.
        """
        logger.debug(f"Repository: Searching items with query='{query}', field={field}")
        with session_scope() as session:
            search_pattern = f"%{query}%"

            # Join Item with ItemType for searching type-related fields
            base_query = session.query(Item).join(ItemType)

            if field == "item_type":
                items = base_query.filter(ItemType.name.ilike(search_pattern)).limit(limit).all()
            elif field == "sub_type":
                items = base_query.filter(ItemType.sub_type.ilike(search_pattern)).limit(limit).all()
            elif field == "details":
                items = base_query.filter(ItemType.details.ilike(search_pattern)).limit(limit).all()
            elif field == "serial_number":
                items = (
                    session.query(Item)
                    .filter(Item.serial_number.ilike(search_pattern))
                    .limit(limit)
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
                        )
                    )
                    .limit(limit)
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
            field: Field to search in ('item_type', 'sub_type', 'details', 'serial_number', or None for all).
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
                prefix_lower = prefix.lower()
                details_rows = (
                    session.query(ItemType.details)
                    .filter(ItemType.details.ilike(f"%{prefix}%"))
                    .limit(limit)
                    .all()
                )
                for (detail,) in details_rows:
                    if detail:
                        for word in detail.split():
                            if word.lower().startswith(prefix_lower):
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
    def delete_by_serial_numbers(serial_numbers: List[str], notes: str = "") -> int:
        """Delete items by their serial numbers in a single transaction.

        Creates REMOVE transaction records for each deleted item before deletion.

        Args:
            serial_numbers: List of serial numbers to delete.
            notes: Reason/notes for the deletion (for audit trail).

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

            # Create REMOVE transactions first
            for item in items:
                transaction = Transaction(
                    item_type_id=item.item_type_id,
                    transaction_type=TransactionType.REMOVE,
                    quantity_change=1,
                    quantity_before=1,
                    quantity_after=0,
                    serial_number=item.serial_number,
                    notes=notes,
                )
                session.add(transaction)

            # Flush transactions into DB before items are deleted
            session.flush()

            # Delete items via direct SQL to bypass ORM cascade (preserves the
            # REMOVE transactions we just inserted as audit records)
            session.execute(
                sql_delete(Item).where(Item.serial_number.in_(serial_numbers))
            )

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
    def get_by_type_and_date_range(
        type_id: int,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1000,
    ) -> List[Transaction]:
        """Get all transactions for an ItemType within a date range.

        Args:
            type_id: ItemType ID to filter by.
            start_date: Start of the date range.
            end_date: End of the date range.
            limit: Maximum number of rows to return (default 1000).

        Returns:
            List of Transaction instances ordered by date (newest first).
        """
        with session_scope() as session:
            transactions = (
                session.query(Transaction)
                .filter(
                    Transaction.item_type_id == type_id,
                    Transaction.created_at >= start_date,
                    Transaction.created_at <= end_date,
                )
                .order_by(Transaction.created_at.desc())
                .limit(limit)
                .all()
            )
            return [_detach_transaction(t) for t in transactions]

    @staticmethod
    def get_recent(limit: int = 50) -> List[Transaction]:
        """Get recent transactions.

        Args:
            limit: Maximum number of transactions to return.

        Returns:
            List of Transaction instances ordered by date (newest first).
        """
        with session_scope() as session:
            transactions = (
                session.query(Transaction)
                .order_by(Transaction.created_at.desc())
                .limit(limit)
                .all()
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
                session.flush()
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
                keep_ids = [h.id for h in all_history[:SearchHistoryRepository.MAX_HISTORY]]
                session.execute(
                    sql_delete(SearchHistory).where(SearchHistory.id.notin_(keep_ids))
                )

            session.flush()
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
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _detach_transaction(trans: Transaction) -> Transaction:
    """Create a detached copy of a Transaction."""
    if trans is None:
        return None
    return Transaction(
        id=trans.id,
        item_type_id=trans.item_type_id,
        transaction_type=trans.transaction_type,
        quantity_change=trans.quantity_change,
        quantity_before=trans.quantity_before,
        quantity_after=trans.quantity_after,
        notes=trans.notes,
        serial_number=trans.serial_number,
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
