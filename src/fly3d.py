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
    "emote": "B", "camera": "F", "ui_up": "UP", "ui_down": "DN",
    "ui_select": "ENT",
}

KEY_LAYOUT = [
    [("Q", 0), ("W", 1), ("E", 2), ("R", 3), ("T", 4)],
    [("A", 0), ("S", 1), ("D", 2), ("F", 3), ("G", 4)],
    [("SHIFT", 0), ("Z", 1), ("X", 2), ("C", 3), ("B", 4)],
    [("CTRL", 0), ("SPACE", 1)],
]

class FlyKeyboardWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 280)
        self._active_keys: Set[str] = set()
        self._wing = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def _tick(self) -> None:
        self._wing += 0.35
        self.update()

    def set_active(self, actions: Iterable[str]) -> None:
        keys = set()
        for a in actions:
            k = ACTION_TO_KEY.get(a)
            if k:
                keys.add(k.upper())
            if isinstance(a, str) and len(a) <= 5:
                keys.add(a.upper())
        self._active_keys = keys
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(BG_CARD))
        p.setPen(QColor(ACCENT))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        p.drawText(10, 18, "3D FLY + KEYBOARD")
        kb_top = 40
        key_w, key_h = 44, 36
        gap = 6
        for row_i, row in enumerate(KEY_LAYOUT):
            for label, col in row:
                if label == "SPACE":
                    x = 20 + col * (key_w + gap)
                    ww = key_w * 3 + gap * 2
                else:
                    x = 20 + col * (key_w + gap)
                    ww = key_w
                y = kb_top + row_i * (key_h + gap)
                on = label.upper() in self._active_keys
                p.setBrush(QBrush(QColor(ACCENT if on else "#1A2230")))
                p.setPen(QPen(QColor(ACCENT if on else BORDER), 1))
                p.drawRoundedRect(x, y, ww, key_h, 6, 6)
                p.setPen(QColor("#0B0E14" if on else TEXT_SECONDARY))
                p.setFont(QFont("Cascadia Code", 8))
                p.drawText(x, y, ww, key_h, Qt.AlignmentFlag.AlignCenter, label)
        cx, cy = w // 2, h - 70
        wing = math.sin(self._wing) * 12
        p.setBrush(QBrush(QColor(ACCENT)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(cx - 10, cy - 8, 20, 16)
        p.setBrush(QBrush(QColor("#7AE7FF")))
        p.drawEllipse(cx - 22 - int(wing), cy - 6, 16, 10)
        p.drawEllipse(cx + 6 + int(wing), cy - 6, 16, 10)
        p.setPen(QColor(TEXT_PRIMARY))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(10, h - 12, "active: " + (", ".join(sorted(self._active_keys)) or "—"))
