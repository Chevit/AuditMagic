from PyQt6.QtGui import QStandardItem
from PyQt6.QtWidgets import QMainWindow

class ListItem(QStandardItem):
    def __init__(self, parent=None):
        super().__init__(parent)