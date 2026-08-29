"""Stock: the equipment of one ItemType at one Location.

Every change to Stock is addressed by a :class:`StockRef` — never by an ``Item.id``.
Callers name *what stock* they mean; this module decides which Item rows implement it.
See ``docs/adr/0001-stock-addressed-by-type-and-location.md``.

Non-serialized Stock holds an invariant: at most one Item row per (ItemType, Location),
enforced by the uq_item_type_location_bulk partial unique index.
"""

from dataclasses import dataclass
from typing import List, Sequence, Tuple, Union

from core.db import unit_of_work
from core.logger import logger
from core.repositories import ItemRepository, ItemTypeRepository

# ─── Errors ───────────────────────────────────────────────────────────────────


class StockError(ValueError):
    """Base for stock errors.

    Subclasses ValueError so existing ``except ValueError`` handlers in the UI keep
    working unchanged.
    """


class NoStockAtLocation(StockError):
    """The ref holds no stock."""


class InsufficientStock(StockError):
    """The removal exceeds what the ref holds."""


class UnknownSerials(StockError):
    """One or more serial numbers are not at this location."""


class MovementMismatch(StockError):
    """A Quantity movement was applied to serialized stock, or vice versa."""


# ─── Value objects ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StockRef:
    """The (ItemType, Location) pair that identifies Stock."""

    item_type_id: int
    location_id: int


@dataclass(frozen=True)
class Quantity:
    """A Movement of non-serialized stock, expressed as a count."""

    count: int

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("Quantity must be positive")


@dataclass(frozen=True)
class Serials:
    """A Movement of serialized stock, expressed as serial numbers.

    Accepts any sequence; stores a tuple, so the movement cannot be mutated
    after the availability check that validated it.
    """

    numbers: Sequence[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "numbers", tuple(self.numbers))
        if not self.numbers:
            raise ValueError("Serials requires at least one serial number")
        if len(set(self.numbers)) != len(self.numbers):
            raise ValueError("Serials contains duplicate serial numbers")


Movement = Union[Quantity, Serials]


@dataclass(frozen=True)
class StockLevel:
    """The state of a ref after a Movement."""

    ref: StockRef
    quantity: int
    serial_numbers: Tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        return self.quantity == 0


# ─── Internals ────────────────────────────────────────────────────────────────


def _item_type(ref: StockRef):
    item_type = ItemTypeRepository.get_by_id(ref.item_type_id)
    if item_type is None:
        raise StockError(f"ItemType id={ref.item_type_id} not found")
    return item_type


def _rows(ref: StockRef) -> List:
    """Every Item row implementing this ref, lowest id first.

    A serialized ref has one row per serial; a non-serialized ref has at most one.
    """
    rows = ItemRepository.get_by_type_and_location(ref.item_type_id, ref.location_id)
    return sorted(rows, key=lambda item: item.id)


def _level(ref: StockRef) -> StockLevel:
    rows = _rows(ref)
    return StockLevel(
        ref=ref,
        quantity=sum(row.quantity for row in rows),
        serial_numbers=tuple(sorted(r.serial_number for r in rows if r.serial_number)),
    )


# ─── Interface ────────────────────────────────────────────────────────────────


def has_stock(ref: StockRef) -> bool:
    """Whether this ref holds any stock."""
    return bool(_rows(ref))


def add(ref: StockRef, movement: Movement, notes: str = "") -> StockLevel:
    """Add stock at a ref.

    Non-serialized stock merges into the existing row, upholding the one-row
    invariant; serialized stock adds one row per serial number. The whole
    movement is one transaction, so a duplicate serial part-way through a batch
    leaves none of it behind.

    Raises:
        MovementMismatch: If the movement kind doesn't match the ItemType.
        StockError: If the ItemType doesn't exist.
        ValueError: If a serial number is already in use.
    """
    item_type = _item_type(ref)

    if isinstance(movement, Quantity):
        if item_type.is_serialized:
            raise MovementMismatch(
                f"'{item_type.name}' is serialized; add serial numbers, not a quantity"
            )
        with unit_of_work():
            rows = [row for row in _rows(ref) if row.serial_number is None]
            if rows:
                ItemRepository.add_quantity(rows[0].id, movement.count, notes)
            else:
                ItemRepository.create(
                    item_type_id=ref.item_type_id,
                    quantity=movement.count,
                    serial_number=None,
                    location_id=ref.location_id,
                    transaction_notes=notes or None,
                )
    elif isinstance(movement, Serials):
        if not item_type.is_serialized:
            raise MovementMismatch(
                f"'{item_type.name}' is not serialized; add a quantity, not serials"
            )
        with unit_of_work():
            for serial_number in movement.numbers:
                ItemRepository.create_serialized(
                    item_type_id=ref.item_type_id,
                    serial_number=serial_number,
                    location_id=ref.location_id,
                    notes=notes,
                )
    else:
        raise TypeError(f"Unsupported movement: {movement!r}")

    logger.info(f"Stock added at {ref}: {movement}")
    return _level(ref)


def remove(ref: StockRef, movement: Movement, notes: str = "") -> StockLevel:
    """Remove stock from a ref, recording the removal in the audit trail.

    The availability check and the write share one transaction, so what was
    checked is what is removed.

    Raises:
        NoStockAtLocation: If the ref holds nothing.
        InsufficientStock: If the removal exceeds what the ref holds.
        UnknownSerials: If a serial number is not at this location.
        MovementMismatch: If the movement kind doesn't match the ItemType.
    """
    item_type = _item_type(ref)

    with unit_of_work():
        rows = _rows(ref)
        if not rows:
            raise NoStockAtLocation(
                f"No stock of '{item_type.name}' at location id={ref.location_id}"
            )

        if isinstance(movement, Quantity):
            if item_type.is_serialized:
                raise MovementMismatch(
                    f"'{item_type.name}' is serialized; "
                    "remove serial numbers, not a quantity"
                )
            countable = [row for row in rows if row.serial_number is None]
            available = sum(row.quantity for row in countable)
            if not countable:
                raise NoStockAtLocation(
                    f"No countable stock of '{item_type.name}' "
                    f"at location id={ref.location_id}"
                )
            if movement.count > available:
                raise InsufficientStock(
                    f"Cannot remove {movement.count} of '{item_type.name}': "
                    f"only {available} available"
                )
            # A row cannot be left at zero — check_serial_or_quantity requires
            # quantity > 0 — so a row emptied by this removal is deleted, with
            # its own REMOVE transaction.
            row = countable[0]
            if movement.count == row.quantity:
                ItemRepository.delete_non_serialized(row.id, notes)
            else:
                ItemRepository.remove_quantity(row.id, movement.count, notes)
        elif isinstance(movement, Serials):
            if not item_type.is_serialized:
                raise MovementMismatch(
                    f"'{item_type.name}' is not serialized; "
                    "remove a quantity, not serials"
                )
            here = {row.serial_number for row in rows if row.serial_number}
            missing = [sn for sn in movement.numbers if sn not in here]
            if missing:
                raise UnknownSerials(
                    f"Serial numbers not at location id={ref.location_id}: "
                    f"{', '.join(missing)}"
                )
            ItemRepository.delete_by_serial_numbers(list(movement.numbers), notes)
        else:
            raise TypeError(f"Unsupported movement: {movement!r}")

    logger.info(f"Stock removed at {ref}: {movement}")
    return _level(ref)


def set_quantity(ref: StockRef, quantity: Quantity, notes: str = "") -> StockLevel:
    """Set the countable stock at a ref to an exact quantity, recording an EDIT.

    The edit path's one stock operation: add and remove express a movement,
    this expresses a correction.

    Raises:
        MovementMismatch: If the ItemType is serialized.
        NoStockAtLocation: If the ref holds nothing.
    """
    item_type = _item_type(ref)
    if item_type.is_serialized:
        raise MovementMismatch(
            f"'{item_type.name}' is serialized; its quantity is the serial count"
        )
    with unit_of_work():
        rows = [row for row in _rows(ref) if row.serial_number is None]
        if not rows:
            raise NoStockAtLocation(
                f"No countable stock of '{item_type.name}' "
                f"at location id={ref.location_id}"
            )
        ItemRepository.set_quantity(rows[0].id, quantity.count, notes)
    logger.info(f"Stock quantity set at {ref}: {quantity.count}")
    return _level(ref)


def delete(ref: StockRef, notes: str = "") -> int:
    """Remove all stock at a ref.

    The ItemType and every Transaction survive — only this location's stock goes.

    Returns:
        The number of units removed.

    Raises:
        NoStockAtLocation: If the ref holds nothing.
    """
    item_type = _item_type(ref)
    with unit_of_work():
        rows = _rows(ref)
        if not rows:
            raise NoStockAtLocation(
                f"No stock of '{item_type.name}' at location id={ref.location_id}"
            )

        removed = 0
        serials = [row.serial_number for row in rows if row.serial_number]
        if serials:
            removed += ItemRepository.delete_by_serial_numbers(serials, notes)
        for row in rows:
            if row.serial_number is None:
                removed += ItemRepository.delete_non_serialized(row.id, notes)

    logger.info(f"Stock deleted at {ref}: {removed} units")
    return removed
