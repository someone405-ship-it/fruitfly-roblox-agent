"""Potential unlock — permanent growth that speeds decisions and motor authority."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Dict
from .config import (
    POTENTIAL_PATH, POWER_TIERS,
    DECIDE_THRESHOLD_BASE, DECIDE_THRESHOLD_MIN,
    LOOK_SENSITIVITY, LOOK_MAX_PX,
)


class PotentialCore:
    """Tracks lifetime progress; unlocks faster decide + stronger motor."""

    def __init__(self, path: str = POTENTIAL_PATH) -> None:
        self.path = Path(path)
        self.kills = 0
        self.deaths = 0
        self.portals = 0
        self.joins = 0
        self.mistakes_logged = 0
        self.avoids = 0
        self.play_seconds = 0.0
        self.xp = 0.0
        self.level = 0
        self.unlocked = {
            "snap_aim": False,
            "reflex_loom": False,
            "reflex_portal": False,
            "reflex_water": False,
            "fast_decide": False,
            "overdrive_keys": False,
            "limit_break": False,
        }
        self._session_t0 = time.time()
        self._last_save = 0.0
        self.load()

    def load(self) -> bool:
        if not self.path.is_file():
            return False
        try:
            d = json.loads(self.path.read_text(encoding="utf-8"))
            self.kills = int(d.get("kills", 0))
            self.deaths = int(d.get("deaths", 0))
            self.portals = int(d.get("portals", 0))
            self.joins = int(d.get("joins", 0))
            self.mistakes_logged = int(d.get("mistakes_logged", 0))
            self.avoids = int(d.get("avoids", 0))
            self.play_seconds = float(d.get("play_seconds", 0.0))
            self.xp = float(d.get("xp", 0.0))
            self.level = int(d.get("level", 0))
            self.unlocked.update(d.get("unlocked", {}))
            return True
        except Exception:
            return False

    def save(self) -> None:
        payload: Dict[str, Any] = {
            "kills": self.kills,
            "deaths": self.deaths,
            "portals": self.portals,
            "joins": self.joins,
            "mistakes_logged": self.mistakes_logged,
            "avoids": self.avoids,
            "play_seconds": self.play_seconds,
            "xp": self.xp,
            "level": self.level,
            "unlocked": self.unlocked,
            "updated": time.time(),
        }
        self.path.write_text(json.dumps(payload, indent=0), encoding="utf-8")
        self._last_save = time.time()

    def tick(self, dt: float = 0.05) -> None:
        self.play_seconds += max(0.0, dt)
        self.xp += dt * 0.02
        self._recompute_level()
        if time.time() - self._last_save > 20.0:
            self.save()

    def on_event(self, kind: str) -> None:
        if kind == "kill":
            self.kills += 1
            self.xp += 8.0
        elif kind == "death":
            self.deaths += 1
            self.xp += 0.5
        elif kind == "portal":
            self.portals += 1
            self.xp += 3.0
        elif kind == "join":
            self.joins += 1
            self.xp += 2.0
        elif kind == "mistake":
            self.mistakes_logged += 1
            self.xp += 1.0
        elif kind == "avoid":
            self.avoids += 1
            self.xp += 0.4
        self._recompute_level()
        self.save()

    def _recompute_level(self) -> None:
        # soft level from xp
        self.level = int(self.xp ** 0.55)
        # feature unlocks by thresholds
        self.unlocked["reflex_water"] = self.deaths >= 1 or self.mistakes_logged >= 1
        self.unlocked["reflex_portal"] = self.portals >= 1 or self.level >= 2
        self.unlocked["reflex_loom"] = self.kills >= 1 or self.level >= 3
        self.unlocked["snap_aim"] = self.level >= 4 or self.kills >= 3
        self.unlocked["fast_decide"] = self.level >= 5 or self.avoids >= 10
        self.unlocked["overdrive_keys"] = self.level >= 8 or self.kills >= 10
        self.unlocked["limit_break"] = self.level >= 12 or self.kills >= 25

    def power_mult(self) -> float:
        mult = 1.0
        name = "dormant"
        for need, m, n in POWER_TIERS:
            if self.level >= need:
                mult, name = m, n
        if self.unlocked.get("limit_break"):
            mult = max(mult, 1.95)
        return float(mult)

    def power_name(self) -> str:
        name = "dormant"
        for need, _m, n in POWER_TIERS:
            if self.level >= need:
                name = n
        return name

    def decide_threshold(self) -> float:
        t = DECIDE_THRESHOLD_BASE
        if self.unlocked.get("fast_decide"):
            t *= 0.72
        if self.unlocked.get("overdrive_keys"):
            t *= 0.85
        if self.unlocked.get("limit_break"):
            t *= 0.8
        return float(max(DECIDE_THRESHOLD_MIN, t))

    def look_params(self) -> tuple:
        sens = LOOK_SENSITIVITY
        mx = LOOK_MAX_PX
        if self.unlocked.get("snap_aim"):
            sens *= 1.18
            mx = int(mx * 1.12)
        if self.unlocked.get("limit_break"):
            sens *= 1.12
            mx = int(mx * 1.08)
        return float(sens), int(mx)

    def summary(self) -> str:
        return (
            f"potential lv={self.level} xp={self.xp:.0f} "
            f"k={self.kills} d={self.deaths} p={self.portals} "
            f"power={self.power_name()} thr={self.decide_threshold():.3f}"
        )


# process-wide singleton for motor/trainer
_CORE: PotentialCore | None = None


def get_potential() -> PotentialCore:
    global _CORE
    if _CORE is None:
        _CORE = PotentialCore()
    return _CORE
