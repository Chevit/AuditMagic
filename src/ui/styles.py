"""Centralized styling system for AuditMagic.

This module provides consistent styling across all UI components with support
for theme-aware colors and dimensions that adapt to the selected theme.
All theme parameters are retrieved from the Theme enum.
"""

from theme_config import get_theme_colors, get_theme_dimensions


# Color Palette (theme-aware)
class Colors:
    """Theme-aware application color palette.

    Colors automatically adapt based on current theme.
    All colors are retrieved from the Theme enum configuration.
    """

    @staticmethod
    def get_main_color() -> str:
        """Get main text/foreground color based on current theme."""
        return get_theme_colors().main

    @staticmethod
    def get_secondary_color() -> str:
        """Get secondary/background color based on current theme."""
        return get_theme_colors().secondary

    @staticmethod
    def get_border_default() -> str:
        """Get default border color based on current theme."""
        return get_theme_colors().border_default

    @staticmethod
    def get_bg_default() -> str:
        """Get default background color based on current theme."""
        return get_theme_colors().bg_default

    @staticmethod
    def get_bg_hover() -> str:
        """Get hover background color based on current theme."""
        return get_theme_colors().bg_hover

    @staticmethod
    def get_bg_disabled() -> str:
        """Get disabled background color based on current theme."""
        return get_theme_colors().bg_disabled

    @staticmethod
    def get_text_secondary() -> str:
        """Get secondary text color based on current theme."""
        return get_theme_colors().text_secondary

    @staticmethod
    def get_text_disabled() -> str:
        """Get disabled text color based on current theme."""
        return get_theme_colors().text_disabled

    @staticmethod
    def get_border_hover() -> str:
        """Get hover border color based on current theme."""
        return get_theme_colors().border_hover

    @staticmethod
    def get_border_focus() -> str:
        """Get focus border color based on current theme."""
        return get_theme_colors().border_focus

    @staticmethod
    def get_primary() -> str:
        """Get primary action color based on current theme."""
        return get_theme_colors().primary

    @staticmethod
    def get_primary_hover() -> str:
        """Get primary hover color based on current theme."""
        return get_theme_colors().primary_hover

    @staticmethod
    def get_primary_pressed() -> str:
        """Get primary pressed color based on current theme."""
        return get_theme_colors().primary_pressed

    @staticmethod
    def get_danger() -> str:
        """Get danger action color based on current theme."""
        return get_theme_colors().danger

    @staticmethod
    def get_danger_hover() -> str:
        """Get danger hover color based on current theme."""
        return get_theme_colors().danger_hover

    @staticmethod
    def get_danger_pressed() -> str:
        """Get danger pressed color based on current theme."""
        return get_theme_colors().danger_pressed

    @staticmethod
    def get_info() -> str:
        """Get info action color based on current theme."""
        return get_theme_colors().info

    @staticmethod
    def get_info_hover() -> str:
        """Get info hover color based on current theme."""
        return get_theme_colors().info_hover

    @staticmethod
    def get_info_pressed() -> str:
        """Get info pressed color based on current theme."""
        return get_theme_colors().info_pressed


# Dimensions (theme-aware)
class Dimensions:
    """Theme-aware UI dimensions.

    Dimensions are retrieved from the current theme configuration,
    allowing different themes to have different sizes.
    """

    @staticmethod
    def get_input_height() -> int:
        """Get input field height from current theme."""
        return get_theme_dimensions().input_height

    @staticmethod
    def get_button_height() -> int:
        """Get button height from current theme."""
        return get_theme_dimensions().button_height

    @staticmethod
    def get_button_min_width() -> int:
        """Get button minimum width from current theme."""
        return get_theme_dimensions().button_min_width

    @staticmethod
    def get_button_padding() -> int:
        """Get button padding from current theme."""
        return get_theme_dimensions().button_padding

    @staticmethod
    def get_border_radius() -> int:
        """Get border radius from current theme."""
        return get_theme_dimensions().border_radius

    @staticmethod
    def get_font_size() -> int:
        """Get font size from current theme."""
        return get_theme_dimensions().font_size

    @staticmethod
    def get_font_size_large() -> int:
        """Get large font size from current theme."""
        return get_theme_dimensions().font_size_large

    # Static properties (constant across themes)
    BORDER_WIDTH = 2
    INPUT_PADDING = 8

    # Spacing (constant)
    SPACING_SMALL = 5
    SPACING_MEDIUM = 10
    SPACING_LARGE = 15
    SPACING_XLARGE = 20


# StyleSheet Templates
class Styles:
    """Pre-defined StyleSheet strings for common widgets with theme-aware colors and dimensions."""

    @staticmethod
    def get_line_edit_style() -> str:
        """Get QLineEdit stylesheet with theme-aware colors and dimensions."""
        return f"""
            QLineEdit {{
                padding: {Dimensions.INPUT_PADDING}px;
                font-size: {Dimensions.get_font_size()}px;
                border: {Dimensions.BORDER_WIDTH}px solid {Colors.get_border_default()};
                border-radius: {Dimensions.get_border_radius()}px;
                background-color: {Colors.get_bg_default()};
                color: {Colors.get_main_color()};
                height: {Dimensions.get_input_height()}px;
            }}
            QLineEdit:focus {{
                border: {Dimensions.BORDER_WIDTH}px solid {Colors.get_border_focus()};
            }}
            QLineEdit:hover {{
                border: {Dimensions.BORDER_WIDTH}px solid {Colors.get_border_hover()};
            }}
            QLineEdit:disabled {{
                background-color: {Colors.get_bg_disabled()};
                color: {Colors.get_text_disabled()};
            }}
        """

    @staticmethod
    def get_line_edit_large_style() -> str:
        """Get large QLineEdit stylesheet with theme-aware colors and dimensions."""
        return f"""
            QLineEdit {{
                padding: {Dimensions.INPUT_PADDING}px;
                font-size: {Dimensions.get_font_size_large()}px;
                border: {Dimensions.BORDER_WIDTH}px solid {Colors.get_border_default()};
                border-radius: {Dimensions.get_border_radius()}px;
                background-color: {Colors.get_bg_default()};
                color: {Colors.get_main_color()};
            }}
            QLineEdit:focus {{
                border: {Dimensions.BORDER_WIDTH}px solid {Colors.get_border_focus()};
            }}
            QLineEdit:hover {{
                border: {Dimensions.BORDER_WIDTH}px solid {Colors.get_border_hover()};
            }}
            QLineEdit:disabled {{
                background-color: {Colors.get_bg_disabled()};
                color: {Colors.get_text_disabled()};
            }}
        """

    @staticmethod
    def get_text_edit_style() -> str:
        """Get QTextEdit stylesheet with theme-aware colors and dimensions."""
        return f"""
            QTextEdit {{
                padding: 5px;
                border: {Dimensions.BORDER_WIDTH}px solid {Colors.get_border_default()};
                border-radius: {Dimensions.get_border_radius()}px;
                background-color: {Colors.get_bg_default()};
                color: {Colors.get_main_color()};
                font-size: {Dimensions.get_font_size()}px;
            }}
            QTextEdit:focus {{
                border: {Dimensions.BORDER_WIDTH}px solid {Colors.get_border_focus()};
            }}
            QTextEdit:disabled {{
                background-color: {Colors.get_bg_disabled()};
                color: {Colors.get_text_disabled()};
            }}
        """

    @staticmethod
    def get_combo_box_style() -> str:
        """Get QComboBox stylesheet with theme-aware colors and dimensions."""
        return f"""
            QComboBox {{
                padding: {Dimensions.INPUT_PADDING}px;
                font-size: {Dimensions.get_font_size()}px;
                border: {Dimensions.BORDER_WIDTH}px solid {Colors.get_border_default()};
                border-radius: {Dimensions.get_border_radius()}px;
                background-color: {Colors.get_bg_default()};
                color: {Colors.get_main_color()};
                height: {Dimensions.get_input_height()}px;
            }}
            QComboBox:hover {{
                border: {Dimensions.BORDER_WIDTH}px solid {Colors.get_border_hover()};
            }}
            QComboBox:focus {{
                border: {Dimensions.BORDER_WIDTH}px solid {Colors.get_border_focus()};
            }}
            QComboBox:disabled {{
                background-color: {Colors.get_bg_disabled()};
                color: {Colors.get_text_disabled()};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {Colors.get_main_color()};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.get_bg_default()};
                color: {Colors.get_main_color()};
                selection-background-color: {Colors.get_primary()};
                selection-color: white;
                border: 1px solid {Colors.get_border_default()};
            }}
        """

    @staticmethod
    def get_button_primary_style() -> str:
        """Get primary button stylesheet with theme-aware dimensions."""
        return f"""
            QPushButton {{
                background-color: {Colors.get_primary()};
                color: white;
                padding: 2px {Dimensions.get_button_padding()}px;
                border-radius: {Dimensions.get_border_radius()}px;
                font-weight: bold;
                border: none;
                height: {Dimensions.get_button_height()}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.get_primary_hover()};
            }}
            QPushButton:pressed {{
                background-color: {Colors.get_primary_pressed()};
            }}
            QPushButton:disabled {{
                background-color: {Colors.get_bg_disabled()};
                color: {Colors.get_text_disabled()};
            }}
        """

    @staticmethod
    def get_button_danger_style() -> str:
        """Get danger button stylesheet with theme-aware dimensions."""
        return f"""
            QPushButton {{
                background-color: {Colors.get_danger()};
                color: white;
                padding: 2px {Dimensions.get_button_padding()}px;
                border-radius: {Dimensions.get_border_radius()}px;
                font-weight: bold;
                border: none;
                height: {Dimensions.get_button_height()}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.get_danger_hover()};
            }}
            QPushButton:pressed {{
                background-color: {Colors.get_danger_pressed()};
            }}
            QPushButton:disabled {{
                background-color: {Colors.get_bg_disabled()};
                color: {Colors.get_text_disabled()};
            }}
        """

    @staticmethod
    def get_button_info_style() -> str:
        """Get info button stylesheet with theme-aware dimensions."""
        return f"""
            QPushButton {{
                background-color: {Colors.get_info()};
                color: white;
                padding: 2px {Dimensions.get_button_padding()}px;
                border-radius: {Dimensions.get_border_radius()}px;
                font-weight: bold;
                border: none;
                height: {Dimensions.get_button_height()}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.get_info_hover()};
            }}
            QPushButton:pressed {{
                background-color: {Colors.get_info_pressed()};
            }}
            QPushButton:disabled {{
                background-color: {Colors.get_bg_disabled()};
                color: {Colors.get_text_disabled()};
            }}
        """

    @staticmethod
    def get_button_secondary_style() -> str:
        """Get secondary button stylesheet with theme-aware colors and dimensions."""
        return f"""
            QPushButton {{
                background-color: {Colors.get_secondary_color()};
                color: {Colors.get_main_color()};
                padding: 2px {Dimensions.get_button_padding()}px;
                border-radius: {Dimensions.get_border_radius()}px;
                border: {Dimensions.BORDER_WIDTH}px solid {Colors.get_border_default()};
                height: {Dimensions.get_button_height()}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.get_bg_hover()};
                border: {Dimensions.BORDER_WIDTH}px solid {Colors.get_border_hover()};
            }}
            QPushButton:pressed {{
                background-color: {Colors.get_bg_default()};
            }}
            QPushButton:disabled {{
                background-color: {Colors.get_bg_disabled()};
                color: {Colors.get_text_disabled()};
            }}
        """


# Helper Functions
def apply_input_style(widget, large=False):
    """Apply standard input field styling to a widget.

    Args:
        widget: QLineEdit or similar input widget
        large: If True, use larger font size
    """
    if large:
        widget.setStyleSheet(Styles.get_line_edit_large_style())
        widget.setMinimumHeight(Dimensions.get_input_height())
    else:
        widget.setStyleSheet(Styles.get_line_edit_style())
        widget.setMinimumHeight(Dimensions.get_input_height())


def apply_button_style(button, style="primary"):
    """Apply button styling.

    Args:
        button: QPushButton
        style: One of "primary", "danger", "info", "secondary"
    """
    button.setMinimumWidth(Dimensions.get_button_min_width())
    button.setMinimumHeight(Dimensions.get_button_height())

    if style == "primary":
        button.setStyleSheet(Styles.get_button_primary_style())
    elif style == "danger":
        button.setStyleSheet(Styles.get_button_danger_style())
    elif style == "info":
        button.setStyleSheet(Styles.get_button_info_style())
    elif style == "secondary":
        button.setStyleSheet(Styles.get_button_secondary_style())


def apply_text_edit_style(widget):
    """Apply standard text edit styling.

    Args:
        widget: QTextEdit widget
    """
    widget.setStyleSheet(Styles.get_text_edit_style())


def apply_combo_box_style(widget):
    """Apply standard combo box styling.

    Args:
        widget: QComboBox widget
    """
    widget.setStyleSheet(Styles.get_combo_box_style())
