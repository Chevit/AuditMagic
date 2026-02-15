import sys

from PyQt6.QtWidgets import QApplication

from config import config
from db import run_migrations
from logger import logger
from theme_config import Theme
from theme_manager import init_theme_manager
from ui_entities.main_window import MainWindow


def main():
    logger.info("=" * 80)
    logger.info("AuditMagic Application Starting")
    logger.info("=" * 80)

    try:
        app = QApplication(sys.argv)
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
