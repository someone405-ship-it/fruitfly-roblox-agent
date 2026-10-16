"""Entry point — ensure deps, then launch."""
from __future__ import annotations
import sys


def main() -> None:
    try:
        from src.deps import ensure_packages
        ok = ensure_packages(print)
        if not ok:
            print("WARNING: some packages still missing — trying to start anyway")
    except Exception as e:
        print(f"deps check skipped: {e}")

    try:
        from src.config import N_HIDDEN
        print(f"FruitFly · {N_HIDDEN} neurons (FlyWire-scale) · loading…")
    except Exception:
        pass

    from src.main import main as app_main
    app_main()


if __name__ == "__main__":
    main()
