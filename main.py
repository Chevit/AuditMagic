import sys
from PyQt6.QtWidgets import QApplication
from ui_entities.main_window import MainWindow
from logger import logger


def main():
    logger.info("=" * 80)
    logger.info("AuditMagic Application Starting")
    logger.info("=" * 80)

    try:
        app = QApplication(sys.argv)
        logger.info("QApplication created successfully")

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
