"""Ensure required packages are installed (skip if already present)."""
from __future__ import annotations
import importlib
import subprocess
import sys
from typing import List, Tuple

# (import_name, pip_name)
REQUIRED: List[Tuple[str, str]] = [
    ("PyQt6", "PyQt6"),
    ("numpy", "numpy"),
    ("cv2", "opencv-python-headless"),
    ("PIL", "Pillow"),
    ("pydirectinput", "pydirectinput"),
    ("pygetwindow", "pygetwindow"),
    ("pynput", "pynput"),
    ("mss", "mss"),
    ("psutil", "psutil"),
]

if sys.platform == "win32":
    REQUIRED.append(("win32api", "pywin32"))


def _missing() -> List[Tuple[str, str]]:
    out = []
    for mod, pip in REQUIRED:
        try:
            importlib.import_module(mod)
        except Exception:
            out.append((mod, pip))
    return out


def ensure_packages(log=print) -> bool:
    """Install only what is missing. Returns True if environment is OK."""
    miss = _missing()
    if not miss:
        log("deps: all required packages already installed")
        return True
    names = sorted({pip for _, pip in miss})
    log(f"deps: installing missing → {', '.join(names)}")
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", *names]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            log(f"deps: pip failed (code {r.returncode})")
            err = (r.stderr or r.stdout or "")[-500:]
            if err:
                log(err)
            # re-check — partial success still ok
        still = _missing()
        if still:
            log("deps: still missing: " + ", ".join(p for _, p in still))
            return False
        log("deps: install complete")
        return True
    except Exception as e:
        log(f"deps: error {type(e).__name__}: {e}")
        return len(_missing()) == 0
