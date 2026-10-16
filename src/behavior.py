"""Instinct layer: fear, food chat, explore bias."""
from __future__ import annotations
import time
from typing import List, Tuple
import numpy as np
from .config import MOTOR_NAMES, N_MOTOR

class BehaviorLayer:
    def __init__(self) -> None:
        self.fear = 0.0
        self.hunger = 0.4
        self.curiosity = 0.5
        self._last_food_chat = 0.0
        self._food_cooldown = 8.0
        self.pending_chat: str | None = None
        self.idx = {n: i for i, n in enumerate(MOTOR_NAMES)}

    def modulate(self, motor: np.ndarray, meta: dict) -> Tuple[np.ndarray, List[str], dict]:
        m = motor.astype(np.float32).copy()
        if m.size < N_MOTOR:
            pad = np.zeros(N_MOTOR, dtype=np.float32)
            pad[: m.size] = m
            m = pad
        motion = float(meta.get("motion", 0.0))
        food = float(meta.get("food_score", 0.0))
        if motion > 0.12:
            self.fear = min(1.0, self.fear + 0.25)
        else:
            self.fear = max(0.0, self.fear - 0.04)
        notes = []
        if self.fear < 0.35:
            m[self.idx["forward"]] += 0.35 * self.curiosity
            m[self.idx["sprint"]] += 0.08 * self.curiosity
            notes.append("explore")
        else:
            m[self.idx["forward"]] -= 0.6
            m[self.idx["back"]] += 0.45 * self.fear
            m[self.idx["look_left"]] += 0.3 * self.fear
            m[self.idx["look_right"]] += 0.25 * self.fear
            m[self.idx["jump"]] += 0.15 * self.fear
            notes.append("scared")
        now = time.time()
        if food > 0.35:
            self.hunger = min(1.0, self.hunger + 0.05)
            m[self.idx["forward"]] += 0.4
            m[self.idx["interact"]] += 0.35
            notes.append("food_seen")
            if now - self._last_food_chat >= self._food_cooldown:
                self.pending_chat = "food"
                self._last_food_chat = now
                notes.append("chat_food")
        else:
            self.hunger = max(0.1, self.hunger - 0.01)
        for name in ("chat_toggle", "ui_up", "ui_down", "ui_select", "reset", "emote", "camera", "secondary"):
            i = self.idx[name]
            if name == "chat_toggle" and self.pending_chat:
                continue
            m[i] = min(m[i], 0.15)
        m = np.clip(m, -1.0, 1.0)
        info = {"fear": self.fear, "hunger": self.hunger, "curiosity": self.curiosity,
                "notes": notes, "food_score": food, "motion": motion}
        return m, notes, info

    def take_chat(self) -> str | None:
        msg = self.pending_chat
        self.pending_chat = None
        return msg
