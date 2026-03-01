"""Runtime helpers for PyInstaller compatibility."""

import os
import sys


def get_base_path() -> str:
    """Get the base path for resource files.

    When running from a PyInstaller bundle, files are in sys._MEIPASS.
    When running from source, files are in the script directory.

    Returns:
        Base path string.
    """
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path: str) -> str:
    """Get absolute path to a bundled resource file.

    Args:
        relative_path: Path relative to project root (e.g., 'ui/MainWindow.ui').

    Returns:
        Absolute path that works in both dev and bundled mode.
    """
    return os.path.join(get_base_path(), relative_path)
