"""Input validators for form fields."""

from typing import Tuple

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QIntValidator, QRegularExpressionValidator, QValidator


class PositiveIntValidator(QIntValidator):
    """Validator for positive integers only."""

    def __init__(self, minimum: int = 1, maximum: int = 999999, parent=None):
        """Initialize validator with range.

        Args:
            minimum: Minimum allowed value (default: 1)
            maximum: Maximum allowed value (default: 999999)
            parent: Parent QObject
        """
        super().__init__(minimum, maximum, parent)

    def validate(self, input_str: str, pos: int) -> Tuple[QValidator.State, str, int]:
        """Validate input string as a positive integer.

        Args:
            input_str: The input string to validate
            pos: Cursor position

        Returns:
            Tuple of (validation state, validated string, cursor position)
        """
        if input_str == "":
            return (QValidator.State.Intermediate, input_str, pos)

        state, validated_str, new_pos = super().validate(input_str, pos)

        if state == QValidator.State.Acceptable:
            try:
                value = int(validated_str)
                if value < 1:
                    return (QValidator.State.Invalid, validated_str, new_pos)
            except ValueError:
                return (QValidator.State.Invalid, validated_str, new_pos)

        return (state, validated_str, new_pos)


class ItemTypeValidator(QRegularExpressionValidator):
    """Validator for item type field.

    Allows letters (Latin and Cyrillic), numbers, spaces,
    and basic punctuation.
    """

    def __init__(self, parent=None):
        """Initialize validator.

        Args:
            parent: Parent QObject
        """
        pattern = QRegularExpression(r"^[A-Za-zА-Яа-яІіЇїЄєҐґ0-9\s\-_.,/]*$")
        super().__init__(pattern, parent)


class SerialNumberValidator(QRegularExpressionValidator):
    """Validator for serial numbers.

    Allows letters, numbers, and hyphens only.
    """

    def __init__(self, parent=None):
        """Initialize validator.

        Args:
            parent: Parent QObject
        """
        pattern = QRegularExpression(r"^[A-Za-z0-9\-]*$")
        super().__init__(pattern, parent)


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
