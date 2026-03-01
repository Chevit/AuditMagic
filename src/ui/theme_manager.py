"""Theme management for AuditMagic using qt-material.

This module provides theme switching with all theme parameters
stored in Theme enum values.
"""

from typing import Optional

from PyQt6.QtWidgets import QApplication
from qt_material import apply_stylesheet

from logger import logger
from theme_config import Theme, get_current_theme, set_current_theme


class ThemeManager:
    """Manages application themes using qt-material and Theme enum."""

    def __init__(self, app: QApplication):
        """Initialize theme manager.

        Args:
            app: QApplication instance
        """
        self._app = app
        logger.info("ThemeManager initialized")

    def apply_theme(self, theme: Theme, extra_styles: str = "") -> bool:
        """Apply a theme to the application.

        Args:
            theme: Theme enum value
            extra_styles: Additional custom StyleSheet to apply

        Returns:
            True if theme was applied successfully
        """
        try:
            params = theme.params
            logger.info(f"Applying theme: {params.name} ({params.qt_material_theme})")

            # Apply qt-material theme
            apply_stylesheet(
                self._app, theme=params.qt_material_theme, extra=extra_styles
            )

            # Update global current theme
            set_current_theme(theme)

            logger.info(f"Theme applied successfully: {params.name}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to apply theme {theme.value.name}: {e}", exc_info=True
            )
            return False

    def get_current_theme(self) -> Theme:
        """Get current theme.

        Returns:
            Current Theme enum value
        """
        return get_current_theme()

    def get_available_themes(self) -> list[str]:
        """Get all available theme names.

        Returns:
            List of theme names
        """
        return Theme.get_all_names()

    def toggle_theme(self) -> Theme:
        """Toggle between light and dark theme.

        Returns:
            New Theme enum value
        """
        current = get_current_theme()
        new_theme = Theme.DARK if current == Theme.LIGHT else Theme.LIGHT
        self.apply_theme(new_theme)
        logger.info(f"Theme toggled to: {new_theme.value.name}")
        return new_theme


# Global theme manager instance (will be initialized in main.py)
_theme_manager: Optional[ThemeManager] = None


def init_theme_manager(app: QApplication) -> ThemeManager:
    """Initialize the global theme manager.

    Args:
        app: QApplication instance

    Returns:
        ThemeManager instance
    """
    global _theme_manager
    _theme_manager = ThemeManager(app)
    logger.info("Global theme manager initialized")
    return _theme_manager


def get_theme_manager() -> Optional[ThemeManager]:
    """Get the global theme manager instance.

    Returns:
        ThemeManager instance or None if not initialized
    """
    return _theme_manager


def apply_theme(theme: Theme) -> bool:
    """Convenience function to apply theme using global manager.

    Args:
        theme: Theme enum value

    Returns:
        True if successful
    """
    if _theme_manager:
        return _theme_manager.apply_theme(theme)
    else:
        logger.error("Theme manager not initialized")
        return False
