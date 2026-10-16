"""Deadpool kit + rail + portal. E is Air Slash, never a junk interact."""
from __future__ import annotations
from typing import Optional
import time
import numpy as np
from .config import MOTOR_NAMES, N_MOTOR


class BehaviorLayer:
    def __init__(self) -> None:
        self.fear = 0.0
        self.curiosity = 0.7
        self.arousal = 0.5
        self.pending_chat: Optional[str] = None
        self.pending_line: Optional[str] = None
        self.idx = {n: i for i, n in enumerate(MOTOR_NAMES)}
        self.manual_scare = False
        self._food_seen = False
        self.mode = "explore"
        self._flee_until = 0.0
        self._fight_until = 0.0
        self.flee_seconds = 1.1
        self.fight_seconds = 2.6
        self.cd_q = 0.0
        self.cd_e = 0.0
        self.cd_r = 0.0
        self.q_gap = 3.2
        self.e_gap = 2.4
        self.r_gap = 4.5
        self._rot = 0
        self.character = "deadpool"
        self._last_say = 0.0

    def scare(self) -> None:
        self.fear = 1.0
        self.manual_scare = True
        self.mode = "flee"
        self._flee_until = time.time() + self.flee_seconds
        self._say("scared. backing off, then I come back swinging.")

    def _say(self, line: str) -> None:
        now = time.time()
        if now - self._last_say < 1.6 and self.pending_line:
            return
        self.pending_line = line
        self._last_say = now

    def take_line(self) -> Optional[str]:
        line = self.pending_line
        self.pending_line = None
        return line

    def _zero_kit(self, m: np.ndarray) -> None:
        for name in ("interact", "reset", "camera"):
            m[self.idx[name]] = 0.0

    def _fire(self, m: np.ndarray, name: str) -> None:
        m[self.idx[name]] = 0.95

    def _kit(self, m: np.ndarray, now: float, fighting: bool) -> list:
        notes = []
        self._zero_kit(m)
        if not fighting:
            return notes
        order = ("camera", "interact", "reset")
        tags = ("q_dash", "e_slash", "r_combo")
        gaps = (self.q_gap, self.e_gap, self.r_gap)
        cds = [self.cd_q, self.cd_e, self.cd_r]
        i = self._rot % 3
        if now >= cds[i]:
            self._fire(m, order[i])
            notes.append(tags[i])
            if i == 0:
                self.cd_q = now + gaps[0]
                self._say("Q — Immortal Dash. closing the gap.")
            elif i == 1:
                self.cd_e = now + gaps[1]
                self._say("E — Air Slash. I only spend this in a fight.")
            else:
                self.cd_r = now + gaps[2]
                self._say("R — combo. that's the finisher, not a reset.")
            self._rot = (i + 1) % 3
        return notes

    def _steer(self, m: np.ndarray, cx: float, strength: float = 0.7) -> None:
        err = cx - 0.5
        if err > 0.06:
            m[self.idx["right"]] += strength * min(1.0, err * 3)
            m[self.idx["look_right"]] += 0.45 * min(1.0, err * 3)
            m[self.idx["left"]] -= 0.3
        elif err < -0.06:
            m[self.idx["left"]] += strength * min(1.0, -err * 3)
            m[self.idx["look_left"]] += 0.45 * min(1.0, -err * 3)
            m[self.idx["right"]] -= 0.3

    def modulate(self, motor, meta, circuit_bias=None):
        m = motor.astype(np.float32).copy()
        if m.size < N_MOTOR:
            pad = np.zeros(N_MOTOR, dtype=np.float32)
            pad[: m.size] = m
            m = pad
        if circuit_bias is not None:
            cb = np.asarray(circuit_bias, dtype=np.float32).ravel()
            n = min(N_MOTOR, cb.size)
            m[:n] = 0.35 * m[:n] + 0.65 * cb[:n]

        now = time.time()
        motion = float(meta.get("motion", 0.0))
        food = float(meta.get("food_score", 0.0))
        loom = float(meta.get("loom_score", 0.0))
        water = float(meta.get("water_score", 0.0))
        lobby = float(meta.get("lobby_score", 0.0))
        threat = float(meta.get("threat_score", 0.0))
        rail = float(meta.get("rail_score", 0.0))
        rail_cx = float(meta.get("rail_cx", 0.5))
        portal = float(meta.get("portal_score", 0.0))
        portal_cx = float(meta.get("portal_cx", 0.5))

        if water > 0.35:
            self.mode = "flee"
            m[self.idx["forward"]] -= 1.2
            m[self.idx["back"]] += 1.0
            m[self.idx["jump"]] += 0.55
            wx = float(meta.get("water_cx", 0.5))
            self._steer(m, 1.0 - wx, 0.8)
            self._zero_kit(m)
            notes = ["water_death"]
            self._say("water. that's death. I'm not walking in.")
            m = np.clip(m, -1.0, 1.0)
            return m, notes, self._info(notes, food, motion, loom, water, lobby, threat, rail, portal)

        if lobby > 0.45 and portal < 0.25:
            self.mode = "rail"
            m[self.idx["forward"]] += 0.55
            self._steer(m, rail_cx, 0.5)
            self._zero_kit(m)
            notes = ["leave_lobby"]
            self._say("lobby is outside. I'm not staying.")
            m = np.clip(m, -1.0, 1.0)
            return m, notes, self._info(notes, food, motion, loom, water, lobby, threat, rail, portal)

        if portal > 0.28:
            self.mode = "portal"
            m[self.idx["forward"]] += 0.75
            m[self.idx["sprint"]] += 0.25
            self._steer(m, portal_cx, 0.9)
            self._zero_kit(m)
            notes = ["seek_portal"]
            self._say("portal. combat world's through that. staying on it.")
            m = np.clip(m, -1.0, 1.0)
            return m, notes, self._info(notes, food, motion, loom, water, lobby, threat, rail, portal)

        if self.manual_scare:
            self.fear = 0.95
            self.manual_scare = False
            self.mode = "flee"
            self._flee_until = now + self.flee_seconds
        elif threat > 0.42 or loom > 0.55:
            self.fear = min(1.0, self.fear + 0.22 + 0.2 * threat)
            if self.mode in ("explore", "rail") and self.fear > 0.4:
                self.mode = "flee"
                self._flee_until = now + self.flee_seconds
                self._say("danger. I run, then I turn around and fight.")
        else:
            self.fear = max(0.0, self.fear - 0.08)

        if self.mode == "flee" and now >= self._flee_until:
            self.mode = "fight"
            self._fight_until = now + self.fight_seconds
            self._rot = 0
            self._say("back in. Q, then E, then R. that's the whole kit.")
        if self.mode == "fight" and now >= self._fight_until:
            self.mode = "rail" if rail > 0.2 else "explore"

        fighting = self.mode == "fight"
        if self.mode == "flee":
            m[self.idx["forward"]] -= 0.7
            m[self.idx["back"]] += 0.65
            m[self.idx["sprint"]] += 0.4
            m[self.idx["jump"]] += 0.2
            self._zero_kit(m)
            notes = ["flee", "scared"]
        elif fighting:
            m[self.idx["forward"]] += 0.65
            m[self.idx["sprint"]] += 0.3
            m[self.idx["jump"]] += 0.25
            m[self.idx["secondary"]] += 0.4
            notes = ["fight", "attack"]
            notes += self._kit(m, now, True)
        else:
            if rail > 0.18:
                self.mode = "rail"
                self._steer(m, rail_cx, 0.65)
                notes = ["rail"]
                self._say("on the rail. I follow it, I don't wander off.")
            else:
                self.mode = "explore"
                notes = ["explore"]
            m[self.idx["forward"]] += 0.42 * self.curiosity
            m[self.idx["sprint"]] += 0.08
            self._zero_kit(m)

        if food > 0.5 and not fighting:
            notes.append("food_seen")
            if not self._food_seen:
                self.pending_chat = "food"
                notes.append("chat_food")
                self._say("food. saying it once.")
            self._food_seen = True
        else:
            self._food_seen = False

        for name in ("chat_toggle", "ui_up", "ui_down", "ui_select", "emote"):
            if name == "chat_toggle" and self.pending_chat:
                continue
            m[self.idx[name]] = min(float(m[self.idx[name]]), 0.05)

        m = np.clip(m, -1.0, 1.0)
        return m, notes, self._info(notes, food, motion, loom, water, lobby, threat, rail, portal)

    def _info(self, notes, food, motion, loom, water, lobby, threat, rail, portal):
        return {
            "fear": self.fear, "curiosity": self.curiosity, "arousal": self.arousal,
            "notes": notes, "food_score": food, "motion": motion, "loom_score": loom,
            "water_score": water, "lobby_score": lobby, "threat_score": threat,
            "rail_score": rail, "portal_score": portal,
            "combat_mode": self.mode, "character": self.character, "rot": self._rot,
        }

    def take_chat(self):
        msg = self.pending_chat
        self.pending_chat = None
        return msg
