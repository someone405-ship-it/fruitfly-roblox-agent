"""Online training — imitation + reward shaping + kill loot."""
from __future__ import annotations
import numpy as np
from typing import Dict, List
from .config import N_MOTOR, N_SENSORY

HOST_KEY_TO_MOTOR: Dict[str, int] = {
    "w": 0, "s": 1, "a": 2, "d": 3, "space": 4, "shift": 5,
    "e": 10, "q": 18, "r": 15, "ctrl": 16,
}


def _one_hot(idx: int, val: float = 1.0) -> np.ndarray:
    t = np.zeros(N_MOTOR, dtype=np.float32)
    if 0 <= idx < N_MOTOR:
        t[idx] = val
    return t


class Trainer:
    def __init__(self, brain, lr: float = 0.18) -> None:
        self.brain = brain
        self.lr = lr
        self.imit_lr = 0.28
        self.enabled = True
        self.mode = "reward"
        self._last_target = np.zeros(N_MOTOR, dtype=np.float32)
        self.samples = 0
        self.imit_samples = 0
        self.last_err = 0.0
        self.last_reward = 0.0

    def set_enabled(self, on: bool) -> None:
        self.enabled = on

    def set_mode(self, mode: str) -> None:
        if mode in ("imitation", "reward"):
            self.mode = mode

    def record_host_keys(self, keys_down: List[str]) -> None:
        target = np.zeros(N_MOTOR, dtype=np.float32)
        for k in keys_down:
            idx = HOST_KEY_TO_MOTOR.get(k.lower())
            if idx is not None and idx < N_MOTOR:
                target[idx] = 1.0
        if target[0] > 0.5 and target[5] > 0.5:
            target[5] = 1.0
        self._last_target = target

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
        return self.last_err

    def reward_from_notes(self, notes: List[str], meta: dict, motor: np.ndarray) -> float:
        r = 0.0
        if "water_death" in notes:
            r -= 0.8
        if "seek_portal" in notes:
            r += 0.55
        if "rail" in notes and float(motor[0]) > 0.2:
            r += 0.3
        if "predict_dodge" in notes:
            r += 0.4
        if "fight" in notes or "attack" in notes:
            r += 0.35
        if "lock_in" in notes:
            r += 0.25
        if "q_dash" in notes or "e_slash" in notes or "r_combo" in notes:
            r += 0.3
        if "food_seen" in notes:
            r += 0.1
        if "kill" in notes:
            r += 1.0
        if any(n.startswith("loot:") for n in notes):
            r += 0.4
        if "eat_food" in notes:
            r += 0.2
        if float(meta.get("threat_score", 0)) > 0.4 and ("fight" in notes or "attack" in notes):
            r += 0.3
        if float(meta.get("threat_score", 0)) > 0.5 and "flee" in notes:
            r += 0.15
        if "leave_lobby" in notes or "browse" in notes:
            r += 0.2
        if "parkour" in notes:
            r += 0.15
        if "patrol" in notes:
            r += 0.1
        if any(n.startswith("goal:") for n in notes):
            r += 0.05
        return float(np.clip(r, -1.5, 2.0))

    def step_reward(self, reward: float) -> None:
        if not self.enabled:
            return
        rate = 0.7 * self.brain.rate + 0.3 * self.brain.rate_slow
        motor = self.brain.last_motor
        self.brain.W_out += (self.lr * 0.85) * reward * np.outer(motor, rate)
        self.brain.W_out *= 0.9997
        self.samples += 1
        self.last_reward = reward

    def online_step(self, notes: List[str], meta: dict, motor: np.ndarray) -> float:
        if self.mode == "imitation":
            return self.step_imitation()
        r = self.reward_from_notes(notes, meta, motor)
        self.step_reward(r)
        return r

    def bootstrap_explore(self, steps: int = 400) -> None:
        rng = np.random.default_rng(11)
        scenes = [
            dict(t=np.array([0.95, 0, 0, 0, 0.1, 0.4] + [0.0] * 14, dtype=np.float32)),
            dict(t=np.array([0.5, 0, 0.85, 0, 0.2, 0.2] + [0.0] * 14, dtype=np.float32)),
            dict(t=np.array([0.5, 0, 0, 0.85, 0.2, 0.2] + [0.0] * 14, dtype=np.float32)),
            dict(t=np.array([0, 0.7, 0, 0, 0.5, 0.3] + [0.0] * 14, dtype=np.float32)),
            dict(t=_one_hot(18, 0.95)),
            dict(t=_one_hot(10, 0.95)),
            dict(t=_one_hot(15, 0.95)),
            dict(t=_one_hot(19, 0.9) + _one_hot(0, 0.7) + _one_hot(5, 0.4)),
            dict(t=_one_hot(0, 1.0) + _one_hot(5, 0.8) + _one_hot(19, 0.6)),
        ]
        err = np.zeros(1)
        for i in range(steps):
            sc = scenes[i % len(scenes)]
            target = sc["t"]
            if target.size < N_MOTOR:
                t = np.zeros(N_MOTOR, dtype=np.float32)
                t[: target.size] = target
                target = t
            s = rng.random(N_SENSORY).astype(np.float32) * 0.55
            if i % 5 == 0:
                s[20:50] += 0.35
            self.brain.step(s)
            rate = 0.7 * self.brain.rate + 0.3 * self.brain.rate_slow
            pred = self.brain.W_out @ rate
            err = target - np.tanh(pred)
            self.brain.W_out += self.lr * np.outer(err, rate)
            self.samples += 1
        self.last_err = float(np.mean(np.abs(err)))
