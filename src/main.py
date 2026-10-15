"""FruitFly Roblox Agent — full app. Auto-launch Roblox, live monitor, 3D fly keyboard, train."""

from __future__ import annotations
import sys, time
from typing import List
import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut, QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame, QSplitter, QStatusBar, QComboBox,
)
from .config import WINDOW_W, WINDOW_H, BG_DEEP, BG_PANEL, BG_CARD, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, BORDER, DANGER, SUCCESS
from .brain import FruitFlyBrain
from .vision import VisionEncoder
from .motor import MotorController
from .monitor import LiveMonitor
from .fly3d import FlyKeyboardWidget
from .logger import ActionLogger
from .roblox_launcher import launch_roblox, is_roblox_running, find_roblox_player
from .trainer import Trainer

class AgentWorker(QThread):
    frame_ready = pyqtSignal(object)
    log_ready = pyqtSignal(str)
    status_ready = pyqtSignal(str)
    actions_ready = pyqtSignal(list)
    stats_ready = pyqtSignal(dict)
    def __init__(self):
        super().__init__()
        self._running = False
        self._paused = True
        self.brain = FruitFlyBrain(seed=42)
        self.vision = VisionEncoder()
        self.motor = MotorController()
        self.logger = ActionLogger()
        self.trainer = Trainer(self.brain)
        self._host_keys: List[str] = []
    def run(self):
        self._running = True
        self.log_ready.emit("worker online — fruit fly brain loaded")
        while self._running:
            if self._paused:
                self.msleep(40); continue
            t0 = time.perf_counter()
            try:
                frame = self.vision.capture()
                sensory = self.vision.encode(frame)
                motor, info = self.brain.step(sensory)
                if self.trainer.enabled and self.trainer.mode == "imitation":
                    self.trainer.record_host_keys(self._host_keys)
                    err = self.trainer.step_imitation()
                    info["train_err"] = err; info["train_samples"] = self.trainer.samples
                    actions = self.brain.decide(motor, threshold=0.35)
                else:
                    actions = self.brain.decide(motor, threshold=0.22)
                sent = self.motor.apply(actions, motor.tolist())
                self.frame_ready.emit(frame); self.actions_ready.emit(actions); self.stats_ready.emit(info)
                if sent:
                    msg = f"→ {', '.join(sent)} | spikes={info['n_spikes']}"
                    self.log_ready.emit(msg); self.logger.log(msg)
                self.status_ready.emit("flying" if not self.trainer.enabled else "training+flying")
            except Exception as e:
                self.log_ready.emit(f"error: {e}"); self.status_ready.emit(f"error: {e}")
            self.msleep(max(1, int(33 - (time.perf_counter()-t0)*1000)))
        self.motor.release_all(); self.vision.close(); self.log_ready.emit("worker stopped")
    def set_host_keys(self, keys: List[str]): self._host_keys = list(keys)
    def start_fly(self):
        self._paused = False; self.motor.resume(); self.log_ready.emit("F8 — fly engaged")
    def pause_fly(self):
        self._paused = True; self.motor.release_all(); self.log_ready.emit("F8 — fly paused")
    def emergency(self):
        self._paused = True; self.motor.emergency_stop(); self.log_ready.emit("F9 — emergency stop")
    def stop(self):
        self._running = False; self.motor.release_all()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FruitFly Roblox Agent  ·  absolute olliE")
        self.resize(WINDOW_W, WINDOW_H)
        self.setStyleSheet(self._ss())
        self._flying = False
        self._host_keys: List[str] = []
        self.worker = AgentWorker()
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.log_ready.connect(self._on_log)
        self.worker.status_ready.connect(self._on_status)
        self.worker.actions_ready.connect(self._on_actions)
        self.worker.stats_ready.connect(self._on_stats)
        self._build(); self._hotkeys(); self.worker.start(); self._bootstrap_roblox()
    def _ss(self):
        return f"""
        QMainWindow, QWidget {{ background:{BG_DEEP}; color:{TEXT_PRIMARY}; font-family:Segoe UI,sans-serif; }}
        QFrame#panel {{ background:{BG_PANEL}; border:1px solid {BORDER}; border-radius:12px; }}
        QPushButton {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:8px; padding:8px 16px; font-weight:600; }}
        QPushButton:hover {{ border-color:{ACCENT}; color:{ACCENT}; }}
        QPushButton#startBtn {{ background:{ACCENT}; color:#0B0E14; border:none; }}
        QPushButton#stopBtn {{ background:{DANGER}; color:white; border:none; }}
        QPushButton#trainBtn {{ background:{SUCCESS}; color:#0B0E14; border:none; }}
        QTextEdit {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:8px; color:{TEXT_SECONDARY}; font-family:Consolas,monospace; font-size:12px; padding:8px; }}
        QLabel#title {{ color:{ACCENT}; font-size:18px; font-weight:700; }}
        QStatusBar {{ background:{BG_PANEL}; color:{TEXT_SECONDARY}; border-top:1px solid {BORDER}; }}
        QComboBox {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:6px; padding:4px 8px; color:{TEXT_PRIMARY}; }}
        """
    def _build(self):
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(16,16,16,8)
        header = QHBoxLayout()
        title = QLabel("FRUITFLY  ·  ROBLOX AGENT"); title.setObjectName("title"); header.addWidget(title); header.addStretch()
        self.btn_launch = QPushButton("LAUNCH ROBLOX"); self.btn_launch.clicked.connect(self._bootstrap_roblox); header.addWidget(self.btn_launch)
        self.btn_start = QPushButton("START FLY  (F8)"); self.btn_start.setObjectName("startBtn"); self.btn_start.clicked.connect(self._toggle); header.addWidget(self.btn_start)
        self.btn_train = QPushButton("TRAIN OFF  (T)"); self.btn_train.setObjectName("trainBtn"); self.btn_train.clicked.connect(self._toggle_train); header.addWidget(self.btn_train)
        self.train_mode = QComboBox(); self.train_mode.addItems(["imitation","reward"]); self.train_mode.currentTextChanged.connect(lambda m: self.worker.trainer.set_mode(m)); header.addWidget(self.train_mode)
        self.btn_stop = QPushButton("EMERGENCY  (F9)"); self.btn_stop.setObjectName("stopBtn"); self.btn_stop.clicked.connect(self.worker.emergency); header.addWidget(self.btn_stop)
        root.addLayout(header)
        split = QSplitter(Qt.Orientation.Horizontal)
        left = QFrame(); left.setObjectName("panel"); ll = QVBoxLayout(left); ll.setContentsMargins(12,12,12,12)
        self.monitor = LiveMonitor(); ll.addWidget(self.monitor)
        log_lbl = QLabel("ACTION OUTPUT"); log_lbl.setStyleSheet(f"color:{ACCENT}; font-size:11px; font-weight:600;"); ll.addWidget(log_lbl)
        self.log_view = QTextEdit(); self.log_view.setReadOnly(True); self.log_view.setMinimumHeight(160); ll.addWidget(self.log_view)
        split.addWidget(left)
        right = QFrame(); right.setObjectName("panel"); rl = QVBoxLayout(right); rl.setContentsMargins(12,12,12,12)
        self.fly_kb = FlyKeyboardWidget(); rl.addWidget(self.fly_kb)
        self.stats_lbl = QLabel("brain: idle"); self.stats_lbl.setStyleSheet(f"color:{TEXT_SECONDARY}; font-family:Consolas; font-size:12px; padding:8px;"); rl.addWidget(self.stats_lbl)
        help_lbl = QLabel("TRAIN imitation: hold WASD/Space/E to teach.\nTRAIN reward: + / - reinforce.\nKeys light on 3D keyboard when fly presses them."); help_lbl.setWordWrap(True); help_lbl.setStyleSheet(f"color:{TEXT_SECONDARY}; font-size:11px; padding:8px;"); rl.addWidget(help_lbl); rl.addStretch()
        split.addWidget(right); split.setSizes([720,500]); root.addWidget(split, 1)
        self.status = QStatusBar(); self.setStatusBar(self.status); self.status.showMessage("booting…")
    def _hotkeys(self):
        QShortcut(QKeySequence("F8"), self, activated=self._toggle)
        QShortcut(QKeySequence("F9"), self, activated=self.worker.emergency)
        QShortcut(QKeySequence("T"), self, activated=self._toggle_train)
        QShortcut(QKeySequence("Esc"), self, activated=self.close)
        QShortcut(QKeySequence("+"), self, activated=lambda: self._reward(1.0))
        QShortcut(QKeySequence("-"), self, activated=lambda: self._reward(-1.0))
    def _bootstrap_roblox(self):
        path = find_roblox_player()
        if path: self.log_view.append(f"found Roblox: {path}")
        ok, msg = launch_roblox(wait_seconds=6.0)
        self.log_view.append(msg)
        self.status.showMessage("Roblox ready — F8 to play" if ok else msg)
    def _toggle(self):
        if self._flying:
            self.worker.pause_fly(); self.btn_start.setText("START FLY  (F8)"); self._flying = False
        else:
            if not is_roblox_running(): self._bootstrap_roblox()
            self.worker.start_fly(); self.btn_start.setText("PAUSE FLY  (F8)"); self._flying = True
    def _toggle_train(self):
        t = self.worker.trainer; t.set_enabled(not t.enabled)
        self.btn_train.setText("TRAIN ON  (T)" if t.enabled else "TRAIN OFF  (T)")
        self.log_view.append(f"train {'ON' if t.enabled else 'OFF'} mode={t.mode}")
    def _reward(self, r: float):
        self.worker.trainer.step_reward(r); self.log_view.append(f"reward: {r:+.1f}")
    def keyPressEvent(self, event):
        mapping = {Qt.Key.Key_W:"w", Qt.Key.Key_A:"a", Qt.Key.Key_S:"s", Qt.Key.Key_D:"d", Qt.Key.Key_Space:"space", Qt.Key.Key_Shift:"shift", Qt.Key.Key_E:"e"}
        name = mapping.get(event.key())
        if name and name not in self._host_keys:
            self._host_keys.append(name); self.worker.set_host_keys(self._host_keys)
        super().keyPressEvent(event)
    def keyReleaseEvent(self, event):
        mapping = {Qt.Key.Key_W:"w", Qt.Key.Key_A:"a", Qt.Key.Key_S:"s", Qt.Key.Key_D:"d", Qt.Key.Key_Space:"space", Qt.Key.Key_Shift:"shift", Qt.Key.Key_E:"e"}
        name = mapping.get(event.key())
        if name and name in self._host_keys:
            self._host_keys.remove(name); self.worker.set_host_keys(self._host_keys)
        super().keyReleaseEvent(event)
    def _on_frame(self, frame): self.monitor.update_frame(frame)
    def _on_log(self, msg):
        self.log_view.append(msg); sb = self.log_view.verticalScrollBar(); sb.setValue(sb.maximum())
    def _on_status(self, text):
        self.monitor.set_status(text); self.status.showMessage(text)
    def _on_actions(self, actions): self.fly_kb.set_active(actions)
    def _on_stats(self, info):
        t = self.worker.trainer
        extra = f"\ntrain samples: {t.samples}" if t.enabled else ""
        if "train_err" in info: extra += f"\nimitation err: {info['train_err']:.3f}"
        self.stats_lbl.setText(f"brain time: {info['t_ms']:.0f} ms\nspikes: {info['n_spikes']}\nmean rate: {info['mean_rate']:.4f}{extra}")
    def closeEvent(self, event):
        self.worker.stop(); self.worker.wait(2000); event.accept()

def main():
    app = QApplication(sys.argv); app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(BG_DEEP))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_PRIMARY))
    pal.setColor(QPalette.ColorRole.Base, QColor(BG_CARD))
    pal.setColor(QPalette.ColorRole.Text, QColor(TEXT_PRIMARY))
    pal.setColor(QPalette.ColorRole.Button, QColor(BG_PANEL))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT_PRIMARY))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    app.setPalette(pal)
    win = MainWindow(); win.show(); sys.exit(app.exec())

if __name__ == "__main__":
    main()
