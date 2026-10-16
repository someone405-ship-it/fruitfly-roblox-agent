"""Quick import sanity check — run: python -m src.sanity_check"""
from __future__ import annotations

def main() -> None:
    from .config import N_HIDDEN, N_MOTOR, MOTOR_NAMES, STAT_MAX
    assert N_HIDDEN == 139255, N_HIDDEN
    assert N_MOTOR == len(MOTOR_NAMES) == 26
    assert "luck" in STAT_MAX and STAT_MAX["food"] == 99
    from .runtime_bans import set_bans, get_bans, get_prefer, get_look_scale
    set_bans({"secondary"}, {"forward"})
    assert "secondary" in get_bans()
    sens, mx = get_look_scale()
    assert sens > 0 and mx > 0
    from .mistake_memory import MistakeMemory, WinMemory
    mm = MistakeMemory()
    wm = WinMemory()
    from .stats import get_stats, FlyStats
    st = FlyStats(path="/tmp/fly_stats_sanity.json")
    st.values = {k: 20.0 for k in st.values}
    d = st.on_death()
    assert d.get("applied", {}).get("food", 0) < 0, d
    from .potential import get_potential
    from .reflex import get_reflex
    get_potential()
    get_reflex()
    from .brain import FruitFlyBrain, using_gpu
    print(f"OK n_hidden={N_HIDDEN} gpu={using_gpu()} stats={st.summary()} mistakes={mm.summary()}")

if __name__ == "__main__":
    main()
