"""Online training — heavy bootstrap + imitation + permanent skill memory."""
from __future__ import annotations
import numpy as np
from typing import Dict, List, Optional
from .config import N_MOTOR, N_SENSORY
from .skill_memory import SkillMemory

HOST_KEY_TO_MOTOR: Dict[str, int] = {
    "w": 0, "s": 1, "a": 2, "d": 3, "space": 4, "shift": 5,
    "e": 10, "q": 18, "r": 15, "ctrl": 16, "f": 21,
    "rmb": 20, "lmb": 19,
}


def _one_hot(idx: int, val: float = 1.0) -> np.ndarray:
    t = np.zeros(N_MOTOR, dtype=np.float32)
    if 0 <= idx < N_MOTOR:
        t[idx] = val
    return t


def _portal_target() -> np.ndarray:
    """Sprint + forward + look toward portal + rmb."""
    t = np.zeros(N_MOTOR, dtype=np.float32)
    t[0] = 1.0   # forward
    t[5] = 0.85  # sprint
    t[7] = 0.55  # look_right bias
    t[20] = 0.8  # rmb_look
    return t


class Trainer:
    def __init__(self, brain, lr: float = 0.15) -> None:
        self.brain = brain
        self.lr = lr
        self.imit_lr = 0.34
        self.enabled = True
        self.mode = "reward"
        self._last_target = np.zeros(N_MOTOR, dtype=np.float32)
        self.samples = 0
        self.imit_samples = 0
        self.last_err = 0.0
        self.last_reward = 0.0
        self.memory = SkillMemory()
        self._last_keys: List[str] = []

    def set_enabled(self, on: bool) -> None:
        self.enabled = on

    def set_mode(self, mode: str) -> None:
        if mode in ("imitation", "reward"):
            self.mode = mode

    def record_host_keys(self, keys_down: List[str], meta: Optional[dict] = None) -> None:
        target = np.zeros(N_MOTOR, dtype=np.float32)
        for k in keys_down:
            idx = HOST_KEY_TO_MOTOR.get(k.lower())
            if idx is not None and idx < N_MOTOR:
                target[idx] = 1.0
        if target[0] > 0.5 and target[5] > 0.5:
            target[5] = 1.0
        if "rmb" in [x.lower() for x in keys_down]:
            target[20] = 1.0
            target[6] = max(target[6], 0.45)
            target[7] = max(target[7], 0.45)
        self._last_target = target
        self._last_keys = list(keys_down)
        try:
            self.memory.record(keys_down, target, meta=meta or {}, tag="host")
        except Exception:
            pass

    def step_imitation(self) -> float:
        if not self.enabled:
            return 0.0
        rate = 0.7 * self.brain.rate + 0.3 * self.brain.rate_slow
        pred = self.brain.W_out @ rate
        err = self._last_target - np.tanh(pred)
        self.brain.W_out += self.imit_lr * np.outer(err, rate)
        self.samples += 1
        self.imit_samples += 1
        self.last_err = float(np.mean(np.abs(err)))
        if self.imit_samples % 30 == 0:
            try:
                self.memory.save()
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
            r -= 1.2  # punish fighting without portal
        if "rail" in notes and float(motor[0]) > 0.2:
            r += 0.3
        if "predict_dodge" in notes:
            r += 0.4
        if ("fight" in notes or "attack" in notes) and "in_arena" in notes:
            r += 0.4
        if "lock_in" in notes and "in_arena" in notes:
            r += 0.25
        if "q_dash" in notes or "e_slash" in notes or "r_combo" in notes:
            r += 0.3
        if "kill" in notes:
            r += 1.0
        if any(n.startswith("loot:") for n in notes):
            r += 0.4
        if "eat_food" in notes:
            r += 0.2
        if float(meta.get("threat_score", 0)) > 0.4 and "in_arena" in notes and ("fight" in notes):
            r += 0.3
        if "leave_lobby" in notes or "browse" in notes:
            r += 0.15
        if "parkour" in notes:
            r += 0.15
        if "hunting_portal" in notes:
            r += 0.2
        if any(n.startswith("goal:portal") for n in notes):
            r += 0.15
        return float(np.clip(r, -1.5, 2.0))

    def step_reward(self, reward: float) -> None:
        if not self.enabled:
            return
        rate = 0.7 * self.brain.rate + 0.3 * self.brain.rate_slow
        motor = self.brain.last_motor
        self.brain.W_out += (self.lr * 0.9) * reward * np.outer(motor, rate)
        self.brain.W_out *= 0.9996
        self.samples += 1
        self.last_reward = reward

    def online_step(self, notes: List[str], meta: dict, motor: np.ndarray) -> float:
        if self.mode == "imitation":
            return self.step_imitation()
        try:
            bias = self.memory.motor_bias_from_memory(meta, strength=0.24)
            if float(np.abs(bias).sum()) > 0.05:
                rate = 0.7 * self.brain.rate + 0.3 * self.brain.rate_slow
                pred = self.brain.W_out @ rate
                err = bias - np.tanh(pred)
                self.brain.W_out += 0.09 * np.outer(err, rate)
        except Exception:
            pass
        r = self.reward_from_notes(notes, meta, motor)
        self.step_reward(r)
        return r

    def bootstrap_explore(self, steps: int = 2400) -> None:
        """Heavy pre-train: portal-first sequences + combat only after portal."""
        rng = np.random.default_rng(11)
        scenes = [
            # portal approach (many copies = strong prior)
            dict(t=_portal_target(), tag="portal"),
            dict(t=_portal_target(), tag="portal"),
            dict(t=_portal_target(), tag="portal"),
            dict(t=_one_hot(0, 1.0) + _one_hot(5, 0.9) + _one_hot(6, 0.6) + _one_hot(20, 0.7), tag="portal_left"),
            dict(t=_one_hot(0, 1.0) + _one_hot(5, 0.9) + _one_hot(7, 0.6) + _one_hot(20, 0.7), tag="portal_right"),
            dict(t=_one_hot(0, 0.95) + _one_hot(4, 0.5) + _one_hot(5, 0.7), tag="portal_jump"),
            # explore / rail toward portal
            dict(t=np.array([0.9, 0, 0.3, 0, 0.1, 0.5] + [0.0] * (N_MOTOR - 6), dtype=np.float32), tag="explore"),
            dict(t=np.array([0.85, 0, 0, 0.4, 0.1, 0.45] + [0.0] * (N_MOTOR - 6), dtype=np.float32), tag="explore"),
            dict(t=_one_hot(0, 0.9) + _one_hot(5, 0.5), tag="rail"),
            # lobby browse
            dict(t=_one_hot(13, 0.9), tag="ui"),  # ui_down
            dict(t=_one_hot(14, 0.9), tag="ui"),  # ui_select
            # arena combat (after portal)
            dict(t=_one_hot(19, 0.95) + _one_hot(0, 0.85) + _one_hot(5, 0.7), tag="fight"),
            dict(t=_one_hot(0, 1.0) + _one_hot(5, 0.85) + _one_hot(19, 0.8) + _one_hot(18, 0.7), tag="fight"),
            dict(t=_one_hot(10, 0.95) + _one_hot(0, 0.7), tag="e_slash"),
            dict(t=_one_hot(18, 0.95) + _one_hot(0, 0.7), tag="q_dash"),
            dict(t=_one_hot(15, 0.95) + _one_hot(0, 0.6), tag="r_combo"),
            # flee / water
            dict(t=_one_hot(1, 0.9) + _one_hot(5, 0.6), tag="flee"),
            # look around fast
            dict(t=_one_hot(20, 0.95) + _one_hot(7, 0.9), tag="look"),
            dict(t=_one_hot(20, 0.95) + _one_hot(6, 0.9), tag="look"),
            dict(t=_one_hot(20, 0.9) + _one_hot(8, 0.7), tag="look"),
            dict(t=_one_hot(20, 0.9) + _one_hot(9, 0.7), tag="look"),
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
            # sensory bias: portal scenes get purple-ish mid features
            if "portal" in tag:
                s[40:80] += 0.45
                s[100:120] += 0.3
            elif tag == "fight":
                s[20:40] += 0.4
            elif tag == "flee":
                s[60:90] += 0.35
            if i % 4 == 0:
                s[10:30] += 0.25
            self.brain.step(s)
            rate = 0.7 * self.brain.rate + 0.3 * self.brain.rate_slow
            pred = self.brain.W_out @ rate
            err = target - np.tanh(pred)
            # portal scenes get higher learning rate
            lr = self.lr * (1.35 if "portal" in tag else 1.0)
            self.brain.W_out += lr * np.outer(err, rate)
            self.samples += 1
            # seed skill memory with portal patterns
            if i % 12 == 0 and "portal" in tag:
                try:
                    self.memory.record(["w", "shift"], target, meta={"portal_score": 0.6, "threat_score": 0.05}, tag="bootstrap_portal")
                except Exception:
                    pass
        self.last_err = float(np.mean(np.abs(err)))
        try:
            self.memory.save()
        except Exception:
            pass

    def flush_memory(self) -> str:
        self.memory.save()
        return self.memory.summary()
