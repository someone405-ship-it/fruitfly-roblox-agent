"""3D-ish mouse visualizer — shows look deltas."""
from __future__ import annotations
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush
from PyQt6.QtWidgets import QWidget
from .config import BG_CARD, ACCENT, TEXT_PRIMARY

class Mouse3DWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(140)
        self._dx = 0
        self._dy = 0
        self._trail = []

    def set_delta(self, dx: int, dy: int) -> None:
        self._dx = int(dx)
        self._dy = int(dy)
        self._trail.append((self._dx, self._dy))
        if len(self._trail) > 24:
            self._trail.pop(0)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(BG_CARD))
        p.setPen(QColor(ACCENT))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        p.drawText(10, 18, "3D MOUSE (look)")
        cx, cy = w // 2, h // 2 + 8
        p.setPen(QPen(QColor(50, 60, 80), 1))
        p.drawEllipse(cx - 50, cy - 50, 100, 100)
        p.drawLine(cx - 55, cy, cx + 55, cy)
        p.drawLine(cx, cy - 55, cx, cy + 55)
        for i, (dx, dy) in enumerate(self._trail):
            a = 40 + i * 8
            p.setPen(QPen(QColor(0, 229, 255, min(255, a)), 2))
            p.drawLine(cx, cy, cx + dx * 2, cy + dy * 2)
        p.setPen(QPen(QColor(ACCENT), 3))
        p.drawLine(cx, cy, cx + self._dx * 3, cy + self._dy * 3)
        p.setBrush(QBrush(QColor(ACCENT)))
        p.drawEllipse(cx + self._dx * 3 - 5, cy + self._dy * 3 - 5, 10, 10)
        p.setBrush(QBrush(QColor(40, 48, 64)))
        p.setPen(QPen(QColor(ACCENT), 1))
        p.drawRoundedRect(cx - 18, cy + 40, 36, 48, 10, 10)
        p.drawLine(cx, cy + 40, cx, cy + 58)
        p.setPen(QColor(TEXT_PRIMARY))
        p.setFont(QFont("Cascadia Code", 9))
        p.drawText(10, h - 10, f"dx={self._dx:+d}  dy={self._dy:+d}")
