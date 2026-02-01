from PyQt6.QtCore import Qt, QSize, QRect
from PyQt6.QtGui import QPainter, QFont, QColor, QPen
from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle
from ui_entities.inventory_model import InventoryItemRole


class InventoryItemDelegate(QStyledItemDelegate):
    """Custom delegate for rendering inventory items with labels."""

    ROW_HEIGHT = 80
    PADDING = 10
    LABEL_HEIGHT = 20
    LABEL_SPACING = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self._label_font = QFont()
        self._label_font.setBold(True)
        self._label_font.setPointSize(9)

        self._value_font = QFont()
        self._value_font.setPointSize(10)

        self._label_color = QColor(100, 100, 100)
        self._value_color = QColor(30, 30, 30)
        self._border_color = QColor(200, 200, 200)
        self._hover_color = QColor(240, 248, 255)
        self._selected_color = QColor(200, 220, 255)

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return QSize(option.rect.width(), self.ROW_HEIGHT)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()

        # Get item data
        item_type = index.data(InventoryItemRole.ItemType) or ""
        sub_type = index.data(InventoryItemRole.SubType) or ""
        quantity = index.data(InventoryItemRole.Quantity)
        serial_number = index.data(InventoryItemRole.SerialNumber) or ""

        quantity_str = str(quantity) if quantity is not None else ""

        # Draw background
        rect = option.rect
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, self._selected_color)
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(rect, self._hover_color)
        else:
            painter.fillRect(rect, Qt.GlobalColor.white)

        # Draw border at bottom
        painter.setPen(QPen(self._border_color, 1))
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())

        # Calculate label positions (2x2 grid)
        col_width = (rect.width() - 3 * self.PADDING) // 2
        row_height = self.LABEL_HEIGHT + self.LABEL_SPACING

        # Labels and values
        labels_data = [
            ("Type:", item_type, 0, 0),
            ("Sub-type:", sub_type, 1, 0),
            ("Quantity:", quantity_str, 0, 1),
            ("Serial Number:", serial_number, 1, 1),
        ]

        for label, value, col, row in labels_data:
            x = rect.left() + self.PADDING + col * (col_width + self.PADDING)
            y = rect.top() + self.PADDING + row * (row_height + 8)

            # Draw label
            painter.setFont(self._label_font)
            painter.setPen(self._label_color)
            label_rect = QRect(x, y, col_width, self.LABEL_HEIGHT)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, label)

            # Draw value below label
            painter.setFont(self._value_font)
            painter.setPen(self._value_color)
            value_rect = QRect(x, y + 14, col_width, self.LABEL_HEIGHT)
            painter.drawText(value_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, value)

        painter.restore()
