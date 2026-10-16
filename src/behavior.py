"""Deadpool kit + rail/portal + pain/anger + predict/dodge."""
from __future__ import annotations
from typing import Optional, List
import time
import numpy as np
from .config import MOTOR_NAMES, N_MOTOR


class BehaviorLayer:
    def __init__(self) -> None:
        self.fear = 0.0
        self.pain = 0.0
        self.anger = 0.0
        self.curiosity = 0.75
        self.arousal = 0.5
        self.pending_chat: Optional[str] = None
        self.pending_line: Optional[str] = None
        self.idx = {n: i for i, n in enumerate(MOTOR_NAMES)}
        self.manual_scare = False
        self._food_seen = False
        self.mode = "explore"
        self._flee_until = 0.0
        self._fight_until = 0.0
        self.flee_seconds = 0.85
        self.fight_seconds = 3.0
        self.cd_q = self.cd_e = self.cd_r = 0.0
        self.q_gap, self.e_gap, self.r_gap = 3.0, 2.2, 4.2
        self._rot = 0
        self._next_rot_at = 0.0
        self.character = "deadpool"
        self._last_say = 0.0
        self._hist_motion: List[float] = []
        self._hist_cx: List[float] = []
        self._pred_side = 0.0
        self._last_dodge = 0.0

    def scare(self) -> None:
        self.fear = 1.0
        self.pain = min(1.0, self.pain + 0.35)
        self.manual_scare = True
        self.mode = "flee"
        self._flee_until = time.time() + self.flee_seconds
        self._say("that hurt. backing off — then I come in angry.")

    def _say(self, line: str) -> None:
        now = time.time()
        if now - self._last_say < 1.2 and self.pending_line:
            return
        self.pending_line = line
        self._last_say = now

    def take_line(self):
        line = self.pending_line
        self.pending_line = None
        return line

    def take_chat(self):
        msg = self.pending_chat
        self.pending_chat = None
        return msg

    def _zero_kit(self, m):
        for name in ("interact", "reset", "camera"):
            m[self.idx[name]] = 0.0

    def _fire(self, m, name: str) -> None:
        m[self.idx[name]] = 0.95

    def _kit(self, m, now: float, fighting: bool):
        notes = []
        self._zero_kit(m)
        if not fighting or now < self._next_rot_at:
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
                self._say("Q — Immortal Dash. gap closed.")
            elif i == 1:
                self.cd_e = now + gaps[1]
                self._say("E — Air Slash. fight only.")
            else:
                self.cd_r = now + gaps[2]
                self._say("R — Deadpool Combo. finisher.")
            self._rot = (i + 1) % 3
            self._next_rot_at = now + 0.85
        return notes

    def _steer(self, m, cx: float, strength: float = 0.7) -> None:
        err = cx - 0.5
        if err > 0.05:
            m[self.idx["right"]] += strength * min(1.0, err * 3.2)
            m[self.idx["look_right"]] += 0.5 * min(1.0, err * 3.2)
            m[self.idx["left"]] -= 0.35
        elif err < -0.05:
            m[self.idx["left"]] += strength * min(1.0, -err * 3.2)
            m[self.idx["look_left"]] += 0.5 * min(1.0, -err * 3.2)
            m[self.idx["right"]] -= 0.35

    def _predict_and_dodge(self, m, meta, now):
        notes = []
        motion = float(meta.get("motion", 0.0))
        loom = float(meta.get("loom_score", 0.0))
        threat = float(meta.get("threat_score", 0.0))
        cx = float(meta.get("threat_cx", meta.get("portal_cx", 0.5)))
        self._hist_motion.append(motion)
        self._hist_cx.append(cx)
        if len(self._hist_motion) > 8:
            self._hist_motion.pop(0)
            self._hist_cx.pop(0)
        if len(self._hist_motion) < 3:
            return notes
        dm = self._hist_motion[-1] - self._hist_motion[0]
        pred = loom * 0.5 + threat * 0.4 + max(0.0, dm) * 2.0
        if pred < 0.35:
            return notes
        dcx = self._hist_cx[-1] - self._hist_cx[0]
        side = 1.0 if dcx >= 0 else -1.0
        self._pred_side = side
        if now - self._last_dodge < 0.45:
            return notes
        self._last_dodge = now
        if side > 0:
            m[self.idx["left"]] += 0.9
            m[self.idx["look_left"]] += 0.35
            notes.append("dodge_left")
        else:
            m[self.idx["right"]] += 0.9
            m[self.idx["look_right"]] += 0.35
            notes.append("dodge_right")
        m[self.idx["jump"]] += 0.55
        m[self.idx["forward"]] -= 0.15
        notes.append("predict_dodge")
        self.pain = min(1.0, self.pain + 0.12)
        self.anger = min(1.0, self.anger + 0.18)
        self._say("I see it coming. dodge.")
        return notes

    def modulate(self, motor, meta, circuit_bias=None):
        m = motor.astype(np.float32).copy()
        if m.size < N_MOTOR:
            pad = np.zeros(N_MOTOR, dtype=np.float32)
            pad[: m.size] = m
            m = pad
        if circuit_bias is not None:
            cb = np.asarray(circuit_bias, dtype=np.float32).ravel()
            n = min(N_MOTOR, cb.size)
            m[:n] = 0.3 * m[:n] + 0.7 * cb[:n]
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
        hit = max(0.0, loom - 0.55) + max(0.0, threat - 0.5)
        if hit > 0:
            self.pain = min(1.0, self.pain + hit * 0.45)
            self.anger = min(1.0, self.anger + hit * 0.35)
        else:
            self.pain = max(0.0, self.pain - 0.04)
            self.anger = max(0.0, self.anger - 0.025)
        if water > 0.35:
            self.mode = "flee"
            m[self.idx["forward"]] -= 1.2
            m[self.idx["back"]] += 1.0
            m[self.idx["jump"]] += 0.55
            self._steer(m, 1.0 - float(meta.get("water_cx", 0.5)), 0.85)
            self._zero_kit(m)
            notes = ["water_death"]
            self._say("water is death. not walking in.")
            return np.clip(m, -1, 1), notes, self._info(notes, food, motion, loom, water, lobby, threat, rail, portal)
        if lobby > 0.45 and portal < 0.25:
            self.mode = "rail"
            m[self.idx["forward"]] += 0.6
            self._steer(m, rail_cx, 0.55)
            self._zero_kit(m)
            notes = ["leave_lobby"]
            self._say("lobby is outside. moving.")
            return np.clip(m, -1, 1), notes, self._info(notes, food, motion, loom, water, lobby, threat, rail, portal)
        if portal > 0.28:
            self.mode = "portal"
            m[self.idx["forward"]] += 0.8
            m[self.idx["sprint"]] += 0.3
            self._steer(m, portal_cx, 0.95)
            self._zero_kit(m)
            notes = ["seek_portal"]
            self._say("portal. combat world is through there.")
            return np.clip(m, -1, 1), notes, self._info(notes, food, motion, loom, water, lobby, threat, rail, portal)
        if self.manual_scare:
            self.fear = 0.95
            self.manual_scare = False
            self.mode = "flee"
            self._flee_until = now + self.flee_seconds
        elif threat > 0.4 or loom > 0.5:
            self.fear = min(1.0, self.fear + 0.25 + 0.2 * threat)
            if self.mode in ("explore", "rail") and (self.fear > 0.35 or self.pain > 0.4):
                self.mode = "flee"
                self._flee_until = now + self.flee_seconds
                self._say("hit me once. I run, then I fight angry.")
        else:
            self.fear = max(0.0, self.fear - 0.08)
        if self.mode == "flee" and now >= self._flee_until:
            self.mode = "fight"
            self._fight_until = now + self.fight_seconds * (1.0 + 0.4 * self.anger)
            self._rot = 0
            self._say("back in. Q, E, R. that's the whole kit.")
        if self.mode == "fight" and now >= self._fight_until:
            self.mode = "rail" if rail > 0.2 else "explore"
        notes = []
        if threat > 0.25 or loom > 0.35:
            notes += self._predict_and_dodge(m, meta, now)
        fighting = self.mode == "fight"
        if self.mode == "flee":
            m[self.idx["forward"]] -= 0.65
            m[self.idx["back"]] += 0.7
            m[self.idx["sprint"]] += 0.45
            m[self.idx["jump"]] += 0.25
            self._zero_kit(m)
            notes += ["flee", "scared"]
        elif fighting:
            push = 0.55 + 0.35 * self.anger
            m[self.idx["forward"]] += push
            m[self.idx["sprint"]] += 0.25 + 0.2 * self.anger
            m[self.idx["jump"]] += 0.2
            m[self.idx["secondary"]] += 0.45
            notes += ["fight", "attack"]
            if self.anger > 0.55:
                notes.append("angry")
            if self.pain > 0.4:
                notes.append("pain")
            notes += self._kit(m, now, True)
        else:
            if rail > 0.18:
                self.mode = "rail"
                self._steer(m, rail_cx, 0.7)
                notes += ["rail"]
                self._say("on the rail. stay on it.")
            else:
                self.mode = "explore"
                notes += ["explore"]
            m[self.idx["forward"]] += 0.45 * self.curiosity
            m[self.idx["sprint"]] += 0.1
            self._zero_kit(m)
        if food > 0.5 and not fighting:
            notes.append("food_seen")
            if not self._food_seen:
                self.pending_chat = "food"
                notes.append("chat_food")
            self._food_seen = True
        else:
            self._food_seen = False
        for name in ("chat_toggle", "ui_up", "ui_down", "ui_select", "emote"):
            if name == "chat_toggle" and self.pending_chat:
                continue
            m[self.idx[name]] = min(float(m[self.idx[name]]), 0.04)
        return np.clip(m, -1, 1), notes, self._info(notes, food, motion, loom, water, lobby, threat, rail, portal)

    def _info(self, notes, food, motion, loom, water, lobby, threat, rail, portal):
        return {
            "fear": self.fear, "pain": self.pain, "anger": self.anger,
            "curiosity": self.curiosity, "arousal": self.arousal,
            "notes": notes, "food_score": food, "motion": motion, "loom_score": loom,
            "water_score": water, "lobby_score": lobby, "threat_score": threat,
            "rail_score": rail, "portal_score": portal,
            "combat_mode": self.mode, "character": self.character, "rot": self._rot,
            "pred_side": self._pred_side,
        }
