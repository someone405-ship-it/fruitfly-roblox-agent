"""Instinct drives + free-will goal arbiter."""
from __future__ import annotations
import time
import math
from typing import Dict, List, Tuple
import numpy as np

GOALS = (
    "explore", "fight", "flee", "portal", "rail", "forage",
    "social", "browse", "rest", "parkour", "patrol", "hunt",
    "wander", "camera_look", "rejoin",
)


class InstinctCore:
    def __init__(self, seed: int = 7) -> None:
        rng = np.random.default_rng(seed)
        self.aggression = float(0.55 + 0.2 * rng.random())
        self.curiosity = float(0.65 + 0.25 * rng.random())
        self.caution = float(0.35 + 0.25 * rng.random())
        self.social = float(0.25 + 0.2 * rng.random())
        self.persistence = float(0.5 + 0.3 * rng.random())
        self.boredom = 0.2
        self.arousal = 0.4
        self.fatigue = 0.0
        self.novelty = 0.5
        self.confidence = 0.5
        self.last_goal = "explore"
        self.goal_since = time.time()
        self.goal_hist: List[str] = []
        self.success_counts = {g: 1 for g in GOALS}
        self.fail_counts = {g: 1 for g in GOALS}
        self._prev_hist = None
        self._idle_frames = 0
        self._look_phase = 0.0
        self.session_goals = 0

    def observe_vision(self, meta: dict, motion: float) -> None:
        b = float(meta.get("brightness", 0.5))
        if self._prev_hist is None:
            self._prev_hist = b
        delta = abs(b - self._prev_hist)
        self._prev_hist = b
        self.novelty = 0.85 * self.novelty + 0.15 * min(1.0, delta * 8)
        if motion < 0.015:
            self._idle_frames += 1
            self.boredom = min(1.0, self.boredom + 0.012)
            self.fatigue = min(1.0, self.fatigue + 0.004)
        else:
            self._idle_frames = 0
            self.boredom = max(0.0, self.boredom - 0.02)
            self.fatigue = max(0.0, self.fatigue - 0.01)
        self.arousal = 0.7 * self.arousal + 0.3 * min(1.0, motion * 5 + float(meta.get("threat_score", 0)))

    def reward_goal(self, goal: str, ok: bool) -> None:
        if goal not in self.success_counts:
            return
        if ok:
            self.success_counts[goal] += 1
            self.confidence = min(1.0, self.confidence + 0.02)
            if goal in ("fight", "hunt"):
                self.aggression = min(0.95, self.aggression + 0.01)
            if goal in ("explore", "wander", "parkour"):
                self.curiosity = min(0.95, self.curiosity + 0.01)
            if goal == "flee":
                self.caution = min(0.9, self.caution + 0.008)
        else:
            self.fail_counts[goal] += 1
            self.confidence = max(0.15, self.confidence - 0.015)

    def pick_goal(self, meta: dict, pain: float, anger: float, mode_hint: str) -> str:
        threat = float(meta.get("threat_score", 0))
        loom = float(meta.get("loom_score", 0))
        portal = float(meta.get("portal_score", 0))
        rail = float(meta.get("rail_score", 0))
        water = float(meta.get("water_score", 0))
        lobby = float(meta.get("lobby_score", 0))
        food = float(meta.get("food_score", 0))
        motion = float(meta.get("motion", 0))
        scores = {g: 0.05 for g in GOALS}
        scores["portal"] += portal * 2.2
        scores["rail"] += rail * 1.6
        scores["fight"] += threat * (1.2 * self.aggression + 0.5 * anger)
        scores["hunt"] += threat * 0.8 * self.aggression
        scores["flee"] += (loom * 1.4 + threat * 0.6) * self.caution + pain * 0.8
        scores["forage"] += food * 1.5 * self.curiosity
        scores["browse"] += lobby * 1.8 + (0.4 if lobby > 0.3 else 0)
        scores["rejoin"] += 0.6 if lobby > 0.5 and self.boredom > 0.4 else 0
        scores["explore"] += self.curiosity * (0.5 + self.boredom) + self.novelty * 0.4
        scores["wander"] += self.boredom * 0.9 + (0.3 if motion < 0.02 else 0)
        scores["parkour"] += self.curiosity * 0.35 + (0.25 if self.boredom > 0.55 else 0)
        scores["patrol"] += self.persistence * 0.3
        scores["social"] += self.social * 0.4 + (0.15 if self.boredom > 0.6 else 0)
        scores["camera_look"] += self.curiosity * 0.25 + (0.3 if self._idle_frames > 40 else 0)
        scores["rest"] += self.fatigue * 0.9 - self.arousal * 0.3
        if water > 0.5:
            scores["flee"] += 2.0
            scores["explore"] -= 1.0
        scores[self.last_goal] += 0.15 * self.persistence
        for g in GOALS:
            s, f = self.success_counts[g], self.fail_counts[g]
            scores[g] += 0.15 * (s / (s + f))
        keys = list(scores.keys())
        arr = np.array([max(1e-6, scores[k]) for k in keys], dtype=np.float64)
        arr = arr / arr.sum()
        temp = 0.7 + 0.6 * self.curiosity
        arr = np.power(arr, 1.0 / temp)
        arr = arr / arr.sum()
        choice = str(np.random.choice(keys, p=arr))
        if water > 0.55:
            choice = "flee"
        elif portal > 0.28:
            choice = "portal"
        elif threat > 0.55 and self.aggression > 0.45:
            choice = "fight" if anger + self.aggression > self.caution else "flee"
        elif lobby > 0.5 and self.boredom > 0.35:
            choice = "browse" if self.curiosity > 0.4 else "rejoin"
        if choice != self.last_goal:
            self.goal_since = time.time()
            self.session_goals += 1
            self.goal_hist.append(choice)
            if len(self.goal_hist) > 40:
                self.goal_hist.pop(0)
        self.last_goal = choice
        return choice

    def look_wander(self) -> Tuple[float, float]:
        self._look_phase += 0.07 + 0.05 * self.curiosity
        lx = math.sin(self._look_phase) * 0.6
        ly = math.sin(self._look_phase * 0.37) * 0.25
        return lx, ly

    def snapshot(self) -> Dict:
        return {
            "aggression": self.aggression, "curiosity": self.curiosity,
            "caution": self.caution, "social": self.social,
            "boredom": self.boredom, "novelty": self.novelty,
            "fatigue": self.fatigue, "confidence": self.confidence,
            "goal": self.last_goal, "session_goals": self.session_goals,
            "idle_frames": self._idle_frames,
        }
