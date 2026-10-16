"""Animated fruit fly on keyboard — lights keys from motor action names."""
from __future__ import annotations
import math
from typing import Set, Iterable
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PyQt6.QtWidgets import QWidget
from .config import BG_CARD, ACCENT, TEXT_SECONDARY, BORDER, TEXT_PRIMARY

ACTION_TO_KEY = {
    "forward": "W", "back": "S", "left": "A", "right": "D",
    "jump": "SPACE", "sprint": "SHIFT", "interact": "E",
    "crouch": "CTRL", "reset": "R", "chat_toggle": "/",
    "emote": "B", "camera": "Q", "ui_up": "UP", "ui_down": "DN",
    "ui_select": "ENT", "secondary": "LMB",
}

KEY_LAYOUT = [
    [("Q", 0), ("W", 1), ("E", 2), ("R", 3), ("T", 4)],
    [("A", 0), ("S", 1), ("D", 2), ("F", 3), ("G", 4)],
    [("SHIFT", 0), ("Z", 1), ("X", 2), ("C", 3), ("SPACE", 4)],
]


class FlyKeyboardWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self._active: Set[str] = set()
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def _tick(self) -> None:
        self._phase += 0.12
        self.update()

    def set_active(self, actions: Iterable[str]) -> None:
        keys = set()
        for a in actions:
            k = ACTION_TO_KEY.get(a)
            if k:
                keys.add(k)
            if a.startswith("look"):
                keys.add("LOOK")
        self._active = keys
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(BG_CARD))
        p.setPen(QPen(QColor(BORDER)))
        p.drawRoundedRect(self.rect().adjusted(4, 4, -4, -4), 10, 10)
        p.setPen(QColor(ACCENT))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.drawText(14, 22, "3D FLY + KEYBOARD")
        key_w, key_h = 42, 32
        ox, oy = 24, 40
        for row_i, row in enumerate(KEY_LAYOUT):
            for label, col in row:
                x = ox + col * (key_w + 6) + (8 if row_i == 1 else 0)
                y = oy + row_i * (key_h + 6)
                lit = label in self._active
                if label == "SPACE" and "SPACE" in self._active:
                    lit = True
                bg = QColor(ACCENT) if lit else QColor("#1A1F2B")
                p.setBrush(QBrush(bg))
                p.setPen(QPen(QColor(ACCENT if lit else BORDER)))
                p.drawRoundedRect(x, y, key_w if label != "SPACE" else key_w + 20, key_h, 6, 6)
                p.setPen(QColor("#0B0E14" if lit else TEXT_PRIMARY))
                p.drawText(x, y, key_w if label != "SPACE" else key_w + 20, key_h,
                           Qt.AlignmentFlag.AlignCenter, label[:5])
        # simple fly body
        fx = 200 + int(12 * math.sin(self._phase))
        fy = 160 + int(6 * math.cos(self._phase * 1.3))
        p.setBrush(QColor("#C4A35A"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(fx, fy, 18, 12)
        p.setBrush(QColor("#222"))
        p.drawEllipse(fx + 12, fy + 2, 6, 6)
        p.setPen(QColor(TEXT_SECONDARY))
        p.drawText(14, self.height() - 12, "lit = active motor")
