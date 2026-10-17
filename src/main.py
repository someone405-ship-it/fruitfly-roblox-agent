"""FruitFly Roblox Agent — restored working UI loop."""
from __future__ import annotations
import sys
import time
import traceback
import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame, QStatusBar, QSlider,
)
from .config import (
    WINDOW_W, WINDOW_H, BG_DEEP, BG_PANEL, BG_CARD, ACCENT, TEXT_PRIMARY,
    TEXT_SECONDARY, BORDER, DANGER, SUCCESS, WEIGHTS_PATH, N_HIDDEN, N_COLS,
    DECIDE_THRESHOLD_BASE, LOOK_SENSITIVITY,
)
from .brain import FruitFlyBrain, using_gpu
from .vision import VisionEncoder
from .motor import MotorController
from .trainer import Trainer
from .behavior import BehaviorLayer
from . import host_learn, input_lock

try:
    from .roblox_launcher import launch_roblox, is_roblox_running, maximize_roblox_window
except Exception:
    def launch_roblox(*a, **k):
        return False, "launcher missing"
    def is_roblox_running():
        return False
    def maximize_roblox_window():
        return False


class AgentWorker(QThread):
    log_ready = pyqtSignal(str)
    status_ready = pyqtSignal(str)
    actions_ready = pyqtSignal(list)
    stats_ready = pyqtSignal(dict)
    worker_ready = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._paused = True
        self.brain = FruitFlyBrain(seed=42)
        self._weights_loaded = self.brain.load_weights(WEIGHTS_PATH)
        self.vision = VisionEncoder()
        self.motor = MotorController()
        self.trainer = Trainer(self.brain)
        self.behavior = BehaviorLayer()
        self.learning = False
        self.auto_focus = True
        try:
            if hasattr(self.trainer, "bootstrap_explore"):
                self.trainer.bootstrap_explore(800)
            elif hasattr(self.trainer, "bootstrap"):
                self.trainer.bootstrap(800)
            self._boot_err = ""
        except Exception as e:
            self._boot_err = str(e)

    def run(self) -> None:
        self._running = True
        backend = "CUDA" if using_gpu() else "CPU"
        self.log_ready.emit(f"FruitFly · {N_HIDDEN} neurons · {backend}")
        if self._weights_loaded:
            self.log_ready.emit("loaded weights")
        else:
            self.log_ready.emit("fresh brain")
        if self._boot_err:
            self.log_ready.emit(f"bootstrap warn: {self._boot_err}")
        self.worker_ready.emit()

        while self._running:
            if self._paused and not self.learning:
                self.msleep(20)
                continue
            t0 = time.perf_counter()
            try:
                if self.learning:
                    frame = self.vision.capture()
                    sensory = self.vision.encode(frame)
                    motor, info = self.brain.step(sensory)
                    keys = host_learn.keys_down() if hasattr(host_learn, "keys_down") else []
                    meta = self.vision.last_meta or {}
                    self.trainer.set_mode("imitation")
                    self.trainer.record_host_keys(keys, meta=meta, sensory=sensory)
                    err = self.trainer.step_imitation()
                    if keys:
                        self.log_ready.emit(f"learn <- {keys} err={err:.3f}")
                    self.status_ready.emit(f"LEARN n={getattr(self.trainer,'imit_samples',0)}")
                    self.msleep(8)
                    continue

                if self.auto_focus and self.brain.steps % 30 == 0:
                    try:
                        self.motor.focus_roblox(maximize=True)
                    except Exception:
                        pass

                frame = self.vision.capture()
                sensory = self.vision.encode(frame)
                motor, info = self.brain.step(sensory)
                meta = self.vision.last_meta or {}
                self.trainer.set_mode("reward")
                motor, notes, binfo = self.behavior.modulate(motor, meta)
                info.update(binfo)
                thr = float(getattr(self.trainer, "lr", 0.14))
                actions = self.brain.decide(motor, threshold=DECIDE_THRESHOLD_BASE)
                for a in binfo.get("force") or []:
                    if a not in actions:
                        actions.append(a)
                line = self.behavior.take_line()
                if line:
                    self.log_ready.emit(f"fly: {line}")
                try:
                    rew = self.trainer.online_step(notes, meta, motor, sensory=sensory, actions=actions)
                    if abs(float(rew)) > 0.4 and self.brain.steps % 25 == 0:
                        self.log_ready.emit(f"train r={rew:+.2f}")
                except Exception as e:
                    if self.brain.steps % 100 == 0:
                        self.log_ready.emit(f"train skip: {e}")

                if self.brain.steps > 0 and self.brain.steps % 200 == 0:
                    try:
                        self.brain.save_weights(WEIGHTS_PATH)
                        self.trainer.flush_memory()
                        self.log_ready.emit("autosave")
                    except Exception as e:
                        self.log_ready.emit(f"autosave: {e}")

                sent = self.motor.apply(actions, motor.tolist())
                self.actions_ready.emit(actions)
                self.stats_ready.emit(info)
                if sent:
                    self.log_ready.emit(f"-> {', '.join(map(str, sent[:8]))}")
                self.status_ready.emit(
                    f"goal={info.get('goal','?')} portal={float(meta.get('portal_score',0) or 0):.2f} "
                    f"steps={self.brain.steps}"
                )
            except Exception as e:
                self.log_ready.emit(f"error: {type(e).__name__}: {e}")
                self.log_ready.emit(traceback.format_exc().splitlines()[-1][:160])
            dt = (time.perf_counter() - t0) * 1000.0
            self.msleep(max(2, int(12 - dt)))

        self.motor.release_all()
        try:
            self.vision.close()
        except Exception:
            pass
        try:
            self.brain.save_weights(WEIGHTS_PATH)
            self.trainer.flush_memory()
        except Exception:
            pass
        try:
            input_lock.unlock()
        except Exception:
            pass

    def start_fly(self) -> None:
        self.motor.resume()
        try:
            maximize_roblox_window()
            self.motor.focus_roblox(True)
        except Exception:
            pass
        try:
            input_lock.lock()
        except Exception:
            pass
        self._paused = False
        self.log_ready.emit("START")

    def stop_fly(self) -> None:
        self._paused = True
        self.motor.release_all()
        try:
            input_lock.unlock()
        except Exception:
            pass
        try:
            self.brain.save_weights(WEIGHTS_PATH)
            self.trainer.flush_memory()
        except Exception:
            pass
        self.log_ready.emit("STOP")

    def emergency(self) -> None:
        self._paused = True
        self.motor.emergency_stop()
        try:
            input_lock.unlock()
        except Exception:
            pass
        self.learning = False
        self.log_ready.emit("F9")

    def stop(self) -> None:
        self._running = False
        self.motor.release_all()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FruitFly Roblox Agent")
        self.resize(WINDOW_W, WINDOW_H)
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background:{BG_DEEP}; color:{TEXT_PRIMARY}; }}
            QPushButton {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:8px; padding:10px 14px; font-weight:700; }}
            QPushButton#startBtn {{ background:{SUCCESS}; color:#0B0E14; border:none; }}
            QPushButton#stopBtn {{ background:{DANGER}; color:white; border:none; }}
            QTextEdit {{ background:{BG_CARD}; border:1px solid {BORDER}; color:{TEXT_SECONDARY}; font-family:Consolas; }}
            QLabel#title {{ color:{ACCENT}; font-size:18px; font-weight:800; }}
        """)
        self._ok = False
        self.worker = AgentWorker()
        self.worker.log_ready.connect(self._log)
        self.worker.status_ready.connect(lambda t: self.status.showMessage(t))
        self.worker.stats_ready.connect(self._stats)
        self.worker.actions_ready.connect(lambda a: self.act_lbl.setText("actions: " + ", ".join(a[:12])))
        self.worker.worker_ready.connect(self._ready)
        c = QWidget(); self.setCentralWidget(c)
        root = QVBoxLayout(c)
        title = QLabel("FRUITFLY · 139255")
        title.setObjectName("title"); root.addWidget(title)
        self.setup_lbl = QLabel("booting…"); root.addWidget(self.setup_lbl)
        row = QHBoxLayout()
        self.btn_start = QPushButton("START"); self.btn_start.setObjectName("startBtn")
        self.btn_start.clicked.connect(self._start); self.btn_start.setEnabled(False)
        row.addWidget(self.btn_start)
        self.btn_stop = QPushButton("STOP"); self.btn_stop.setObjectName("stopBtn")
        self.btn_stop.clicked.connect(self._stop); self.btn_stop.setEnabled(False)
        row.addWidget(self.btn_stop)
        self.btn_learn = QPushButton("LEARN FROM ME"); self.btn_learn.setCheckable(True)
        self.btn_learn.clicked.connect(self._learn); row.addWidget(self.btn_learn)
        row.addStretch(); root.addLayout(row)
        self.log_view = QTextEdit(); self.log_view.setReadOnly(True); root.addWidget(self.log_view, 1)
        self.act_lbl = QLabel("actions: —"); root.addWidget(self.act_lbl)
        self.stats_lbl = QLabel(""); root.addWidget(self.stats_lbl)
        self.status = QStatusBar(); self.setStatusBar(self.status)
        QShortcut(QKeySequence("F9"), self, activated=self._emerg)
        self.worker.start()
        QTimer.singleShot(400, self._setup)

    def _setup(self):
        ok, msg = launch_roblox(wait_seconds=8.0, maximize=True)
        self._log(f"setup: {msg}")
        self.setup_lbl.setText("READY" if self._ok else "wait brain…")

    def _ready(self):
        self._ok = True
        self.setup_lbl.setText("READY")
        self.btn_start.setEnabled(True)

    def _start(self):
        self.worker.start_fly()
        self.btn_start.setEnabled(False); self.btn_stop.setEnabled(True)

    def _stop(self):
        self.worker.stop_fly()
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)

    def _learn(self):
        self.worker.learning = self.btn_learn.isChecked()
        if self.worker.learning:
            self.worker._paused = False
            self._log("LEARN ON")

    def _emerg(self):
        self.worker.emergency()
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)
        self.btn_learn.setChecked(False)

    def _log(self, m):
        self.log_view.append(m)

    def _stats(self, info):
        self.stats_lbl.setText(f"goal={info.get('goal')} notes={info.get('notes')}")

    def closeEvent(self, e):
        try:
            self.worker.stop(); self.worker.wait(2500)
        except Exception:
            pass
        e.accept()


def main():
    app = QApplication(sys.argv)
    win = MainWindow(); win.show()
    sys.exit(app.exec())
