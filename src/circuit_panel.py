"""Live circuit rates panel (desktop-fly brain-window idea)."""
from __future__ import annotations
from typing import Dict, Any
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtWidgets import QWidget
from .config import BG_CARD, ACCENT, TEXT_SECONDARY, TEXT_PRIMARY, DANGER, SUCCESS

CHANNELS = [
    ("loom_rate", "LC4/LPLC2 loom", ACCENT),
    ("gf_rate", "GF escape", DANGER),
    ("forward", "DNp09 forward", SUCCESS),
    ("reverse", "MDN reverse", "#FF9F43"),
    ("steer_l", "DNa steer L", ACCENT),
    ("steer_r", "DNa steer R", ACCENT),
    ("groom", "DNg11 groom", TEXT_SECONDARY),
]


class CircuitPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(160)
        self._r: Dict[str, float] = {k: 0.0 for k, _, _ in CHANNELS}
        self._escape = False

    def set_rates(self, rates: Dict[str, float]) -> None:
        for k, _, _ in CHANNELS:
            self._r[k] = float(rates.get(k, 0.0))
        self._escape = bool(rates.get("escape", False))
        self.update()

    def set_circuit(self, info: Dict[str, Any]) -> None:
        """Accept full stats dict from worker (alias used by main)."""
        if not isinstance(info, dict):
            return
        rates = {
            "loom_rate": float(info.get("loom_rate", info.get("loom_score", 0.0) or 0.0)),
            "gf_rate": float(info.get("gf_rate", 0.0) or 0.0),
            "forward": float(info.get("forward", 0.0) or 0.0),
            "reverse": float(info.get("reverse", 0.0) or 0.0),
            "steer_l": float(info.get("steer_l", 0.0) or 0.0),
            "steer_r": float(info.get("steer_r", 0.0) or 0.0),
            "groom": float(info.get("groom", 0.0) or 0.0),
            "escape": bool(info.get("escape", False)),
        }
        # fallbacks from behavior/vision
        if rates["gf_rate"] < 1e-6 and float(info.get("loom_score", 0) or 0) > 0.4:
            rates["gf_rate"] = float(info.get("loom_score", 0)) * 0.6
        if rates["forward"] < 1e-6:
            rates["forward"] = max(0.0, float(info.get("drv_arousal", 0) or 0) * 0.5)
        self.set_rates(rates)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(BG_CARD))
        p.setPen(QColor(DANGER if self._escape else ACCENT))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        p.drawText(10, 18, "CIRCUIT (FlyWire-style)" + ("  ·  ESCAPE" if self._escape else ""))
        n = len(CHANNELS)
        top, row_h = 28, max(14, (h - 34) // n)
        for i, (key, label, col) in enumerate(CHANNELS):
            y = top + i * row_h
            val = self._r.get(key, 0.0)
            p.setPen(QColor(TEXT_SECONDARY))
            p.setFont(QFont("Cascadia Code", 8))
            p.drawText(10, y + row_h - 4, f"{label:18s}")
            bw = int(min(1.0, val) * max(10, w - 140))
            p.fillRect(120, y + 3, bw, row_h - 6, QColor(col))
            p.setPen(QColor(TEXT_PRIMARY))
            p.drawText(w - 48, y + row_h - 4, f"{val:.2f}")
