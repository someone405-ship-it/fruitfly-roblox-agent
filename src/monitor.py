"""Live preview widget — shows what the fly is looking at."""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget, QFrame

from .config import MONITOR_W, MONITOR_H, ACCENT, BG_CARD, TEXT_SECONDARY, BORDER


class LiveMonitor(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("LiveMonitor")
        self._frame: np.ndarray | None = None
        self._status = "idle"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.title = QLabel("LIVE MONITOR — FLY VISION")
        self.title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.title.setStyleSheet(
            f"color: {ACCENT}; font-size: 11px; font-weight: 600; letter-spacing: 1.5px; padding: 6px 8px;"
        )
        layout.addWidget(self.title)

        self.view = QLabel()
        self.view.setFixedSize(MONITOR_W, MONITOR_H)
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view.setStyleSheet(
            f"background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 8px;"
        )
        self.view.setText("no signal")
        self.view.setStyleSheet(
            self.view.styleSheet() + f" color: {TEXT_SECONDARY}; font-family: monospace;"
        )
        layout.addWidget(self.view)

        self.status_lbl = QLabel("status: idle")
        self.status_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; padding: 4px 8px;")
        layout.addWidget(self.status_lbl)

    def update_frame(self, frame_bgr: np.ndarray) -> None:
        """Accept BGR uint8 (H,W,3) and display."""
        if frame_bgr is None:
            return
        h, w = frame_bgr.shape[:2]
        rgb = frame_bgr[:, :, ::-1].copy()
        qimg = QImage(rgb.data, w, h, w * 3, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(qimg).scaled(
            MONITOR_W,
            MONITOR_H,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.view.setPixmap(pix)

    def set_status(self, text: str) -> None:
        self._status = text
        self.status_lbl.setText(f"status: {text}")
