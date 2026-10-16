"""Reflex engine — sub-brain-latency reactions from vision meta."""
from __future__ import annotations
from typing import Dict, List, Set, Tuple, Optional
import numpy as np
from .config import N_MOTOR, MOTOR_NAMES, REFLEX_ENABLED
from .potential import get_potential


def _idx(name: str) -> int:
    try:
        return MOTOR_NAMES.index(name)
    except ValueError:
        return -1


class ReflexEngine:
    def __init__(self) -> None:
        self.last_notes: List[str] = []

    def react(
        self,
        meta: dict,
        notes: List[str],
        in_arena: bool = False,
    ) -> Tuple[np.ndarray, Set[str], List[str]]:
        bias = np.zeros(N_MOTOR, dtype=np.float32)
        force: Set[str] = set()
        rnotes: List[str] = []
        if not REFLEX_ENABLED:
            return bias, force, rnotes

        pot = get_potential()
        threat = float(meta.get("threat_score", 0.0) or 0.0)
        loom = float(meta.get("loom_score", 0.0) or 0.0)
        portal = float(meta.get("portal_score", 0.0) or 0.0)
        water = float(meta.get("water_score", 0.0) or 0.0)
        motion = float(meta.get("motion", 0.0) or 0.0)
        cx = float(meta.get("threat_cx", meta.get("motion_cx", 0.5)) or 0.5)

        if pot.unlocked.get("reflex_water", True) and water > 0.35:
            i_f, i_s, i_b, i_j = _idx("forward"), _idx("sprint"), _idx("back"), _idx("jump")
            if i_f >= 0: bias[i_f] -= 1.2
            if i_s >= 0: bias[i_s] -= 1.0
            if i_b >= 0: bias[i_b] += 0.95
            if i_j >= 0: bias[i_j] += 0.55
            force.update({"back", "jump"})
            force.discard("forward")
            force.discard("sprint")
            rnotes.append("reflex_water")

        if pot.unlocked.get("reflex_portal", True) and portal > 0.28 and not in_arena:
            for n, v in (("forward", 0.95), ("sprint", 0.85), ("rmb_look", 0.5)):
                i = _idx(n)
                if i >= 0:
                    bias[i] += v
            force.update({"forward", "sprint", "rmb_look"})
            rnotes.append("reflex_portal")

        if pot.unlocked.get("reflex_loom", True) and (loom > 0.35 or (threat > 0.55 and motion > 0.12)):
            i_j = _idx("jump"); i_b = _idx("back")
            if i_j >= 0: bias[i_j] += 0.9
            if i_b >= 0: bias[i_b] += 0.45
            if cx < 0.42:
                i = _idx("right")
                if i >= 0: bias[i] += 0.75
                force.add("right")
            elif cx > 0.58:
                i = _idx("left")
                if i >= 0: bias[i] += 0.75
                force.add("left")
            force.update({"jump", "rmb_look"})
            rnotes.append("reflex_loom")

        if in_arena and threat > 0.4:
            for n, v in (("secondary", 0.8), ("forward", 0.55), ("sprint", 0.4)):
                i = _idx(n)
                if i >= 0:
                    bias[i] += v
            force.update({"secondary", "forward", "rmb_look"})
            rnotes.append("reflex_attack")

        if not in_arena and threat > 0.5 and portal < 0.2:
            i = _idx("secondary")
            if i >= 0: bias[i] -= 1.0
            i = _idx("back")
            if i >= 0: bias[i] += 0.6
            i = _idx("sprint")
            if i >= 0: bias[i] += 0.5
            force.discard("secondary")
            force.update({"back", "sprint"})
            rnotes.append("reflex_flee_no_portal")

        bias *= float(pot.power_mult())
        self.last_notes = rnotes
        return bias, force, rnotes


_ENGINE: Optional[ReflexEngine] = None


def get_reflex() -> ReflexEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ReflexEngine()
    return _ENGINE
