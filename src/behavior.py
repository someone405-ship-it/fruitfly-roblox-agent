"""Instincts: water=death, lobby=out, fight-or-flight combat cycle."""
from __future__ import annotations
from typing import List, Tuple, Optional
import time
import numpy as np
from .config import MOTOR_NAMES, N_MOTOR


class BehaviorLayer:
    def __init__(self) -> None:
        self.fear = 0.0
        self.curiosity = 0.65
        self.arousal = 0.5
        self.pending_chat: Optional[str] = None
        self.idx = {n: i for i, n in enumerate(MOTOR_NAMES)}
        self.manual_scare = False
        self._food_seen = False
        self.mode = "explore"
        self._flee_until = 0.0
        self._fight_until = 0.0
        self._last_threat = 0.0
        self.flee_seconds = 1.4
        self.fight_seconds = 2.2
        self.water_danger = 0.0
        self.lobby_score = 0.0

    def scare(self) -> None:
        self.fear = 1.0
        self.manual_scare = True
        self.mode = "flee"
        self._flee_until = time.time() + self.flee_seconds

    def modulate(self, motor: np.ndarray, meta: dict,
                 circuit_bias: Optional[np.ndarray] = None):
        m = motor.astype(np.float32).copy()
        if m.size < N_MOTOR:
            pad = np.zeros(N_MOTOR, dtype=np.float32)
            pad[: m.size] = m
            m = pad
        if circuit_bias is not None:
            cb = np.asarray(circuit_bias, dtype=np.float32).ravel()
            n = min(N_MOTOR, cb.size)
            m[:n] = 0.4 * m[:n] + 0.6 * cb[:n]

        now = time.time()
        motion = float(meta.get("motion", 0.0))
        food = float(meta.get("food_score", 0.0))
        loom = float(meta.get("loom_score", 0.0))
        water = float(meta.get("water_score", 0.0))
        lobby = float(meta.get("lobby_score", 0.0))
        threat = float(meta.get("threat_score", 0.0))
        self.water_danger = water
        self.lobby_score = lobby

        if water > 0.35:
            m[self.idx["forward"]] -= 1.2
            m[self.idx["back"]] += 1.0
            m[self.idx["jump"]] += 0.6
            m[self.idx["sprint"]] += 0.5
            wx = float(meta.get("water_cx", 0.5))
            if wx < 0.45:
                m[self.idx["right"]] += 0.7
                m[self.idx["look_right"]] += 0.4
            elif wx > 0.55:
                m[self.idx["left"]] += 0.7
                m[self.idx["look_left"]] += 0.4
            else:
                m[self.idx["back"]] += 0.4
            notes = ["water_death"]
            m = np.clip(m, -1.0, 1.0)
            return m, notes, self._info(notes, food, motion, loom, water, lobby, threat)

        if lobby > 0.4:
            m[self.idx["forward"]] += 0.5
            m[self.idx["ui_select"]] = min(m[self.idx["ui_select"]], 0.05)
            m[self.idx["back"]] -= 0.3
            notes = ["leave_lobby"]
            m = np.clip(m, -1.0, 1.0)
            return m, notes, self._info(notes, food, motion, loom, water, lobby, threat)

        if self.manual_scare:
            self.fear = max(self.fear, 0.95)
            self.manual_scare = False
            self.mode = "flee"
            self._flee_until = now + self.flee_seconds
        elif loom > 0.5 or threat > 0.4 or motion > 0.18:
            self.fear = min(1.0, self.fear + 0.2 + 0.25 * loom + 0.2 * threat)
            self._last_threat = now
            if self.mode == "explore" and self.fear > 0.45:
                self.mode = "flee"
                self._flee_until = now + self.flee_seconds
        else:
            self.fear = max(0.0, self.fear - 0.07)

        self.arousal = 0.85 * self.arousal + 0.15 * (0.4 + 0.4 * motion + 0.3 * threat)

        if self.mode == "flee" and now >= self._flee_until:
            self.mode = "fight"
            self._fight_until = now + self.fight_seconds
            self.fear = max(0.2, self.fear * 0.5)
        if self.mode == "fight" and now >= self._fight_until:
            self.mode = "explore"

        notes = [self.mode]
        if self.mode == "flee":
            m[self.idx["forward"]] -= 0.8
            m[self.idx["back"]] += 0.7
            m[self.idx["sprint"]] += 0.5
            m[self.idx["jump"]] += 0.25
            m[self.idx["look_left"]] += 0.25
            m[self.idx["look_right"]] += 0.25
            notes.append("scared")
        elif self.mode == "fight":
            m[self.idx["forward"]] += 0.7
            m[self.idx["sprint"]] += 0.35
            m[self.idx["jump"]] += 0.45
            m[self.idx["interact"]] += 0.5
            m[self.idx["secondary"]] += 0.55
            notes.append("attack")
        else:
            m[self.idx["forward"]] += 0.4 * self.curiosity
            m[self.idx["sprint"]] += 0.1 * self.curiosity
            notes.append("explore")

        if food > 0.45:
            m[self.idx["forward"]] += 0.25
            m[self.idx["interact"]] += 0.2
            notes.append("food_seen")
            if not self._food_seen:
                self.pending_chat = "food"
                notes.append("chat_food")
            self._food_seen = True
        else:
            self._food_seen = False

        for name in ("chat_toggle", "ui_up", "ui_down", "ui_select", "reset", "emote", "camera"):
            i = self.idx[name]
            if name == "chat_toggle" and self.pending_chat:
                continue
            m[i] = min(float(m[i]), 0.08)

        m = np.clip(m, -1.0, 1.0)
        return m, notes, self._info(notes, food, motion, loom, water, lobby, threat)

    def _info(self, notes, food, motion, loom, water, lobby, threat):
        return {
            "fear": self.fear, "curiosity": self.curiosity, "arousal": self.arousal,
            "notes": notes, "food_score": food, "motion": motion, "loom_score": loom,
            "water_score": water, "lobby_score": lobby, "threat_score": threat,
            "combat_mode": self.mode,
        }

    def take_chat(self):
        msg = self.pending_chat
        self.pending_chat = None
        return msg
