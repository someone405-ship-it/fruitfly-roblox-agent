"""Quick import sanity check — run: python -m src.sanity_check"""
from __future__ import annotations

def main() -> None:
    from .config import N_HIDDEN, N_MOTOR, MOTOR_NAMES, MISTAKE_MEMORY_PATH
    assert N_HIDDEN == 139255, N_HIDDEN
    assert N_MOTOR == len(MOTOR_NAMES) == 26
    from .runtime_bans import set_bans, get_bans
    set_bans({"secondary"}, {"forward"})
    assert "secondary" in get_bans()
    from .mistake_memory import MistakeMemory, WinMemory
    mm = MistakeMemory()
    wm = WinMemory()
    from .brain import FruitFlyBrain, using_gpu
    print(f"OK n_hidden={N_HIDDEN} gpu={using_gpu()} mistakes={mm.summary()} wins={wm.summary()}")

if __name__ == "__main__":
    main()
