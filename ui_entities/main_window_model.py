from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QStandardItemModel


class CustomModel(QStandardItemModel):
    def __init__(self, rows: int = 5, cols: int = 2):
        super().__init__()
        self._rows = rows
        self._cols = cols
        self._data = [[f"R{r}C{c}" for c in range(cols)] for r in range(rows)]

    def rowCount(self, parent=None):
        return self._rows

    def columnCount(self, parent=None):
        return self._cols

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.BackgroundRole:
            if index.row() % 2 == 0:
                return QColor(Qt.GlobalColor.lightGray)

        if role == Qt.ItemDataRole.ForegroundRole:
            if index.column() == 0:
                return QColor(Qt.GlobalColor.red)

        if role == Qt.ItemDataRole.DisplayRole:
            return self._data[index.row()][index.column()]

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter

        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.EditRole:
            self._data[index.row()][index.column()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index):
        return (Qt.ItemFlag.ItemIsEnabled |
                Qt.ItemFlag.ItemIsSelectable |
                Qt.ItemFlag.ItemIsEditable)