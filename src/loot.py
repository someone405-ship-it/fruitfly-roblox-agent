"""Kill rewards — gamble table, mostly food."""
from __future__ import annotations
import time
from typing import Dict, List, Optional, Tuple
import numpy as np

LOOT_TABLE = [
    ("food", 55, {"food": 1}),
    ("food_x2", 15, {"food": 2}),
    ("food_feast", 8, {"food": 3}),
    ("speed_candy", 8, {"speed": 8.0}),
    ("rage_candy", 6, {"rage": 10.0, "food": 1}),
    ("heal_bit", 5, {"heal": 0.35}),
    ("shield_bit", 2, {"shield": 6.0}),
    ("jackpot", 1, {"food": 5, "speed": 12.0, "rage": 12.0, "heal": 0.5}),
]


class KillLootSystem:
    def __init__(self, seed: int = 21) -> None:
        self.rng = np.random.default_rng(seed)
        self.kills = 0
        self.food = 0
        self.total_food_earned = 0
        self.buff_speed_until = 0.0
        self.buff_rage_until = 0.0
        self.buff_shield_until = 0.0
        self.last_drop: Optional[str] = None
        self.last_drop_at = 0.0
        self.history: List[str] = []

    def weights(self) -> Tuple[List[str], np.ndarray]:
        names = [x[0] for x in LOOT_TABLE]
        w = np.array([x[1] for x in LOOT_TABLE], dtype=np.float64)
        w = w / w.sum()
        return names, w

    def roll(self) -> str:
        names, w = self.weights()
        return str(self.rng.choice(names, p=w))

    def on_kill(self) -> Dict:
        now = time.time()
        self.kills += 1
        name = self.roll()
        payload = dict(next(p for n, _, p in LOOT_TABLE if n == name))
        food_gain = int(payload.get("food", 0))
        self.food += food_gain
        self.total_food_earned += food_gain
        if "speed" in payload:
            self.buff_speed_until = max(self.buff_speed_until, now + float(payload["speed"]))
        if "rage" in payload:
            self.buff_rage_until = max(self.buff_rage_until, now + float(payload["rage"]))
        if "shield" in payload:
            self.buff_shield_until = max(self.buff_shield_until, now + float(payload["shield"]))
        heal = float(payload.get("heal", 0.0))
        self.last_drop = name
        self.last_drop_at = now
        self.history.append(name)
        if len(self.history) > 30:
            self.history.pop(0)
        return {
            "kill": True, "drop": name, "food_gain": food_gain,
            "food_total": self.food, "kills": self.kills, "heal": heal, "payload": payload,
        }

    def spend_food(self, n: int = 1) -> bool:
        if self.food >= n:
            self.food -= n
            return True
        return False

    def active_buffs(self, now: Optional[float] = None) -> Dict[str, float]:
        now = now or time.time()
        return {
            "speed": max(0.0, self.buff_speed_until - now),
            "rage": max(0.0, self.buff_rage_until - now),
            "shield": max(0.0, self.buff_shield_until - now),
        }

    def snapshot(self) -> Dict:
        b = self.active_buffs()
        return {
            "kills": self.kills, "food": self.food, "food_earned": self.total_food_earned,
            "last_drop": self.last_drop or "",
            "buff_speed": b["speed"], "buff_rage": b["rage"], "buff_shield": b["shield"],
        }
