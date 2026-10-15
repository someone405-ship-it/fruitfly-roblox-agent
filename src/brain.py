"""
FruitFlyBrain — real-time LIF-style reservoir inspired by Drosophila connectome dynamics.

Not a full MaleCNS (167k neurons); that would not run at 30–60 Hz on consumer hardware.
This is a practical 512-unit recurrent reservoir with sensory drive and linear motor readout,
parameterised after published LIF models (Shiu et al. Nature 2024 style).
"""

from __future__ import annotations

import numpy as np
from typing import Tuple

from .config import (
    N_SENSORY,
    N_HIDDEN,
    N_MOTOR,
    DT_MS,
    TAU_MEM,
    V_THRESH,
    V_RESET,
    NOISE_SCALE,
    MOTOR_NAMES,
)


class FruitFlyBrain:
    """Spiking reservoir + linear readout → motor command vector."""

    def __init__(self, seed: int = 42) -> None:
        rng = np.random.default_rng(seed)

        # Sensory → hidden (dense, small)
        self.W_in = rng.normal(0.0, 0.4, size=(N_HIDDEN, N_SENSORY)).astype(np.float32)

        # Recurrent reservoir (sparse-ish, spectral radius ~0.9)
        W = rng.normal(0.0, 1.0, size=(N_HIDDEN, N_HIDDEN)).astype(np.float32)
        mask = rng.random(W.shape) < 0.15
        W *= mask
        # scale spectral radius
        eig = np.linalg.eigvals(W)
        radius = np.max(np.abs(eig))
        if radius > 1e-6:
            W *= 0.9 / radius
        self.W_rec = W

        # Hidden → motor
        self.W_out = rng.normal(0.0, 0.3, size=(N_MOTOR, N_HIDDEN)).astype(np.float32)

        # State
        self.v = np.zeros(N_HIDDEN, dtype=np.float32)
        self.spikes = np.zeros(N_HIDDEN, dtype=np.float32)
        self.rate = np.zeros(N_HIDDEN, dtype=np.float32)  # exponential moving average
        self.t = 0.0
        self.last_motor = np.zeros(N_MOTOR, dtype=np.float32)

        # simple eligibility for optional online adaptation
        self.eligibility = np.zeros_like(self.W_out)

    def reset(self) -> None:
        self.v.fill(0.0)
        self.spikes.fill(0.0)
        self.rate.fill(0.0)
        self.t = 0.0
        self.last_motor.fill(0.0)

    def step(self, sensory: np.ndarray) -> Tuple[np.ndarray, dict]:
        """
        Advance one simulation step.

        sensory : (N_SENSORY,) float32 in [0, 1]
        returns : motor_scores (N_MOTOR,), info dict
        """
        s = np.asarray(sensory, dtype=np.float32).ravel()
        if s.size != N_SENSORY:
            s = np.resize(s, N_SENSORY)

        # membrane dynamics (Euler, tau in ms)
        I = self.W_in @ s + self.W_rec @ self.spikes
        I += NOISE_SCALE * np.random.randn(N_HIDDEN).astype(np.float32)

        dv = (-self.v + I) * (DT_MS / TAU_MEM)
        self.v += dv

        # spikes
        fired = self.v >= V_THRESH
        self.spikes = fired.astype(np.float32)
        self.v[fired] = V_RESET

        # rate EMA (for readout stability)
        alpha = 0.15
        self.rate = (1 - alpha) * self.rate + alpha * self.spikes

        # linear readout → motor scores
        motor = self.W_out @ self.rate
        # soft bound
        motor = np.tanh(motor).astype(np.float32)
        self.last_motor = motor

        self.t += DT_MS

        info = {
            "t_ms": self.t,
            "n_spikes": int(self.spikes.sum()),
            "mean_rate": float(self.rate.mean()),
            "motor": {name: float(motor[i]) for i, name in enumerate(MOTOR_NAMES)},
        }
        return motor, info

    def decide(self, motor: np.ndarray, threshold: float = 0.25) -> list[str]:
        """Return list of active action names above threshold."""
        active = []
        for i, name in enumerate(MOTOR_NAMES):
            if motor[i] > threshold:
                active.append(name)
        # mutual exclusion for opposing pairs
        if "forward" in active and "back" in active:
            if motor[0] > motor[1]:
                active.remove("back")
            else:
                active.remove("forward")
        if "left" in active and "right" in active:
            if motor[2] > motor[3]:
                active.remove("right")
            else:
                active.remove("left")
        return active
