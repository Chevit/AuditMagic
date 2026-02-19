import sys

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from config import config
from runtime import resource_path
from db import run_migrations
from logger import logger
from theme_config import Theme
from theme_manager import init_theme_manager
from ui_entities.main_window import MainWindow
from update_checker import UpdateInfo, check_for_update
from version import __version__


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
        app.setWindowIcon(QIcon(resource_path("icon.ico")))
        logger.info("QApplication created successfully")

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

        run_migrations()
        logger.info("Database migrations applied")

        window = MainWindow()
        logger.info("MainWindow created successfully")

        window.setWindowTitle(f"{window.windowTitle()} v{__version__}")

        window.show()
        logger.info("MainWindow displayed")

        def _show_update_dialog(update_info: UpdateInfo) -> None:
            from ui_entities.update_dialog import UpdateDialog

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
        logger.exception("Critical error during application startup")
        raise


if __name__ == "__main__":
    sys.exit(main())
