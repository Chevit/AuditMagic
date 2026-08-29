"""SQLAlchemy ORM models for the inventory management system."""

import enum
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for every model."""


class TransactionType(enum.Enum):
    """Enum for transaction types."""

    ADD = "add"
    REMOVE = "remove"
    EDIT = "edit"
    TRANSFER = "transfer"


class Location(Base):
    """Represents a physical storage location (e.g., warehouse, room, shelf)."""

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    items: Mapped[List["Item"]] = relationship("Item", back_populates="location_ref")

    def __repr__(self) -> str:
        return f"<Location(id={self.id}, name='{self.name}')>"


class ItemType(Base):
    """Represents a type/category of items.

    This is the template/definition for items (e.g., "Laptop ThinkPad X1").
    Actual inventory instances are stored in the Item table.
    """

    __tablename__ = "item_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sub_type: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    is_serialized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    # Relationships
    items: Mapped[List["Item"]] = relationship(
        "Item", back_populates="item_type", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("name", "sub_type", name="uq_item_type_name_subtype"),
    )

    def __repr__(self) -> str:
        return (
            f"<ItemType(id={self.id}, name='{self.name}', "
            f"sub_type='{self.sub_type}', serialized={self.is_serialized})>"
        )

    @property
    def total_quantity(self) -> int:
        """Get total quantity across all items of this type.

        Note: Requires the `items` relationship to be loaded (i.e., valid only
        within an active session). Returns 0 on detached objects created by
        the repository layer, which do not populate the relationship.
        """
        return sum(item.quantity for item in self.items)

    @property
    def serial_numbers(self) -> List[str]:
        """Get all serial numbers for this type (if serialized).

        Note: Requires the `items` relationship to be loaded (i.e., valid only
        within an active session). Returns [] on detached objects created by
        the repository layer, which do not populate the relationship.
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

    This is an instance of an ItemType (e.g., one specific laptop with serial
    number ABC123). For non-serialized items, one row can represent multiple
    units (quantity > 1). For serialized items, one row = one unit (quantity
    must = 1).
    """

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("item_types.id"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    serial_number: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    # nullable: legacy rows pre-locations; wizard assigns them on startup
    location_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("locations.id"), nullable=True, index=True
    )
    condition: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    # Relationships
    item_type: Mapped["ItemType"] = relationship("ItemType", back_populates="items")
    location_ref: Mapped[Optional["Location"]] = relationship(
        "Location", foreign_keys=[location_id], back_populates="items"
    )

    @property
    def location(self) -> str:
        """Backward-compat property. Always returns '' on detached objects
        (location_ref is not populated by the repository layer). Use
        location_id instead.
        """
        return ""

    # Constraints: Either bulk (no SN, qty > 0) OR serialized (has SN, qty = 1)
    __table_args__ = (
        CheckConstraint(
            "(serial_number IS NULL AND quantity > 0) OR "
            "(serial_number IS NOT NULL AND quantity = 1)",
            name="check_serial_or_quantity",
        ),
        # Non-serialized stock: one row per (ItemType, Location). Makes the
        # StockRef addressing in core.stock unambiguous — see docs/adr/0001.
        # Serialized rows are excluded; each serial is its own row.
        Index(
            "uq_item_type_location_bulk",
            "item_type_id",
            "location_id",
            unique=True,
            sqlite_where=text("serial_number IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Item(id={self.id}, type_id={self.item_type_id}, "
            f"qty={self.quantity}, sn={self.serial_number})>"
        )

    @property
    def display_name(self) -> str:
        """Get display name from item type."""
        return (
            self.item_type.display_name
            if self.item_type
            else f"Type #{self.item_type_id}"
        )


class Transaction(Base):
    """SQLAlchemy model for inventory transactions."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("item_types.id"), nullable=False, index=True
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        SQLEnum(TransactionType), nullable=False
    )
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_before: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Location where this transaction occurred (set on ALL types for
    # historical accuracy)
    location_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("locations.id"), nullable=True
    )
    # Transfer-specific: source and destination (set only on TRANSFER type)
    from_location_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("locations.id"), nullable=True
    )
    to_location_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("locations.id"), nullable=True
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=_utcnow, index=True
    )

    # Relationships
    item_type: Mapped["ItemType"] = relationship("ItemType")
    location: Mapped[Optional["Location"]] = relationship(
        "Location", foreign_keys=[location_id]
    )
    from_location: Mapped[Optional["Location"]] = relationship(
        "Location", foreign_keys=[from_location_id]
    )
    to_location: Mapped[Optional["Location"]] = relationship(
        "Location", foreign_keys=[to_location_id]
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, type_id={self.item_type_id}, "
            f"type={self.transaction_type.value}, change={self.quantity_change})>"
        )


class SearchHistory(Base):
    """SQLAlchemy model for search history (last 5 searches)."""

    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_query: Mapped[str] = mapped_column(String(255), nullable=False)
    # 'item_type', 'sub_type', 'details', or None for all
    search_field: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=_utcnow)

    def __repr__(self) -> str:
        return (
            f"<SearchHistory(id={self.id}, query='{self.search_query}', "
            f"field='{self.search_field}')>"
        )
