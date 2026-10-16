"""Online training — keys + eyes + skills + mistakes + wins + potential/reflex (GPU-safe)."""
from __future__ import annotations
import numpy as np
from typing import Dict, List, Optional, Set
from .config import N_MOTOR, N_SENSORY
from .skill_memory import SkillMemory
from .eye_learn import EyeMemory
from .mistake_memory import MistakeMemory, WinMemory
from .potential import get_potential
from .reflex import get_reflex
from . import runtime_reflex

HOST_KEY_TO_MOTOR: Dict[str, int] = {
    "w": 0, "s": 1, "a": 2, "d": 3, "space": 4, "shift": 5,
    "e": 10, "q": 18, "r": 15, "ctrl": 16, "f": 21,
    "rmb": 20, "lmb": 19, "esc": 22, "m": 23,
    "up": 12, "down": 13, "enter": 14,
    "scroll_up": 24, "scroll_down": 25,
}


def _one_hot(idx: int, val: float = 1.0) -> np.ndarray:
    t = np.zeros(N_MOTOR, dtype=np.float32)
    if 0 <= idx < N_MOTOR:
        t[idx] = val
    return t


def _portal_target() -> np.ndarray:
    t = np.zeros(N_MOTOR, dtype=np.float32)
    t[0] = 1.0; t[5] = 0.9; t[7] = 0.5; t[20] = 0.85
    return t


class Trainer:
    def _rates_np(self):
        try:
            from .brain import _to_np
            r = _to_np(self.brain.rate)
            rs = _to_np(self.brain.rate_slow)
            return (0.7 * r + 0.3 * rs).astype(np.float32)
        except Exception:
            r = np.asarray(self.brain.rate, dtype=np.float32)
            rs = np.asarray(self.brain.rate_slow, dtype=np.float32)
            return (0.7 * r + 0.3 * rs).astype(np.float32)

    def _w_out_np(self):
        try:
            from .brain import _to_np
            return _to_np(self.brain.W_out).astype(np.float32)
        except Exception:
            return np.asarray(self.brain.W_out, dtype=np.float32)

    def _set_w_out(self, W):
        try:
            from .brain import _xp, _GPU
            if _GPU:
                self.brain.W_out = _xp.asarray(np.asarray(W, dtype=np.float32))
            else:
                self.brain.W_out = np.asarray(W, dtype=np.float32)
        except Exception:
            self.brain.W_out = np.asarray(W, dtype=np.float32)

    def __init__(self, brain, lr: float = 0.14) -> None:
        self.brain = brain
        self.lr = lr
        self.imit_lr = 0.36
        self.eye_lr = 0.22
        self.enabled = True
        self.mode = "reward"
        self._last_target = np.zeros(N_MOTOR, dtype=np.float32)
        self.samples = 0
        self.imit_samples = 0
        self.eye_samples = 0
        self.last_err = 0.0
        self.last_reward = 0.0
        self.memory = SkillMemory()
        self.eye = EyeMemory()
        self.mistakes = MistakeMemory()
        self.wins = WinMemory()
        self._last_keys: List[str] = []
        self._last_sensory: Optional[np.ndarray] = None
        self._last_actions: List[str] = []
        self.last_mistake_msg = ""

    def set_enabled(self, on: bool) -> None:
        self.enabled = on

    def set_mode(self, mode: str) -> None:
        if mode in ("imitation", "reward"):
            self.mode = mode

    def record_host_keys(self, keys_down: List[str], meta: Optional[dict] = None, sensory: Optional[np.ndarray] = None) -> None:
        target = np.zeros(N_MOTOR, dtype=np.float32)
        for k in keys_down:
            idx = HOST_KEY_TO_MOTOR.get(k.lower())
            if idx is not None and idx < N_MOTOR:
                target[idx] = 1.0
        if target[0] > 0.5 and target[5] > 0.5:
            target[5] = 1.0
        if "rmb" in [x.lower() for x in keys_down]:
            target[20] = 1.0
            target[6] = max(target[6], 0.5)
            target[7] = max(target[7], 0.5)
        self._last_target = target
        self._last_keys = list(keys_down)
        if sensory is not None:
            self._last_sensory = np.asarray(sensory, dtype=np.float32).copy()
            try:
                self.eye.record(sensory, target)
                self.eye_samples += 1
            except Exception:
                pass
        try:
            self.memory.record(keys_down, target, meta=meta or {}, tag="host")
        except Exception:
            pass

    def step_imitation(self) -> float:
        if not self.enabled:
            return 0.0
        rate = self._rates_np()
        W = self._w_out_np()
        pred = W @ rate
        err = self._last_target - np.tanh(pred)
        W = W + self.imit_lr * np.outer(err, rate)
        if self._last_sensory is not None and self.eye.count > 10:
            try:
                eye_t = self.eye.nearest_target(self._last_sensory, k=4)
                if float(np.abs(eye_t).sum()) > 0.05:
                    err2 = eye_t - np.tanh(pred)
                    W = W + self.eye_lr * np.outer(err2, rate)
            except Exception:
                pass
        self._set_w_out(W)
        self.samples += 1
        self.imit_samples += 1
        self.last_err = float(np.mean(np.abs(err)))
        if self.imit_samples % 25 == 0:
            try:
                self.memory.save()
                self.eye.save()
            except Exception:
                pass
        return self.last_err

    def reward_from_notes(self, notes: List[str], meta: dict, motor: np.ndarray) -> float:
        r = 0.0
        if "water_death" in notes:
            r -= 0.8
        if "seek_portal" in notes or "portal_safe" in notes:
            r += 0.7
        if "portal_close" in notes:
            r += 0.45
        if "need_portal" in notes and ("fight" in notes or "attack" in notes):
            r -= 1.2
        if "leave" in notes or "escape_menu" in notes:
            r += 0.25
        if "join_game" in notes or "self_join" in notes:
            r += 0.5
        if "explore_world" in notes:
            r += 0.2
        if "rail" in notes and float(motor[0]) > 0.2:
            r += 0.3
        if "predict_dodge" in notes:
            r += 0.4
        if ("fight" in notes or "attack" in notes) and "in_arena" in notes:
            r += 0.4
        if "kill" in notes:
            r += 1.0
        if any(n.startswith("loot:") for n in notes):
            r += 0.4
        if "hunting_portal" in notes:
            r += 0.2
        return float(np.clip(r, -1.5, 2.0))

    def step_reward(self, reward: float) -> None:
        if not self.enabled:
            return
        rate = self._rates_np()
        motor = np.asarray(self.brain.last_motor, dtype=np.float32)
        W = self._w_out_np()
        W = W + (self.lr * 0.9) * reward * np.outer(motor, rate)
        W = W * 0.9996
        self._set_w_out(W)
        self.samples += 1
        self.last_reward = reward

    def _detect_and_record_mistakes(self, notes, meta, motor, actions=None):
        acts = actions if actions is not None else self._last_actions
        if "water_death" in notes or meta.get("death_event"):
            kind = "water_death" if "water_death" in notes else "death"
            self.mistakes.record(kind, notes, meta, motor, acts)
            self.last_mistake_msg = f"learned mistake:{kind}"
            self.step_reward(-1.2)
        elif "need_portal" in notes and ("fight" in notes or "attack" in notes):
            self.mistakes.record("fight_before_portal", notes, meta, motor, acts)
            self.last_mistake_msg = "learned mistake:fight_before_portal"
            self.step_reward(-1.0)
        elif meta.get("death_event"):
            self.mistakes.record("death", notes, meta, motor, acts)
            self.last_mistake_msg = "learned mistake:death"

    def _detect_and_record_wins(self, notes, meta, motor):
        if "kill" in notes:
            self.wins.record("kill", notes, meta, motor)
            self.step_reward(0.6)
        elif "portal_close" in notes or "portal_safe" in notes:
            self.wins.record("portal", notes, meta, motor)
        elif "self_join" in notes or "join_game" in notes:
            self.wins.record("join", notes, meta, motor)

    def apply_mistake_filters(self, motor, notes, meta, actions):
        m = motor.astype(np.float32).copy()
        if m.size < N_MOTOR:
            pad = np.zeros(N_MOTOR, dtype=np.float32)
            pad[: m.size] = m
            m = pad
        try:
            avoid = self.mistakes.avoid_bias(meta, notes, strength=0.9)
            boost = self.wins.boost_bias(meta, notes, strength=0.35)
            m = np.clip(m + avoid + boost, -1.5, 1.5).astype(np.float32)
        except Exception:
            pass
        banned = self.mistakes.ban_actions(meta, notes)
        prefer = self.mistakes.prefer_actions(meta, notes)
        acts = [a for a in actions if a not in banned]
        for p in prefer:
            if p not in acts and p not in banned and p in ("back", "left", "right", "forward", "sprint", "jump", "rmb_look"):
                acts.append(p)
        self._last_actions = list(acts)
        try:
            self.mistakes.publish_runtime(meta, notes)
        except Exception:
            pass
        return m, acts, banned

    def online_step(self, notes, meta, motor, sensory=None, actions=None):
        if self.mode == "imitation":
            return self.step_imitation()
        if actions is not None:
            self._last_actions = list(actions)
        try:
            bias = self.memory.motor_bias_from_memory(meta, strength=0.22)
            if sensory is not None and self.eye.count > 8:
                eye_b = self.eye.nearest_target(sensory, k=4)
                bias = 0.55 * bias + 0.45 * eye_b
            avoid = self.mistakes.avoid_bias(meta, notes, strength=0.4)
            boost = self.wins.boost_bias(meta, notes, strength=0.25)
            bias = bias + boost + avoid
            if float(np.abs(bias).sum()) > 0.05:
                rate = self._rates_np()
                W = self._w_out_np()
                pred = W @ rate
                err = np.clip(bias, -1.0, 1.0) - np.tanh(pred)
                self._set_w_out(W + 0.12 * np.outer(err, rate))
        except Exception:
            pass
        self._detect_and_record_mistakes(notes, meta, motor, actions)
        self._detect_and_record_wins(notes, meta, motor)
        try:
            self.mistakes.publish_runtime(meta, notes)
        except Exception:
            pass
        try:
            pot = get_potential()
            pot.tick(0.05)
            in_arena = ("in_arena" in notes) or bool(meta.get("in_arena"))
            bias_r, force, rnotes = get_reflex().react(meta, notes, in_arena=in_arena)
            sens, mx = pot.look_params()
            runtime_reflex.publish(
                force, bias_r, rnotes,
                threshold=pot.decide_threshold(),
                look_sens=sens,
                look_max=mx,
            )
            if "kill" in notes:
                pot.on_event("kill")
            if "water_death" in notes or meta.get("death_event"):
                pot.on_event("death")
            if "portal_close" in notes or "portal_safe" in notes:
                pot.on_event("portal")
            if "self_join" in notes or "join_game" in notes:
                pot.on_event("join")
            if getattr(self, "last_mistake_msg", ""):
                pot.on_event("mistake")
        except Exception:
            pass
        r = self.reward_from_notes(notes, meta, motor)
        self.step_reward(r)
        return r

    def bootstrap_explore(self, steps: int = 500) -> None:
        rng = np.random.default_rng(11)
        scenes = [
            dict(t=_portal_target(), tag="portal"),
            dict(t=_portal_target(), tag="portal"),
            dict(t=_one_hot(0, 1.0) + _one_hot(5, 0.9) + _one_hot(7, 0.6) + _one_hot(20, 0.7), tag="portal"),
            dict(t=_one_hot(22, 0.95), tag="leave"),
            dict(t=_one_hot(25, 0.9), tag="join"),
            dict(t=_one_hot(13, 0.9) + _one_hot(14, 0.85), tag="join"),
            dict(t=_one_hot(19, 0.95) + _one_hot(0, 0.85) + _one_hot(5, 0.7), tag="fight"),
            dict(t=_one_hot(1, 0.9) + _one_hot(5, 0.6), tag="flee"),
            dict(t=_one_hot(0, 0.9) + _one_hot(5, 0.5), tag="explore"),
            dict(t=_one_hot(1, 0.95), tag="water_avoid"),
        ]
        err = np.zeros(1)
        for i in range(steps):
            sc = scenes[i % len(scenes)]
            target = sc["t"]
            if target.size < N_MOTOR:
                t = np.zeros(N_MOTOR, dtype=np.float32)
                t[: target.size] = target
                target = t
            s = rng.random(N_SENSORY).astype(np.float32) * 0.5
            tag = sc.get("tag", "")
            if "portal" in tag:
                s[40:90] += 0.45
            elif tag == "fight":
                s[20:45] += 0.4
            elif tag == "join":
                s[100:140] += 0.35
            self.brain.step(s)
            rate = self._rates_np()
            W = self._w_out_np()
            pred = W @ rate
            err = target - np.tanh(pred)
            lr = self.lr * (1.3 if tag in ("portal", "join", "leave", "water_avoid") else 1.0)
            self._set_w_out(W + lr * np.outer(err, rate))
            self.samples += 1
            if i % 15 == 0:
                try:
                    self.eye.record(s, target)
                    self.memory.record([tag], target, meta={"tag": tag}, tag=f"boot_{tag}")
                except Exception:
                    pass
        self.last_err = float(np.mean(np.abs(err)))
        try:
            self.memory.save()
            self.eye.save()
            self.mistakes.save()
            self.wins.save()
        except Exception:
            pass

    def flush_memory(self) -> str:
        self.memory.save()
        self.eye.save()
        self.mistakes.save()
        self.wins.save()
        try:
            get_potential().save()
        except Exception:
            pass
        try:
            return f"{self.memory.summary()} | {self.eye.summary()} | {self.mistakes.summary()} | {self.wins.summary()} | {get_potential().summary()}"
        except Exception:
            return f"{self.memory.summary()} | {self.eye.summary()} | {self.mistakes.summary()} | {self.wins.summary()}"
