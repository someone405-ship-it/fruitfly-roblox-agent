"""FruitFly Roblox Agent — 3072 neurons, kill/death, Figma UI."""
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
from .mouse3d import Mouse3DWidget
from . import input_lock, host_learn


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
        self.learning = False
        try:
            self.trainer.bootstrap_explore(420)
        except Exception:
            pass

    def run(self) -> None:
        self._running = True
        self.log_ready.emit("brain online — 3072 neurons · kill/loot · death hurt · full autonomy")
        if self.trainer.samples:
            self.log_ready.emit(f"pre-train samples={self.trainer.samples}")
        self.worker_ready.emit()
        while self._running:
            if self._paused and not self.learning:
                self.msleep(40)
                continue
            t0 = time.perf_counter()
            try:
                if self.learning:
                    frame = self.vision.capture()
                    sensory = self.vision.encode(frame)
                    motor, info = self.brain.step(sensory)
                    keys = host_learn.keys_down()
                    self.trainer.set_mode("imitation")
                    self.trainer.record_host_keys(keys)
                    err = self.trainer.step_imitation()
                    self.frame_ready.emit(frame)
                    self.stats_ready.emit({**info, "learning": True, "imit_samples": self.trainer.imit_samples})
                    if keys:
                        self.log_ready.emit(f"learn <- {','.join(keys)} err={err:.3f} n={self.trainer.imit_samples}")
                    self.status_ready.emit(f"LEARNING samples={self.trainer.imit_samples}")
                    self.msleep(20)
                    continue

                if self.auto_focus and self.brain.steps % 8 == 0:
                    self.motor.focus_roblox()
                frame = self.vision.capture()
                sensory = self.vision.encode(frame)
                motor, info = self.brain.step(sensory)
                meta = self.vision.last_meta
                self.trainer.set_mode("reward")
                loom = float(meta.get("loom_score", 0.0))
                motion = float(meta.get("motion", 0.0))
                turn = float(motor[2] - motor[3]) if motor.size > 3 else 0.0
                fwd_drive = max(0.0, float(motor[0]) * 0.5 + 0.4)
                calm = max(0.0, 1.0 - loom - motion * 2)
                cread = self.circuit.step(loom=loom, forward_drive=fwd_drive, turn=turn, calm=calm)
                cbias = self.circuit.motor_bias(cread)
                motor, notes, binfo = self.behavior.modulate(motor, meta, circuit_bias=cbias)
                info.update(binfo)
                info.update(cread)
                actions = self.brain.decide(motor, threshold=0.16)
                junk = {"emote", "crouch", "chat_toggle"}
                if not any(t in notes for t in ("browse", "join_intent", "ui_scroll", "ui_select")):
                    junk |= {"ui_up", "ui_down", "ui_select"}
                actions = [a for a in actions if not a.startswith("look_") and a not in junk]
                if "ui_scroll" in notes and "ui_down" not in actions:
                    actions.append("ui_down")
                if "ui_select" in notes and "ui_select" not in actions:
                    actions.append("ui_select")
                if any(t in notes for t in ("explore", "rail", "seek_portal", "fight", "attack", "lock_in", "wander", "parkour", "patrol", "hunt", "forage")):
                    if "forward" not in actions:
                        actions.insert(0, "forward")
                    if "sprint" not in actions and any(t in notes for t in ("fight", "attack", "lock_in", "seek_portal")):
                        actions.append("sprint")
                if any(t in notes for t in ("attack", "fight", "lock_in")) and "secondary" not in actions:
                    actions.append("secondary")
                if "q_dash" in notes and "camera" not in actions:
                    actions.append("camera")
                if "e_slash" in notes and "interact" not in actions:
                    actions.append("interact")
                if "r_combo" in notes and "reset" not in actions:
                    actions.append("reset")
                if "e_slash" not in notes:
                    actions = [a for a in actions if a != "interact"]
                if "r_combo" not in notes:
                    actions = [a for a in actions if a != "reset"]
                if "q_dash" not in notes:
                    actions = [a for a in actions if a != "camera"]
                line = self.behavior.take_line()
                if line:
                    self.log_ready.emit(f"fly: {line}")
                try:
                    rew = self.trainer.online_step(notes, meta, motor)
                    if abs(rew) > 0.35 and self.brain.steps % 15 == 0:
                        self.log_ready.emit(f"train r={rew:+.2f} n={self.trainer.samples}")
                except Exception:
                    pass
                sent = self.motor.apply(actions, motor.tolist())
                chat = self.behavior.take_chat()
                if chat:
                    self.motor.type_text(chat)
                    sent.append(f'chat:"{chat}"')
                self.frame_ready.emit(frame)
                self.actions_ready.emit(actions)
                self.stats_ready.emit(info)
                self.motor_ready.emit({n: float(motor[i]) for i, n in enumerate(MOTOR_NAMES)}, actions)
                if sent:
                    self.log_ready.emit(f"-> {', '.join(sent)} | {','.join(notes)} | spk={info['n_spikes']}")
                self.status_ready.emit(
                    f"{binfo.get('combat_mode','?')} goal={binfo.get('goal','?')} power={binfo.get('power','?')} pain={binfo.get('pain',0):.2f}"
                )
            except Exception as e:
                self.log_ready.emit(f"error: {type(e).__name__}: {e}")
            dt = (time.perf_counter() - t0) * 1000.0
            self.msleep(max(1, int(28 - dt)))
        self.motor.release_all()
        self.vision.close()
        try:
            self.brain.save_weights(WEIGHTS_PATH)
        except Exception:
            pass
        input_lock.unlock()
        host_learn.stop()

    def start_fly(self) -> None:
        self.motor.resume()
        self.motor.focus_roblox()
        ok = input_lock.lock()
        self._paused = False
        self.log_ready.emit("START — autonomy" if ok else "START")

    def stop_fly(self) -> None:
        self._paused = True
        self.motor.release_all()
        input_lock.unlock()
        self.log_ready.emit("STOP")

    def emergency(self) -> None:
        self._paused = True
        self.motor.emergency_stop()
        input_lock.unlock()
        host_learn.stop()
        self.learning = False
        self.log_ready.emit("F9 emergency")

    def stop(self) -> None:
        self._running = False
        self.motor.release_all()
        input_lock.unlock()
        host_learn.stop()


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
        QFrame#panel {{ background:{BG_PANEL}; border:1px solid {BORDER}; border-radius:14px; }}
        QPushButton {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:10px; padding:10px 18px; font-weight:600; }}
        QPushButton:hover {{ border-color:{ACCENT}; }}
        QPushButton#startBtn {{ background:{SUCCESS}; color:#0B0E14; border:none; font-size:15px; min-width:130px; }}
        QPushButton#stopBtn {{ background:{DANGER}; color:white; border:none; font-size:15px; min-width:130px; }}
        QPushButton:disabled {{ color:{TEXT_SECONDARY}; }}
        QTextEdit {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:10px;
                     color:{TEXT_SECONDARY}; font-family:Consolas,monospace; font-size:12px; }}
        QLabel#title {{ color:{ACCENT}; font-size:18px; font-weight:700; letter-spacing:0.5px; }}
        QLabel#setupLbl {{ color:{TEXT_SECONDARY}; font-size:13px; padding:8px; }}
        QLabel#watchLbl {{ color:{DANGER}; font-size:13px; font-weight:700; padding:6px; }}
        QStatusBar {{ background:{BG_PANEL}; color:{TEXT_SECONDARY}; }}
        """

    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 10)
        root.setSpacing(10)
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
        self.btn_scare = QPushButton("SCARE")
        self.btn_scare.clicked.connect(self._on_scare)
        self.btn_scare.setVisible(False)
        ctrl.addWidget(self.btn_scare)
        self.btn_learn = QPushButton("LEARN FROM ME")
        self.btn_learn.setCheckable(True)
        self.btn_learn.clicked.connect(self._on_learn)
        self.btn_learn.setVisible(False)
        self.btn_learn.setStyleSheet(f"QPushButton:checked {{ background:{ACCENT}; color:#0B0E14; }}")
        ctrl.addWidget(self.btn_learn)
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
        self.mouse3d = Mouse3DWidget()
        rl.addWidget(self.mouse3d)
        self.stats_lbl = QLabel("waiting")
        rl.addWidget(self.stats_lbl)
        rl.addStretch()
        split.addWidget(right)
        split.setSizes([560, 400, 420])
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
        if self._setup_done or not (self._worker_ok and self._roblox_ok):
            return
        self._setup_done = True
        self.setup_lbl.setText("3072 neurons · kill→food gamble · death→hurt · LEARN trains · free will")
        self.setup_lbl.setStyleSheet(f"color:{SUCCESS}; font-size:13px; font-weight:600;")
        self.btn_start.setVisible(True)
        self.btn_stop.setVisible(True)
        self.btn_scare.setVisible(True)
        self.btn_learn.setVisible(True)
        self.btn_start.setEnabled(True)

    def _roblox_ready_for_play(self) -> bool:
        try:
            info = self.worker.vision.find_roblox_window_info()
        except Exception:
            info = None
        if not info:
            self.log_view.append("No Roblox window")
            return False
        self.log_view.append(f"Roblox window: {info.get('title')}")
        return True

    def _on_start(self) -> None:
        if not self._setup_done or self._flying:
            return
        if self.btn_learn.isChecked():
            self.btn_learn.setChecked(False)
            self._on_learn()
        if not is_roblox_running():
            launch_roblox(6.0)
        if not self._roblox_ready_for_play():
            return
        self.worker.start_fly()
        self._flying = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.watch_lbl.setText("AUTONOMY — kill rewards food · death hurts · STOP/F9")
        self.watch_lbl.setVisible(True)

    def _on_stop(self) -> None:
        if not self._flying:
            return
        self.worker.stop_fly()
        self._flying = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.watch_lbl.setVisible(False)

    def _on_scare(self) -> None:
        try:
            self.worker.behavior.scare()
            self.log_view.append("SCARE")
        except Exception as e:
            self.log_view.append(f"scare failed: {e}")

    def _on_learn(self) -> None:
        on = self.btn_learn.isChecked()
        if on:
            if self._flying:
                self.worker.stop_fly()
                self._flying = False
                self.btn_start.setEnabled(True)
                self.btn_stop.setEnabled(False)
                self.watch_lbl.setVisible(False)
            host_learn.start()
            self.worker.learning = True
            self.worker._paused = False
            self.btn_learn.setText("LEARNING… (stop)")
            self.log_view.append("LEARN ON — play; he copies keys")
        else:
            host_learn.stop()
            self.worker.learning = False
            self.worker._paused = True
            self.btn_learn.setText("LEARN FROM ME")
            self.log_view.append(f"LEARN OFF n={self.worker.trainer.imit_samples}")

    def _on_emergency(self) -> None:
        self.worker.emergency()
        self._flying = False
        self.btn_learn.setChecked(False)
        self.btn_learn.setText("LEARN FROM ME")
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
        try:
            self.mouse3d.set_delta(*self.worker.motor.last_mouse)
            self.mouse3d.set_buttons(lmb=("secondary" in a), rmb=False)
        except Exception:
            pass

    def _on_stats(self, info: dict) -> None:
        self.circuit_panel.set_rates(info)
        try:
            self.fly_kb.set_state(
                pain=float(info.get("pain", 0)),
                lock_in=bool(info.get("lock_in") or info.get("combat_mode") == "fight"),
            )
        except Exception:
            pass
        self.stats_lbl.setText(
            f"t={info.get('t_ms',0):.0f}ms steps={info.get('steps',0)}\n"
            f"spk={info.get('n_spikes',0)} rate={info.get('mean_rate',0):.3f}\n"
            f"pain={info.get('pain',0):.2f} anger={info.get('anger',0):.2f}\n"
            f"mode={info.get('combat_mode','?')} goal={info.get('goal','?')}\n"
            f"kills={info.get('loot_kills',0)} deaths={info.get('deaths',0)} food={info.get('loot_food',0)}\n"
            f"power={info.get('power','dormant')} x{info.get('power_mult',1):.2f} neurons=3072\n"
            f"drop={info.get('loot_last_drop','-')} train={self.worker.trainer.samples}"
        )

    def closeEvent(self, e) -> None:
        host_learn.stop()
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
