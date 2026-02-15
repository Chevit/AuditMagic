"""SQLAlchemy ORM models for the inventory management system."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Text,
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class TransactionType(enum.Enum):
    """Enum for transaction types."""

    ADD = "add"
    REMOVE = "remove"
    EDIT = "edit"


class Item(Base):
    """SQLAlchemy model for inventory items."""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_type = Column(String(255), nullable=False, index=True)
    sub_type = Column(String(255), nullable=True, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    serial_number = Column(String(255), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship to transactions
    transactions = relationship(
        "Transaction", back_populates="item", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Item(id={self.id}, type='{self.item_type}', sub_type='{self.sub_type}', qty={self.quantity})>"


class Transaction(Base):
    """SQLAlchemy model for inventory transactions."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    quantity_change = Column(Integer, nullable=False)
    quantity_before = Column(Integer, nullable=False)
    quantity_after = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationship to item
    item = relationship("Item", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(id={self.id}, item_id={self.item_id}, type={self.transaction_type.value}, change={self.quantity_change})>"


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
