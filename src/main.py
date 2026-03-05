import sys

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from core.config import config
from runtime import resource_path
from core.db import run_migrations
from core.logger import logger
from ui.theme_config import Theme
from ui.theme_manager import init_theme_manager
from ui.main_window import MainWindow
from update_checker import UpdateInfo, check_for_update
from version import __version__

try:
    import pyi_splash as _pyi_splash  # only available in PyInstaller bundle

    def _splash(text: str) -> None:
        _pyi_splash.update_text(text)

    def _splash_close() -> None:
        _pyi_splash.close()

except ImportError:
    def _splash(text: str) -> None:  # type: ignore[misc]
        pass

    def _splash_close() -> None:  # type: ignore[misc]
        pass


class UpdateCheckWorker(QThread):
    """Background thread for checking for application updates."""

    update_available = pyqtSignal(object)  # emits UpdateInfo

    def run(self) -> None:
        result = check_for_update()
        if result:
            self.update_available.emit(result)


def main():
    logger.info("=" * 80)
    logger.info("AuditMagic Application Starting")
    logger.info("=" * 80)

    try:
        app = QApplication(sys.argv)
        _icon_file = (
            "icon.icns" if sys.platform == "darwin"
            else "icon.png" if sys.platform != "win32"
            else "icon.ico"
        )
        app.setWindowIcon(QIcon(resource_path(_icon_file)))
        logger.info("QApplication created successfully")
        _splash(f"AuditMagic v{__version__}")

        # Initialize theme manager and apply saved theme
        theme_manager = init_theme_manager(app)
        theme_name = config.get("theme", "Light")
        try:
            theme = Theme.get_by_name(theme_name)
        except ValueError:
            logger.warning(f"Invalid theme '{theme_name}', using Light theme")
            theme = Theme.LIGHT
        theme_manager.apply_theme(theme)
        logger.info(f"Theme applied: {theme.value.name}")
        logger.info(
            f"Theme dimensions: input_height={theme.value.dimensions.input_height}, button_height={theme.value.dimensions.button_height}"
        )

        _splash("Applying migrations...")
        run_migrations()
        logger.info("Database migrations applied")

        _splash("Loading interface...")
        window = MainWindow()
        logger.info("MainWindow created successfully")

        window.setWindowTitle(f"{window.windowTitle()} v{__version__}")

        window.show()
        _splash_close()
        logger.info("MainWindow displayed")

        def _show_update_dialog(update_info: UpdateInfo) -> None:
            from ui.dialogs.update_dialog import UpdateDialog

            dialog = UpdateDialog(update_info, window)
            dialog.exec()

        update_worker = UpdateCheckWorker()
        update_worker.update_available.connect(_show_update_dialog)
        update_worker.start()
        logger.info("Update check started in background")

        exit_code = app.exec()
        logger.info(f"Application exited with code: {exit_code}")
        return exit_code

    except Exception as e:
        _splash_close()
        logger.exception("Critical error during application startup")
        raise


if __name__ == "__main__":
    sys.exit(main())
