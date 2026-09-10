"""The Qt side of form validation: showing a FieldError list to the user.

Pairs with ui/form_rules.py, which computes the errors without touching Qt.
This module is the one place that turns them into a QMessageBox and a
focused widget — replacing what used to be three near-identical blocks in
add_item_dialog.py, edit_item_dialog.py and quantity_dialog.py.
"""

from typing import Dict, List

from PyQt6.QtWidgets import QLineEdit, QMessageBox, QWidget

from core.logger import logger
from ui.form_rules import FieldError
from ui.translations import tr


def show_validation_errors(
    parent: QWidget,
    errors: List[FieldError],
    widgets: Dict[str, QWidget],
    log_prefix: str,
) -> None:
    """Show errors in one message box, then focus the first bad field.

    Args:
        parent: Dialog to parent the message box to.
        errors: Field errors, in the order they should be shown and focused.
        widgets: Field key -> widget, for the fields this dialog can focus.
            A key with no matching widget (e.g. "serial" when the dialog has
            no serial field to focus) is skipped rather than raising.
        log_prefix: Distinguishes this dialog's log lines, e.g. "Form",
            "Edit form", "Quantity".
    """
    QMessageBox.warning(
        parent,
        tr("message.validation_error"),
        tr("message.fix_errors") + "\n\n" + "\n".join(f"• {e.message}" for e in errors),
    )
    logger.warning(f"{log_prefix} validation failed: {[e.message for e in errors]}")

    if not errors:
        return
    widget = widgets.get(errors[0].field)
    if widget is None:
        return
    widget.setFocus()
    if isinstance(widget, QLineEdit):
        widget.selectAll()
