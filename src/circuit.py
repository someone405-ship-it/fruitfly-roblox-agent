"""Named FlyWire-style descending circuit (reduced, real-time).
Inspired by DenisSergeevitch/desktop-fly roles: loom→GF, DNp09, MDN, DNa, DNg11.
"""
from __future__ import annotations
import numpy as np
from typing import Dict

DT = 1.0
TAU_M = 12.0
V_TH = 0.6
V_RESET = 0.0
REFRACT = 2.0
N_LOOM, N_GF = 24, 2
N_STEER_L, N_STEER_R, N_FWD, N_REV, N_GROOM = 4, 4, 4, 4, 6
N_TOTAL = N_LOOM + N_GF + N_STEER_L + N_STEER_R + N_FWD + N_REV + N_GROOM

class FlyCircuit:
    def __init__(self, seed: int = 3) -> None:
        rng = np.random.default_rng(seed)
        self.rng = rng
        self.v = np.zeros(N_TOTAL, dtype=np.float32)
        self.refr = np.zeros(N_TOTAL, dtype=np.float32)
        self.spikes = np.zeros(N_TOTAL, dtype=np.float32)
        self.rate = np.zeros(N_TOTAL, dtype=np.float32)
        i = 0
        self.sl_loom = slice(i, i + N_LOOM); i += N_LOOM
        self.sl_gf = slice(i, i + N_GF); i += N_GF
        self.sl_sl = slice(i, i + N_STEER_L); i += N_STEER_L
        self.sl_sr = slice(i, i + N_STEER_R); i += N_STEER_R
        self.sl_fwd = slice(i, i + N_FWD); i += N_FWD
        self.sl_rev = slice(i, i + N_REV); i += N_REV
        self.sl_groom = slice(i, i + N_GROOM)
        self.W_loom_gf = rng.uniform(0.15, 0.35, size=(N_GF, N_LOOM)).astype(np.float32)

    def step(self, loom: float, forward_drive: float, turn: float, calm: float, n_sub: int = 20) -> Dict[str, float]:
        loom = float(np.clip(loom, 0, 1))
        forward_drive = float(np.clip(forward_drive, 0, 1))
        turn = float(np.clip(turn, -1, 1))
        calm = float(np.clip(calm, 0, 1))
        for _ in range(n_sub):
            I = np.zeros(N_TOTAL, dtype=np.float32)
            noise = 0.05 * self.rng.standard_normal(N_TOTAL).astype(np.float32)
            I[self.sl_loom] += 3.0 * loom + noise[self.sl_loom]
            I[self.sl_gf] += 2.2 * loom + (self.W_loom_gf @ self.spikes[self.sl_loom])
            gf_r = float(self.rate[self.sl_gf].mean())
            I[self.sl_fwd] += 2.0 * forward_drive - 1.2 * gf_r + noise[self.sl_fwd]
            I[self.sl_rev] += 1.8 * gf_r + 0.3 * max(0.0, -forward_drive)
            I[self.sl_sl] += 1.6 * max(0.0, -turn) + 0.4 * gf_r
            I[self.sl_sr] += 1.6 * max(0.0, turn) + 0.4 * gf_r
            I[self.sl_groom] += 1.4 * calm * (1.0 - loom) * (1.0 - min(1.0, gf_r * 3))
            active = self.refr <= 0
            self.v[active] += (-self.v[active] + I[active]) * (DT / TAU_M)
            self.refr = np.maximum(0.0, self.refr - DT)
            fired = (self.v >= V_TH) & active
            self.spikes = fired.astype(np.float32)
            self.v[fired] = V_RESET
            self.refr[fired] = REFRACT
            self.rate = 0.8 * self.rate + 0.2 * self.spikes
        def mr(sl):
            return float(self.rate[sl].mean())
        return {
            "loom_rate": mr(self.sl_loom), "gf_rate": mr(self.sl_gf),
            "steer_l": mr(self.sl_sl), "steer_r": mr(self.sl_sr),
            "forward": mr(self.sl_fwd), "reverse": mr(self.sl_rev),
            "groom": mr(self.sl_groom), "escape": mr(self.sl_gf) > 0.15,
        }

    def motor_bias(self, read: Dict[str, float]):
        from .config import N_MOTOR, MOTOR_NAMES
        b = np.zeros(N_MOTOR, dtype=np.float32)
        idx = {n: i for i, n in enumerate(MOTOR_NAMES)}
        b[idx["forward"]] += 1.3 * read["forward"] - 0.9 * read["reverse"]
        b[idx["back"]] += 1.3 * read["reverse"]
        b[idx["left"]] += 1.1 * read["steer_l"]
        b[idx["right"]] += 1.1 * read["steer_r"]
        b[idx["look_left"]] += 0.5 * read["steer_l"]
        b[idx["look_right"]] += 0.5 * read["steer_r"]
        if read["escape"]:
            b[idx["jump"]] += 1.6
            b[idx["back"]] += 0.9
            b[idx["forward"]] -= 1.2
        b[idx["sprint"]] += 0.35 * read["forward"]
        b[idx["crouch"]] += 0.25 * read["groom"]
        b[idx["emote"]] += 0.15 * read["groom"]
        return np.clip(b, -1.5, 1.5)
