"""Animated fruit fly on keyboard with eyes that track look direction."""
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
        self.setMinimumHeight(240)
        self._active: Set[str] = set()
        self._phase = 0.0
        self._look_x = 0.0
        self._look_y = 0.0
        self._pain = 0.0
        self._lock_in = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def _tick(self) -> None:
        self._phase += 0.14
        self.update()

    def set_active(self, actions: Iterable[str]) -> None:
        keys = set()
        lx = ly = 0.0
        for a in actions:
            k = ACTION_TO_KEY.get(a)
            if k:
                keys.add(k)
            if a in ("look_left", "left"):
                lx -= 1
            if a in ("look_right", "right"):
                lx += 1
            if a == "look_up":
                ly -= 1
            if a == "look_down":
                ly += 1
        self._active = keys
        if lx or ly:
            n = max(1.0, abs(lx) + abs(ly))
            self._look_x = lx / n
            self._look_y = ly / n
        self.update()

    def set_state(self, pain: float = 0.0, lock_in: bool = False, look_x: float = 0.0, look_y: float = 0.0) -> None:
        self._pain = float(pain)
        self._lock_in = bool(lock_in)
        if look_x or look_y:
            self._look_x = float(look_x)
            self._look_y = float(look_y)
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(BG_CARD))
        p.setPen(QPen(QColor(BORDER)))
        p.drawRoundedRect(self.rect().adjusted(4, 4, -4, -4), 10, 10)
        p.setPen(QColor(ACCENT))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title = "3D FLY + EYES"
        if self._lock_in:
            title += "  [LOCKED IN]"
        p.drawText(14, 22, title)
        key_w, key_h = 42, 32
        ox, oy = 24, 40
        for row_i, row in enumerate(KEY_LAYOUT):
            for label, col in row:
                x = ox + col * (key_w + 6) + (8 if row_i == 1 else 0)
                y = oy + row_i * (key_h + 6)
                lit = label in self._active
                bg = QColor(ACCENT) if lit else QColor("#1A1F2B")
                p.setBrush(QBrush(bg))
                p.setPen(QPen(QColor(ACCENT if lit else BORDER)))
                ww = key_w if label != "SPACE" else key_w + 20
                p.drawRoundedRect(x, y, ww, key_h, 6, 6)
                p.setPen(QColor("#0B0E14" if lit else TEXT_PRIMARY))
                p.drawText(x, y, ww, key_h, Qt.AlignmentFlag.AlignCenter, label[:5])
        fx = 200 + int(10 * math.sin(self._phase))
        fy = 175 + int(5 * math.cos(self._phase * 1.3))
        body = QColor("#C4A35A")
        if self._pain > 0.4:
            body = QColor("#C45A5A")
        elif self._lock_in:
            body = QColor("#E5C04A")
        p.setBrush(body)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(fx, fy, 28, 18)
        p.setBrush(QColor(180, 200, 220, 120))
        p.drawEllipse(fx - 8, fy - 4, 14, 10)
        p.drawEllipse(fx + 22, fy - 4, 14, 10)
        p.setBrush(body)
        p.drawEllipse(fx + 18, fy - 2, 14, 12)
        eye_dx = int(self._look_x * 3)
        eye_dy = int(self._look_y * 2)
        p.setBrush(QColor("#F5F5F0"))
        p.drawEllipse(fx + 20 + eye_dx, fy + eye_dy, 6, 6)
        p.drawEllipse(fx + 27 + eye_dx, fy + eye_dy, 6, 6)
        p.setBrush(QColor("#111"))
        p.drawEllipse(fx + 22 + eye_dx * 2, fy + 1 + eye_dy * 2, 3, 3)
        p.drawEllipse(fx + 29 + eye_dx * 2, fy + 1 + eye_dy * 2, 3, 3)
        if self._pain > 0.3:
            p.setPen(QPen(QColor("#FF4D6A"), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(fx - 2, fy - 4, 34, 26)
        p.setPen(QColor(TEXT_SECONDARY))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(14, self.height() - 12, "eyes track look · red = pain · gold = lock-in")
