"""Live motor output panel — bar meters for every motor channel."""

from __future__ import annotations
from typing import Dict
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtWidgets import QWidget
from .config import MOTOR_NAMES, MOTOR_LABELS, BG_CARD, BORDER, ACCENT, TEXT_SECONDARY, TEXT_PRIMARY, MOTOR_POS, MOTOR_NEG

class MotorOutputPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(280)
        self._motor: Dict[str, float] = {n: 0.0 for n in MOTOR_NAMES}
        self._active = set()

    def set_motor(self, motor_dict: Dict[str, float], active=None) -> None:
        self._motor = {n: float(motor_dict.get(n, 0.0)) for n in MOTOR_NAMES}
        self._active = set(active or [])
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(BG_CARD))
        p.setPen(QColor(ACCENT))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        p.drawText(10, 18, "MOTOR OUTPUT")
        n = len(MOTOR_NAMES)
        top = 28
        row_h = max(12, (h - top - 8) // n)
        mid = int(w * 0.55)
        bar_max = w - mid - 16
        for i, name in enumerate(MOTOR_NAMES):
            y = top + i * row_h
            val = self._motor.get(name, 0.0)
            label = MOTOR_LABELS.get(name, name)
            on = name in self._active
            p.setPen(QColor(ACCENT) if on else QColor(TEXT_SECONDARY))
            p.setFont(QFont("Cascadia Code", 8))
            p.drawText(10, y + row_h - 4, f"{label[:14]:14s}")
            p.setPen(QPen(QColor(BORDER), 1))
            p.drawLine(mid, y + 2, mid, y + row_h - 4)
            mag = min(1.0, abs(val))
            bw = int(mag * bar_max)
            if val >= 0:
                p.fillRect(mid, y + 3, bw, row_h - 6, QColor(MOTOR_POS if on else "#1A4A55"))
            else:
                p.fillRect(mid - bw, y + 3, bw, row_h - 6, QColor(MOTOR_NEG))
            p.setPen(QColor(TEXT_PRIMARY if on else TEXT_SECONDARY))
            p.drawText(w - 52, y + row_h - 4, f"{val:+.2f}")
