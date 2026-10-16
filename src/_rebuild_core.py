"""Restore main/behavior/motor from base64 chunk files."""
from __future__ import annotations
from pathlib import Path
import base64

def _restore(name: str) -> None:
    here = Path(__file__).resolve().parent
    parts = []
    i = 0
    while True:
        p = here / f"_{name}_b64_{i}.txt"
        if not p.is_file():
            break
        parts.append(p.read_text(encoding="utf-8").strip())
        i += 1
    if not parts:
        return
    data = base64.b64decode("".join(parts))
    out = here / f"{name}.py"
    out.write_bytes(data)
    print(f"restored {out.name} ({len(data)} bytes)")

def rebuild_all() -> None:
    for name in ("main", "behavior", "motor"):
        target = Path(__file__).resolve().parent / f"{name}.py"
        need = (not target.is_file()) or target.stat().st_size < 500
        if need:
            _restore(name)
            continue
        head = target.read_text(encoding="utf-8", errors="ignore")[:80]
        if "PLACEHOLDER" in head or len(head.strip()) < 30:
            _restore(name)

if __name__ == "__main__":
    rebuild_all()
