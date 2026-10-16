"""Instinct + circuit bias layer."""
from __future__ import annotations
import time
from typing import List, Tuple, Optional
import numpy as np
from .config import MOTOR_NAMES, N_MOTOR

class BehaviorLayer:
    def __init__(self) -> None:
        self.fear = 0.0
        self.hunger = 0.4
        self.curiosity = 0.55
        self._last_food_chat = 0.0
        self._food_cooldown = 8.0
        self.pending_chat: Optional[str] = None
        self.idx = {n: i for i, n in enumerate(MOTOR_NAMES)}

    def modulate(self, motor: np.ndarray, meta: dict, circuit_bias: Optional[np.ndarray] = None) -> Tuple[np.ndarray, List[str], dict]:
        m = motor.astype(np.float32).copy()
        if m.size < N_MOTOR:
            pad = np.zeros(N_MOTOR, dtype=np.float32)
            pad[: m.size] = m
            m = pad
        if circuit_bias is not None:
            cb = np.asarray(circuit_bias, dtype=np.float32).ravel()
            if cb.size >= N_MOTOR:
                m = 0.55 * m + 0.45 * cb[:N_MOTOR]
            else:
                m[: cb.size] += 0.45 * cb
        motion = float(meta.get("motion", 0.0))
        food = float(meta.get("food_score", 0.0))
        loom = float(meta.get("loom_score", 0.0))
        if motion > 0.12 or loom > 0.45:
            self.fear = min(1.0, self.fear + 0.2 + 0.3 * loom)
        else:
            self.fear = max(0.0, self.fear - 0.035)
        notes = []
        if self.fear < 0.35:
            m[self.idx["forward"]] += 0.3 * self.curiosity
            notes.append("explore")
        else:
            m[self.idx["forward"]] -= 0.5
            m[self.idx["back"]] += 0.4 * self.fear
            m[self.idx["jump"]] += 0.25 * self.fear
            notes.append("scared")
        now = time.time()
        if food > 0.35:
            self.hunger = min(1.0, self.hunger + 0.05)
            m[self.idx["forward"]] += 0.35
            m[self.idx["interact"]] += 0.3
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
            m[i] = min(m[i], 0.12)
        m = np.clip(m, -1.0, 1.0)
        info = {"fear": self.fear, "hunger": self.hunger, "curiosity": self.curiosity,
                "notes": notes, "food_score": food, "motion": motion, "loom_score": loom}
        return m, notes, info

    def take_chat(self) -> Optional[str]:
        msg = self.pending_chat
        self.pending_chat = None
        return msg
