"""Permanent skill memory — learned patterns saved forever and reused."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np
from .config import SKILL_MEMORY_PATH, N_MOTOR, MOTOR_NAMES


class SkillMemory:
    """Stores host-learned action sequences + context tags permanently."""

    def __init__(self, path: str = SKILL_MEMORY_PATH) -> None:
        self.path = Path(path)
        self.skills: List[Dict[str, Any]] = []
        self.stats = {"total_saves": 0, "total_loads": 0, "last_save": 0.0}
        self.load()

    def load(self) -> bool:
        if not self.path.is_file():
            return False
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.skills = data.get("skills", [])
            self.stats = data.get("stats", self.stats)
            self.stats["total_loads"] = int(self.stats.get("total_loads", 0)) + 1
            return True
        except Exception:
            return False

    def save(self) -> None:
        payload = {
            "version": 2,
            "updated": time.time(),
            "skills": self.skills[-800:],  # keep last 800 skills forever-ish
            "stats": {**self.stats, "total_saves": int(self.stats.get("total_saves", 0)) + 1, "last_save": time.time()},
        }
        self.path.write_text(json.dumps(payload, indent=0), encoding="utf-8")
        self.stats = payload["stats"]

    def record(
        self,
        keys: List[str],
        motor_target: np.ndarray,
        meta: Optional[dict] = None,
        tag: str = "host",
    ) -> None:
        if not keys and float(np.abs(motor_target).sum()) < 0.05:
            return
        entry = {
            "t": time.time(),
            "tag": tag,
            "keys": list(keys)[:12],
            "motor": [float(x) for x in np.asarray(motor_target, dtype=np.float32).ravel()[:N_MOTOR]],
            "context": {
                "threat": float((meta or {}).get("threat_score", 0.0)),
                "loom": float((meta or {}).get("loom_score", 0.0)),
                "motion": float((meta or {}).get("motion", 0.0)),
                "food": float((meta or {}).get("food_score", 0.0)),
                "portal": float((meta or {}).get("portal_score", 0.0)),
            },
        }
        self.skills.append(entry)
        if len(self.skills) % 25 == 0:
            self.save()

    def nearest(self, meta: dict, k: int = 5) -> List[Dict[str, Any]]:
        if not self.skills:
            return []
        threat = float(meta.get("threat_score", 0.0))
        loom = float(meta.get("loom_score", 0.0))
        motion = float(meta.get("motion", 0.0))
        scored = []
        for s in self.skills[-400:]:
            c = s.get("context", {})
            d = (
                abs(float(c.get("threat", 0)) - threat)
                + abs(float(c.get("loom", 0)) - loom)
                + abs(float(c.get("motion", 0)) - motion) * 0.5
            )
            scored.append((d, s))
        scored.sort(key=lambda x: x[0])
        return [s for _, s in scored[:k]]

    def motor_bias_from_memory(self, meta: dict, strength: float = 0.35) -> np.ndarray:
        """Blend nearest learned motors into current decision."""
        near = self.nearest(meta, k=4)
        out = np.zeros(N_MOTOR, dtype=np.float32)
        if not near:
            return out
        wsum = 0.0
        for i, s in enumerate(near):
            w = 1.0 / (1.0 + i * 0.6)
            m = np.asarray(s.get("motor", []), dtype=np.float32)
            if m.size < N_MOTOR:
                pad = np.zeros(N_MOTOR, dtype=np.float32)
                pad[: m.size] = m
                m = pad
            out += w * m[:N_MOTOR]
            wsum += w
        if wsum > 1e-6:
            out /= wsum
        return (out * strength).astype(np.float32)

    def summary(self) -> str:
        return f"skills={len(self.skills)} saves={self.stats.get('total_saves', 0)}"
