"""Multi-hero + lock-in combat + portal/rail first + no UI spam."""
from __future__ import annotations
from typing import Optional, List, Dict, Any
import time
import numpy as np
from .config import MOTOR_NAMES, N_MOTOR

CHAR_KITS: Dict[str, Dict[str, Any]] = {
    "deadpool": {
        "label": "Deadpool",
        "q": "Immortal Dash", "e": "Air Slash", "r": "Deadpool Combo",
        "q_gap": 1.8, "e_gap": 1.4, "r_gap": 2.6,
        "aggro": 0.95, "dodge_bias": 0.85, "melee": 0.8,
        "say_pick": "picking Deadpool. slash and dash.",
    },
    "batman": {
        "label": "Batman",
        "q": "Grapple", "e": "Batarang", "r": "Smoke Bomb",
        "q_gap": 1.6, "e_gap": 1.3, "r_gap": 3.0,
        "aggro": 0.7, "dodge_bias": 1.15, "melee": 0.65,
        "say_pick": "switching to Batman. stay mobile, throw, smoke.",
    },
    "war_machine": {
        "label": "War Machine",
        "q": "Jet Boost", "e": "Missile", "r": "Heavy Barrage",
        "q_gap": 1.7, "e_gap": 1.5, "r_gap": 2.4,
        "aggro": 1.15, "dodge_bias": 0.7, "melee": 0.85,
        "say_pick": "War Machine online. boost, missile, barrage.",
    },
}
CHAR_ORDER = ("deadpool", "batman", "war_machine")


class BehaviorLayer:
    def __init__(self) -> None:
        self.fear = 0.0
        self.pain = 0.0
        self.anger = 0.0
        self.weakness = 0.0
        self.curiosity = 0.8
        self.arousal = 0.5
        self.pending_chat = None
        self.pending_line = None
        self.idx = {n: i for i, n in enumerate(MOTOR_NAMES)}
        self.manual_scare = False
        self._food_seen = False
        self._danger_seen = False
        self._danger_now = False
        self._last_chat_at = 0.0
        self.mode = "explore"
        self._flee_until = 0.0
        self._fight_until = 0.0
        self.flee_seconds = 0.55
        self.fight_seconds = 4.5
        self.cd_q = self.cd_e = self.cd_r = 0.0
        self._rot = 0
        self._next_rot_at = 0.0
        self.character = "deadpool"
        self._char_i = 0
        self._last_switch = 0.0
        self.switch_cooldown = 18.0
        self._last_say = 0.0
        self._hist_motion = []
        self._hist_cx = []
        self._pred_side = 0.0
        self._last_dodge = 0.0
        self._hits = 0
        self.lock_in = False
        self.kit = CHAR_KITS[self.character]

    def _apply_char(self, name: str) -> None:
        if name not in CHAR_KITS:
            name = "deadpool"
        self.character = name
        self.kit = CHAR_KITS[name]
        self._char_i = CHAR_ORDER.index(name) if name in CHAR_ORDER else 0
        self.cd_q = self.cd_e = self.cd_r = 0.0
        self._rot = 0
        self._next_rot_at = 0.0
        self._say(self.kit["say_pick"])

    def maybe_switch_character(self, now: float):
        weak = self.pain > 0.72 or self.weakness > 0.75 or (self.fear > 0.85 and self.pain > 0.55)
        if not weak or now - self._last_switch < self.switch_cooldown:
            return None
        self._last_switch = now
        self._char_i = (self._char_i + 1) % len(CHAR_ORDER)
        name = CHAR_ORDER[self._char_i]
        self._apply_char(name)
        self.pain = max(0.15, self.pain * 0.45)
        self.weakness = max(0.0, self.weakness - 0.35)
        self.anger = min(1.0, self.anger + 0.2)
        return name

    def scare(self) -> None:
        self.fear = 1.0
        self.pain = min(1.0, self.pain + 0.35)
        self.weakness = min(1.0, self.weakness + 0.25)
        self.manual_scare = True
        self.mode = "flee"
        self._flee_until = time.time() + self.flee_seconds
        self._say("that hurt. backing off — then I lock in.")

    def _say(self, line: str) -> None:
        now = time.time()
        if now - self._last_say < 1.5 and self.pending_line:
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

    def _zero_junk(self, m):
        for name in ("chat_toggle", "ui_up", "ui_down", "ui_select", "emote", "crouch"):
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
        gaps = (float(self.kit["q_gap"]), float(self.kit["e_gap"]), float(self.kit["r_gap"]))
        cds = [self.cd_q, self.cd_e, self.cd_r]
        i = self._rot % 3
        if now >= cds[i]:
            self._fire(m, order[i])
            notes.append(tags[i])
            if i == 0:
                self.cd_q = now + gaps[0]
                self._say(f"Q — {self.kit['q']}.")
            elif i == 1:
                self.cd_e = now + gaps[1]
                self._say(f"E — {self.kit['e']}.")
            else:
                self.cd_r = now + gaps[2]
                self._say(f"R — {self.kit['r']}.")
            self._rot = (i + 1) % 3
            self._next_rot_at = now + 0.45
        return notes

    def _steer(self, m, cx: float, strength: float = 0.7) -> None:
        err = cx - 0.5
        if err > 0.05:
            m[self.idx["right"]] += strength * min(1.0, err * 3.2)
            m[self.idx["look_right"]] += 0.85 * min(1.0, err * 3.5)
            m[self.idx["left"]] = 0.0
        elif err < -0.05:
            m[self.idx["left"]] += strength * min(1.0, -err * 3.2)
            m[self.idx["look_left"]] += 0.85 * min(1.0, -err * 3.5)
            m[self.idx["right"]] = 0.0

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
        bias = float(self.kit.get("dodge_bias", 1.0))
        if pred * bias < 0.32:
            return notes
        dcx = self._hist_cx[-1] - self._hist_cx[0]
        side = 1.0 if dcx >= 0 else -1.0
        self._pred_side = side
        if now - self._last_dodge < 0.35:
            return notes
        self._last_dodge = now
        if side > 0:
            m[self.idx["left"]] += 0.95
            m[self.idx["look_left"]] += 0.4
            notes.append("dodge_left")
        else:
            m[self.idx["right"]] += 0.95
            m[self.idx["look_right"]] += 0.4
            notes.append("dodge_right")
        m[self.idx["jump"]] += 0.25
        notes.append("predict_dodge")
        self.pain = min(1.0, self.pain + 0.08)
        self.anger = min(1.0, self.anger + 0.2)
        self._say("dodge.")
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
            m[:n] = 0.25 * m[:n] + 0.75 * cb[:n]
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
        hit = max(0.0, loom - 0.5) + max(0.0, threat - 0.4)
        if hit > 0:
            self.pain = min(1.0, self.pain + hit * 0.5)
            self.anger = min(1.0, self.anger + hit * 0.4)
            self.weakness = min(1.0, self.weakness + hit * 0.25)
            self._hits += 1
        else:
            self.pain = max(0.0, self.pain - 0.03)
            self.anger = max(0.0, self.anger - 0.018)
            self.weakness = max(0.0, self.weakness - 0.012)
        switched = self.maybe_switch_character(now)
        notes = []
        if switched:
            notes.append(f"switch_{switched}")

        if portal > 0.18:
            self.mode = "portal"
            m[self.idx["forward"]] = 0.95
            m[self.idx["sprint"]] = 0.6
            m[self.idx["back"]] = 0.0
            m[self.idx["jump"]] = 0.0
            self._steer(m, portal_cx, 1.0)
            self._zero_kit(m)
            self._zero_junk(m)
            notes += ["seek_portal"]
            self._say("portal — following it.")
            return np.clip(m, -1, 1), notes, self._info(notes, food, motion, loom, water, lobby, threat, rail, portal)

        if rail > 0.15:
            self.mode = "rail"
            m[self.idx["forward"]] = 0.9
            m[self.idx["sprint"]] = 0.45
            m[self.idx["back"]] = 0.0
            m[self.idx["jump"]] = 0.0
            self._steer(m, rail_cx, 0.9)
            self._zero_kit(m)
            self._zero_junk(m)
            notes += ["rail"]
            return np.clip(m, -1, 1), notes, self._info(notes, food, motion, loom, water, lobby, threat, rail, portal)

        if water > 0.55:
            self.mode = "flee"
            m[self.idx["forward"]] = 0.0
            m[self.idx["back"]] = 0.7
            m[self.idx["jump"]] = 0.15
            self._steer(m, 1.0 - float(meta.get("water_cx", 0.5)), 0.7)
            self._zero_kit(m)
            self._zero_junk(m)
            notes += ["water_death"]
            self._say("water — step back.")
            return np.clip(m, -1, 1), notes, self._info(notes, food, motion, loom, water, lobby, threat, rail, portal)

        if lobby > 0.45:
            self.mode = "rail"
            m[self.idx["forward"]] = 0.75
            self._steer(m, 0.5, 0.4)
            self._zero_kit(m)
            self._zero_junk(m)
            notes += ["leave_lobby"]
            return np.clip(m, -1, 1), notes, self._info(notes, food, motion, loom, water, lobby, threat, rail, portal)

        if self.manual_scare:
            self.fear = 0.95
            self.manual_scare = False
            self.mode = "flee"
            self._flee_until = now + self.flee_seconds
        elif threat > 0.35 or loom > 0.45:
            self.fear = min(1.0, self.fear + 0.2 + 0.15 * threat)
            if self.mode in ("explore", "rail") and self.fear > 0.5 and self.pain < 0.3:
                self.mode = "flee"
                self._flee_until = now + self.flee_seconds
                self._say("hit — run then lock in.")
                self.lock_in = False
        else:
            self.fear = max(0.0, self.fear - 0.1)

        danger_level = max(threat, loom * 0.9)
        self._danger_now = danger_level > 0.38
        if self.mode == "flee" and now >= self._flee_until:
            self.mode = "fight"
            self._fight_until = now + self.fight_seconds * (1.0 + 0.5 * self.anger)
            self._rot = 0
            self.lock_in = True
            self._say(f"locked in as {self.kit['label']}.")
        if self.mode == "fight" and now >= self._fight_until and not (self.pain > 0.4 or threat > 0.4):
            self.mode = "explore"
            self.lock_in = False

        if self._danger_now:
            notes.append("danger")
            if not self._danger_seen:
                self._say("danger")
                if now - self._last_chat_at > 5.0:
                    self.pending_chat = "danger"
                    notes.append("chat_danger")
                    self._last_chat_at = now
                self._danger_seen = True
        else:
            self._danger_seen = False

        if threat > 0.25 or loom > 0.35:
            notes += self._predict_and_dodge(m, meta, now)

        fighting = self.mode == "fight"
        aggro = float(self.kit["aggro"])
        melee = float(self.kit["melee"])

        self.lock_in = self.pain > 0.35 or self.anger > 0.4 or threat > 0.35
        if self.lock_in and self.mode in ("explore", "rail", "portal", "flee"):
            self.mode = "fight"
            self._fight_until = max(self._fight_until, now + 2.8)
            fighting = True
            notes.append("lock_in")

        if self.mode == "flee" and not self.lock_in:
            m[self.idx["forward"]] = 0.0
            m[self.idx["back"]] = 0.55
            m[self.idx["sprint"]] = 0.45
            m[self.idx["jump"]] = 0.1
            self._zero_kit(m)
            notes += ["flee", "scared"]
        elif fighting or self.lock_in:
            self.mode = "fight"
            push = (0.8 + 0.4 * self.anger) * max(aggro, 0.9)
            m[self.idx["forward"]] = min(1.0, push)
            m[self.idx["sprint"]] = min(1.0, 0.6 + 0.3 * self.anger)
            m[self.idx["jump"]] = 0.05
            m[self.idx["secondary"]] = max(melee, 0.8)
            notes += ["fight", "attack"]
            if self.lock_in:
                notes.append("lock_in")
            if self.anger > 0.4:
                notes.append("angry")
            if self.pain > 0.3:
                notes.append("pain")
            notes += self._kit(m, now, True)
        else:
            self.mode = "explore"
            notes += ["explore"]
            m[self.idx["forward"]] = 0.75 * self.curiosity
            m[self.idx["sprint"]] = 0.4
            m[self.idx["jump"]] = 0.0
            self._zero_kit(m)

        if food > 0.5 and not fighting:
            notes.append("food_seen")
            if not self._food_seen:
                if now - self._last_chat_at > 5.0:
                    self.pending_chat = "food"
                    notes.append("chat_food")
                    self._last_chat_at = now
            self._food_seen = True
        else:
            self._food_seen = False

        self._zero_junk(m)
        return np.clip(m, -1, 1), notes, self._info(notes, food, motion, loom, water, lobby, threat, rail, portal)

    def _info(self, notes, food, motion, loom, water, lobby, threat, rail, portal):
        return {
            "fear": self.fear, "pain": self.pain, "anger": self.anger,
            "weakness": self.weakness, "curiosity": self.curiosity, "arousal": self.arousal,
            "notes": notes, "food_score": food, "motion": motion, "loom_score": loom,
            "water_score": water, "lobby_score": lobby, "threat_score": threat,
            "rail_score": rail, "portal_score": portal,
            "combat_mode": self.mode, "character": self.character,
            "char_label": self.kit["label"], "rot": self._rot, "pred_side": self._pred_side,
            "hits": self._hits, "lock_in": self.lock_in,
        }
