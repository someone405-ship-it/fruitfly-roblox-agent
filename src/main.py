"""FruitFly advanced main — motor panel + dual-timescale brain."""
from __future__ import annotations
import sys, time
from typing import List
from pathlib import Path
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut, QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame, QSplitter, QStatusBar, QComboBox,
)
from .config import (
    WINDOW_W, WINDOW_H, BG_DEEP, BG_PANEL, BG_CARD, ACCENT,
    TEXT_PRIMARY, TEXT_SECONDARY, BORDER, DANGER, SUCCESS, WEIGHTS_PATH,
)
from .brain import FruitFlyBrain
from .vision import VisionEncoder
from .motor import MotorController
from .monitor import LiveMonitor
from .fly3d import FlyKeyboardWidget
from .logger import ActionLogger
from .roblox_launcher import launch_roblox, is_roblox_running, find_roblox_player
from .trainer import Trainer
from .motor_panel import MotorOutputPanel

class AgentWorker(QThread):
    frame_ready = pyqtSignal(object)
    log_ready = pyqtSignal(str)
    status_ready = pyqtSignal(str)
    actions_ready = pyqtSignal(list)
    stats_ready = pyqtSignal(dict)
    motor_ready = pyqtSignal(dict, list)
    def __init__(self):
        super().__init__()
        self._running = False
        self._paused = True
        self.brain = FruitFlyBrain(seed=42)
        self.brain.load_weights(WEIGHTS_PATH)
        self.vision = VisionEncoder()
        self.motor = MotorController()
        self.logger = ActionLogger()
        self.trainer = Trainer(self.brain)
        self._host_keys: List[str] = []
        self.auto_focus = True
    def run(self):
        self._running = True
        self.log_ready.emit("advanced brain online (1024 dual-timescale)")
        while self._running:
            if self._paused:
                self.msleep(40); continue
            t0 = time.perf_counter()
            try:
                if self.auto_focus and self.brain.steps % 30 == 0:
                    self.motor.focus_roblox()
                frame = self.vision.capture()
                sensory = self.vision.encode(frame)
                motor, info = self.brain.step(sensory)
                if self.trainer.enabled and self.trainer.mode == "imitation":
                    self.trainer.record_host_keys(self._host_keys)
                    info["train_err"] = self.trainer.step_imitation()
                    info["train_samples"] = self.trainer.samples
                    actions = self.brain.decide(motor, threshold=0.32)
                else:
                    actions = self.brain.decide(motor, threshold=0.20)
                sent = self.motor.apply(actions, motor.tolist())
                self.frame_ready.emit(frame)
                self.actions_ready.emit(actions)
                self.stats_ready.emit(info)
                self.motor_ready.emit(info.get("motor", {}), actions)
                if sent:
                    self.log_ready.emit(f"-> {', '.join(sent)} | spk={info['n_spikes']}")
                self.status_ready.emit("flying" if not self.trainer.enabled else "training")
            except Exception as e:
                self.log_ready.emit(f"error: {e}")
            self.msleep(max(1, int(33 - (time.perf_counter()-t0)*1000)))
        self.motor.release_all()
        self.vision.close()
        try:
            self.brain.save_weights(WEIGHTS_PATH)
        except Exception:
            pass
    def set_host_keys(self, keys):
        self._host_keys = list(keys)
    def start_fly(self):
        self._paused = False; self.motor.resume(); self.motor.focus_roblox()
        self.log_ready.emit("F8 fly on")
    def pause_fly(self):
        self._paused = True; self.motor.release_all(); self.log_ready.emit("F8 pause")
    def emergency(self):
        self._paused = True; self.motor.emergency_stop(); self.log_ready.emit("F9 stop")
    def stop(self):
        self._running = False; self.motor.release_all()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FruitFly ADVANCED")
        self.resize(WINDOW_W, WINDOW_H)
        self.setStyleSheet(f"QMainWindow,QWidget{{background:{BG_DEEP};color:{TEXT_PRIMARY};}} QFrame#panel{{background:{BG_PANEL};border:1px solid {BORDER};border-radius:12px;}} QPushButton{{background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:8px 14px;font-weight:600;}} QPushButton#startBtn{{background:{ACCENT};color:#0B0E14;border:none;}} QPushButton#stopBtn{{background:{DANGER};color:white;border:none;}} QPushButton#trainBtn{{background:{SUCCESS};color:#0B0E14;border:none;}} QTextEdit{{background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;color:{TEXT_SECONDARY};font-family:Consolas;font-size:12px;}} QLabel#title{{color:{ACCENT};font-size:18px;font-weight:700;}}")
        self._flying = False
        self._host_keys = []
        self.worker = AgentWorker()
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.log_ready.connect(self._on_log)
        self.worker.status_ready.connect(self._on_status)
        self.worker.actions_ready.connect(self._on_actions)
        self.worker.stats_ready.connect(self._on_stats)
        self.worker.motor_ready.connect(self._on_motor)
        self._build(); self._hotkeys(); self.worker.start(); self._boot()
    def _build(self):
        c = QWidget(); self.setCentralWidget(c)
        root = QVBoxLayout(c)
        h = QHBoxLayout()
        t = QLabel("FRUITFLY ADVANCED"); t.setObjectName("title"); h.addWidget(t); h.addStretch()
        self.btn_start = QPushButton("START F8"); self.btn_start.setObjectName("startBtn"); self.btn_start.clicked.connect(self._toggle); h.addWidget(self.btn_start)
        self.btn_train = QPushButton("TRAIN OFF"); self.btn_train.setObjectName("trainBtn"); self.btn_train.clicked.connect(self._toggle_train); h.addWidget(self.btn_train)
        b = QPushButton("LAUNCH"); b.clicked.connect(self._boot); h.addWidget(b)
        b = QPushButton("SAVE"); b.clicked.connect(self._save); h.addWidget(b)
        b = QPushButton("LOAD"); b.clicked.connect(self._load); h.addWidget(b)
        b = QPushButton("STOP F9"); b.setObjectName("stopBtn"); b.clicked.connect(self.worker.emergency); h.addWidget(b)
        self.train_mode = QComboBox(); self.train_mode.addItems(["imitation","reward"])
        self.train_mode.currentTextChanged.connect(lambda m: self.worker.trainer.set_mode(m)); h.addWidget(self.train_mode)
        root.addLayout(h)
        split = QSplitter(Qt.Orientation.Horizontal)
        left = QFrame(); left.setObjectName("panel"); ll = QVBoxLayout(left)
        self.monitor = LiveMonitor(); ll.addWidget(self.monitor)
        self.log_view = QTextEdit(); self.log_view.setReadOnly(True); self.log_view.setMinimumHeight(120); ll.addWidget(self.log_view)
        split.addWidget(left)
        mid = QFrame(); mid.setObjectName("panel"); ml = QVBoxLayout(mid)
        self.motor_panel = MotorOutputPanel(); ml.addWidget(self.motor_panel)
        split.addWidget(mid)
        right = QFrame(); right.setObjectName("panel"); rl = QVBoxLayout(right)
        self.fly_kb = FlyKeyboardWidget(); rl.addWidget(self.fly_kb)
        self.stats_lbl = QLabel("idle"); rl.addWidget(self.stats_lbl); rl.addStretch()
        split.addWidget(right)
        split.setSizes([560,400,400]); root.addWidget(split, 1)
        self.status = QStatusBar(); self.setStatusBar(self.status)
    def _hotkeys(self):
        QShortcut(QKeySequence("F8"), self, activated=self._toggle)
        QShortcut(QKeySequence("F9"), self, activated=self.worker.emergency)
        QShortcut(QKeySequence("T"), self, activated=self._toggle_train)
        QShortcut(QKeySequence("Esc"), self, activated=self.close)
        QShortcut(QKeySequence("+"), self, activated=lambda: self._reward(1.0))
        QShortcut(QKeySequence("-"), self, activated=lambda: self._reward(-1.0))
    def _boot(self):
        p = find_roblox_player()
        if p: self.log_view.append(f"found {p}")
        ok, msg = launch_roblox(6.0)
        self.log_view.append(msg); self.status.showMessage(msg)
    def _toggle(self):
        if self._flying:
            self.worker.pause_fly(); self.btn_start.setText("START F8"); self._flying = False
        else:
            if not is_roblox_running(): self._boot()
            self.worker.start_fly(); self.btn_start.setText("PAUSE F8"); self._flying = True
    def _toggle_train(self):
        t = self.worker.trainer; t.set_enabled(not t.enabled)
        self.btn_train.setText("TRAIN ON" if t.enabled else "TRAIN OFF")
    def _reward(self, r):
        self.worker.trainer.step_reward(r); self.log_view.append(f"reward {r:+.1f}")
    def _save(self):
        self.worker.brain.save_weights(WEIGHTS_PATH); self.log_view.append("saved brain")
    def _load(self):
        ok = self.worker.brain.load_weights(WEIGHTS_PATH)
        self.log_view.append("loaded" if ok else "no file")
    def keyPressEvent(self, e):
        m = {Qt.Key.Key_W:"w",Qt.Key.Key_A:"a",Qt.Key.Key_S:"s",Qt.Key.Key_D:"d",Qt.Key.Key_Space:"space",Qt.Key.Key_Shift:"shift",Qt.Key.Key_E:"e"}
        n = m.get(e.key())
        if n and n not in self._host_keys:
            self._host_keys.append(n); self.worker.set_host_keys(self._host_keys)
        super().keyPressEvent(e)
    def keyReleaseEvent(self, e):
        m = {Qt.Key.Key_W:"w",Qt.Key.Key_A:"a",Qt.Key.Key_S:"s",Qt.Key.Key_D:"d",Qt.Key.Key_Space:"space",Qt.Key.Key_Shift:"shift",Qt.Key.Key_E:"e"}
        n = m.get(e.key())
        if n and n in self._host_keys:
            self._host_keys.remove(n); self.worker.set_host_keys(self._host_keys)
        super().keyReleaseEvent(e)
    def _on_frame(self, f): self.monitor.update_frame(f)
    def _on_log(self, m):
        self.log_view.append(m); sb = self.log_view.verticalScrollBar(); sb.setValue(sb.maximum())
    def _on_status(self, t):
        self.monitor.set_status(t); self.status.showMessage(t)
    def _on_actions(self, a): self.fly_kb.set_active(a)
    def _on_motor(self, d, a): self.motor_panel.set_motor(d, a)
    def _on_stats(self, info):
        self.stats_lbl.setText(
            f"t={info['t_ms']:.0f}ms steps={info.get('steps',0)}\n"
            f"spk={info['n_spikes']} total={info.get('total_spikes',0)}\n"
            f"rate={info['mean_rate']:.4f} slow={info.get('mean_rate_slow',0):.4f}\n"
            f"gain={info.get('mean_gain',1):.3f}"
        )
    def closeEvent(self, e):
        self.worker.stop(); self.worker.wait(3000); e.accept()

def main():
    app = QApplication(sys.argv); app.setStyle("Fusion")
    win = MainWindow(); win.show(); sys.exit(app.exec())

if __name__ == "__main__":
    main()
