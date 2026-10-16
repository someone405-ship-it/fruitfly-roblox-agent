"""Motor decoder — clamped look, no corner slam, safe key holds."""
from __future__ import annotations
from typing import List, Optional, Set
import time

try:
    import pydirectinput
    pydirectinput.FAILSAFE = False
    pydirectinput.PAUSE = 0.0
except ImportError:
    pydirectinput = None

try:
    import pygetwindow as gw
except ImportError:
    gw = None

KEY_MAP = {
    "forward": "w", "back": "s", "left": "a", "right": "d",
    "jump": "space", "sprint": "shift", "interact": "e",
    "chat_toggle": "/", "ui_up": "up", "ui_down": "down",
    "ui_select": "enter", "reset": "r", "crouch": "ctrl",
    "emote": "b", "camera": "f", "secondary": None,
}
PULSE_ACTIONS = {"chat_toggle", "interact", "reset", "emote", "camera", "ui_select", "secondary"}


class MotorController:
    def __init__(self) -> None:
        self.active: Set[str] = set()
        self.enabled = True
        self.last_sent: List[str] = []
        self.look_sensitivity = 4.0
        self.look_deadzone = 0.45
        self.max_look_px = 12
        self._last_pulse: dict = {}
        self._pulse_cooldown = 1.2
        self._last_look_t = 0.0
        self._look_interval = 0.05

    def focus_roblox(self) -> bool:
        if gw is None:
            return False
        try:
            wins = [w for w in gw.getAllWindows()
                    if w.title and "roblox" in w.title.lower()
                    and "fruitfly" not in w.title.lower()]
            if not wins:
                return False
            w = max(wins, key=lambda x: max(0, x.width) * max(0, x.height))
            if w.width < 80:
                return False
            if w.isMinimized:
                w.restore()
            w.activate()
            return True
        except Exception:
            return False

    def apply(self, actions: List[str], motor_scores: Optional[list] = None) -> List[str]:
        if not self.enabled or pydirectinput is None:
            return []
        now = time.time()
        desired = set(actions)
        sent: List[str] = []
        for name in list(self.active):
            if name not in desired and name in KEY_MAP and KEY_MAP[name]:
                try:
                    pydirectinput.keyUp(KEY_MAP[name])
                except Exception:
                    pass
                self.active.discard(name)
        for name in desired:
            key = KEY_MAP.get(name)
            if not key:
                continue
            if name in PULSE_ACTIONS:
                last = self._last_pulse.get(name, 0.0)
                if now - last < self._pulse_cooldown:
                    continue
                try:
                    pydirectinput.press(key)
                    self._last_pulse[name] = now
                    sent.append(name)
                except Exception:
                    pass
                continue
            if name not in self.active:
                try:
                    pydirectinput.keyDown(key)
                    self.active.add(name)
                    sent.append(name)
                except Exception:
                    pass
        if motor_scores is not None and len(motor_scores) >= 10:
            if now - self._last_look_t >= self._look_interval:
                ll, lr = float(motor_scores[6]), float(motor_scores[7])
                lu, ld = float(motor_scores[8]), float(motor_scores[9])
                raw_x, raw_y = (-ll + lr), (-lu + ld)
                if abs(raw_x) < self.look_deadzone:
                    raw_x = 0.0
                if abs(raw_y) < self.look_deadzone:
                    raw_y = 0.0
                dx = int(max(-self.max_look_px, min(self.max_look_px, raw_x * self.look_sensitivity)))
                dy = int(max(-self.max_look_px, min(self.max_look_px, raw_y * self.look_sensitivity * 0.8)))
                if dx != 0 or dy != 0:
                    try:
                        pydirectinput.moveRel(dx, dy, relative=True)
                        sent.append(f"look({dx},{dy})")
                        self._last_look_t = now
                    except Exception:
                        pass
        if "secondary" in desired:
            last = self._last_pulse.get("secondary", 0.0)
            if now - last >= self._pulse_cooldown:
                try:
                    pydirectinput.click(button="right")
                    self._last_pulse["secondary"] = now
                    sent.append("secondary")
                except Exception:
                    pass
        self.last_sent = sent
        return sent

    def type_text(self, text: str) -> None:
        if not self.enabled or pydirectinput is None:
            return
        try:
            pydirectinput.press("/")
            time.sleep(0.15)
            pydirectinput.typewrite(text, interval=0.04)
            time.sleep(0.05)
            pydirectinput.press("enter")
        except Exception:
            pass

    def release_all(self) -> None:
        if pydirectinput is None:
            return
        for name in list(self.active):
            key = KEY_MAP.get(name)
            if key:
                try:
                    pydirectinput.keyUp(key)
                except Exception:
                    pass
        self.active.clear()

    def emergency_stop(self) -> None:
        self.enabled = False
        self.release_all()

    def resume(self) -> None:
        self.enabled = True
