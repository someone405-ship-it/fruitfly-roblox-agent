"""Live preview of what the fly sees."""
from __future__ import annotations
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from .config import BG_CARD, ACCENT, TEXT_SECONDARY, BORDER

class LiveMonitor(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 200)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        self.title = QLabel("LIVE VISION")
        self.title.setStyleSheet(f"color:{ACCENT}; font-weight:700; font-size:11px;")
        lay.addWidget(self.title)
        self.view = QLabel("waiting for frame…")
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view.setMinimumHeight(180)
        self.view.setStyleSheet(f"background:{BG_CARD}; border:1px solid {BORDER}; border-radius:8px; color:{TEXT_SECONDARY};")
        lay.addWidget(self.view, 1)
        self.status = QLabel("")
        self.status.setStyleSheet(f"color:{TEXT_SECONDARY}; font-size:11px;")
        lay.addWidget(self.status)

    def update_frame(self, frame) -> None:
        if frame is None:
            return
        try:
            arr = np.ascontiguousarray(frame)
            if arr.ndim != 3 or arr.shape[2] < 3:
                return
            h, w, _ = arr.shape
            rgb = arr[:, :, ::-1].copy()
            qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
            pix = QPixmap.fromImage(qimg.copy())
            self.view.setPixmap(pix.scaled(
                max(1, self.view.width()), max(1, self.view.height()),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        except Exception as e:
            self.status.setText(f"frame error: {e}")

    def set_status(self, text: str) -> None:
        self.status.setText(text)
