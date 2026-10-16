"""LIF reservoir brain — power-iteration spectral radius."""
from __future__ import annotations
from pathlib import Path
from typing import Tuple
import numpy as np
from .config import (
    N_SENSORY, N_HIDDEN, N_MOTOR, MOTOR_NAMES, DT_MS, TAU_MEM, TAU_SLOW,
    V_THRESH, V_RESET, NOISE_SCALE, SPARSITY, SPECTRAL_RADIUS, WEIGHTS_PATH,
)


def _spectral_radius_estimate(W: np.ndarray, iters: int = 40) -> float:
    """Power iteration — avoids full eigvalsh hang on large matrices."""
    n = W.shape[0]
    if n == 0:
        return 0.0
    rng = np.random.default_rng(0)
    v = rng.standard_normal(n).astype(np.float32)
    v /= (np.linalg.norm(v) + 1e-9)
    for _ in range(iters):
        w = W @ v
        nrm = float(np.linalg.norm(w)) + 1e-9
        v = w / nrm
    return float(np.linalg.norm(W @ v))


class FruitFlyBrain:
    def __init__(self, seed: int = 0) -> None:
        self.rng = np.random.default_rng(seed)
        rng = self.rng
        self.W_in = rng.normal(0.0, 0.4, size=(N_HIDDEN, N_SENSORY)).astype(np.float32)
        W = rng.normal(0.0, 1.0, size=(N_HIDDEN, N_HIDDEN)).astype(np.float32)
        W *= (rng.random(W.shape) < SPARSITY).astype(np.float32)
        signs = np.where(rng.random(N_HIDDEN) < 0.5, 1.0, -1.0).astype(np.float32)
        W *= signs[None, :]
        radius = _spectral_radius_estimate(W)
        if radius > 1e-6:
            W *= np.float32(SPECTRAL_RADIUS / radius)
        self.W_rec = W
        self.W_out = rng.normal(0.0, 0.25, size=(N_MOTOR, N_HIDDEN)).astype(np.float32)
        self.v = np.zeros(N_HIDDEN, dtype=np.float32)
        self.v_slow = np.zeros(N_HIDDEN, dtype=np.float32)
        self.spikes = np.zeros(N_HIDDEN, dtype=np.float32)
        self.rate = np.zeros(N_HIDDEN, dtype=np.float32)
        self.rate_slow = np.zeros(N_HIDDEN, dtype=np.float32)
        self.gain = np.ones(N_HIDDEN, dtype=np.float32)
        self.t = 0.0
        self.last_motor = np.zeros(N_MOTOR, dtype=np.float32)
        self.total_spikes = 0
        self.steps = 0

    def reset(self) -> None:
        self.v.fill(0.0); self.v_slow.fill(0.0); self.spikes.fill(0.0)
        self.rate.fill(0.0); self.rate_slow.fill(0.0); self.gain.fill(1.0)
        self.t = 0.0; self.last_motor.fill(0.0)
        self.total_spikes = 0; self.steps = 0

    def step(self, sensory: np.ndarray) -> Tuple[np.ndarray, dict]:
        s = np.asarray(sensory, dtype=np.float32).ravel()
        if s.size != N_SENSORY:
            out = np.zeros(N_SENSORY, dtype=np.float32)
            n = min(s.size, N_SENSORY)
            out[:n] = s[:n]
            s = out
        I = self.W_in @ s + self.W_rec @ (self.spikes * self.gain)
        I += 0.15 * self.v_slow
        I += NOISE_SCALE * self.rng.standard_normal(N_HIDDEN).astype(np.float32)
        self.v += (-self.v + I) * (DT_MS / TAU_MEM)
        self.v_slow += (-self.v_slow + self.v) * (DT_MS / TAU_SLOW)
        fired = self.v >= V_THRESH
        self.spikes = fired.astype(np.float32)
        self.v[fired] = V_RESET
        n_sp = int(self.spikes.sum())
        self.total_spikes += n_sp
        self.steps += 1
        self.rate = 0.82 * self.rate + 0.18 * self.spikes
        self.rate_slow = 0.97 * self.rate_slow + 0.03 * self.spikes
        self.gain *= 1.0 + 0.002 * (0.05 - self.rate_slow)
        np.clip(self.gain, 0.5, 2.0, out=self.gain)
        motor = self.W_out @ (0.7 * self.rate + 0.3 * self.rate_slow)
        motor = np.tanh(motor).astype(np.float32)
        self.last_motor = motor
        self.t += DT_MS
        info = {
            "t_ms": self.t, "n_spikes": n_sp,
            "mean_rate": float(self.rate.mean()),
            "mean_rate_slow": float(self.rate_slow.mean()),
            "mean_gain": float(self.gain.mean()),
            "total_spikes": self.total_spikes, "steps": self.steps,
            "motor": {MOTOR_NAMES[i]: float(motor[i]) for i in range(min(N_MOTOR, motor.size))},
            "motor_vec": motor.copy(),
        }
        return motor, info

    def decide(self, motor: np.ndarray, threshold: float = 0.18) -> list:
        active = [MOTOR_NAMES[i] for i in range(min(len(MOTOR_NAMES), motor.size)) if motor[i] > threshold]
        pairs = [("forward", "back"), ("left", "right"), ("look_left", "look_right"), ("look_up", "look_down")]
        name_to_i = {n: i for i, n in enumerate(MOTOR_NAMES)}
        for a, b in pairs:
            if a in active and b in active:
                if motor[name_to_i[a]] >= motor[name_to_i[b]]:
                    active.remove(b)
                else:
                    active.remove(a)
        return active

    def save_weights(self, path=WEIGHTS_PATH) -> None:
        path = Path(path)
        np.savez_compressed(path, W_in=self.W_in, W_rec=self.W_rec, W_out=self.W_out, gain=self.gain)

    def load_weights(self, path=WEIGHTS_PATH) -> bool:
        path = Path(path)
        if not path.is_file():
            return False
        try:
            data = np.load(path)
            if data["W_in"].shape != self.W_in.shape: return False
            if data["W_rec"].shape != self.W_rec.shape: return False
            if data["W_out"].shape != self.W_out.shape: return False
            self.W_in = data["W_in"].astype(np.float32)
            self.W_rec = data["W_rec"].astype(np.float32)
            self.W_out = data["W_out"].astype(np.float32)
            if "gain" in data and data["gain"].shape == self.gain.shape:
                self.gain = data["gain"].astype(np.float32)
            return True
        except Exception:
            return False
