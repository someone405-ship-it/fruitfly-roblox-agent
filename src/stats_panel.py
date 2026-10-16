"""Qt panel — live fly stats bars."""
from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QFrame
from .config import BG_CARD, BORDER, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, SUCCESS, WARNING, DANGER
from .stats import STAT_ORDER, STAT_LABELS, get_stats


class StatsPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statsPanel")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(4)
        title = QLabel("FLY STATS")
        title.setStyleSheet(f"color:{ACCENT}; font-weight:700; font-size:13px;")
        lay.addWidget(title)
        self.score_lbl = QLabel("power 0%")
        self.score_lbl.setStyleSheet(f"color:{TEXT_SECONDARY}; font-size:11px;")
        lay.addWidget(self.score_lbl)
        self.bars = {}
        self.val_lbls = {}
        for name in STAT_ORDER:
            row = QFrame()
            rl = QVBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(1)
            top = QLabel(STAT_LABELS.get(name, name))
            top.setStyleSheet(f"color:{TEXT_PRIMARY}; font-size:10px; font-weight:600;")
            rl.addWidget(top)
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedHeight(8)
            bar.setStyleSheet(
                f"QProgressBar {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:3px; }}"
                f"QProgressBar::chunk {{ background:{ACCENT}; border-radius:3px; }}"
            )
            rl.addWidget(bar)
            self.bars[name] = bar
            self.val_lbls[name] = top
            lay.addWidget(row)
        self.msg_lbl = QLabel("")
        self.msg_lbl.setWordWrap(True)
        self.msg_lbl.setStyleSheet(f"color:{WARNING}; font-size:10px;")
        lay.addWidget(self.msg_lbl)
        lay.addStretch()

    def update_from_snapshot(self, snap: dict) -> None:
        bars = snap.get("bars", {})
        for name in STAT_ORDER:
            info = bars.get(name, {})
            pct = float(info.get("pct", 0.0))
            val = float(info.get("value", 0.0))
            mx = float(info.get("max", 100))
            maxed = bool(info.get("maxed", False))
            bar = self.bars[name]
            bar.setValue(int(max(0.0, min(1.0, pct)) * 1000))
            label = STAT_LABELS.get(name, name)
            if maxed:
                self.val_lbls[name].setText(f"{label}  MAX")
                self.val_lbls[name].setStyleSheet(f"color:{SUCCESS}; font-size:10px; font-weight:700;")
                bar.setStyleSheet(
                    f"QProgressBar {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:3px; }}"
                    f"QProgressBar::chunk {{ background:{SUCCESS}; border-radius:3px; }}"
                )
            else:
                self.val_lbls[name].setText(f"{label}  {int(val)}/{int(mx)}")
                self.val_lbls[name].setStyleSheet(f"color:{TEXT_PRIMARY}; font-size:10px; font-weight:600;")
                bar.setStyleSheet(
                    f"QProgressBar {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:3px; }}"
                    f"QProgressBar::chunk {{ background:{ACCENT}; border-radius:3px; }}"
                )
        ps = float(snap.get("power_score", 0.0))
        if snap.get("all_max"):
            self.score_lbl.setText("ALL MAX — FULLY POWERFUL")
            self.score_lbl.setStyleSheet(f"color:{SUCCESS}; font-size:11px; font-weight:700;")
        else:
            self.score_lbl.setText(f"power {int(ps * 100)}%")
            self.score_lbl.setStyleSheet(f"color:{TEXT_SECONDARY}; font-size:11px;")

    def set_message(self, text: str) -> None:
        self.msg_lbl.setText(text or "")

    def refresh(self) -> None:
        self.update_from_snapshot(get_stats().snapshot())
