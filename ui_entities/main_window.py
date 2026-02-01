from PyQt6 import uic
from PyQt6.QtGui import QStandardItem, QFont
from PyQt6.QtWidgets import QMainWindow
from ui_entities.main_window_model import CustomModel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/MainWindow.ui", self)

        model = CustomModel()

        # Sample data
        names = ['Alice', 'Bob', 'Charlie', 'David', 'Eve']
        statuses = ['Active', 'Inactive', 'Active', 'Pending', 'Active']

        for row in range(len(names)):
            name_item = QStandardItem(names[row])
            status_item = QStandardItem(statuses[row])
            model.setItem(row, 0, name_item)
            model.setItem(row, 1, status_item)

        self.tableView.setModel(model)

        self.addButton.clicked.connect(self.on_add_clicked)

    def on_add_clicked(self):
        print("Add button clicked")