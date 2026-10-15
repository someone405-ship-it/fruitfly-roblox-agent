"""Advanced motor decoder — expanded action set + focus helper."""

from __future__ import annotations

from typing import List, Optional, Set

try:
    import pydirectinput
    pydirectinput.FAILSAFE = True
    pydirectinput.PAUSE = 0.008
except ImportError:
    pydirectinput = None

try:
    import pygetwindow as gw
except ImportError:
    gw = None

from .config import MOTOR_NAMES

KEY_MAP = {
    "forward": "w", "back": "s", "left": "a", "right": "d",
    "jump": "space", "sprint": "shift", "interact": "e",
    "chat_toggle": "/", "ui_up": "up", "ui_down": "down",
    "ui_select": "enter", "reset": "r", "crouch": "ctrl",
    "emote": "b", "camera": "f", "secondary": None,
}


class MotorController:
    def __init__(self) -> None:
        self.active: Set[str] = set()
        self.enabled = True
        self.last_sent: List[str] = []
        self.look_sensitivity = 10.0

    def focus_roblox(self) -> bool:
        if gw is None:
            return False
        try:
            wins = [w for w in gw.getAllWindows() if w.title and "roblox" in w.title.lower()]
            if not wins:
                return False
            w = max(wins, key=lambda x: x.width * x.height)
            if w.isMinimized:
                w.restore()
            w.activate()
            return True
        except Exception:
            return False

    def apply(self, actions: List[str], motor_scores: Optional[list] = None) -> List[str]:
        if not self.enabled or pydirectinput is None:
            return []
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
            if key and name not in self.active:
                try:
                    pydirectinput.keyDown(key)
                    self.active.add(name)
                    sent.append(name)
                except Exception:
                    pass
        if motor_scores is not None and len(motor_scores) >= 10:
            dx = (-float(motor_scores[6]) + float(motor_scores[7])) * self.look_sensitivity
            dy = (-float(motor_scores[8]) + float(motor_scores[9])) * (self.look_sensitivity * 0.75)
            if abs(dx) > 0.4 or abs(dy) > 0.4:
                try:
                    pydirectinput.moveRel(int(dx), int(dy), relative=True)
                    sent.append(f"look({dx:.0f},{dy:.0f})")
                except Exception:
                    pass
        if "secondary" in desired:
            try:
                pydirectinput.click(button="right")
                sent.append("secondary")
            except Exception:
                pass
        self.last_sent = sent
        return sent

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
