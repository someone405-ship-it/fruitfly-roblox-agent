"""
Motor decoder — turns brain motor scores into real keyboard / mouse events.

On Windows prefers pyrobloxbot when available; falls back to pydirectinput.
"""

from __future__ import annotations

import time
from typing import List, Optional, Set

from .config import MOTOR_NAMES

# optional heavy deps
try:
    import pydirectinput
    pydirectinput.FAILSAFE = True
    pydirectinput.PAUSE = 0.01
except ImportError:
    pydirectinput = None

try:
    import pyrobloxbot as prb
except ImportError:
    prb = None


# map action name → key or special handler
KEY_MAP = {
    "forward": "w",
    "back": "s",
    "left": "a",
    "right": "d",
    "jump": "space",
    "sprint": "shift",
    "interact": "e",
    "chat_toggle": "/",
    "ui_up": "up",
    "ui_down": "down",
    "ui_select": "enter",
    "reset": "r",
}


class MotorController:
    def __init__(self) -> None:
        self.active: Set[str] = set()
        self.last_look = (0.0, 0.0)
        self.enabled = True
        self.use_pyroblox = prb is not None

    def apply(self, actions: List[str], motor_scores: Optional[list] = None) -> List[str]:
        """
        Press / release keys so that only the given actions are held.
        Returns the list of actions that were actually sent.
        """
        if not self.enabled or pydirectinput is None:
            return []

        desired = set(actions)
        sent: List[str] = []

        # release keys no longer wanted
        for name in list(self.active):
            if name not in desired and name in KEY_MAP:
                key = KEY_MAP[name]
                try:
                    pydirectinput.keyUp(key)
                except Exception:
                    pass
                self.active.discard(name)

        # press new keys
        for name in desired:
            if name in KEY_MAP and name not in self.active:
                key = KEY_MAP[name]
                try:
                    pydirectinput.keyDown(key)
                    self.active.add(name)
                    sent.append(name)
                except Exception:
                    pass

        # mouse look (relative)
        if motor_scores is not None and len(motor_scores) >= 10:
            dx = 0.0
            dy = 0.0
            # look_left / look_right / look_up / look_down are indices 6-9
            dx -= float(motor_scores[6]) * 8.0
            dx += float(motor_scores[7]) * 8.0
            dy -= float(motor_scores[8]) * 6.0
            dy += float(motor_scores[9]) * 6.0
            if abs(dx) > 0.5 or abs(dy) > 0.5:
                try:
                    pydirectinput.moveRel(int(dx), int(dy), relative=True)
                    sent.append(f"look({dx:.1f},{dy:.1f})")
                except Exception:
                    pass

        return sent

    def release_all(self) -> None:
        if pydirectinput is None:
            return
        for name in list(self.active):
            if name in KEY_MAP:
                try:
                    pydirectinput.keyUp(KEY_MAP[name])
                except Exception:
                    pass
        self.active.clear()

    def emergency_stop(self) -> None:
        self.enabled = False
        self.release_all()

    def resume(self) -> None:
        self.enabled = True
