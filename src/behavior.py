"""Instinct + circuit bias — no hunger, soft fear, keep moving."""
from __future__ import annotations
import time
from typing import List, Tuple, Optional
import numpy as np
from .config import MOTOR_NAMES, N_MOTOR


class BehaviorLayer:
    def __init__(self) -> None:
        self.fear = 0.0
        self.curiosity = 0.6
        self.arousal = 0.5
        self._last_food_chat = 0.0
        self._food_cooldown = 10.0
        self.pending_chat: Optional[str] = None
        self.idx = {n: i for i, n in enumerate(MOTOR_NAMES)}
        self.manual_scare = False

    def scare(self) -> None:
        self.fear = 1.0
        self.manual_scare = True

    def modulate(self, motor: np.ndarray, meta: dict,
                 circuit_bias: Optional[np.ndarray] = None) -> Tuple[np.ndarray, List[str], dict]:
        m = motor.astype(np.float32).copy()
        if m.size < N_MOTOR:
            pad = np.zeros(N_MOTOR, dtype=np.float32)
            pad[: m.size] = m
            m = pad
        if circuit_bias is not None:
            cb = np.asarray(circuit_bias, dtype=np.float32).ravel()
            n = min(N_MOTOR, cb.size)
            m[:n] = 0.5 * m[:n] + 0.5 * cb[:n]

        motion = float(meta.get("motion", 0.0))
        food = float(meta.get("food_score", 0.0))
        loom = float(meta.get("loom_score", 0.0))

        if self.manual_scare:
            self.fear = max(self.fear, 0.9)
            self.manual_scare = False
        elif motion > 0.15 or loom > 0.55:
            self.fear = min(1.0, self.fear + 0.15 + 0.25 * loom)
        else:
            self.fear = max(0.0, self.fear - 0.08)

        self.arousal = 0.85 * self.arousal + 0.15 * (0.4 + 0.4 * motion + 0.3 * loom)

        notes: List[str] = []
        m[self.idx["forward"]] += 0.25 * self.curiosity * (1.0 - 0.4 * self.fear)

        if self.fear >= 0.55:
            m[self.idx["back"]] += 0.35 * self.fear
            m[self.idx["jump"]] += 0.2 * self.fear
            m[self.idx["look_left"]] += 0.15 * self.fear
            m[self.idx["look_right"]] += 0.15 * self.fear
            notes.append("alert")
        else:
            m[self.idx["sprint"]] += 0.1 * self.curiosity
            notes.append("explore")

        now = time.time()
        if food > 0.4:
            m[self.idx["forward"]] += 0.25
            m[self.idx["interact"]] += 0.25
            notes.append("food_seen")
            if now - self._last_food_chat >= self._food_cooldown:
                self.pending_chat = "food"
                self._last_food_chat = now
                notes.append("chat_food")

        for name in ("chat_toggle", "ui_up", "ui_down", "ui_select", "reset", "emote", "camera", "secondary"):
            i = self.idx[name]
            if name == "chat_toggle" and self.pending_chat:
                continue
            m[i] = min(float(m[i]), 0.1)

        m = np.clip(m, -1.0, 1.0)
        info = {
            "fear": self.fear,
            "curiosity": self.curiosity,
            "arousal": self.arousal,
            "notes": notes,
            "food_score": food,
            "motion": motion,
            "loom_score": loom,
        }
        return m, notes, info

    def take_chat(self) -> Optional[str]:
        msg = self.pending_chat
        self.pending_chat = None
        return msg
