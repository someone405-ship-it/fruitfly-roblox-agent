"""Permanent fly stats — luck, food, items, power… max caps + death: 0=HURT, 1+=lose."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from .config import STATS_PATH, STAT_MAX

STAT_ORDER = [
    "luck", "food", "items", "power", "speed",
    "rage", "shield", "vitality", "focus", "grit",
]

STAT_LABELS = {
    "luck": "LUCK",
    "food": "FOOD",
    "items": "ITEMS",
    "power": "POWER",
    "speed": "SPEED",
    "rage": "RAGE",
    "shield": "SHIELD",
    "vitality": "VITALITY",
    "focus": "FOCUS",
    "grit": "GRIT",
}

EVENT_REWARDS = {
    "kill": {"luck": 1, "power": 2, "rage": 3, "items": 1, "grit": 1},
    "portal": {"focus": 2, "luck": 1, "grit": 1},
    "join": {"focus": 1, "items": 1},
    "mistake": {"grit": 2, "focus": 1},
    "avoid": {"focus": 1, "luck": 1},
    "heal": {"vitality": 3, "food": -1},
    "loot_food": {"food": 1},
    "loot_food_x2": {"food": 2, "luck": 1},
    "loot_food_feast": {"food": 3, "luck": 2},
    "loot_speed": {"speed": 5, "items": 1},
    "loot_rage": {"rage": 5, "items": 1},
    "loot_heal": {"vitality": 5},
    "loot_shield": {"shield": 5, "items": 1},
    "loot_jackpot": {"food": 3, "luck": 5, "power": 5, "speed": 5, "rage": 5, "items": 2},
    "death": {
        "vitality": -12,
        "food": -4,
        "power": -5,
        "rage": -6,
        "speed": -4,
        "shield": -5,
        "luck": -2,
        "items": -1,
        "focus": -2,
        "grit": 1,
    },
}

MAX_LINES = [
    "MAX — you're already at the ceiling on {stat}.",
    "MAX & POWERFUL — {stat} can't go higher.",
    "STAT CAP — {stat} is full. no more of that.",
    "you're maxed on {stat}. spend it or flex it.",
    "PEAK {stat} — nothing more to gain here.",
]

DEATH_LINES = [
    "DEATH — unrewarded. lost food, power, rage, speed, shield.",
    "YOU DIED — stats stripped. earn them back.",
    "DOWN — unreward hit. vitality and loot took the fall.",
    "DEATH PENALTY — no reward, only loss.",
]


class FlyStats:
    def __init__(self, path: str = STATS_PATH) -> None:
        self.path = Path(path)
        self.values: Dict[str, float] = {k: 0.0 for k in STAT_ORDER}
        self.lifetime_gained: Dict[str, float] = {k: 0.0 for k in STAT_ORDER}
        self.maxed_counts: Dict[str, int] = {k: 0 for k in STAT_ORDER}
        self.deaths = 0
        self.last_messages: List[str] = []
        self.last_reward_log: List[str] = []
        self.all_max_announced = False
        self._last_death_at = 0.0
        self._last_hurt: List[str] = []
        self.load()

    def load(self) -> bool:
        if not self.path.is_file():
            return False
        try:
            d = json.loads(self.path.read_text(encoding="utf-8"))
            for k in STAT_ORDER:
                self.values[k] = float(d.get("values", {}).get(k, 0.0))
                self.lifetime_gained[k] = float(d.get("lifetime", {}).get(k, 0.0))
                self.maxed_counts[k] = int(d.get("maxed_counts", {}).get(k, 0))
            self.all_max_announced = bool(d.get("all_max_announced", False))
            self.deaths = int(d.get("deaths", 0))
            return True
        except Exception:
            return False

    def save(self) -> None:
        payload = {
            "values": self.values,
            "lifetime": self.lifetime_gained,
            "maxed_counts": self.maxed_counts,
            "all_max_announced": self.all_max_announced,
            "deaths": self.deaths,
            "updated": time.time(),
        }
        self.path.write_text(json.dumps(payload, indent=0), encoding="utf-8")

    def max_for(self, name: str) -> float:
        return float(STAT_MAX.get(name, 100))

    def is_max(self, name: str) -> bool:
        return float(self.values.get(name, 0.0)) >= self.max_for(name) - 1e-6

    def all_max(self) -> bool:
        return all(self.is_max(k) for k in STAT_ORDER)

    def _msg_max(self, name: str) -> str:
        i = self.maxed_counts.get(name, 0) % len(MAX_LINES)
        return MAX_LINES[i].format(stat=STAT_LABELS.get(name, name.upper()))

    def grant(self, name: str, amount: float) -> Tuple[float, Optional[str]]:
        if name not in self.values:
            return 0.0, None
        if amount == 0:
            return 0.0, None

        if amount < 0:
            before = float(self.values[name])
            # 0 stat → cannot lose more → HURT signal
            if before <= 0.0:
                self.save()
                return 0.0, f"HURT:{name}"
            # 1+ → lose stat (floor at 0)
            self.values[name] = max(0.0, before + amount)
            delta = self.values[name] - before
            self.save()
            return delta, None

        if self.is_max(name):
            self.maxed_counts[name] = int(self.maxed_counts.get(name, 0)) + 1
            msg = self._msg_max(name)
            self.last_messages.append(msg)
            if len(self.last_messages) > 12:
                self.last_messages.pop(0)
            if self.all_max() and not self.all_max_announced:
                self.all_max_announced = True
                big = "ALL STATS MAX — you're fully powered. nothing left to stack. absolute peak."
                self.last_messages.append(big)
                msg = big
            self.save()
            return 0.0, msg

        cap = self.max_for(name)
        before = self.values[name]
        room = cap - before
        applied = min(float(amount), room)
        self.values[name] = before + applied
        self.lifetime_gained[name] = float(self.lifetime_gained.get(name, 0.0)) + applied

        msg = None
        if self.is_max(name):
            self.maxed_counts[name] = int(self.maxed_counts.get(name, 0)) + 1
            msg = f"{STAT_LABELS.get(name, name)} hit MAX — you're powerful here."
            self.last_messages.append(msg)
            if self.all_max() and not self.all_max_announced:
                self.all_max_announced = True
                big = "ALL STATS MAX — you're fully powered. nothing left to stack. absolute peak."
                self.last_messages.append(big)
                msg = big

        self.save()
        return applied, msg

    def on_death(self) -> Dict[str, Any]:
        """Roblox death — lose stats if >=1; HURT if already 0. Debounced."""
        now = time.time()
        if now - self._last_death_at < 2.5:
            return {"event": "death", "applied": {}, "hurt": [], "messages": [], "line": "", "skipped": True}
        self._last_death_at = now
        self.deaths += 1

        table = EVENT_REWARDS.get("death", {})
        applied: Dict[str, float] = {}
        hurt: List[str] = []
        for k, amt in table.items():
            if float(amt) >= 0:
                delta, msg = self.grant(k, float(amt))
                if abs(delta) > 1e-9:
                    applied[k] = delta
                continue
            before = float(self.values.get(k, 0.0))
            if before <= 0.0:
                hurt.append(k)
            else:
                delta, msg = self.grant(k, float(amt))
                if abs(delta) > 1e-9:
                    applied[k] = delta
                elif msg and str(msg).startswith("HURT:"):
                    hurt.append(k)
        line_idx = self.deaths % len(DEATH_LINES)
        death_msg = DEATH_LINES[line_idx]
        parts = []
        if applied:
            parts.append("lost " + " ".join(
                f"{STAT_LABELS.get(k, k)}{delta:+.0f}" for k, delta in applied.items()
            ))
        if hurt:
            parts.append("HURT (0-stat) " + ",".join(STAT_LABELS.get(k, k) for k in hurt))
        if parts:
            death_msg = death_msg + " | " + " | ".join(parts)
        self.last_messages.append(death_msg)
        self.last_reward_log.append(death_msg)
        self._last_hurt = list(hurt)
        self.save()
        return {
            "event": "death",
            "applied": applied,
            "hurt": hurt,
            "messages": [death_msg],
            "line": death_msg,
            "deaths": self.deaths,
            "snapshot": self.snapshot(),
        }

    def reward_event(self, event: str) -> Dict[str, Any]:
        if event == "death":
            return self.on_death()

        table = EVENT_REWARDS.get(event, {})
        applied: Dict[str, float] = {}
        messages: List[str] = []
        blocked: List[str] = []
        for k, amt in table.items():
            delta, msg = self.grant(k, float(amt))
            if abs(delta) > 1e-9:
                applied[k] = delta
            if msg:
                messages.append(msg)
                if "MAX" in msg.upper() or "CAP" in msg.upper() or "peak" in msg.lower():
                    blocked.append(k)
                if str(msg).startswith("HURT:"):
                    messages.append(f"HURT — {STAT_LABELS.get(k, k)} was 0, took damage instead of losing stat.")
        line = ""
        if applied:
            parts = [f"{STAT_LABELS.get(k, k)}{delta:+.0f}" for k, delta in applied.items()]
            line = "stats " + " ".join(parts)
            self.last_reward_log.append(line)
            if len(self.last_reward_log) > 20:
                self.last_reward_log.pop(0)
        return {
            "event": event,
            "applied": applied,
            "messages": messages,
            "blocked": blocked,
            "line": line,
            "snapshot": self.snapshot(),
        }

    def snapshot(self) -> Dict[str, Any]:
        bars = {}
        for k in STAT_ORDER:
            mx = self.max_for(k)
            v = float(self.values.get(k, 0.0))
            bars[k] = {
                "value": v,
                "max": mx,
                "pct": (v / mx) if mx > 0 else 0.0,
                "maxed": v >= mx - 1e-6,
                "label": STAT_LABELS.get(k, k.upper()),
            }
        return {
            "bars": bars,
            "all_max": self.all_max(),
            "power_score": self.power_score(),
            "deaths": self.deaths,
        }

    def power_score(self) -> float:
        total = 0.0
        for k in STAT_ORDER:
            mx = self.max_for(k)
            total += float(self.values.get(k, 0.0)) / mx if mx else 0.0
        return float(total / max(1, len(STAT_ORDER)))

    def motor_mult(self) -> Dict[str, float]:
        def n(name: str) -> float:
            mx = self.max_for(name)
            return float(self.values.get(name, 0.0)) / mx if mx else 0.0

        return {
            "look": 1.0 + 0.25 * n("focus") + 0.15 * n("luck"),
            "move": 1.0 + 0.30 * n("speed") + 0.10 * n("power"),
            "attack": 1.0 + 0.35 * n("rage") + 0.15 * n("power"),
            "tank": 1.0 + 0.40 * n("shield") + 0.20 * n("vitality"),
            "loot_luck": 1.0 + 0.50 * n("luck"),
            "decide": max(0.55, 1.0 - 0.25 * n("focus") - 0.15 * n("grit")),
        }

    def take_messages(self) -> List[str]:
        out = list(self.last_messages)
        self.last_messages.clear()
        return out

    def summary(self) -> str:
        bits = [f"{STAT_LABELS[k][:1]}{int(self.values[k])}" for k in STAT_ORDER]
        peak = " MAXED" if self.all_max() else ""
        return "stats[" + " ".join(bits) + f"] d={self.deaths}" + peak


_STATS: Optional[FlyStats] = None


def get_stats() -> FlyStats:
    global _STATS
    if _STATS is None:
        _STATS = FlyStats()
    return _STATS
