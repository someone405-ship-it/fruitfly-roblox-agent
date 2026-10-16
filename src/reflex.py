"""Reflex engine — sub-brain-latency reactions from vision meta."""
from __future__ import annotations
from typing import Dict, List, Set, Tuple
import numpy as np
from .config import N_MOTOR, MOTOR_NAMES, REFLEX_ENABLED
from .potential import get_potential


def _idx(name: str) -> int:
    try:
        return MOTOR_NAMES.index(name)
    except ValueError:
        return -1


class ReflexEngine:
    """Hardwired fast paths: loom / portal / water / arena threat."""

    def __init__(self) -> None:
        self.last_notes: List[str] = []

    def react(
        self,
        meta: dict,
        notes: List[str],
        in_arena: bool = False,
    ) -> Tuple[np.ndarray, Set[str], List[str]]:
        """Return (motor_bias, force_actions, reflex_notes)."""
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

        # WATER — never walk in
        if pot.unlocked.get("reflex_water", True) and water > 0.35:
            bias[_idx("forward")] -= 1.2
            bias[_idx("sprint")] -= 1.0
            bias[_idx("back")] += 0.95
            bias[_idx("jump")] += 0.55
            force.update({"back", "jump"})
            force.discard("forward")
            force.discard("sprint")
            rnotes.append("reflex_water")

        # PORTAL seek — sprint in
        if pot.unlocked.get("reflex_portal", True) and portal > 0.28 and not in_arena:
            bias[_idx("forward")] += 0.95
            bias[_idx("sprint")] += 0.85
            bias[_idx("rmb_look")] += 0.5
            force.update({"forward", "sprint", "rmb_look"})
            rnotes.append("reflex_portal")

        # LOOM / close threat — dodge
        if pot.unlocked.get("reflex_loom", True) and (loom > 0.35 or (threat > 0.55 and motion > 0.12)):
            bias[_idx("jump")] += 0.9
            bias[_idx("back")] += 0.45
            # strafe away from threat side
            if cx < 0.42:
                bias[_idx("right")] += 0.75
                force.add("right")
            elif cx > 0.58:
                bias[_idx("left")] += 0.75
                force.add("left")
            else:
                bias[_idx("left" if (hash(loom) % 2) else "right")] += 0.55
            force.update({"jump", "rmb_look"})
            rnotes.append("reflex_loom")

        # ARENA threat — commit attack
        if in_arena and threat > 0.4:
            bias[_idx("secondary")] += 0.8
            bias[_idx("forward")] += 0.55
            bias[_idx("sprint")] += 0.4
            force.update({"secondary", "forward", "rmb_look"})
            rnotes.append("reflex_attack")

        # Outside arena + high threat without portal → flee not fight
        if not in_arena and threat > 0.5 and portal < 0.2:
            bias[_idx("secondary")] -= 1.0
            bias[_idx("back")] += 0.6
            bias[_idx("sprint")] += 0.5
            force.discard("secondary")
            force.update({"back", "sprint"})
            rnotes.append("reflex_flee_no_portal")

        # power scale
        mult = pot.power_mult()
        bias *= float(mult)

        self.last_notes = rnotes
        return bias, force, rnotes


_ENGINE: ReflexEngine | None = None


def get_reflex() -> ReflexEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ReflexEngine()
    return _ENGINE
