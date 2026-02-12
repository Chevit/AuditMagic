import sys
from PyQt6.QtWidgets import QApplication
from ui_entities.main_window import MainWindow
from db import run_migrations
from logger import logger
from theme_manager import init_theme_manager
from config import config


def main():
    logger.info("=" * 80)
    logger.info("AuditMagic Application Starting")
    logger.info("=" * 80)

    try:
        app = QApplication(sys.argv)
        logger.info("QApplication created successfully")

        # Initialize theme manager and apply saved theme
        theme_manager = init_theme_manager(app)
        theme_mode = config.get("theme.mode", "light")
        theme_variant = config.get("theme.variant", "default")
        theme_manager.apply_theme(theme_mode, theme_variant)
        logger.info(f"Theme applied: {theme_mode}/{theme_variant}")

        window = MainWindow()
        logger.info("MainWindow created successfully")

        run_migrations()
        logger.info("Database migrations applied")

        window.show()
        logger.info("MainWindow displayed")

        exit_code = app.exec()
        logger.info(f"Application exited with code: {exit_code}")
        return exit_code

    except Exception as e:
        logger.exception("Critical error during application startup")
        raise


if __name__ == "__main__":
    sys.exit(main())
