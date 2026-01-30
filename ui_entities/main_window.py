from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/MainWindow.ui", self)

        self.addButton.clicked.connect(self.on_add_clicked)

    def on_add_clicked(self):
        print("Add button clicked")