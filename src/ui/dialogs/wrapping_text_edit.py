"""QTextEdit that word-wraps its placeholder text.

QTextEdit's built-in placeholder does not wrap, so long placeholder copy gets
clipped. This subclass paints the placeholder itself with word-wrap when the
field is empty.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QTextEdit


class WrappingTextEdit(QTextEdit):
    """QTextEdit whose placeholder text word-wraps instead of clipping."""

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.toPlainText() or not self.placeholderText():
            return
        viewport = self.viewport()
        if viewport is None:
            return
        painter = QPainter(viewport)
        painter.setPen(self.palette().placeholderText().color())
        rect = viewport.rect().adjusted(4, 4, -4, -4)
        painter.drawText(rect, Qt.TextFlag.TextWordWrap, self.placeholderText())
