from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from styles import Colors
from ui_entities.inventory_model import InventoryItemRole
from ui_entities.translations import tr


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

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return QSize(option.rect.width(), self.ROW_HEIGHT)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()

        # Get theme-aware colors dynamically
        label_color = QColor(Colors.get_text_secondary())
        value_color = QColor(Colors.get_main_color())
        border_color = QColor(Colors.get_border_default())
        bg_default = QColor(Colors.get_bg_default())
        bg_hover = QColor(Colors.get_bg_hover())
        selected_color = QColor(Colors.PRIMARY)
        selected_color.setAlpha(50)  # Semi-transparent

        # Get item data
        item_type = index.data(InventoryItemRole.ItemType) or ""
        sub_type = index.data(InventoryItemRole.SubType) or ""
        quantity = index.data(InventoryItemRole.Quantity)
        serial_number = index.data(InventoryItemRole.SerialNumber) or ""

        quantity_str = str(quantity) if quantity is not None else ""

        # Draw background
        rect = option.rect
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, selected_color)
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(rect, bg_hover)
        else:
            painter.fillRect(rect, bg_default)

        # Draw border at bottom
        painter.setPen(QPen(border_color, 1))
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())

        # Calculate label positions (2x2 grid)
        col_width = (rect.width() - 3 * self.PADDING) // 2
        row_height = self.LABEL_HEIGHT + self.LABEL_SPACING

        # Labels and values with translations
        labels_data = [
            (tr("label.type"), item_type, 0, 0),
            (tr("label.subtype"), sub_type if sub_type else "-", 1, 0),
            (tr("label.quantity"), quantity_str, 0, 1),
            (tr("label.serial_number"), serial_number if serial_number else "-", 1, 1),
        ]

        for label, value, col, row in labels_data:
            x = rect.left() + self.PADDING + col * (col_width + self.PADDING)
            y = rect.top() + self.PADDING + row * (row_height + 8)

            # Draw label
            painter.setFont(self._label_font)
            painter.setPen(label_color)
            label_rect = QRect(x, y, col_width, self.LABEL_HEIGHT)
            painter.drawText(
                label_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                label,
            )

            # Draw value below label
            painter.setFont(self._value_font)
            painter.setPen(value_color)
            value_rect = QRect(x, y + 14, col_width, self.LABEL_HEIGHT)
            painter.drawText(
                value_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                value,
            )

        painter.restore()
