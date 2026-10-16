"""Autonomy — portal-first, leave/join self, explore, combat gate."""
from __future__ import annotations
from typing import Dict, Any, List
import time
import numpy as np
from .config import MOTOR_NAMES, N_MOTOR
from .instincts import InstinctCore
from .loot import KillLootSystem

CHAR_KITS: Dict[str, Dict[str, Any]] = {
    "deadpool": {
        "label": "Deadpool", "q": "Immortal Dash", "e": "Air Slash", "r": "Deadpool Combo",
        "q_gap": 1.2, "e_gap": 1.0, "r_gap": 1.9, "aggro": 0.95, "dodge_bias": 0.85, "melee": 0.88,
        "say_pick": "Deadpool. messy and fast.",
    },
    "batman": {
        "label": "Batman", "q": "Grapple", "e": "Batarang", "r": "Smoke Bomb",
        "q_gap": 1.2, "e_gap": 0.95, "r_gap": 2.2, "aggro": 0.7, "dodge_bias": 1.1, "melee": 0.75,
        "say_pick": "Batman. quiet and precise.",
    },
    "war_machine": {
        "label": "War Machine", "q": "Jet Boost", "e": "Missile", "r": "Heavy Barrage",
        "q_gap": 1.15, "e_gap": 1.1, "r_gap": 1.85, "aggro": 1.1, "dodge_bias": 0.7, "melee": 0.92,
        "say_pick": "War Machine. heavy pressure.",
    },
}
CHAR_ORDER = ("deadpool", "batman", "war_machine")


class BehaviorLayer:
    def __init__(self) -> None:
        self.instinct = InstinctCore(seed=11)
        self.loot = KillLootSystem(seed=21)
        self.fear = self.pain = self.anger = self.weakness = 0.0
        self.curiosity = 0.85
        self.arousal = 0.5
        self.pending_chat = None
        self.pending_line = None
        self.idx = {n: i for i, n in enumerate(MOTOR_NAMES)}
        self.manual_scare = False
        self._last_chat_at = 0.0
        self.mode = "explore"
        self._flee_until = 0.0
        self.cd_q = self.cd_e = self.cd_r = 0.0
        self._rot = 0
        self._next_rot_at = 0.0
        self.character = "deadpool"
        self._char_i = 0
        self._last_switch = 0.0
        self.switch_cooldown = 14.0
        self._last_say = 0.0
        self._hist_motion: List[float] = []
        self._hist_cx: List[float] = []
        self._last_dodge = 0.0
        self._hits = 0
        self._deaths = 0
        self.lock_in = False
        self.kit = CHAR_KITS[self.character]
        self.goal = "explore"
        self.features_active = 96
        self._last_kill_at = 0.0
        self._last_death_at = 0.0
        self._pending_kill_notes: List[str] = []
        self._portal_seek_streak = 0
        # leave / join autonomy
        self._leave_until = 0.0
        self._join_phase = 0
        self._join_until = 0.0
        self._bored_leave_at = time.time() + 90.0
        self._last_escape_at = 0.0

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
        if not (self.pain > 0.7 or self.weakness > 0.7) or now - self._last_switch < self.switch_cooldown:
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
        self._flee_until = time.time() + 0.5
        self._say("hurt — reset then lock in.")

    def _say(self, line: str) -> None:
        now = time.time()
        if now - self._last_say < 1.0 and self.pending_line:
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

    def _zero_combat(self, m):
        m[self.idx["secondary"]] = 0.0
        self._zero_kit(m)

    def _fire(self, m, name: str) -> None:
        m[self.idx[name]] = 0.98

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
            self._next_rot_at = now + 0.28
        return notes

    def _steer(self, m, cx: float, strength: float = 0.8) -> None:
        err = cx - 0.5
        if err > 0.035:
            m[self.idx["right"]] += strength * min(1.0, err * 3.8)
            m[self.idx["look_right"]] += 1.0 * min(1.0, err * 4.0)
            m[self.idx["left"]] = 0.0
        elif err < -0.035:
            m[self.idx["left"]] += strength * min(1.0, -err * 3.8)
            m[self.idx["look_left"]] += 1.0 * min(1.0, -err * 4.0)
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
        if pred * float(self.kit.get("dodge_bias", 1.0)) < 0.28 or now - self._last_dodge < 0.22:
            return notes
        self._last_dodge = now
        side = 1.0 if (self._hist_cx[-1] - self._hist_cx[0]) >= 0 else -1.0
        if side > 0:
            m[self.idx["left"]] += 0.98; notes.append("dodge_left")
        else:
            m[self.idx["right"]] += 0.98; notes.append("dodge_right")
        notes.append("predict_dodge")
        self.anger = min(1.0, self.anger + 0.12)
        return notes

    def modulate(self, motor, meta, circuit_bias=None):
        m = motor.astype(np.float32).copy()
        if m.size < N_MOTOR:
            pad = np.zeros(N_MOTOR, dtype=np.float32)
            pad[:m.size] = m
            m = pad
        if circuit_bias is not None:
            cb = np.asarray(circuit_bias, dtype=np.float32).ravel()
            n = min(N_MOTOR, cb.size)
            m[:n] = 0.22 * m[:n] + 0.78 * cb[:n]

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
        kill_event = bool(meta.get("kill_event", False))
        death_event = bool(meta.get("death_event", False))
        portal_passed = bool(meta.get("portal_passed", False))
        portal_event = bool(meta.get("portal_event", False))

        if portal_passed or portal_event:
            self.instinct.in_arena = True
            self.instinct.portal_locked_until = now + 90.0
            self._say("portal — arena.")
            self.instinct.reward_goal("portal", True)
            self._bored_leave_at = now + 120.0

        if kill_event and (now - self._last_kill_at) > 1.0:
            self._last_kill_at = now
            ev = self.loot.on_kill()
            self._pending_kill_notes = ["kill", f"loot:{ev['drop']}"]
            if ev["heal"] > 0:
                self.pain = max(0.0, self.pain - ev["heal"])
            self.anger = min(1.0, self.anger + 0.12)
            self._say(f"kill → {ev['drop']}")
            self.instinct.reward_goal("fight", True)

        if death_event and (now - self._last_death_at) > 2.0:
            self._last_death_at = now
            self._deaths += 1
            self.pain = min(1.0, self.pain + 0.5)
            self.fear = min(1.0, self.fear + 0.35)
            self._say("died — leaving / rejoin.")
            self.instinct.in_arena = False
            # after death: leave menu path
            self._leave_until = now + 2.5
            self._join_until = now + 12.0
            self._join_phase = 0

        hit = max(0.0, loom - 0.48) + max(0.0, threat - 0.38)
        if hit > 0 and self.instinct.in_arena:
            self.pain = min(1.0, self.pain + hit * 0.45)
            self.anger = min(1.0, self.anger + hit * 0.4)
            self._hits += 1
        else:
            self.pain = max(0.0, self.pain - 0.03)
            self.anger = max(0.0, self.anger - 0.018)
            self.weakness = max(0.0, self.weakness - 0.01)

        self.instinct.observe_vision(meta, motion)
        self.curiosity = self.instinct.curiosity
        switched = self.maybe_switch_character(now)
        notes: List[str] = []
        if switched:
            notes.append(f"switch_{switched}")
        if self._pending_kill_notes:
            notes += self._pending_kill_notes
            self._pending_kill_notes = []

        in_arena = bool(self.instinct.in_arena)
        notes.append("in_arena" if in_arena else "need_portal")

        # voluntary leave when bored / high pain
        if in_arena and now > self._bored_leave_at and (self.pain > 0.55 or self.instinct.boredom > 0.7):
            self._leave_until = now + 2.0
            self._join_until = now + 14.0
            self._join_phase = 0
            self.instinct.in_arena = False
            self._bored_leave_at = now + 150.0
            self._say("leaving — find new game.")

        # LEAVE sequence: ESC
        if now < self._leave_until:
            self.mode = "leave"
            self._zero_combat(m)
            if now - self._last_escape_at > 0.55:
                m[self.idx["escape"]] = 0.98
                self._last_escape_at = now
            notes += ["leave", "escape_menu"]
            goal = "leave"
            self.goal = goal
            notes.append(f"goal:{goal}")
            snap = self.instinct.snapshot()
            info = self._info(notes, meta, motion, food, loom, water, lobby, threat, rail, portal, in_arena, snap)
            return np.clip(m, -1, 1), notes, info

        # JOIN / browse sequence: scroll + select
        if now < self._join_until and not in_arena:
            self.mode = "join"
            self._zero_combat(m)
            phase = int((now * 2.2) % 8)
            if phase in (0, 1, 2):
                m[self.idx["scroll_down"]] = 0.95
                notes.append("scroll_down")
            elif phase in (3, 4):
                m[self.idx["ui_down"]] = 0.9
                notes.append("ui_scroll")
            elif phase == 5:
                m[self.idx["ui_select"]] = 0.95
                notes.append("ui_select")
            elif phase == 6:
                m[self.idx["secondary"]] = 0.7  # click join
                notes.append("click_join")
            notes += ["join_game", "self_join", "browse"]
            if lobby > 0.3:
                notes.append("lobby")
            goal = "join"
            self.goal = goal
            notes.append(f"goal:{goal}")
            snap = self.instinct.snapshot()
            info = self._info(notes, meta, motion, food, loom, water, lobby, threat, rail, portal, in_arena, snap)
            return np.clip(m, -1, 1), notes, info

        goal = self.instinct.pick_goal(meta, self.pain, self.anger, self.mode)

        if not in_arena:
            if portal > 0.08:
                goal = "portal"
            elif lobby > 0.4:
                goal = "browse"
            elif rail > 0.25:
                goal = "rail"
            else:
                if goal in ("fight", "hunt", "patrol"):
                    goal = "explore"
            self._zero_combat(m)

        if lobby > 0.5 and threat < 0.25 and portal < 0.15 and not in_arena:
            goal = "browse"
        elif portal > 0.12 and not in_arena:
            goal = "portal"

        self.goal = goal
        notes.append(f"goal:{goal}")
        allow_ui = False

        if goal == "portal":
            self.mode = "portal"
            self._portal_seek_streak += 1
            m[self.idx["forward"]] = 0.99
            m[self.idx["sprint"]] = 0.82
            self._steer(m, portal_cx, 1.2)
            pcy = float(meta.get("portal_cy", 0.5))
            if pcy < 0.4:
                m[self.idx["look_up"]] += 0.6
            elif pcy > 0.65:
                m[self.idx["look_down"]] += 0.5
            m[self.idx["rmb_look"]] = 0.8
            self._zero_combat(m)
            notes += ["seek_portal", "portal_safe"]
            if portal > 0.35:
                notes.append("portal_close")
                if int(now * 5) % 4 == 0:
                    m[self.idx["jump"]] = 0.75
        elif goal == "rail":
            self.mode = "rail"
            m[self.idx["forward"]] = 0.94
            m[self.idx["sprint"]] = 0.6
            self._steer(m, rail_cx, 1.0)
            self._zero_combat(m)
            notes += ["rail"]
        elif goal == "flee" or water > 0.55 or (now < self._flee_until):
            self.mode = "flee"
            m[self.idx["forward"]] = 0.0
            m[self.idx["back"]] = 0.8
            m[self.idx["sprint"]] = 0.6
            if water > 0.4:
                self._steer(m, 1.0 - float(meta.get("water_cx", 0.5)), 0.9)
                notes += ["water_death"]
            notes += ["flee"]
            self._zero_kit(m)
        elif goal in ("fight", "hunt") and in_arena:
            self.mode = "fight"
            self.lock_in = True
            push = (0.9 + 0.4 * self.anger) * max(float(self.kit["aggro"]), 0.9)
            m[self.idx["forward"]] = min(1.0, push)
            m[self.idx["sprint"]] = min(1.0, 0.75 + 0.25 * self.anger)
            m[self.idx["secondary"]] = max(float(self.kit["melee"]), 0.9)
            if threat > 0.28:
                if int(now * 4) % 2 == 0:
                    m[self.idx["left"]] += 0.45
                else:
                    m[self.idx["right"]] += 0.45
            m[self.idx["rmb_look"]] = 0.65
            notes += ["fight", "attack", "lock_in"]
            notes += self._kit(m, now, True)
            notes += self._predict_and_dodge(m, meta, now)
        elif goal in ("browse", "rejoin") or (lobby > 0.55 and not in_arena):
            self.mode = "browse"
            allow_ui = True
            m[self.idx["forward"]] = 0.1
            phase = int((now * 1.6) % 7)
            self._zero_combat(m)
            if phase in (0, 1):
                m[self.idx["scroll_down"]] = 0.9; notes.append("scroll_down")
            elif phase in (2, 3):
                m[self.idx["ui_down"]] = 0.9; notes.append("ui_scroll")
            elif phase == 4:
                m[self.idx["ui_select"]] = 0.9; notes.append("ui_select")
            elif phase == 5:
                m[self.idx["secondary"]] = 0.6; notes.append("click_join")
            notes += ["browse", "join_intent", "self_join"]
        elif goal == "parkour":
            m[self.idx["forward"]] = 0.9
            m[self.idx["sprint"]] = 0.8
            m[self.idx["jump"]] = 0.85 if int(now * 5) % 3 == 0 else 0.1
            notes += ["parkour"]
            if not in_arena:
                self._zero_combat(m)
        else:
            self.mode = "explore"
            m[self.idx["forward"]] = 0.82 + 0.15 * self.curiosity
            m[self.idx["sprint"]] = 0.55
            if not in_arena:
                lx, ly = self.instinct.look_wander()
                if lx > 0:
                    m[self.idx["look_right"]] += abs(lx)
                else:
                    m[self.idx["look_left"]] += abs(lx)
                if ly > 0:
                    m[self.idx["look_up"]] += abs(ly) * 0.5
                else:
                    m[self.idx["look_down"]] += abs(ly) * 0.5
                m[self.idx["rmb_look"]] = 0.55
                self._zero_combat(m)
                notes += ["explore", "wander", "hunting_portal", "explore_world"]
            else:
                notes += ["explore", "wander", "explore_world"]

        buffs = self.loot.active_buffs(now)
        if buffs["speed"] > 0:
            m[self.idx["sprint"]] = min(1.0, float(m[self.idx["sprint"]]) + 0.4)
            notes.append("buff_speed")
        if buffs["rage"] > 0 and in_arena:
            m[self.idx["secondary"]] = min(1.0, max(float(m[self.idx["secondary"]]), 0.92))
            notes.append("buff_rage")

        kills = int(self.loot.kills)
        power_mult, power_name = 1.0, "dormant"
        for need, mult, name in ((0, 1.0, "dormant"), (3, 1.08, "awake"), (8, 1.16, "charged"),
                                  (15, 1.28, "ascendant"), (25, 1.42, "unlocked"), (40, 1.55, "ascended")):
            if kills >= need:
                power_mult, power_name = mult, name
        if power_mult > 1.0 and in_arena:
            for ch in ("forward", "sprint", "secondary", "look_left", "look_right"):
                m[self.idx[ch]] = float(np.clip(m[self.idx[ch]] * power_mult, -1.5, 1.5))
            notes.append(f"power:{power_name}")

        if not allow_ui:
            self._zero_junk(m)

        snap = self.instinct.snapshot()
        info = self._info(notes, meta, motion, food, loom, water, lobby, threat, rail, portal, in_arena, snap)
        info["power"] = power_name
        info["power_mult"] = power_mult
        return np.clip(m, -1, 1), notes, info

    def _info(self, notes, meta, motion, food, loom, water, lobby, threat, rail, portal, in_arena, snap):
        return {
            "fear": self.fear, "pain": self.pain, "anger": self.anger,
            "weakness": self.weakness, "curiosity": self.curiosity, "arousal": self.arousal,
            "notes": notes, "food_score": food, "motion": motion, "loom_score": loom,
            "water_score": water, "lobby_score": lobby, "threat_score": threat,
            "rail_score": rail, "portal_score": portal,
            "combat_mode": self.mode, "character": self.character,
            "char_label": self.kit["label"], "rot": self._rot,
            "hits": self._hits, "lock_in": self.lock_in, "goal": self.goal,
            "features": self.features_active, "deaths": self._deaths, "in_arena": in_arena,
            **{f"drv_{k}": v for k, v in snap.items() if isinstance(v, (int, float, bool))},
            **{f"loot_{k}": v for k, v in self.loot.snapshot().items() if isinstance(v, (int, float, str))},
        }
