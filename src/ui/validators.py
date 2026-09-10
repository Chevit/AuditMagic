"""Input validators for form fields.

The pure validation helpers (validate_required_field, validate_positive_integer,
validate_length) live in ui/form_rules.py instead of here — this module imports
PyQt6, so anything that needs to stay Qt-free can't import from it.
"""

from typing import Optional, Tuple

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

    def validate(
        self, input_str: Optional[str], pos: int
    ) -> Tuple[QValidator.State, str, int]:
        """Validate input string as a positive integer.

        Args:
            input_str: The input string to validate
            pos: Cursor position

        Returns:
            Tuple of (validation state, validated string, cursor position)
        """
        if not input_str:
            return (QValidator.State.Intermediate, "", pos)

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

    Allows any non-empty input.
    """

    def __init__(self, parent=None):
        """Initialize validator.

        Args:
            parent: Parent QObject
        """
        pattern = QRegularExpression(r"^.+$")
        super().__init__(pattern, parent)
