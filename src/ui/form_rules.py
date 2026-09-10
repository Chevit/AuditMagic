"""Form validation rules for the item dialogs.

Qt-free by design: no PyQt6 import here, so this module is testable without
a QApplication. The Qt side lives in ui/dialogs/validation_feedback.py,
which turns the FieldError list this module returns into a QMessageBox and
a focused widget.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from ui.translations import tr


@dataclass(frozen=True)
class FieldError:
    """One validation failure, tied to the field key that caused it."""

    field: str
    message: str


def validate_required_field(value: str, field_name: str) -> Tuple[bool, str]:
    """Validate that a required field is not empty.

    Args:
        value: Field value
        field_name: Name of field for error message

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value or value.strip() == "":
        return (False, f"{field_name} is required")
    return (True, "")


def validate_positive_integer(
    value: str, field_name: str, minimum: int = 1, maximum: int = 999999
) -> Tuple[bool, str]:
    """Validate that a value is a positive integer within range.

    Args:
        value: Value to validate
        field_name: Name of field for error message
        minimum: Minimum allowed value (default: 1)
        maximum: Maximum allowed value (default: 999999)

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        int_value = int(value)
        if int_value < minimum:
            return (False, f"{field_name} must be at least {minimum}")
        if int_value > maximum:
            return (False, f"{field_name} must be at most {maximum}")
        return (True, "")
    except (ValueError, TypeError):
        return (False, f"{field_name} must be a valid number")


def validate_length(
    value: str, field_name: str, min_length: int = 0, max_length: int = 255
) -> Tuple[bool, str]:
    """Validate string length.

    Args:
        value: Value to validate
        field_name: Name of field for error message
        min_length: Minimum length (default: 0)
        max_length: Maximum length (default: 255)

    Returns:
        Tuple of (is_valid, error_message)
    """
    length = len(value.strip()) if value else 0

    if length < min_length:
        return (False, f"{field_name} must be at least {min_length} characters")
    if length > max_length:
        return (False, f"{field_name} must be at most {max_length} characters")

    return (True, "")


def add_item_rules(
    *,
    item_type: str,
    quantity_text: str,
    serial_number: str,
    initial_notes: str,
    is_serialized: bool,
) -> List[FieldError]:
    """Validate the Add Item form. Returns errors in field order."""
    errors: List[FieldError] = []

    valid, message = validate_required_field(item_type, tr("field.type"))
    if not valid:
        errors.append(FieldError("type", message))
    else:
        valid, message = validate_length(
            item_type, tr("field.type"), min_length=2, max_length=255
        )
        if not valid:
            errors.append(FieldError("type", message))

    if not quantity_text:
        errors.append(FieldError("quantity", tr("message.quantity_required")))
    else:
        try:
            quantity = int(quantity_text)
            valid, message = validate_positive_integer(
                str(quantity), tr("field.quantity"), minimum=1
            )
            if not valid:
                errors.append(FieldError("quantity", message))
        except ValueError:
            errors.append(FieldError("quantity", tr("message.quantity_invalid")))

    if is_serialized:
        if not serial_number:
            errors.append(FieldError("serial", tr("error.serial.required")))
        else:
            valid, message = validate_length(
                serial_number, tr("field.serial_number"), max_length=255
            )
            if not valid:
                errors.append(FieldError("serial", message))
    elif serial_number:
        errors.append(FieldError("serial", tr("error.serial.not_allowed")))

    if initial_notes:
        valid, message = validate_length(
            initial_notes, tr("label.initial_notes"), max_length=1000
        )
        if not valid:
            errors.append(FieldError("notes", message))

    return errors


def edit_item_rules(
    *,
    item_type: str,
    quantity_text: str,
    serial_number: str,
    item_details: str,
    edit_reason: str,
    is_serialized: bool,
    remaining_serial_count: int,
) -> List[FieldError]:
    """Validate the Edit Item form. Returns errors in field order."""
    errors: List[FieldError] = []

    valid, message = validate_required_field(item_type, tr("field.type"))
    if not valid:
        errors.append(FieldError("type", message))
    else:
        valid, message = validate_length(
            item_type, tr("field.type"), min_length=2, max_length=255
        )
        if not valid:
            errors.append(FieldError("type", message))

    # Serialized items show a read-only serial count, not an editable
    # quantity — nothing to validate here.
    if not is_serialized:
        if not quantity_text:
            errors.append(FieldError("quantity", tr("message.quantity_required")))
        else:
            try:
                quantity = int(quantity_text)
                valid, message = validate_positive_integer(
                    str(quantity), tr("field.quantity"), minimum=1
                )
                if not valid:
                    errors.append(FieldError("quantity", message))
            except ValueError:
                errors.append(FieldError("quantity", tr("message.quantity_invalid")))

    if serial_number:
        valid, message = validate_length(
            serial_number, tr("field.serial_number"), max_length=255
        )
        if not valid:
            errors.append(FieldError("serial", message))

    if item_details:
        valid, message = validate_length(
            item_details, tr("field.details"), max_length=1000
        )
        if not valid:
            errors.append(FieldError("details", message))

    valid, message = validate_required_field(edit_reason, tr("field.edit_reason"))
    if not valid:
        errors.append(FieldError("edit_reason", message))
    else:
        valid, message = validate_length(
            edit_reason, tr("field.edit_reason"), min_length=3, max_length=1000
        )
        if not valid:
            errors.append(FieldError("edit_reason", message))

    if is_serialized and remaining_serial_count == 0:
        errors.append(FieldError("serial", tr("message.at_least_one_serial")))

    return errors


def quantity_rules(
    *,
    quantity_text: str,
    notes: str,
    is_add: bool,
    current_quantity: int,
) -> List[FieldError]:
    """Validate the Add/Remove Quantity form. Returns errors in field order."""
    errors: List[FieldError] = []

    if not quantity_text:
        errors.append(FieldError("quantity", tr("message.quantity_required")))
    else:
        try:
            quantity = int(quantity_text)
            if quantity < 1:
                errors.append(FieldError("quantity", tr("message.quantity_positive")))
            elif not is_add and quantity > current_quantity:
                detail = tr(
                    "message.not_enough_quantity_detail",
                    requested=quantity,
                    available=current_quantity,
                )
                message = f"{tr('message.not_enough_quantity')}\n{detail}"
                errors.append(FieldError("quantity", message))
        except ValueError:
            errors.append(FieldError("quantity", tr("message.quantity_invalid")))

    if notes:
        valid, message = validate_length(notes, tr("field.notes"), max_length=1000)
        if not valid:
            errors.append(FieldError("notes", message))

    return errors


def has_serialization_conflict(
    *,
    existing_is_serialized: Optional[bool],
    current_is_serialized: bool,
) -> bool:
    """Whether a type name/sub-type resolves to a type with a different
    serialization state than the one currently selected."""
    if existing_is_serialized is None:
        return False
    return existing_is_serialized != current_is_serialized
