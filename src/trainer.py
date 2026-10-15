"""Online training for the advanced fly brain readout."""

from __future__ import annotations

import numpy as np
from typing import Dict, List

from .config import N_MOTOR

HOST_KEY_TO_MOTOR: Dict[str, int] = {
    "w": 0, "s": 1, "a": 2, "d": 3, "space": 4, "shift": 5, "e": 10,
}


class Trainer:
    def __init__(self, brain, lr: float = 0.06) -> None:
        self.brain = brain
        self.lr = lr
        self.enabled = False
        self.mode = "imitation"
        self._last_target = np.zeros(N_MOTOR, dtype=np.float32)
        self.samples = 0

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
        self._last_target = target

    def step_imitation(self) -> float:
        if not self.enabled or self.mode != "imitation":
            return 0.0
        rate = 0.7 * self.brain.rate + 0.3 * self.brain.rate_slow
        pred = self.brain.W_out @ rate
        err = self._last_target - np.tanh(pred)
        self.brain.W_out += self.lr * np.outer(err, rate)
        self.samples += 1
        return float(np.mean(np.abs(err)))

    def step_reward(self, reward: float) -> None:
        if not self.enabled or self.mode != "reward":
            return
        rate = 0.7 * self.brain.rate + 0.3 * self.brain.rate_slow
        motor = self.brain.last_motor
        self.brain.W_out += self.lr * reward * np.outer(motor, rate)
        self.samples += 1
