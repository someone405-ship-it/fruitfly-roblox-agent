"""Process-wide reflex force-actions + motor bias (read by motor every tick)."""
from __future__ import annotations
from typing import List, Set, Optional
import numpy as np
from .config import N_MOTOR

_FORCE: Set[str] = set()
_BIAS = np.zeros(N_MOTOR, dtype=np.float32)
_NOTES: List[str] = []
_THRESHOLD = 0.09
_LOOK_SENS = 110.0
_LOOK_MAX = 185


def publish(
    force: Set[str],
    bias,
    notes: Optional[List[str]] = None,
    threshold: float = 0.09,
    look_sens: float = 110.0,
    look_max: int = 185,
) -> None:
    global _FORCE, _BIAS, _NOTES, _THRESHOLD, _LOOK_SENS, _LOOK_MAX
    _FORCE = set(force or set())
    b = np.asarray(bias, dtype=np.float32).ravel()
    if b.size < N_MOTOR:
        pad = np.zeros(N_MOTOR, dtype=np.float32)
        pad[: b.size] = b
        b = pad
    _BIAS = b[:N_MOTOR].copy()
    _NOTES = list(notes or [])
    _THRESHOLD = float(threshold)
    _LOOK_SENS = float(look_sens)
    _LOOK_MAX = int(look_max)


def get_force() -> Set[str]:
    return set(_FORCE)


def get_bias() -> np.ndarray:
    return _BIAS.copy()


def get_notes() -> List[str]:
    return list(_NOTES)


def get_threshold() -> float:
    return float(_THRESHOLD)


def get_look() -> tuple:
    return float(_LOOK_SENS), int(_LOOK_MAX)
