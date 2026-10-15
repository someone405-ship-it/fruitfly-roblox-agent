"""3D fruit fly on keyboard — keys light when fly presses them."""

from __future__ import annotations
from typing import Set
import math
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient, QPainterPath
from PyQt6.QtWidgets import QWidget
from .config import BG_CARD, ACCENT, BORDER, TEXT_SECONDARY

KEY_LAYOUT = {(0,1):"forward",(1,0):"left",(1,1):"back",(1,2):"right",(2,1):"jump",(0,4):"sprint",(0,5):"interact"}
LABELS = {(0,1):"W",(1,0):"A",(1,1):"S",(1,2):"D",(2,1):"SPC",(0,4):"SH",(0,5):"E"}

class FlyKeyboardWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(420, 280)
        self.active_keys: Set[str] = set()
        self._wing_phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_active(self, actions: Set[str] | list) -> None:
        self.active_keys = set(actions)
        self.update()

    def _tick(self) -> None:
        self._wing_phase = (self._wing_phase + 0.35) % 6.28318
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(BG_CARD))
        p.setPen(QColor(ACCENT))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        p.drawText(12, 22, "3D FRUIT FLY  ·  KEYBOARD")
        base = QRectF(40, 90, w - 80, 140)
        grad = QLinearGradient(base.topLeft(), base.bottomRight())
        grad.setColorAt(0, QColor("#1E2430")); grad.setColorAt(1, QColor("#151A24"))
        p.setBrush(QBrush(grad)); p.setPen(QPen(QColor(BORDER), 1.5))
        p.drawRoundedRect(base, 10, 10)
        key_w, key_h, ox, oy = 36, 32, 70, 110
        for (row, col), action in KEY_LAYOUT.items():
            x = ox + col * (key_w + 8); y = oy + row * (key_h + 8)
            kw = key_w * 2.2 if action == "jump" else key_w
            lit = action in self.active_keys
            rect = QRectF(x, y, kw, key_h)
            p.setBrush(QColor(ACCENT) if lit else QColor("#2A3140"))
            p.setPen(QPen(QColor("#FFFFFF" if lit else BORDER), 1))
            p.drawRoundedRect(rect, 5, 5)
            p.setPen(QColor("#0B0E14" if lit else TEXT_SECONDARY))
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, LABELS.get((row, col), ""))
        self._draw_fly(p, w // 2, 70)
        p.setPen(QColor(TEXT_SECONDARY)); p.setFont(QFont("Cascadia Code", 9))
        p.drawText(12, h - 14, "active: " + (", ".join(sorted(self.active_keys)) if self.active_keys else "resting"))

    def _draw_fly(self, p: QPainter, cx: float, cy: float) -> None:
        p.setBrush(QColor("#3A2A1A")); p.setPen(QPen(QColor("#1A120C"), 1))
        p.drawEllipse(QPointF(cx, cy), 14, 8)
        p.setBrush(QColor("#2A1C12")); p.drawEllipse(QPointF(cx - 12, cy - 2), 7, 6)
        p.setBrush(QColor("#E02020")); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx - 15, cy - 4), 3.5, 3.5)
        p.drawEllipse(QPointF(cx - 15, cy + 1), 3.5, 3.5)
        wing_y = math.sin(self._wing_phase) * 6
        p.setBrush(QColor(180, 220, 255, 90)); p.setPen(QPen(QColor(ACCENT), 1))
        for side, sign in ((-1, 1), (1, -1)):
            path = QPainterPath(); path.moveTo(cx + side * 2, cy)
            path.quadTo(cx + side * 30, cy - 25 + sign * wing_y, cx + side * 8, cy - 8)
            path.closeSubpath(); p.drawPath(path)
        p.setPen(QPen(QColor("#1A120C"), 1.5))
        for dx in (-6, 0, 6):
            p.drawLine(QPointF(cx + dx, cy + 6), QPointF(cx + dx - 4, cy + 18))
            p.drawLine(QPointF(cx + dx, cy + 6), QPointF(cx + dx + 4, cy + 18))
