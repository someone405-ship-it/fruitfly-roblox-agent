"""Motor output — interest % per channel (what the fly is into)."""
from __future__ import annotations
from typing import Dict, List
from PyQt6.QtGui import QPainter, QColor, QFont, QPen
from PyQt6.QtWidgets import QWidget
from .config import (
    MOTOR_NAMES, MOTOR_LABELS, BG_CARD, ACCENT, TEXT_SECONDARY, TEXT_PRIMARY,
    MOTOR_POS, MOTOR_NEG,
)


class MotorOutputPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(320)
        self._motor: Dict[str, float] = {n: 0.0 for n in MOTOR_NAMES}
        self._active = set()
        self._pct: Dict[str, float] = {n: 0.0 for n in MOTOR_NAMES}
        self._top: List[tuple] = []

    def set_motor(self, motor_dict: Dict[str, float], active=None) -> None:
        self._motor = {n: float(motor_dict.get(n, 0.0)) for n in MOTOR_NAMES}
        self._active = set(active or [])
        abs_vals = {n: abs(self._motor[n]) for n in MOTOR_NAMES}
        total = sum(abs_vals.values()) + 1e-6
        self._pct = {n: 100.0 * abs_vals[n] / total for n in MOTOR_NAMES}
        self._top = sorted(self._pct.items(), key=lambda x: -x[1])[:5]
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(BG_CARD))

        p.setPen(QColor(ACCENT))
        p.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        p.drawText(10, 20, "MOTOR INTEREST  (%)")

        y = 36
        p.setFont(QFont("Cascadia Code", 9))
        if self._top:
            parts = []
            for name, pct in self._top:
                if pct < 1.0:
                    continue
                label = MOTOR_LABELS.get(name, name)
                parts.append(f"{label} {pct:.0f}%")
            p.setPen(QColor(TEXT_PRIMARY))
            p.drawText(10, y, "focus: " + " · ".join(parts[:4]))
        y = 52

        n = len(MOTOR_NAMES)
        row_h = max(12, min(18, (h - y - 8) // max(1, n)))
        p.setFont(QFont("Cascadia Code", 8))
        for i, name in enumerate(MOTOR_NAMES):
            ry = y + i * row_h
            if ry + row_h > h:
                break
            val = self._motor[name]
            pct = self._pct[name]
            label = MOTOR_LABELS.get(name, name)
            col = QColor(ACCENT) if name in self._active else QColor(TEXT_SECONDARY)
            p.setPen(col)
            p.drawText(8, ry + row_h - 3, f"{label[:16]:16s}")

            bar_x = 120
            bar_w = max(40, w - 180)
            mid = bar_x + bar_w // 2
            p.setPen(QPen(QColor(60, 70, 90), 1))
            p.drawLine(mid, ry + 2, mid, ry + row_h - 4)
            max_px = bar_w // 2 - 2
            px = int(max(-max_px, min(max_px, val * max_px)))
            if px > 0:
                p.fillRect(mid, ry + 3, px, row_h - 6, QColor(MOTOR_POS))
            elif px < 0:
                p.fillRect(mid + px, ry + 3, -px, row_h - 6, QColor(MOTOR_NEG))
            p.setPen(QColor(TEXT_PRIMARY) if pct >= 8 else QColor(TEXT_SECONDARY))
            p.drawText(w - 52, ry + row_h - 3, f"{pct:5.1f}%")
