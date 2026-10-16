"""Isometric 3D desktop mouse — not a radar/crosshair."""
from __future__ import annotations
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPainterPath, QLinearGradient
from PyQt6.QtWidgets import QWidget
from .config import BG_CARD, ACCENT, TEXT_SECONDARY, BORDER, DANGER


class Mouse3DWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self._dx = 0
        self._dy = 0
        self._lmb = False
        self._rmb = False
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def _tick(self) -> None:
        self._phase += 0.08
        self.update()

    def set_delta(self, dx: int, dy: int) -> None:
        self._dx = int(dx)
        self._dy = int(dy)
        self.update()

    def set_buttons(self, lmb: bool = False, rmb: bool = False) -> None:
        self._lmb = bool(lmb)
        self._rmb = bool(rmb)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(BG_CARD))
        p.setPen(QPen(QColor(BORDER)))
        p.drawRoundedRect(4, 4, w - 8, h - 8, 10, 10)

        p.setPen(QColor(ACCENT))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.drawText(14, 22, "3D MOUSE")

        desk = QLinearGradient(0, h * 0.55, 0, h)
        desk.setColorAt(0, QColor("#1A2030"))
        desk.setColorAt(1, QColor("#0E121A"))
        p.fillRect(8, int(h * 0.55), w - 16, int(h * 0.45) - 8, desk)

        cx = w // 2 + self._dx // 2
        cy = int(h * 0.58) + self._dy // 3

        p.setBrush(QColor(0, 0, 0, 80))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(cx - 42, cy + 28, 90, 22)

        body = QPainterPath()
        body.addRoundedRect(cx - 36, cy - 48, 72, 90, 28, 28)
        grad = QLinearGradient(cx - 36, cy - 48, cx + 36, cy + 40)
        grad.setColorAt(0, QColor("#2A3348"))
        grad.setColorAt(0.5, QColor("#1E2535"))
        grad.setColorAt(1, QColor("#151A26"))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(BORDER), 1.5))
        p.drawPath(body)

        if abs(self._dx) + abs(self._dy) > 0:
            p.setPen(QPen(QColor(0, 229, 255, 120), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(cx - 38, cy - 50, 76, 94, 30, 30)

        p.setBrush(QColor(ACCENT if self._lmb else "#252C3C"))
        p.setPen(QPen(QColor(ACCENT if self._lmb else BORDER), 1))
        p.drawRoundedRect(cx - 30, cy - 42, 28, 36, 8, 8)

        p.setBrush(QColor(DANGER if self._rmb else "#252C3C"))
        p.setPen(QPen(QColor(DANGER if self._rmb else BORDER), 1))
        p.drawRoundedRect(cx + 2, cy - 42, 28, 36, 8, 8)

        p.setBrush(QColor("#3A4558"))
        p.setPen(QPen(QColor(ACCENT), 1))
        p.drawRoundedRect(cx - 6, cy - 38, 12, 28, 4, 4)
        p.setPen(QPen(QColor(ACCENT), 1))
        for i in range(4):
            yy = cy - 34 + i * 6
            p.drawLine(cx - 4, yy, cx + 4, yy)

        p.setPen(QPen(QColor("#3A4558"), 3))
        p.drawLine(cx, cy + 42, cx - 10, cy + 70)
        p.drawLine(cx - 10, cy + 70, cx - 40, h - 16)

        p.setPen(QColor(TEXT_SECONDARY))
        p.setFont(QFont("Cascadia Code", 9))
        p.drawText(14, h - 14, f"dx={self._dx:+d}  dy={self._dy:+d}  LMB={'ON' if self._lmb else 'off'}")
