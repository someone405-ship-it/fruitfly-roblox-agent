"""Process-wide action bans + prefer/force + look scale bridge."""
from __future__ import annotations
from typing import Set, Optional, Tuple

_BANNED: Set[str] = set()
_PREFER: Set[str] = set()


def set_bans(banned: Set[str], prefer: Optional[Set[str]] = None) -> None:
    global _BANNED, _PREFER
    _BANNED = set(banned or set())
    _PREFER = set(prefer or set())


def get_bans() -> Set[str]:
    return set(_BANNED)


def get_prefer() -> Set[str]:
    out = set(_PREFER)
    try:
        from . import runtime_reflex
        out |= runtime_reflex.get_force()
    except Exception:
        pass
    return out


def get_look_scale() -> Tuple[float, int]:
    """Returns (sensitivity, max_px) from potential/reflex if published."""
    try:
        from . import runtime_reflex
        return runtime_reflex.get_look()
    except Exception:
        from .config import LOOK_SENSITIVITY, LOOK_MAX_PX
        return float(LOOK_SENSITIVITY), int(LOOK_MAX_PX)
