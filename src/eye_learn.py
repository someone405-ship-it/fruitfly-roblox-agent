"""Visual (eye) imitation — learn from what you see + what you press."""
from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
from .config import EYE_MEMORY_PATH, N_SENSORY, N_MOTOR


class EyeMemory:
    """Stores paired (sensory, motor_target) snapshots from host play."""

    def __init__(self, path: str = EYE_MEMORY_PATH, max_pairs: int = 4000) -> None:
        self.path = Path(path)
        self.max_pairs = max_pairs
        self.sensory: Optional[np.ndarray] = None  # (N, N_SENSORY)
        self.targets: Optional[np.ndarray] = None  # (N, N_MOTOR)
        self.count = 0
        self.load()

    def load(self) -> bool:
        if not self.path.is_file():
            return False
        try:
            data = np.load(self.path)
            self.sensory = data["sensory"].astype(np.float32)
            self.targets = data["targets"].astype(np.float32)
            self.count = int(self.sensory.shape[0])
            return True
        except Exception:
            return False

    def save(self) -> None:
        if self.sensory is None or self.count == 0:
            return
        np.savez_compressed(
            self.path,
            sensory=self.sensory[: self.count],
            targets=self.targets[: self.count],
        )

    def record(self, sensory: np.ndarray, motor_target: np.ndarray) -> None:
        s = np.asarray(sensory, dtype=np.float32).ravel()
        t = np.asarray(motor_target, dtype=np.float32).ravel()
        if s.size != N_SENSORY:
            pad = np.zeros(N_SENSORY, dtype=np.float32)
            pad[: min(s.size, N_SENSORY)] = s[:N_SENSORY]
            s = pad
        if t.size != N_MOTOR:
            pad = np.zeros(N_MOTOR, dtype=np.float32)
            pad[: min(t.size, N_MOTOR)] = t[:N_MOTOR]
            t = pad
        if self.sensory is None:
            self.sensory = np.zeros((self.max_pairs, N_SENSORY), dtype=np.float32)
            self.targets = np.zeros((self.max_pairs, N_MOTOR), dtype=np.float32)
            self.count = 0
        if self.count >= self.max_pairs:
            # ring buffer — drop oldest 10%
            drop = self.max_pairs // 10
            self.sensory[:-drop] = self.sensory[drop:]
            self.targets[:-drop] = self.targets[drop:]
            self.count = self.max_pairs - drop
        self.sensory[self.count] = s
        self.targets[self.count] = t
        self.count += 1
        if self.count % 40 == 0:
            self.save()

    def nearest_target(self, sensory: np.ndarray, k: int = 5) -> np.ndarray:
        """Return blended motor target from nearest visual matches."""
        out = np.zeros(N_MOTOR, dtype=np.float32)
        if self.sensory is None or self.count < 3:
            return out
        s = np.asarray(sensory, dtype=np.float32).ravel()
        if s.size != N_SENSORY:
            pad = np.zeros(N_SENSORY, dtype=np.float32)
            pad[: min(s.size, N_SENSORY)] = s[:N_SENSORY]
            s = pad
        # subsample for speed
        n = self.count
        step = max(1, n // 800)
        idx = np.arange(0, n, step)
        bank = self.sensory[idx]
        diffs = bank - s[None, :]
        dists = np.einsum("ij,ij->i", diffs, diffs)
        k = min(k, dists.size)
        nearest = np.argpartition(dists, k - 1)[:k]
        w = 1.0 / (1e-3 + dists[nearest])
        w /= w.sum()
        for wi, ni in zip(w, nearest):
            out += float(wi) * self.targets[idx[ni]]
        return out.astype(np.float32)

    def summary(self) -> str:
        return f"eye_pairs={self.count}"
