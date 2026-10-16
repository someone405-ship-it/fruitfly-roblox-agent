"""Apply reflex force + potential look into a desired action set / motor controller."""
from __future__ import annotations
from typing import Set


def merge_actions(desired: Set[str]) -> Set[str]:
    try:
        from . import runtime_bans
        from . import runtime_reflex
        banned = runtime_bans.get_bans()
        if banned:
            desired -= banned
        prefer = runtime_bans.get_prefer()
        for p in prefer:
            if p not in banned:
                desired.add(p)
        force = runtime_reflex.get_force()
        desired |= force
        if banned:
            desired -= banned
    except Exception:
        pass
    return desired


def apply_look_scale(motor) -> None:
    try:
        from . import runtime_reflex
        sens, mx = runtime_reflex.get_look()
        motor.look_sensitivity = sens
        motor.max_look_px = mx
    except Exception:
        pass


def blend_scores(motor_scores):
    try:
        from . import runtime_reflex
        rb = runtime_reflex.get_bias()
        if rb is None or motor_scores is None:
            return motor_scores
        out = list(motor_scores)
        for i in range(min(len(out), len(rb))):
            out[i] = float(out[i]) + float(rb[i]) * 0.45
        return out
    except Exception:
        return motor_scores
