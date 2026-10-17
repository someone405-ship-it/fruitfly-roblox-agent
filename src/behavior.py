"""FruitFly behavior — portal-first, water avoid, explore, combat when in arena."""
from __future__ import annotations
from typing import List, Set, Tuple
import numpy as np
from .config import MOTOR_NAMES, N_MOTOR


class BehaviorLayer:
    def __init__(self) -> None:
        self.idx = {n: i for i, n in enumerate(MOTOR_NAMES)}
        self._line = ""
        self.in_arena = False

    def _say(self, msg: str) -> None:
        self._line = msg

    def take_line(self) -> str:
        s = self._line
        self._line = ""
        return s

    def modulate(self, motor: np.ndarray, meta: dict, circuit_bias=None):
        m = np.asarray(motor, dtype=np.float32).ravel().copy()
        if m.size < N_MOTOR:
            pad = np.zeros(N_MOTOR, dtype=np.float32)
            pad[: m.size] = m
            m = pad

        notes: List[str] = []
        force: Set[str] = set()
        portal = float(meta.get("portal_score", meta.get("portal", 0)) or 0)
        water = float(meta.get("water_score", meta.get("water", 0)) or 0)
        threat = float(meta.get("threat_score", 0) or 0)
        in_arena = bool(meta.get("in_arena", False)) or portal < 0.15 and threat > 0.25
        self.in_arena = in_arena

        if water > 0.35:
            notes.append("water_avoid")
            force.update({"back", "sprint"})
            m[self.idx["back"]] = max(m[self.idx["back"]], 0.9)
            m[self.idx["sprint"]] = max(m[self.idx["sprint"]], 0.8)

        if portal > 0.2 and not in_arena:
            notes.append("seek_portal")
            force.update({"forward", "sprint", "rmb_look"})
            m[self.idx["forward"]] = max(m[self.idx["forward"]], 0.85)
            m[self.idx["sprint"]] = max(m[self.idx["sprint"]], 0.7)
            if portal > 0.55:
                notes.append("portal_close")

        if in_arena:
            notes.append("in_arena")
            if threat > 0.2:
                notes.append("fight")
                force.update({"forward", "secondary", "rmb_look"})
                m[self.idx["secondary"]] = max(m[self.idx.get("secondary", 0)], 0.85)
            else:
                notes.append("explore_world")
                force.add("forward")

        if float(meta.get("death_event", 0)):
            notes.append("water_death")

        info = {
            "goal": notes[0] if notes else "idle",
            "notes": notes[:12],
            "force": list(force),
            "in_arena": in_arena,
            "portal_score": portal,
            "threat_score": threat,
        }
        if notes:
            self._say(" | ".join(notes[:4]))
        return m, notes, info
