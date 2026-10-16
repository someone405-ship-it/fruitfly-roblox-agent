"""Shared safety: apply mistake bans + avoid bias on motor/actions."""
from __future__ import annotations
from typing import List, Optional, Tuple
import numpy as np


def apply_safety(trainer, motor, notes, meta, actions: List[str]) -> Tuple[np.ndarray, List[str], set]:
    """Delegate to trainer mistake filters when available."""
    try:
        return trainer.apply_mistake_filters(motor, notes, meta, actions)
    except Exception:
        return motor, actions, set()
