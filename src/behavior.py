"""Autonomy behavior — free-will goals, kits, instincts, human-like roam."""
from __future__ import annotations
from typing import Dict, Any, List
import time
import math
import numpy as np
from .config import MOTOR_NAMES, N_MOTOR
from .instincts import InstinctCore

CHAR_KITS: Dict[str, Dict[str, Any]] = {
    "deadpool": {
        "label": "Deadpool", "q": "Immortal Dash", "e": "Air Slash", "r": "Deadpool Combo",
        "q_gap": 1.6, "e_gap": 1.3, "r_gap": 2.4, "aggro": 0.95, "dodge_bias": 0.85, "melee": 0.85,
        "say_pick": "Deadpool. messy and fast.",
    },
    "batman": {
        "label": "Batman", "q": "Grapple", "e": "Batarang", "r": "Smoke Bomb",
        "q_gap": 1.5, "e_gap": 1.2, "r_gap": 2.8, "aggro": 0.7, "dodge_bias": 1.1, "melee": 0.7,
        "say_pick": "Batman. quiet and precise.",
    },
    "war_machine": {
        "label": "War Machine", "q": "Jet Boost", "e": "Missile", "r": "Heavy Barrage",
        "q_gap": 1.5, "e_gap": 1.4, "r_gap": 2.2, "aggro": 1.1, "dodge_bias": 0.7, "melee": 0.9,
        "say_pick": "War Machine. heavy pressure.",
    },
}
CHAR_ORDER = ("deadpool", "batman", "war_machine")

LINES = {
    "explore": ("walking. seeing what is out there.", "no plan — just feet moving.", "new angle."),
    "wander": ("drifting.", "why not that way.", "open space."),
    "parkour": ("up.", "timing the jump.", "keep moving vertical."),
    "fight": ("closing in.", "pressure.", "do not freeze."),
    "hunt": ("found motion. chasing.", "on them."),
    "flee": ("space. now.", "reset angle."),
    "portal": ("through.", "portal is the door."),
    "rail": ("path. stay on it.", "trail holds."),
    "browse": ("looking for a game.", "scrolling experiences.", "maybe a different map."),
    "rejoin": ("back into a match.", "finding play."),
    "social": ("say something.", "noise check."),
    "forage": ("color pop — check it.", "something shiny."),
    "rest": ("breathe.", "hold."),
    "patrol": ("loop the area.", "sweep."),
    "camera_look": ("check corners.", "look around."),
}


class BehaviorLayer:
    def __init__(self) -> None:
        self.instinct = InstinctCore(seed=11)
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
        self.flee_seconds = 0.5
        self.fight_seconds = 5.0
        self.cd_q = self.cd_e = self.cd_r = 0.0
        self._rot = 0
        self._next_rot_at = 0.0
        self.character = "deadpool"
        self._char_i = 0
        self._last_switch = 0.0
        self.switch_cooldown = 16.0
        self._last_say = 0.0
        self._hist_motion: List[float] = []
        self._hist_cx: List[float] = []
        self._pred_side = 0.0
        self._last_dodge = 0.0
        self._hits = 0
        self.lock_in = False
        self.kit = CHAR_KITS[self.character]
        self.autonomy = True
        self._line_i = 0
        self.goal = "explore"
        self.features_active = 42

    def _apply_char(self, name: str) -> None:
        if name not in CHAR_KITS:
            name = "deadpool"
        self.character = name
        self.kit = CHAR_KITS[name]
        self._char_i = CHAR_ORDER.index(name) if name in CHAR_ORDER else 0
        self.cd_q = self.cd_e = self.cd_r = 0.0
        self._rot = 0
        self._say(self.kit["say_pick"])

    def maybe_switch_character(self, now: float):
        weak = self.pain > 0.7 or self.weakness > 0.7
        if not weak or now - self._last_switch < self.switch_cooldown:
            return None
        self._last_switch = now
        self._char_i = (self._char_i + 1) % len(CHAR_ORDER)
        self._apply_char(CHAR_ORDER[self._char_i])
        self.pain *= 0.5
        self.weakness *= 0.6
        return self.character

    def scare(self) -> None:
        self.fear = 1.0
        self.pain = min(1.0, self.pain + 0.35)
        self.manual_scare = True
        self.mode = "flee"
        self._flee_until = time.time() + self.flee_seconds
        self._say("hurt — reset then lock in.")

    def _say(self, line: str) -> None:
        now = time.time()
        if now - self._last_say < 1.4 and self.pending_line:
            return
        self.pending_line = line
        self._last_say = now

    def take_line(self):
        line, self.pending_line = self.pending_line, None
        return line

    def take_chat(self):
        msg, self.pending_chat = self.pending_chat, None
        return msg

    def _zero_kit(self, m):
        for n in ("interact", "reset", "camera"):
            m[self.idx[n]] = 0.0

    def _zero_junk(self, m):
        for n in ("chat_toggle", "ui_up", "ui_down", "ui_select", "emote", "crouch"):
            m[self.idx[n]] = 0.0

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
            if i == 0: self.cd_q = now + gaps[0]
            elif i == 1: self.cd_e = now + gaps[1]
            else: self.cd_r = now + gaps[2]
            self._rot = (i + 1) % 3
            self._next_rot_at = now + 0.4
            self._say(f"{tags[i]} — {self.kit['label']}")
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
        cx = float(meta.get("threat_cx", 0.5))
        self._hist_motion.append(motion)
        self._hist_cx.append(cx)
        if len(self._hist_motion) > 8:
            self._hist_motion.pop(0); self._hist_cx.pop(0)
        if len(self._hist_motion) < 3:
            return notes
        dm = self._hist_motion[-1] - self._hist_motion[0]
        pred = loom * 0.5 + threat * 0.4 + max(0.0, dm) * 2.0
        if pred * float(self.kit.get("dodge_bias", 1.0)) < 0.3:
            return notes
        if now - self._last_dodge < 0.32:
            return notes
        self._last_dodge = now
        side = 1.0 if (self._hist_cx[-1] - self._hist_cx[0]) >= 0 else -1.0
        if side > 0:
            m[self.idx["left"]] += 0.95; notes.append("dodge_left")
        else:
            m[self.idx["right"]] += 0.95; notes.append("dodge_right")
        notes.append("predict_dodge")
        self.anger = min(1.0, self.anger + 0.15)
        return notes

    def _line_for(self, goal: str) -> None:
        opts = LINES.get(goal, ("…",))
        self._line_i = (self._line_i + 1) % len(opts)
        self._say(opts[self._line_i])

    def modulate(self, motor, meta, circuit_bias=None):
        m = motor.astype(np.float32).copy()
        if m.size < N_MOTOR:
            pad = np.zeros(N_MOTOR, dtype=np.float32)
            pad[:m.size] = m
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

        hit = max(0.0, loom - 0.48) + max(0.0, threat - 0.38)
        if hit > 0:
            self.pain = min(1.0, self.pain + hit * 0.5)
            self.anger = min(1.0, self.anger + hit * 0.42)
            self.weakness = min(1.0, self.weakness + hit * 0.22)
            self._hits += 1
        else:
            self.pain = max(0.0, self.pain - 0.028)
            self.anger = max(0.0, self.anger - 0.016)
            self.weakness = max(0.0, self.weakness - 0.01)

        self.instinct.observe_vision(meta, motion)
        self.curiosity = self.instinct.curiosity
        switched = self.maybe_switch_character(now)
        notes: List[str] = []
        if switched:
            notes.append(f"switch_{switched}")

        goal = self.instinct.pick_goal(meta, self.pain, self.anger, self.mode)
        if lobby > 0.5 and threat < 0.4 and portal < 0.2:
            goal = "browse"
        elif portal > 0.2 and goal in ("explore", "wander", "portal", "rail", "browse"):
            goal = "portal"
        elif rail > 0.2 and goal in ("explore", "wander", "rail") and portal < 0.2:
            goal = "rail"
        self.goal = goal
        notes.append(f"goal:{goal}")

        allow_ui = False
        if goal == "portal":
            self.mode = "portal"
            m[self.idx["forward"]] = 0.95
            m[self.idx["sprint"]] = 0.65
            m[self.idx["back"]] = 0.0
            self._steer(m, portal_cx, 1.0)
            self._zero_kit(m)
            notes += ["seek_portal"]
            self.instinct.reward_goal("portal", True)
            self._line_for("portal")
        elif goal == "rail":
            self.mode = "rail"
            m[self.idx["forward"]] = 0.9
            m[self.idx["sprint"]] = 0.5
            self._steer(m, rail_cx, 0.9)
            self._zero_kit(m)
            notes += ["rail"]
            self.instinct.reward_goal("rail", True)
            self._line_for("rail")
        elif goal == "flee" or water > 0.55:
            self.mode = "flee"
            m[self.idx["forward"]] = 0.0
            m[self.idx["back"]] = 0.7
            m[self.idx["sprint"]] = 0.5
            m[self.idx["jump"]] = 0.15
            if water > 0.4:
                self._steer(m, 1.0 - float(meta.get("water_cx", 0.5)), 0.8)
                notes += ["water_death"]
            notes += ["flee"]
            self._zero_kit(m)
            self._line_for("flee")
        elif goal in ("fight", "hunt") or (self.pain > 0.35 and threat > 0.25):
            self.mode = "fight"
            self.lock_in = True
            push = (0.85 + 0.4 * self.anger) * max(float(self.kit["aggro"]), 0.9)
            m[self.idx["forward"]] = min(1.0, push)
            m[self.idx["sprint"]] = min(1.0, 0.65 + 0.25 * self.anger)
            m[self.idx["secondary"]] = max(float(self.kit["melee"]), 0.85)
            if threat > 0.3:
                if int(now * 2) % 2 == 0:
                    m[self.idx["left"]] += 0.35
                else:
                    m[self.idx["right"]] += 0.35
            notes += ["fight", "attack", "lock_in"]
            if self.anger > 0.4: notes.append("angry")
            if self.pain > 0.3: notes.append("pain")
            notes += self._kit(m, now, True)
            notes += self._predict_and_dodge(m, meta, now)
            self.instinct.reward_goal("fight", True)
            self._line_for("fight")
        elif goal in ("browse", "rejoin") or lobby > 0.55:
            self.mode = "browse"
            allow_ui = True
            m[self.idx["forward"]] = 0.15
            phase = int((now * 1.2) % 6)
            self._zero_kit(m)
            if phase in (0, 1):
                m[self.idx["ui_down"]] = 0.9
                notes.append("ui_scroll")
            elif phase == 2:
                m[self.idx["ui_up"]] = 0.5
            elif phase == 3:
                m[self.idx["ui_select"]] = 0.9
                notes.append("ui_select")
            elif phase == 4:
                m[self.idx["look_left"]] = 0.3
            else:
                m[self.idx["look_right"]] = 0.3
            notes += ["browse", "join_intent"]
            self.instinct.reward_goal("browse", lobby > 0.3)
            self._line_for("browse")
        elif goal == "parkour":
            self.mode = "explore"
            m[self.idx["forward"]] = 0.85
            m[self.idx["sprint"]] = 0.7
            m[self.idx["jump"]] = 0.75 if int(now * 3) % 3 == 0 else 0.1
            notes += ["parkour"]
            self._zero_kit(m)
            self._line_for("parkour")
        elif goal == "camera_look":
            lx, ly = self.instinct.look_wander()
            if lx > 0: m[self.idx["look_right"]] = abs(lx)
            else: m[self.idx["look_left"]] = abs(lx)
            if ly > 0: m[self.idx["look_down"]] = abs(ly)
            else: m[self.idx["look_up"]] = abs(ly)
            m[self.idx["forward"]] = 0.2
            notes += ["camera_look"]
            self._zero_kit(m)
            self._line_for("camera_look")
        elif goal == "social":
            m[self.idx["forward"]] = 0.25
            if now - self._last_chat_at > 8.0:
                self.pending_chat = str(np.random.choice(["yo", "hi", "ggs", "run", "ok"]))
                notes.append("chat_social")
                self._last_chat_at = now
            notes += ["social"]
            self._zero_kit(m)
            self._line_for("social")
        elif goal == "forage" or food > 0.55:
            m[self.idx["forward"]] = 0.7
            notes += ["forage", "food_seen"]
            if not self._food_seen and now - self._last_chat_at > 5.0:
                self.pending_chat = "food"
                notes.append("chat_food")
                self._last_chat_at = now
            self._food_seen = food > 0.55
            self._zero_kit(m)
            self._line_for("forage")
        elif goal == "rest":
            m[self.idx["forward"]] = 0.05
            m[self.idx["jump"]] = 0.0
            notes += ["rest"]
            self._zero_kit(m)
            self.instinct.fatigue = max(0.0, self.instinct.fatigue - 0.05)
            self._line_for("rest")
        elif goal == "patrol":
            m[self.idx["forward"]] = 0.7
            m[self.idx["sprint"]] = 0.3
            t = math.sin(now * 0.4)
            if t > 0:
                m[self.idx["right"]] = 0.45; m[self.idx["look_right"]] = 0.3
            else:
                m[self.idx["left"]] = 0.45; m[self.idx["look_left"]] = 0.3
            notes += ["patrol"]
            self._zero_kit(m)
            self._line_for("patrol")
        else:
            self.mode = "explore"
            m[self.idx["forward"]] = 0.75 + 0.15 * self.curiosity
            m[self.idx["sprint"]] = 0.45
            lx, ly = self.instinct.look_wander()
            if abs(lx) > 0.2:
                if lx > 0:
                    m[self.idx["look_right"]] = abs(lx) * 0.5; m[self.idx["right"]] = 0.2
                else:
                    m[self.idx["look_left"]] = abs(lx) * 0.5; m[self.idx["left"]] = 0.2
            notes += ["explore", "wander"]
            self._zero_kit(m)
            self.instinct.reward_goal("explore", motion > 0.02)
            self._line_for("explore")

        self._danger_now = max(threat, loom * 0.9) > 0.4
        if self._danger_now:
            notes.append("danger")
            if not self._danger_seen:
                self._say("danger")
                if now - self._last_chat_at > 6.0:
                    self.pending_chat = "danger"
                    notes.append("chat_danger")
                    self._last_chat_at = now
                self._danger_seen = True
        else:
            self._danger_seen = False

        if not allow_ui:
            self._zero_junk(m)
        else:
            for n in ("emote", "crouch", "chat_toggle"):
                m[self.idx[n]] = 0.0

        snap = self.instinct.snapshot()
        return np.clip(m, -1, 1), notes, self._info(notes, food, motion, loom, water, lobby, threat, rail, portal, snap)

    def _info(self, notes, food, motion, loom, water, lobby, threat, rail, portal, snap):
        return {
            "fear": self.fear, "pain": self.pain, "anger": self.anger,
            "weakness": self.weakness, "curiosity": self.curiosity, "arousal": self.arousal,
            "notes": notes, "food_score": food, "motion": motion, "loom_score": loom,
            "water_score": water, "lobby_score": lobby, "threat_score": threat,
            "rail_score": rail, "portal_score": portal,
            "combat_mode": self.mode, "character": self.character,
            "char_label": self.kit["label"], "rot": self._rot, "pred_side": self._pred_side,
            "hits": self._hits, "lock_in": self.lock_in, "goal": self.goal,
            "features": self.features_active,
            **{f"drv_{k}": v for k, v in snap.items() if isinstance(v, (int, float))},
        }
