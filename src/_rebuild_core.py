"""Restore empty main/behavior/motor/stats from artifacts/*.fixed."""
from __future__ import annotations
from pathlib import Path
import shutil

def rebuild_all() -> None:
    here = Path(__file__).resolve().parent
    root = here.parent
    candidates = [root / "artifacts", root.parent / "artifacts", Path("artifacts")]
    for name in ("main", "behavior", "motor", "stats"):
        target = here / f"{name}.py"
        need = (not target.is_file()) or target.stat().st_size < 500
        if target.is_file() and target.stat().st_size >= 500:
            head = target.read_text(encoding="utf-8", errors="ignore")[:40]
            if "PLACEHOLDER" in head:
                need = True
        if not need:
            print(f"ok {name}.py ({target.stat().st_size} bytes)")
            continue
        fixed = None
        for c in candidates:
            p = c / f"{name}.py.fixed"
            if p.is_file() and p.stat().st_size > 500:
                fixed = p
                break
        if fixed is None:
            print(f"MISSING fixed copy for {name} — see RESTORE.md")
            continue
        shutil.copyfile(fixed, target)
        print(f"restored {name}.py from {fixed} ({target.stat().st_size} bytes)")

if __name__ == "__main__":
    rebuild_all()
