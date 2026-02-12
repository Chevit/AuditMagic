"""Theme management for AuditMagic using qt-material.

This module provides easy theme switching between light and dark modes
with multiple color variants. Themes are saved to user configuration.
"""

from typing import Optional
from PyQt6.QtWidgets import QApplication
from qt_material import apply_stylesheet, list_themes
from logger import logger


class ThemeManager:
    """Manages application themes using qt-material."""

    # Available theme configurations
    THEMES = {
        "light": {
            "default": "light_blue.xml",
            "teal": "light_teal.xml",
            "cyan": "light_cyan.xml",
            "purple": "light_purple.xml",
            "pink": "light_pink.xml",
            "amber": "light_amber.xml",
        },
        "dark": {
            "default": "dark_blue.xml",
            "teal": "dark_teal.xml",
            "cyan": "dark_cyan.xml",
            "purple": "dark_purple.xml",
            "pink": "dark_pink.xml",
            "amber": "dark_amber.xml",
        },
    }

    def __init__(self, app: QApplication):
        """Initialize theme manager.

        Args:
            app: QApplication instance
        """
        self._app = app
        self._current_theme = "light"
        self._current_variant = "default"
        logger.info("ThemeManager initialized")

    def apply_theme(
        self, theme: str = "light", variant: str = "default", extra_styles: str = ""
    ) -> bool:
        """Apply a theme to the application.

        Args:
            theme: Theme mode - "light" or "dark"
            variant: Color variant - "default", "teal", "cyan", "purple", "pink", "amber"
            extra_styles: Additional custom StyleSheet to apply

        Returns:
            True if theme was applied successfully
        """
        try:
            # Validate theme and variant
            if theme not in self.THEMES:
                logger.error(f"Invalid theme: {theme}. Using 'light'")
                theme = "light"

            if variant not in self.THEMES[theme]:
                logger.error(f"Invalid variant: {variant}. Using 'default'")
                variant = "default"

            # Get theme file
            theme_file = self.THEMES[theme][variant]

            logger.info(f"Applying theme: {theme}/{variant} ({theme_file})")

            # Apply qt-material theme
            apply_stylesheet(self._app, theme=theme_file, extra=extra_styles)

            # Store current theme
            self._current_theme = theme
            self._current_variant = variant

            logger.info(f"Theme applied successfully: {theme}/{variant}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply theme {theme}/{variant}: {e}", exc_info=True)
            return False

    def get_current_theme(self) -> tuple[str, str]:
        """Get current theme and variant.

        Returns:
            Tuple of (theme, variant)
        """
        return (self._current_theme, self._current_variant)

    def get_available_themes(self) -> dict:
        """Get all available themes.

        Returns:
            Dictionary of available themes and variants
        """
        return self.THEMES

    def toggle_theme(self) -> str:
        """Toggle between light and dark theme.

        Returns:
            New theme mode ("light" or "dark")
        """
        new_theme = "dark" if self._current_theme == "light" else "light"
        self.apply_theme(new_theme, self._current_variant)
        logger.info(f"Theme toggled to: {new_theme}")
        return new_theme

    def set_variant(self, variant: str) -> bool:
        """Change color variant while keeping current theme mode.

        Args:
            variant: Color variant to apply

        Returns:
            True if variant was changed successfully
        """
        return self.apply_theme(self._current_theme, variant)

    @staticmethod
    def list_all_available_themes() -> list:
        """List all themes available in qt-material.

        Returns:
            List of all theme file names
        """
        return list_themes()


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


def apply_theme(theme: str = "light", variant: str = "default") -> bool:
    """Convenience function to apply theme using global manager.

    Args:
        theme: Theme mode - "light" or "dark"
        variant: Color variant

    Returns:
        True if successful
    """
    if _theme_manager:
        return _theme_manager.apply_theme(theme, variant)
    else:
        logger.error("Theme manager not initialized")
        return False
