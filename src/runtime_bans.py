"""Process-wide action bans from mistake memory (read by motor every tick)."""
from __future__ import annotations
from typing import Set, Optional

_BANNED: Set[str] = set()
_PREFER: Set[str] = set()


def set_bans(banned: Set[str], prefer: Optional[Set[str]] = None) -> None:
    global _BANNED, _PREFER
    _BANNED = set(banned or set())
    _PREFER = set(prefer or set())


def get_bans() -> Set[str]:
    return set(_BANNED)


def get_prefer() -> Set[str]:
    """Prefer + reflex force actions (so motor.apply picks them without extra imports)."""
    out = set(_PREFER)
    try:
        from . import runtime_reflex
        out |= runtime_reflex.get_force()
    except Exception:
        pass
    return out
