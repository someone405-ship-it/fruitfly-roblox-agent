"""Kill rewards — gamble table + fly stats grants."""
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

DROP_TO_STAT_EVENT = {
    "food": "loot_food",
    "food_x2": "loot_food_x2",
    "food_feast": "loot_food_feast",
    "speed_candy": "loot_speed",
    "rage_candy": "loot_rage",
    "heal_bit": "loot_heal",
    "shield_bit": "loot_shield",
    "jackpot": "loot_jackpot",
}


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
        self.last_stat_messages: List[str] = []

    def weights(self) -> Tuple[List[str], np.ndarray]:
        names = [x[0] for x in LOOT_TABLE]
        w = np.array([x[1] for x in LOOT_TABLE], dtype=np.float64)
        # luck from stats boosts rare drops slightly
        try:
            from .stats import get_stats
            luck = get_stats().motor_mult().get("loot_luck", 1.0)
            # boost non-food slightly with luck
            for i, n in enumerate(names):
                if n != "food":
                    w[i] *= float(luck)
        except Exception:
            pass
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

        # permanent stats
        stat_result = {}
        try:
            from .stats import get_stats
            st = get_stats()
            st.reward_event("kill")
            ev = DROP_TO_STAT_EVENT.get(name)
            if ev:
                stat_result = st.reward_event(ev)
            self.last_stat_messages = st.take_messages()
        except Exception:
            self.last_stat_messages = []

        return {
            "kill": True, "drop": name, "food_gain": food_gain,
            "food_total": self.food, "kills": self.kills, "heal": heal, "payload": payload,
            "stat_result": stat_result,
            "stat_messages": list(self.last_stat_messages),
        }

    def spend_food(self, n: int = 1) -> bool:
        if self.food >= n:
            self.food -= n
            try:
                from .stats import get_stats
                get_stats().grant("food", -float(n))
            except Exception:
                pass
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
        out = {
            "kills": self.kills, "food": self.food, "food_earned": self.total_food_earned,
            "last_drop": self.last_drop or "",
            "buff_speed": b["speed"], "buff_rage": b["rage"], "buff_shield": b["shield"],
        }
        try:
            from .stats import get_stats
            out["fly_stats"] = get_stats().snapshot()
        except Exception:
            pass
        return out
