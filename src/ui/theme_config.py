"""Theme configuration with all parameters stored in enum values."""

from dataclasses import dataclass
from enum import Enum


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
            main="#0f172a",
            secondary="#f1f5f9",
            border_default="#e2e8f0",
            border_hover="#94a3b8",
            border_focus="#0ea5e9",
            bg_default="#ffffff",
            bg_hover="#f8fafc",
            bg_disabled="#f1f5f9",
            text_secondary="#64748b",
            text_disabled="#94a3b8",
            primary="#059669",
            primary_hover="#047857",
            primary_pressed="#065f46",
            danger="#dc2626",
            danger_hover="#b91c1c",
            danger_pressed="#991b1b",
            info="#2563eb",
            info_hover="#1d4ed8",
            info_pressed="#1e40af",
        ),
        dimensions=ThemeDimensions(
            input_height=36,
            button_height=32,
            button_min_width=100,
            button_padding=14,
            border_radius=6,
            font_size=14,
            font_size_large=16,
        ),
    )

    DARK = ThemeParameters(
        name="Dark",
        mode="dark",
        qt_material_theme="dark_blue.xml",
        colors=ThemeColors(
            main="#e2e8f0",
            secondary="#1e293b",
            border_default="#1e293b",
            border_hover="#334155",
            border_focus="#38bdf8",
            bg_default="#0f172a",
            bg_hover="#1e293b",
            bg_disabled="#0d1424",
            text_secondary="#94a3b8",
            text_disabled="#475569",
            primary="#10b981",
            primary_hover="#059669",
            primary_pressed="#047857",
            danger="#f87171",
            danger_hover="#ef4444",
            danger_pressed="#dc2626",
            info="#60a5fa",
            info_hover="#3b82f6",
            info_pressed="#2563eb",
        ),
        dimensions=ThemeDimensions(
            input_height=36,
            button_height=32,
            button_min_width=100,
            button_padding=14,
            border_radius=6,
            font_size=14,
            font_size_large=16,
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
