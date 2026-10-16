"""Block-sparse LIF brain — exactly 139,255 units (FlyWire FAFB v783 count)."""
from __future__ import annotations
from pathlib import Path
from typing import Tuple, List, Any
import numpy as np
from .config import (
    N_SENSORY, N_HIDDEN, N_MOTOR, N_COLS, COL_SIZE, MOTOR_NAMES,
    DT_MS, TAU_MEM, TAU_SLOW, V_THRESH, V_RESET, NOISE_SCALE,
    SPARSITY, INTER_SPARSITY, SPECTRAL_RADIUS, WEIGHTS_PATH,
)

_xp: Any = np
_GPU = False
try:
    import cupy as cp  # type: ignore
    if cp.cuda.runtime.getDeviceCount() > 0:
        _xp = cp
        _GPU = True
except Exception:
    _xp = np
    _GPU = False


def using_gpu() -> bool:
    return bool(_GPU)


def _to_np(a):
    if _GPU:
        try:
            return _xp.asnumpy(a)
        except Exception:
            return np.asarray(a)
    return np.asarray(a)


def _col_slices(n_hidden: int, col_size: int, n_cols: int) -> List[slice]:
    out = []
    start = 0
    for c in range(n_cols):
        end = min(n_hidden, start + col_size)
        out.append(slice(start, end))
        start = end
    return out


class FruitFlyBrain:
    """139,255 LIF units — FlyWire whole-brain count (block-sparse, not real synapses)."""

    def __init__(self, seed: int = 0) -> None:
        self.rng = np.random.default_rng(seed)
        rng = self.rng
        self.n_cols = N_COLS
        self.col_size = COL_SIZE
        self.n_hidden = N_HIDDEN
        self.backend = "cuda" if _GPU else "cpu"
        self.slices = _col_slices(N_HIDDEN, COL_SIZE, N_COLS)
        self.col_lens = [s.stop - s.start for s in self.slices]

        W_in = rng.normal(0.0, 0.24, size=(N_HIDDEN, N_SENSORY)).astype(np.float32)

        W_cols: List[np.ndarray] = []
        for ln in self.col_lens:
            W = rng.normal(0.0, 1.0, size=(ln, ln)).astype(np.float32)
            W *= (rng.random(W.shape) < SPARSITY).astype(np.float32)
            signs = np.where(rng.random(ln) < 0.5, 1.0, -1.0).astype(np.float32)
            W *= signs[None, :]
            fro = float(np.linalg.norm(W, ord="fro")) + 1e-9
            W *= np.float32(SPECTRAL_RADIUS / max(1.0, fro / np.sqrt(max(1, ln))))
            W_cols.append(W)

        W_left: List[np.ndarray] = []
        W_right: List[np.ndarray] = []
        for c, ln in enumerate(self.col_lens):
            ln_l = self.col_lens[(c - 1) % self.n_cols]
            ln_r = self.col_lens[(c + 1) % self.n_cols]
            Ml = rng.normal(0.0, 0.1, size=(ln, ln_l)).astype(np.float32)
            Ml *= (rng.random(Ml.shape) < INTER_SPARSITY).astype(np.float32)
            Mr = rng.normal(0.0, 0.1, size=(ln, ln_r)).astype(np.float32)
            Mr *= (rng.random(Mr.shape) < INTER_SPARSITY).astype(np.float32)
            W_left.append(Ml)
            W_right.append(Mr)

        W_out = rng.normal(0.0, 0.14, size=(N_MOTOR, N_HIDDEN)).astype(np.float32)

        xp = _xp
        self.W_in = xp.asarray(W_in)
        self.W_cols = [xp.asarray(w) for w in W_cols]
        self.W_left = [xp.asarray(w) for w in W_left]
        self.W_right = [xp.asarray(w) for w in W_right]
        self.W_out = xp.asarray(W_out)

        self.v = xp.zeros(N_HIDDEN, dtype=xp.float32)
        self.v_slow = xp.zeros(N_HIDDEN, dtype=xp.float32)
        self.spikes = xp.zeros(N_HIDDEN, dtype=xp.float32)
        self.rate = xp.zeros(N_HIDDEN, dtype=xp.float32)
        self.rate_slow = xp.zeros(N_HIDDEN, dtype=xp.float32)
        self.gain = xp.ones(N_HIDDEN, dtype=xp.float32)
        self.t = 0.0
        self.last_motor = np.zeros(N_MOTOR, dtype=np.float32)
        self.total_spikes = 0
        self.steps = 0

    def reset(self) -> None:
        xp = _xp
        self.v = xp.zeros(N_HIDDEN, dtype=xp.float32)
        self.v_slow = xp.zeros(N_HIDDEN, dtype=xp.float32)
        self.spikes = xp.zeros(N_HIDDEN, dtype=xp.float32)
        self.rate = xp.zeros(N_HIDDEN, dtype=xp.float32)
        self.rate_slow = xp.zeros(N_HIDDEN, dtype=xp.float32)
        self.gain = xp.ones(N_HIDDEN, dtype=xp.float32)
        self.t = 0.0
        self.last_motor.fill(0.0)
        self.total_spikes = 0
        self.steps = 0

    def step(self, sensory: np.ndarray) -> Tuple[np.ndarray, dict]:
        xp = _xp
        s = np.asarray(sensory, dtype=np.float32).ravel()
        if s.size != N_SENSORY:
            out = np.zeros(N_SENSORY, dtype=np.float32)
            n = min(s.size, N_SENSORY)
            out[:n] = s[:n]
            s = out
        s_x = xp.asarray(s)

        I = self.W_in @ s_x
        gsp = self.spikes * self.gain
        for c in range(self.n_cols):
            sl = self.slices[c]
            I[sl] = I[sl] + self.W_cols[c] @ gsp[sl]
            cl = (c - 1) % self.n_cols
            I[sl] = I[sl] + self.W_left[c] @ gsp[self.slices[cl]]
            cr = (c + 1) % self.n_cols
            I[sl] = I[sl] + self.W_right[c] @ gsp[self.slices[cr]]

        I = I + 0.1 * self.v_slow
        if _GPU:
            I = I + NOISE_SCALE * xp.random.standard_normal(N_HIDDEN, dtype=xp.float32)
        else:
            I = I + NOISE_SCALE * self.rng.standard_normal(N_HIDDEN).astype(np.float32)

        self.v = self.v + (-self.v + I) * (DT_MS / TAU_MEM)
        self.v_slow = self.v_slow + (-self.v_slow + self.v) * (DT_MS / TAU_SLOW)
        fired = self.v >= V_THRESH
        self.spikes = fired.astype(xp.float32)
        self.v = xp.where(fired, xp.float32(V_RESET), self.v)
        n_sp = int(_to_np(self.spikes.sum()))
        self.total_spikes += n_sp
        self.steps += 1
        self.rate = 0.74 * self.rate + 0.26 * self.spikes
        self.rate_slow = 0.93 * self.rate_slow + 0.07 * self.spikes
        self.gain = self.gain * (1.0 + 0.0025 * (0.05 - self.rate_slow))
        self.gain = xp.clip(self.gain, 0.5, 2.0)

        motor_x = self.W_out @ (0.65 * self.rate + 0.35 * self.rate_slow)
        motor_x = xp.tanh(motor_x)
        motor = _to_np(motor_x).astype(np.float32)
        self.last_motor = motor
        self.t += DT_MS
        info = {
            "t_ms": self.t, "n_spikes": n_sp,
            "mean_rate": float(_to_np(self.rate.mean())),
            "mean_rate_slow": float(_to_np(self.rate_slow.mean())),
            "mean_gain": float(_to_np(self.gain.mean())),
            "total_spikes": self.total_spikes, "steps": self.steps,
            "n_hidden": N_HIDDEN, "n_cols": N_COLS, "backend": self.backend,
            "motor": {MOTOR_NAMES[i]: float(motor[i]) for i in range(min(N_MOTOR, motor.size))},
            "motor_vec": motor.copy(),
        }
        return motor, info

    def decide(self, motor: np.ndarray, threshold: float = 0.11) -> list:
        active = [MOTOR_NAMES[i] for i in range(min(len(MOTOR_NAMES), motor.size)) if motor[i] > threshold]
        pairs = [("forward", "back"), ("left", "right"), ("look_left", "look_right"),
                 ("look_up", "look_down"), ("scroll_up", "scroll_down")]
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
        payload = {
            "W_in": _to_np(self.W_in).astype(np.float32),
            "W_out": _to_np(self.W_out).astype(np.float32),
            "gain": _to_np(self.gain).astype(np.float32),
            "n_hidden": np.array([N_HIDDEN]),
            "n_cols": np.array([N_COLS]),
            "col_size": np.array([COL_SIZE]),
        }
        for c, W in enumerate(self.W_cols):
            payload[f"W_col_{c}"] = _to_np(W).astype(np.float32)
        np.savez_compressed(path, **payload)

    def load_weights(self, path=WEIGHTS_PATH) -> bool:
        path = Path(path)
        if not path.is_file():
            return False
        try:
            data = np.load(path)
            if data["W_in"].shape != (N_HIDDEN, N_SENSORY):
                return False
            if data["W_out"].shape != (N_MOTOR, N_HIDDEN):
                return False
            xp = _xp
            self.W_in = xp.asarray(data["W_in"].astype(np.float32))
            self.W_out = xp.asarray(data["W_out"].astype(np.float32))
            if "gain" in data and data["gain"].shape == (N_HIDDEN,):
                self.gain = xp.asarray(data["gain"].astype(np.float32))
            for c in range(N_COLS):
                key = f"W_col_{c}"
                if key in data and c < len(self.W_cols):
                    if data[key].shape == self.W_cols[c].shape:
                        self.W_cols[c] = xp.asarray(data[key].astype(np.float32))
            return True
        except Exception:
            return False
