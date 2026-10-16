"""FruitFly Roblox Agent — circuit + reservoir + instincts."""
from __future__ import annotations
import sys
import time
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame, QSplitter, QStatusBar,
)
from .config import (
    WINDOW_W, WINDOW_H, BG_DEEP, BG_PANEL, BG_CARD, ACCENT,
    TEXT_PRIMARY, TEXT_SECONDARY, BORDER, DANGER, SUCCESS, WEIGHTS_PATH, MOTOR_NAMES,
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
from .behavior import BehaviorLayer
from .circuit import FlyCircuit
from .circuit_panel import CircuitPanel
from . import input_lock


class AgentWorker(QThread):
    frame_ready = pyqtSignal(object)
    log_ready = pyqtSignal(str)
    status_ready = pyqtSignal(str)
    actions_ready = pyqtSignal(list)
    stats_ready = pyqtSignal(dict)
    motor_ready = pyqtSignal(dict, list)
    worker_ready = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._paused = True
        self.brain = FruitFlyBrain(seed=42)
        self.brain.load_weights(WEIGHTS_PATH)
        self.vision = VisionEncoder()
        self.motor = MotorController()
        self.logger = ActionLogger()
        self.trainer = Trainer(self.brain)
        self.behavior = BehaviorLayer()
        self.circuit = FlyCircuit(seed=3)
        self.auto_focus = True
        self.last_circuit = {}
        try:
            self.trainer.bootstrap_explore(180)
        except Exception:
            pass

    def run(self) -> None:
        self._running = True
        self.log_ready.emit("brain online")
        if self.trainer.samples:
            self.log_ready.emit(f"pre-train samples={self.trainer.samples}")
        self.worker_ready.emit()
        while self._running:
            if self._paused:
                self.msleep(40)
                continue
            t0 = time.perf_counter()
            try:
                if self.auto_focus and self.brain.steps % 30 == 0:
                    self.motor.focus_roblox()
                frame = self.vision.capture()
                sensory = self.vision.encode(frame)
                motor, info = self.brain.step(sensory)
                meta = self.vision.last_meta
                loom = float(meta.get("loom_score", 0.0))
                motion = float(meta.get("motion", 0.0))
                turn = float(motor[2] - motor[3]) if motor.size > 3 else 0.0
                fwd_drive = max(0.0, float(motor[0]) * 0.5 + 0.35)
                calm = max(0.0, 1.0 - loom - motion * 2)
                cread = self.circuit.step(loom=loom, forward_drive=fwd_drive, turn=turn, calm=calm)
                self.last_circuit = cread
                cbias = self.circuit.motor_bias(cread)
                motor, notes, binfo = self.behavior.modulate(motor, meta, circuit_bias=cbias)
                info.update(binfo)
                info.update(cread)
                actions = self.brain.decide(motor, threshold=0.38)
                actions = [a for a in actions if not a.startswith("look_")]
                sent = self.motor.apply(actions, motor.tolist())
                chat = self.behavior.take_chat()
                if chat:
                    self.motor.type_text(chat)
                    sent.append(f'chat:"{chat}"')
                    self.log_ready.emit(f"instinct chat -> {chat}")
                self.frame_ready.emit(frame)
                self.actions_ready.emit(actions)
                self.stats_ready.emit(info)
                self.motor_ready.emit({n: float(motor[i]) for i, n in enumerate(MOTOR_NAMES)}, actions)
                if sent:
                    tag = ",".join(notes) if notes else ""
                    esc = " ESCAPE" if cread.get("escape") else ""
                    self.log_ready.emit(f"-> {', '.join(sent)} | {tag}{esc} | spk={info['n_spikes']}")
                self.status_ready.emit(
                    f"WATCH ONLY — fear={binfo.get('fear',0):.2f} gf={cread.get('gf_rate',0):.2f}"
                )
            except Exception as e:
                self.log_ready.emit(f"error: {e}")
            dt = (time.perf_counter() - t0) * 1000.0
            self.msleep(max(1, int(33 - dt)))
        self.motor.release_all()
        self.vision.close()
        try:
            self.brain.save_weights(WEIGHTS_PATH)
        except Exception:
            pass
        input_lock.unlock()

    def start_fly(self) -> None:
        self.motor.resume()
        self.motor.focus_roblox()
        ok = input_lock.lock()
        self._paused = False
        self.log_ready.emit("START — watch only" if ok else "START — fly on (no lock)")

    def stop_fly(self) -> None:
        self._paused = True
        self.motor.release_all()
        input_lock.unlock()
        self.log_ready.emit("STOP — unlocked")
        self.status_ready.emit("stopped")

    def emergency(self) -> None:
        self._paused = True
        self.motor.emergency_stop()
        input_lock.unlock()
        self.log_ready.emit("F9 emergency — unlocked")

    def stop(self) -> None:
        self._running = False
        self.motor.release_all()
        input_lock.unlock()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FruitFly Roblox Agent")
        self.resize(WINDOW_W, WINDOW_H)
        self.setStyleSheet(self._ss())
        self._flying = False
        self._setup_done = False
        self._worker_ok = False
        self._roblox_ok = False
        self.worker = AgentWorker()
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.log_ready.connect(self._on_log)
        self.worker.status_ready.connect(self._on_status)
        self.worker.actions_ready.connect(self._on_actions)
        self.worker.stats_ready.connect(self._on_stats)
        self.worker.motor_ready.connect(self._on_motor)
        self.worker.worker_ready.connect(self._on_worker_ready)
        self._build()
        QShortcut(QKeySequence("F9"), self, activated=self._on_emergency)
        QShortcut(QKeySequence("Esc"), self, activated=self.close)
        self.worker.start()
        QTimer.singleShot(250, self._run_setup)

    def _ss(self) -> str:
        return f"""
        QMainWindow, QWidget {{ background:{BG_DEEP}; color:{TEXT_PRIMARY}; font-family:Segoe UI,sans-serif; }}
        QFrame#panel {{ background:{BG_PANEL}; border:1px solid {BORDER}; border-radius:12px; }}
        QPushButton {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:8px; padding:10px 18px; font-weight:600; }}
        QPushButton#startBtn {{ background:{SUCCESS}; color:#0B0E14; border:none; font-size:15px; min-width:130px; }}
        QPushButton#stopBtn {{ background:{DANGER}; color:white; border:none; font-size:15px; min-width:130px; }}
        QPushButton:disabled {{ color:{TEXT_SECONDARY}; }}
        QTextEdit {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:8px;
                     color:{TEXT_SECONDARY}; font-family:Consolas,monospace; font-size:12px; }}
        QLabel#title {{ color:{ACCENT}; font-size:18px; font-weight:700; }}
        QLabel#setupLbl {{ color:{TEXT_SECONDARY}; font-size:13px; padding:8px; }}
        QLabel#watchLbl {{ color:{DANGER}; font-size:13px; font-weight:700; padding:6px; }}
        QStatusBar {{ background:{BG_PANEL}; color:{TEXT_SECONDARY}; }}
        """

    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 8)
        header = QHBoxLayout()
        title = QLabel("FRUITFLY ROBLOX AGENT")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        root.addLayout(header)
        self.setup_lbl = QLabel("SETTING UP…")
        self.setup_lbl.setObjectName("setupLbl")
        self.setup_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.setup_lbl)
        ctrl = QHBoxLayout()
        ctrl.addStretch()
        self.btn_start = QPushButton("START")
        self.btn_start.setObjectName("startBtn")
        self.btn_start.clicked.connect(self._on_start)
        self.btn_start.setVisible(False)
        ctrl.addWidget(self.btn_start)
        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setObjectName("stopBtn")
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_stop.setVisible(False)
        self.btn_stop.setEnabled(False)
        ctrl.addWidget(self.btn_stop)
        ctrl.addStretch()
        root.addLayout(ctrl)
        self.watch_lbl = QLabel("")
        self.watch_lbl.setObjectName("watchLbl")
        self.watch_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.watch_lbl.setVisible(False)
        root.addWidget(self.watch_lbl)
        split = QSplitter(Qt.Orientation.Horizontal)
        left = QFrame(); left.setObjectName("panel")
        ll = QVBoxLayout(left)
        self.monitor = LiveMonitor()
        ll.addWidget(self.monitor)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(120)
        ll.addWidget(self.log_view)
        split.addWidget(left)
        mid = QFrame(); mid.setObjectName("panel")
        ml = QVBoxLayout(mid)
        self.motor_panel = MotorOutputPanel()
        ml.addWidget(self.motor_panel)
        self.circuit_panel = CircuitPanel()
        ml.addWidget(self.circuit_panel)
        split.addWidget(mid)
        right = QFrame(); right.setObjectName("panel")
        rl = QVBoxLayout(right)
        self.fly_kb = FlyKeyboardWidget()
        rl.addWidget(self.fly_kb)
        self.stats_lbl = QLabel("waiting")
        rl.addWidget(self.stats_lbl)
        rl.addStretch()
        split.addWidget(right)
        split.setSizes([560, 400, 400])
        root.addWidget(split, 1)
        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def _run_setup(self) -> None:
        path = find_roblox_player()
        if path:
            self.log_view.append(f"setup: found {path}")
        ok, msg = launch_roblox(wait_seconds=7.0)
        self.log_view.append(f"setup: {msg}")
        self._roblox_ok = bool(ok) or is_roblox_running()
        if not self._roblox_ok:
            self.setup_lbl.setText("Waiting for Roblox…")
            QTimer.singleShot(2500, self._recheck_roblox)
            return
        self._try_finish_setup()

    def _recheck_roblox(self) -> None:
        if is_roblox_running():
            self._roblox_ok = True
            self._try_finish_setup()
        else:
            QTimer.singleShot(2500, self._recheck_roblox)

    def _on_worker_ready(self) -> None:
        self._worker_ok = True
        self._try_finish_setup()

    def _try_finish_setup(self) -> None:
        if self._setup_done:
            return
        if not (self._worker_ok and self._roblox_ok):
            return
        self._setup_done = True
        self.setup_lbl.setText("READY — START. Circuit: loom→GF escape, DNp09 walk, MDN reverse.")
        self.setup_lbl.setStyleSheet(f"color:{SUCCESS}; font-size:13px; font-weight:600;")
        self.btn_start.setVisible(True)
        self.btn_stop.setVisible(True)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def _on_start(self) -> None:
        if not self._setup_done or self._flying:
            return
        if not is_roblox_running():
            launch_roblox(6.0)
        self.worker.start_fly()
        self._flying = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.watch_lbl.setText("WATCH ONLY — STOP/F9 unlocks. Keep Roblox visible.")
        self.watch_lbl.setVisible(True)

    def _on_stop(self) -> None:
        if not self._flying:
            return
        self.worker.stop_fly()
        self._flying = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.watch_lbl.setVisible(False)

    def _on_emergency(self) -> None:
        self.worker.emergency()
        self._flying = False
        if self._setup_done:
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
        self.watch_lbl.setVisible(False)

    def _on_frame(self, f) -> None:
        self.monitor.update_frame(f)

    def _on_log(self, m: str) -> None:
        self.log_view.append(m)
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_status(self, t: str) -> None:
        self.monitor.set_status(t)
        self.status.showMessage(t)

    def _on_actions(self, a: list) -> None:
        self.fly_kb.set_active(a)

    def _on_motor(self, d: dict, a: list) -> None:
        self.motor_panel.set_motor(d, a)

    def _on_stats(self, info: dict) -> None:
        self.circuit_panel.set_rates(info)
        self.stats_lbl.setText(
            f"t={info.get('t_ms',0):.0f}ms steps={info.get('steps',0)}\n"
            f"spk={info.get('n_spikes',0)} rate={info.get('mean_rate',0):.3f}\n"
            f"fear={info.get('fear',0):.2f} hunger={info.get('hunger',0):.2f}\n"
            f"loom={info.get('loom_score',0):.2f} gf={info.get('gf_rate',0):.2f}\n"
            f"lock={'ON' if input_lock.is_locked() else 'off'}"
        )

    def closeEvent(self, e) -> None:
        input_lock.unlock()
        self.worker.stop()
        self.worker.wait(4000)
        e.accept()


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
