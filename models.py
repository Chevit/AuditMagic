"""SQLAlchemy ORM models for the inventory management system."""

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TransactionType(enum.Enum):
    """Enum for transaction types."""

    ADD = "add"
    REMOVE = "remove"
    EDIT = "edit"


class ItemType(Base):
    """Represents a type/category of items.

    This is the template/definition for items (e.g., "Laptop ThinkPad X1").
    Actual inventory instances are stored in the Item table.
    """

    __tablename__ = "item_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    sub_type = Column(String(255), nullable=True, index=True)
    is_serialized = Column(Boolean, default=False, nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    items = relationship("Item", back_populates="item_type", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('name', 'sub_type', name='uq_item_type_name_subtype'),
    )

    def __repr__(self):
        return f"<ItemType(id={self.id}, name='{self.name}', sub_type='{self.sub_type}', serialized={self.is_serialized})>"

    @property
    def total_quantity(self) -> int:
        """Get total quantity across all items of this type.

        Note: Requires the `items` relationship to be loaded (i.e., valid only
        within an active session). Returns 0 on detached objects created by
        _detach_item_type(), which do not populate the relationship.
        """
        return sum(item.quantity for item in self.items)

    @property
    def serial_numbers(self) -> list:
        """Get all serial numbers for this type (if serialized).

        Note: Requires the `items` relationship to be loaded (i.e., valid only
        within an active session). Returns [] on detached objects created by
        _detach_item_type(), which do not populate the relationship.
        """
        if not self.is_serialized:
            return []
        return [item.serial_number for item in self.items if item.serial_number]

    @property
    def display_name(self) -> str:
        """Get display name with subtype if present."""
        if self.sub_type:
            return f"{self.name} - {self.sub_type}"
        return self.name


class Item(Base):
    """Represents actual inventory items/units.

    This is an instance of an ItemType (e.g., one specific laptop with serial number ABC123).
    For non-serialized items, one row can represent multiple units (quantity > 1).
    For serialized items, one row = one unit (quantity must = 1).
    """

    __tablename__ = "items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_type_id = Column(Integer, ForeignKey("item_types.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    serial_number = Column(String(255), nullable=True, unique=True, index=True)
    location = Column(String(255), nullable=True)
    condition = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    item_type = relationship("ItemType", back_populates="items")

    # Constraints: Either bulk (no SN, qty > 0) OR serialized (has SN, qty = 1)
    __table_args__ = (
        CheckConstraint(
            '(serial_number IS NULL AND quantity > 0) OR (serial_number IS NOT NULL AND quantity = 1)',
            name='check_serial_or_quantity'
        ),
    )

    def __repr__(self):
        return f"<Item(id={self.id}, type_id={self.item_type_id}, qty={self.quantity}, sn={self.serial_number})>"

    @property
    def display_name(self) -> str:
        """Get display name from item type."""
        return self.item_type.display_name if self.item_type else f"Type #{self.item_type_id}"


class Transaction(Base):
    """SQLAlchemy model for inventory transactions."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_type_id = Column(Integer, ForeignKey("item_types.id"), nullable=False, index=True)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    quantity_change = Column(Integer, nullable=False)
    quantity_before = Column(Integer, nullable=False)
    quantity_after = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    serial_number = Column(String(255), nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    # Relationships
    item_type = relationship("ItemType")

    def __repr__(self):
        return f"<Transaction(id={self.id}, type_id={self.item_type_id}, type={self.transaction_type.value}, change={self.quantity_change})>"


class SearchHistory(Base):
    """SQLAlchemy model for search history (last 5 searches)."""

    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    search_query = Column(String(255), nullable=False)
    search_field = Column(
        String(50), nullable=True
    )  # 'item_type', 'sub_type', 'details', or None for all
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<SearchHistory(id={self.id}, query='{self.search_query}', field='{self.search_field}')>"
