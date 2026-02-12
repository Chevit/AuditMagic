"""Centralized UI styles for AuditMagic application.

This module provides additional styling customizations that work alongside qt-material.
qt-material provides the base theme (light/dark with Material Design), while this
module adds specific customizations for dialogs, buttons, and input fields.

The styles defined here complement qt-material's themes and provide:
- Consistent dimensions across all widgets
- Standardized helper functions for applying styles
- Easy-to-use style application without inline CSS

Note: qt-material handles most of the theming automatically. These styles are
additional customizations that maintain consistency across custom dialogs.
"""

# Color Palette
class Colors:
    """Application color palette."""

    # Primary colors
    PRIMARY = "#4CAF50"  # Green - primary actions
    PRIMARY_HOVER = "#45a049"
    PRIMARY_PRESSED = "#3d8b40"

    # Secondary/Danger colors
    DANGER = "#f44336"  # Red - cancel/delete actions
    DANGER_HOVER = "#da190b"
    DANGER_PRESSED = "#c41000"

    # Info/Neutral colors
    INFO = "#2196F3"  # Blue - informational
    INFO_HOVER = "#0b7dda"
    INFO_PRESSED = "#0969c3"

    # Borders and backgrounds
    BORDER_DEFAULT = "#ccc"
    BORDER_HOVER = "#999"
    BORDER_FOCUS = PRIMARY

    # Text colors
    TEXT_PRIMARY = "#000000"
    TEXT_SECONDARY = "#666666"
    TEXT_DISABLED = "#999999"

    # Background colors
    BG_DEFAULT = "#ffffff"
    BG_HOVER = "#f5f5f5"
    BG_DISABLED = "#e0e0e0"


# Common dimensions
class Dimensions:
    """Common UI dimensions."""

    # Input fields
    INPUT_HEIGHT = 35
    INPUT_PADDING = 8
    INPUT_FONT_SIZE = 13

    # Buttons
    BUTTON_HEIGHT = 35
    BUTTON_MIN_WIDTH = 100
    BUTTON_PADDING = 8

    # Border radius
    BORDER_RADIUS = 4
    BORDER_WIDTH = 2

    # Spacing
    SPACING_SMALL = 5
    SPACING_MEDIUM = 10
    SPACING_LARGE = 15
    SPACING_XLARGE = 20


# StyleSheet Templates
class Styles:
    """Pre-defined StyleSheet strings for common widgets."""

    # Input fields (QLineEdit)
    LINE_EDIT = f"""
        QLineEdit {{
            padding: {Dimensions.INPUT_PADDING}px;
            font-size: {Dimensions.INPUT_FONT_SIZE}px;
            border: {Dimensions.BORDER_WIDTH}px solid {Colors.BORDER_DEFAULT};
            border-radius: {Dimensions.BORDER_RADIUS}px;
            background-color: {Colors.BG_DEFAULT};
        }}
        QLineEdit:focus {{
            border: {Dimensions.BORDER_WIDTH}px solid {Colors.BORDER_FOCUS};
        }}
        QLineEdit:hover {{
            border: {Dimensions.BORDER_WIDTH}px solid {Colors.BORDER_HOVER};
        }}
        QLineEdit:disabled {{
            background-color: {Colors.BG_DISABLED};
            color: {Colors.TEXT_DISABLED};
        }}
    """

    # Large input fields (quantity, etc.)
    LINE_EDIT_LARGE = f"""
        QLineEdit {{
            padding: {Dimensions.INPUT_PADDING}px;
            font-size: 14px;
            border: {Dimensions.BORDER_WIDTH}px solid {Colors.BORDER_DEFAULT};
            border-radius: {Dimensions.BORDER_RADIUS}px;
            background-color: {Colors.BG_DEFAULT};
        }}
        QLineEdit:focus {{
            border: {Dimensions.BORDER_WIDTH}px solid {Colors.BORDER_FOCUS};
        }}
        QLineEdit:hover {{
            border: {Dimensions.BORDER_WIDTH}px solid {Colors.BORDER_HOVER};
        }}
        QLineEdit:disabled {{
            background-color: {Colors.BG_DISABLED};
            color: {Colors.TEXT_DISABLED};
        }}
    """

    # Text areas (QTextEdit)
    TEXT_EDIT = f"""
        QTextEdit {{
            padding: 5px;
            border: {Dimensions.BORDER_WIDTH}px solid {Colors.BORDER_DEFAULT};
            border-radius: {Dimensions.BORDER_RADIUS}px;
            background-color: {Colors.BG_DEFAULT};
        }}
        QTextEdit:focus {{
            border: {Dimensions.BORDER_WIDTH}px solid {Colors.BORDER_FOCUS};
        }}
        QTextEdit:hover {{
            border: {Dimensions.BORDER_WIDTH}px solid {Colors.BORDER_HOVER};
        }}
        QTextEdit:disabled {{
            background-color: {Colors.BG_DISABLED};
            color: {Colors.TEXT_DISABLED};
        }}
    """

    # Primary action buttons (Save, Add, OK)
    BUTTON_PRIMARY = f"""
        QPushButton {{
            background-color: {Colors.PRIMARY};
            color: white;
            padding: {Dimensions.BUTTON_PADDING}px;
            border-radius: {Dimensions.BORDER_RADIUS}px;
            font-weight: bold;
            border: none;
            min-height: {Dimensions.BUTTON_HEIGHT}px;
        }}
        QPushButton:hover {{
            background-color: {Colors.PRIMARY_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.PRIMARY_PRESSED};
        }}
        QPushButton:disabled {{
            background-color: {Colors.BG_DISABLED};
            color: {Colors.TEXT_DISABLED};
        }}
    """

    # Danger/Cancel buttons (Cancel, Delete)
    BUTTON_DANGER = f"""
        QPushButton {{
            background-color: {Colors.DANGER};
            color: white;
            padding: {Dimensions.BUTTON_PADDING}px;
            border-radius: {Dimensions.BORDER_RADIUS}px;
            font-weight: bold;
            border: none;
            min-height: {Dimensions.BUTTON_HEIGHT}px;
        }}
        QPushButton:hover {{
            background-color: {Colors.DANGER_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.DANGER_PRESSED};
        }}
        QPushButton:disabled {{
            background-color: {Colors.BG_DISABLED};
            color: {Colors.TEXT_DISABLED};
        }}
    """

    # Info/Neutral buttons (Search, Clear, Details)
    BUTTON_INFO = f"""
        QPushButton {{
            background-color: {Colors.INFO};
            color: white;
            padding: {Dimensions.BUTTON_PADDING}px;
            border-radius: {Dimensions.BORDER_RADIUS}px;
            font-weight: bold;
            border: none;
            min-height: {Dimensions.BUTTON_HEIGHT}px;
        }}
        QPushButton:hover {{
            background-color: {Colors.INFO_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.INFO_PRESSED};
        }}
        QPushButton:disabled {{
            background-color: {Colors.BG_DISABLED};
            color: {Colors.TEXT_DISABLED};
        }}
    """

    # Secondary/Outline buttons
    BUTTON_SECONDARY = f"""
        QPushButton {{
            background-color: transparent;
            color: {Colors.TEXT_PRIMARY};
            padding: {Dimensions.BUTTON_PADDING}px;
            border-radius: {Dimensions.BORDER_RADIUS}px;
            font-weight: bold;
            border: {Dimensions.BORDER_WIDTH}px solid {Colors.BORDER_DEFAULT};
            min-height: {Dimensions.BUTTON_HEIGHT}px;
        }}
        QPushButton:hover {{
            background-color: {Colors.BG_HOVER};
            border-color: {Colors.BORDER_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.BG_DISABLED};
        }}
        QPushButton:disabled {{
            background-color: {Colors.BG_DISABLED};
            color: {Colors.TEXT_DISABLED};
            border-color: {Colors.BORDER_DEFAULT};
        }}
    """

    # ComboBox
    COMBO_BOX = f"""
        QComboBox {{
            padding: {Dimensions.INPUT_PADDING}px;
            border: {Dimensions.BORDER_WIDTH}px solid {Colors.BORDER_DEFAULT};
            border-radius: {Dimensions.BORDER_RADIUS}px;
            background-color: {Colors.BG_DEFAULT};
            min-height: 30px;
        }}
        QComboBox:hover {{
            border: {Dimensions.BORDER_WIDTH}px solid {Colors.BORDER_HOVER};
        }}
        QComboBox:focus {{
            border: {Dimensions.BORDER_WIDTH}px solid {Colors.BORDER_FOCUS};
        }}
        QComboBox::drop-down {{
            border: none;
            padding-right: 5px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid {Colors.TEXT_SECONDARY};
        }}
    """


# Helper functions
def apply_input_style(widget, large=False):
    """Apply standard input field styling to a widget.

    Args:
        widget: QLineEdit or similar input widget
        large: If True, use larger font size
    """
    if large:
        widget.setStyleSheet(Styles.LINE_EDIT_LARGE)
        widget.setMinimumHeight(Dimensions.INPUT_HEIGHT)
    else:
        widget.setStyleSheet(Styles.LINE_EDIT)
        widget.setMinimumHeight(Dimensions.INPUT_HEIGHT)


def apply_button_style(button, style="primary"):
    """Apply button styling.

    Args:
        button: QPushButton
        style: One of "primary", "danger", "info", "secondary"
    """
    button.setMinimumWidth(Dimensions.BUTTON_MIN_WIDTH)
    button.setMinimumHeight(Dimensions.BUTTON_HEIGHT)

    if style == "primary":
        button.setStyleSheet(Styles.BUTTON_PRIMARY)
    elif style == "danger":
        button.setStyleSheet(Styles.BUTTON_DANGER)
    elif style == "info":
        button.setStyleSheet(Styles.BUTTON_INFO)
    elif style == "secondary":
        button.setStyleSheet(Styles.BUTTON_SECONDARY)


def apply_text_edit_style(widget):
    """Apply standard text edit styling.

    Args:
        widget: QTextEdit widget
    """
    widget.setStyleSheet(Styles.TEXT_EDIT)


def apply_combo_box_style(widget):
    """Apply standard combo box styling.

    Args:
        widget: QComboBox widget
    """
    widget.setStyleSheet(Styles.COMBO_BOX)
