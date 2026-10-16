"""Entry point — ensure deps, then launch."""
from __future__ import annotations
import sys


def main() -> None:
    # install missing packages first (ignore ones already present)
    try:
        from src.deps import ensure_packages
        ok = ensure_packages(print)
        if not ok:
            print("WARNING: some packages still missing — trying to start anyway")
    except Exception as e:
        print(f"deps check skipped: {e}")

    from src.main import main as app_main
    app_main()


if __name__ == "__main__":
    main()
