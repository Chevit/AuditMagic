"""Theme configuration with all parameters stored in enum values."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict


@dataclass
class ThemeColors:
    """Color palette for a theme."""

    main: str  # Main text/foreground color
    secondary: str  # Secondary/background color
    border_default: str
    border_hover: str
    border_focus: str
    bg_default: str
    bg_hover: str
    bg_disabled: str
    text_secondary: str
    text_disabled: str

    # Action button colors
    primary: str  # Green - primary actions
    primary_hover: str
    primary_pressed: str

    danger: str  # Red - cancel/delete actions
    danger_hover: str
    danger_pressed: str

    info: str  # Blue - informational
    info_hover: str
    info_pressed: str


@dataclass
class ThemeDimensions:
    """Dimensions for UI elements."""

    input_height: int
    button_height: int
    button_min_width: int
    button_padding: int
    border_radius: int
    font_size: int
    font_size_large: int


@dataclass
class ThemeParameters:
    """Complete theme parameters."""

    name: str
    mode: str  # "light" or "dark"
    qt_material_theme: str
    colors: ThemeColors
    dimensions: ThemeDimensions


class Theme(Enum):
    """Available themes with all parameters."""

    LIGHT = ThemeParameters(
        name="Light",
        mode="light",
        qt_material_theme="light_blue.xml",
        colors=ThemeColors(
            main="#282828",
            secondary="#BBC8C3",
            border_default="#ccc",
            border_hover="#999",
            border_focus="#4CAF50",
            bg_default="#ffffff",
            bg_hover="#f0f0f0",
            bg_disabled="#e0e0e0",
            text_secondary="#666666",
            text_disabled="#999999",
            primary="#4CAF50",
            primary_hover="#45a049",
            primary_pressed="#3d8b40",
            danger="#f44336",
            danger_hover="#da190b",
            danger_pressed="#c41000",
            info="#2196F3",
            info_hover="#0b7dda",
            info_pressed="#0969c3",
        ),
        dimensions=ThemeDimensions(
            input_height=28,
            button_height=25,
            button_min_width=100,
            button_padding=10,
            border_radius=4,
            font_size=13,
            font_size_large=14,
        ),
    )

    DARK = ThemeParameters(
        name="Dark",
        mode="dark",
        qt_material_theme="dark_blue.xml",
        colors=ThemeColors(
            main="#d3d3d3",
            secondary="#130512",
            border_default="#3a3a3a",
            border_hover="#5a5a5a",
            border_focus="#4CAF50",
            bg_default="#1e1e1e",
            bg_hover="#2a2a2a",
            bg_disabled="#2c2c2c",
            text_secondary="#aaaaaa",
            text_disabled="#666666",
            primary="#4CAF50",
            primary_hover="#45a049",
            primary_pressed="#3d8b40",
            danger="#f44336",
            danger_hover="#da190b",
            danger_pressed="#c41000",
            info="#2196F3",
            info_hover="#0b7dda",
            info_pressed="#0969c3",
        ),
        dimensions=ThemeDimensions(
            input_height=28,
            button_height=25,
            button_min_width=100,
            button_padding=10,
            border_radius=4,
            font_size=13,
            font_size_large=14,
        ),
    )

    @classmethod
    def get_by_name(cls, name: str) -> "Theme":
        """Get theme by name.

        Args:
            name: Theme name (e.g., "Light", "Dark")

        Returns:
            Theme enum value

        Raises:
            ValueError: If theme name not found
        """
        for theme in cls:
            if theme.value.name == name:
                return theme
        raise ValueError(f"Theme '{name}' not found")

    @classmethod
    def get_all_names(cls) -> list[str]:
        """Get list of all theme names.

        Returns:
            List of theme names
        """
        return [theme.value.name for theme in cls]

    @property
    def params(self) -> ThemeParameters:
        """Get theme parameters.

        Returns:
            ThemeParameters instance
        """
        return self.value


# Current theme holder (singleton pattern)
_current_theme: Theme = Theme.LIGHT


def get_current_theme() -> Theme:
    """Get the currently active theme.

    Returns:
        Current Theme enum value
    """
    return _current_theme


def set_current_theme(theme: Theme) -> None:
    """Set the currently active theme.

    Args:
        theme: Theme enum value to set as current
    """
    global _current_theme
    _current_theme = theme


def get_theme_colors() -> ThemeColors:
    """Get colors for the current theme.

    Returns:
        ThemeColors instance
    """
    return _current_theme.value.colors


def get_theme_dimensions() -> ThemeDimensions:
    """Get dimensions for the current theme.

    Returns:
        ThemeDimensions instance
    """
    return _current_theme.value.dimensions
