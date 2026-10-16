"""Permanent mistake + win memory — never repeat the same failure."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import numpy as np
from .config import MISTAKE_MEMORY_PATH, WIN_MEMORY_PATH, N_MOTOR, MOTOR_NAMES

# Hard rules always enforced (also written into mistake file on first fire)
HARD_RULES = [
    {
        "id": "no_fight_outside_arena",
        "when": {"need_portal": True},
        "ban_actions": ["secondary", "interact", "reset", "camera"],
        "reason": "fought before portal — death/waste",
    },
    {
        "id": "no_forward_into_water",
        "when": {"water_high": True},
        "ban_actions": ["forward", "sprint"],
        "prefer_actions": ["back", "left", "right"],
        "reason": "walked into water and died",
    },
]


def _ctx_from_meta_notes(meta: dict, notes: List[str]) -> Dict[str, float]:
    return {
        "threat": float(meta.get("threat_score", 0.0) or 0.0),
        "loom": float(meta.get("loom_score", 0.0) or 0.0),
        "motion": float(meta.get("motion", 0.0) or 0.0),
        "portal": float(meta.get("portal_score", 0.0) or 0.0),
        "water": float(meta.get("water_score", 0.0) or 0.0),
        "lobby": float(meta.get("lobby_score", 0.0) or 0.0),
        "rail": float(meta.get("rail_score", 0.0) or 0.0),
        "need_portal": 1.0 if "need_portal" in notes else 0.0,
        "in_arena": 1.0 if "in_arena" in notes else 0.0,
        "water_high": 1.0 if float(meta.get("water_score", 0.0) or 0.0) > 0.4 else 0.0,
    }


def _ctx_distance(a: dict, b: dict) -> float:
    keys = ("threat", "loom", "motion", "portal", "water", "lobby", "rail", "need_portal", "in_arena", "water_high")
    d = 0.0
    for k in keys:
        d += abs(float(a.get(k, 0.0)) - float(b.get(k, 0.0)))
    return d


class MistakeMemory:
    """Stores failures forever; suppresses the same motor pattern in similar context."""

    def __init__(self, path: str = MISTAKE_MEMORY_PATH) -> None:
        self.path = Path(path)
        self.mistakes: List[Dict[str, Any]] = []
        self.banned_rules: Set[str] = set()
        self.stats = {"total_recorded": 0, "total_avoids": 0, "saves": 0}
        self.load()

    def load(self) -> bool:
        if not self.path.is_file():
            return False
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.mistakes = data.get("mistakes", [])
            self.banned_rules = set(data.get("banned_rules", []))
            self.stats = data.get("stats", self.stats)
            return True
        except Exception:
            return False

    def save(self) -> None:
        payload = {
            "version": 1,
            "updated": time.time(),
            "mistakes": self.mistakes[-600:],
            "banned_rules": sorted(self.banned_rules),
            "stats": {**self.stats, "saves": int(self.stats.get("saves", 0)) + 1},
        }
        self.path.write_text(json.dumps(payload, indent=0), encoding="utf-8")
        self.stats = payload["stats"]

    def record(
        self,
        kind: str,
        notes: List[str],
        meta: dict,
        motor: np.ndarray,
        actions: Optional[List[str]] = None,
    ) -> None:
        ctx = _ctx_from_meta_notes(meta, notes)
        m = np.asarray(motor, dtype=np.float32).ravel()
        if m.size < N_MOTOR:
            pad = np.zeros(N_MOTOR, dtype=np.float32)
            pad[: m.size] = m
            m = pad
        entry = {
            "t": time.time(),
            "kind": kind,
            "notes": list(notes)[:20],
            "actions": list(actions or [])[:16],
            "motor": [float(x) for x in m[:N_MOTOR]],
            "context": ctx,
            "count": 1,
        }
        # merge near-duplicates (same kind + close context)
        for old in self.mistakes[-80:]:
            if old.get("kind") == kind and _ctx_distance(old.get("context", {}), ctx) < 0.35:
                old["count"] = int(old.get("count", 1)) + 1
                old["t"] = time.time()
                old["motor"] = entry["motor"]
                old["notes"] = entry["notes"]
                self.stats["total_recorded"] = int(self.stats.get("total_recorded", 0)) + 1
                if self.stats["total_recorded"] % 3 == 0:
                    self.save()
                return
        self.mistakes.append(entry)
        self.stats["total_recorded"] = int(self.stats.get("total_recorded", 0)) + 1
        # promote recurring kinds into permanent ban rules
        if kind in ("death", "water_death", "fight_before_portal"):
            self.banned_rules.add(kind)
        self.save()

    def avoid_bias(self, meta: dict, notes: List[str], strength: float = 0.85) -> np.ndarray:
        """Negative motor bias for patterns that failed in similar contexts."""
        out = np.zeros(N_MOTOR, dtype=np.float32)
        ctx = _ctx_from_meta_notes(meta, notes)
        hits = 0
        for m in self.mistakes[-400:]:
            d = _ctx_distance(m.get("context", {}), ctx)
            if d > 0.9:
                continue
            w = (1.0 / (0.25 + d)) * (0.5 + 0.15 * min(8, int(m.get("count", 1))))
            vec = np.asarray(m.get("motor", []), dtype=np.float32)
            if vec.size < N_MOTOR:
                pad = np.zeros(N_MOTOR, dtype=np.float32)
                pad[: vec.size] = vec
                vec = pad
            # push AWAY from the bad motor pattern
            out -= w * vec[:N_MOTOR]
            hits += 1
        if hits:
            self.stats["total_avoids"] = int(self.stats.get("total_avoids", 0)) + 1
            nrm = float(np.linalg.norm(out)) + 1e-6
            out = (out / nrm) * strength
        return out.astype(np.float32)

    def ban_actions(self, meta: dict, notes: List[str]) -> Set[str]:
        """Hard action bans from rules + learned mistakes."""
        banned: Set[str] = set()
        need_portal = "need_portal" in notes or not ("in_arena" in notes)
        water_high = float(meta.get("water_score", 0.0) or 0.0) > 0.4

        for rule in HARD_RULES:
            when = rule.get("when", {})
            ok = True
            if when.get("need_portal") and not need_portal:
                ok = False
            if when.get("water_high") and not water_high:
                ok = False
            if ok:
                banned.update(rule.get("ban_actions", []))

        # learned permanent bans
        if "fight_before_portal" in self.banned_rules and need_portal:
            banned.update({"secondary", "interact", "reset", "camera"})
        if "water_death" in self.banned_rules and water_high:
            banned.update({"forward", "sprint"})

        # recent identical mistake kinds in this context
        ctx = _ctx_from_meta_notes(meta, notes)
        for m in self.mistakes[-100:]:
            if _ctx_distance(m.get("context", {}), ctx) > 0.5:
                continue
            if int(m.get("count", 1)) < 2:
                continue
            for a in m.get("actions", []):
                if a in MOTOR_NAMES:
                    banned.add(a)
        return banned

    def prefer_actions(self, meta: dict, notes: List[str]) -> Set[str]:
        prefer: Set[str] = set()
        water_high = float(meta.get("water_score", 0.0) or 0.0) > 0.4
        if water_high:
            prefer.update({"back", "left", "right", "jump"})
        if "need_portal" in notes:
            prefer.update({"forward", "sprint", "rmb_look"})
        return prefer

    def summary(self) -> str:
        return (
            f"mistakes={len(self.mistakes)} bans={len(self.banned_rules)} "
            f"avoids={self.stats.get('total_avoids', 0)}"
        )


class WinMemory:
    """Stores successful patterns forever — reinforce what worked."""

    def __init__(self, path: str = WIN_MEMORY_PATH) -> None:
        self.path = Path(path)
        self.wins: List[Dict[str, Any]] = []
        self.stats = {"total": 0, "saves": 0}
        self.load()

    def load(self) -> bool:
        if not self.path.is_file():
            return False
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.wins = data.get("wins", [])
            self.stats = data.get("stats", self.stats)
            return True
        except Exception:
            return False

    def save(self) -> None:
        payload = {
            "version": 1,
            "updated": time.time(),
            "wins": self.wins[-500:],
            "stats": {**self.stats, "saves": int(self.stats.get("saves", 0)) + 1},
        }
        self.path.write_text(json.dumps(payload, indent=0), encoding="utf-8")
        self.stats = payload["stats"]

    def record(self, kind: str, notes: List[str], meta: dict, motor: np.ndarray) -> None:
        ctx = _ctx_from_meta_notes(meta, notes)
        m = np.asarray(motor, dtype=np.float32).ravel()
        if m.size < N_MOTOR:
            pad = np.zeros(N_MOTOR, dtype=np.float32)
            pad[: m.size] = m
            m = pad
        self.wins.append({
            "t": time.time(),
            "kind": kind,
            "notes": list(notes)[:16],
            "motor": [float(x) for x in m[:N_MOTOR]],
            "context": ctx,
        })
        self.stats["total"] = int(self.stats.get("total", 0)) + 1
        if self.stats["total"] % 4 == 0:
            self.save()

    def boost_bias(self, meta: dict, notes: List[str], strength: float = 0.35) -> np.ndarray:
        out = np.zeros(N_MOTOR, dtype=np.float32)
        ctx = _ctx_from_meta_notes(meta, notes)
        n = 0
        for w in self.wins[-300:]:
            d = _ctx_distance(w.get("context", {}), ctx)
            if d > 0.85:
                continue
            weight = 1.0 / (0.3 + d)
            vec = np.asarray(w.get("motor", []), dtype=np.float32)
            if vec.size < N_MOTOR:
                pad = np.zeros(N_MOTOR, dtype=np.float32)
                pad[: vec.size] = vec
                vec = pad
            out += weight * vec[:N_MOTOR]
            n += 1
        if n:
            out /= max(1.0, float(n))
            out *= strength
        return out.astype(np.float32)

    def summary(self) -> str:
        return f"wins={len(self.wins)}"
