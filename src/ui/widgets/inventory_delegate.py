from typing import Optional

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from ui.models.inventory_model import InventoryItemRole
from ui.styles import Colors
from ui.translations import tr


class InventoryItemDelegate(QStyledItemDelegate):
    """Custom delegate for inventory items — type name prominent, qty on right."""

    ROW_HEIGHT = 82
    PAD_H = 16
    PAD_V = 11
    QTY_COL_W = 52

    def __init__(self, parent=None):
        super().__init__(parent)

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return QSize(option.rect.width(), self.ROW_HEIGHT)

    def paint(self, painter: Optional[QPainter], option: QStyleOptionViewItem, index):
        if painter is None:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        main_color = QColor(Colors.get_main_color())
        secondary_color = QColor(Colors.get_text_secondary())
        border_color = QColor(Colors.get_border_default())
        bg_default = QColor(Colors.get_bg_default())
        bg_hover = QColor(Colors.get_bg_hover())
        primary_color = QColor(Colors.get_primary())

        item_type = index.data(InventoryItemRole.ItemType) or ""
        sub_type = index.data(InventoryItemRole.SubType) or ""
        quantity = index.data(InventoryItemRole.Quantity)
        serial_numbers = index.data(InventoryItemRole.SerialNumbers) or []
        is_serialized = index.data(InventoryItemRole.IsSerialized)
        location_name = index.data(InventoryItemRole.LocationName) or ""
        is_multi_location = index.data(InventoryItemRole.IsMultiLocation) or False

        rect = option.rect
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        is_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        # Background
        if is_selected:
            sel_bg = QColor(Colors.get_primary())
            sel_bg.setAlpha(12)
            painter.fillRect(rect, sel_bg)
            # Left accent stripe
            accent_rect = QRect(rect.left(), rect.top(), 3, rect.height())
            painter.fillRect(accent_rect, primary_color)
        elif is_hovered:
            painter.fillRect(rect, bg_hover)
        else:
            painter.fillRect(rect, bg_default)

        # Bottom separator
        painter.setPen(QPen(border_color, 1))
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())

        left = rect.left() + self.PAD_H
        right = rect.right() - self.PAD_H
        top = rect.top()

        # ── Quantity (right column) ──────────────────────────────────────
        qty_x = right - self.QTY_COL_W
        qty_val = (
            str(len(serial_numbers))
            if is_serialized and serial_numbers
            else (str(quantity) if quantity is not None else "0")
        )

        qty_font = QFont()
        qty_font.setPointSize(13)
        qty_font.setBold(True)
        painter.setFont(qty_font)
        painter.setPen(main_color)
        qty_rect = QRect(qty_x, top + self.PAD_V, self.QTY_COL_W, 22)
        painter.drawText(
            qty_rect,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            qty_val,
        )

        unit_font = QFont()
        unit_font.setPointSize(8)
        painter.setFont(unit_font)
        painter.setPen(secondary_color)
        unit_rect = QRect(qty_x, top + self.PAD_V + 24, self.QTY_COL_W, 14)
        painter.drawText(
            unit_rect,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            "шт.",
        )

        # ── Type name (left, prominent) ──────────────────────────────────
        text_width = qty_x - 8 - left

        type_font = QFont()
        type_font.setPointSize(11)
        type_font.setBold(True)
        painter.setFont(type_font)
        painter.setPen(main_color)
        fm_type = QFontMetrics(type_font)
        elided_type = fm_type.elidedText(
            item_type, Qt.TextElideMode.ElideRight, text_width
        )
        type_rect = QRect(left, top + self.PAD_V, text_width, 22)
        painter.drawText(
            type_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_type,
        )

        # ── Sub type ─────────────────────────────────────────────────────
        sub_font = QFont()
        sub_font.setPointSize(9)
        painter.setFont(sub_font)
        painter.setPen(secondary_color)
        fm_sub = QFontMetrics(sub_font)
        sub_display = sub_type if sub_type else "—"
        elided_sub = fm_sub.elidedText(
            sub_display, Qt.TextElideMode.ElideRight, text_width
        )
        sub_rect = QRect(left, top + self.PAD_V + 26, text_width, 16)
        painter.drawText(
            sub_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_sub,
        )

        # ── Serialized badge (bottom-right) ──────────────────────────────
        badge_text = (
            tr("label.serialized_badge")
            if is_serialized
            else tr("label.non_serialized_badge")
        )
        badge_color = QColor("#2e7d32") if is_serialized else QColor("#757575")
        badge_font = QFont()
        badge_font.setPointSize(7)
        badge_font.setBold(True)
        fm_badge = QFontMetrics(badge_font)
        badge_w = fm_badge.horizontalAdvance(badge_text) + 10
        badge_h = fm_badge.height() + 4
        badge_rect = QRect(
            right - badge_w, rect.bottom() - badge_h - 6, badge_w, badge_h
        )

        painter.save()
        painter.setFont(badge_font)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(badge_color)
        painter.drawRoundedRect(badge_rect, 3, 3)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)
        painter.restore()

        # ── Location footer (bottom-left) ─────────────────────────────────
        if is_multi_location or location_name:
            loc_text = tr("location.multiple") if is_multi_location else location_name
            footer_font = QFont()
            footer_font.setPointSize(8)
            painter.save()
            painter.setFont(footer_font)
            painter.setPen(secondary_color)
            footer_y = rect.bottom() - badge_h - 6
            footer_w = badge_rect.left() - left - 8
            footer_rect = QRect(left, footer_y, footer_w, badge_h)
            painter.drawText(
                footer_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                loc_text,
            )
            painter.restore()

        painter.restore()
