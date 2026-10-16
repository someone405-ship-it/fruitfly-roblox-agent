"""Find, launch, maximize Roblox — long waits + many retries for high success rate."""
from __future__ import annotations
import os
import time
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Callable

try:
    import psutil
except ImportError:
    psutil = None

from .config import SETUP_ROBLOX_WAIT_S, SETUP_ROBLOX_RETRIES, SETUP_RETRY_GAP_S, SETUP_MAXIMIZE_PASSES


def _versions_dir() -> Optional[Path]:
    local = os.environ.get("LOCALAPPDATA", "")
    if not local:
        return None
    p = Path(local) / "Roblox" / "Versions"
    return p if p.is_dir() else None


def find_roblox_player() -> Optional[str]:
    base = _versions_dir()
    if base is None:
        return None
    candidates = []
    try:
        for d in base.iterdir():
            if not d.is_dir():
                continue
            for name in ("RobloxPlayerBeta.exe", "RobloxPlayer.exe"):
                exe = d / name
                if exe.is_file():
                    candidates.append(exe)
    except Exception:
        return None
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return str(candidates[0])


def is_roblox_running() -> bool:
    if psutil is None:
        return False
    try:
        for proc in psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").lower()
            if "roblox" in name:
                return True
    except Exception:
        pass
    return False


def maximize_roblox_window() -> bool:
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        found = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def enum_cb(h, _lp):
            if not user32.IsWindowVisible(h):
                return True
            length = user32.GetWindowTextLengthW(h)
            if length < 1:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(h, buf, length + 1)
            title = (buf.value or "").lower()
            if "roblox" in title and "fruitfly" not in title:
                found.append(h)
            return True

        user32.EnumWindows(enum_cb, 0)
        if not found:
            return False
        hwnd = found[0]
        user32.ShowWindow(hwnd, 9)   # restore
        time.sleep(0.2)
        user32.ShowWindow(hwnd, 3)   # maximize
        user32.SetForegroundWindow(hwnd)
        try:
            user32.BringWindowToTop(hwnd)
        except Exception:
            pass
        return True
    except Exception:
        return False


def maximize_roblox_aggressive(passes: int = SETUP_MAXIMIZE_PASSES) -> bool:
    ok = False
    for i in range(max(1, passes)):
        if maximize_roblox_window():
            ok = True
        time.sleep(0.35 + 0.15 * i)
    return ok


def launch_roblox(
    wait_seconds: float = SETUP_ROBLOX_WAIT_S,
    maximize: bool = True,
    log: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, str]:
    def _log(msg: str) -> None:
        if log:
            log(msg)

    if is_roblox_running():
        if maximize:
            maximize_roblox_aggressive()
        return True, "Roblox already running (maximized)" if maximize else "Roblox already running"

    path = find_roblox_player()
    if not path:
        return False, "Roblox Player not found under %LOCALAPPDATA%\\Roblox\\Versions — install Roblox first"

    try:
        subprocess.Popen([path], shell=False)
        _log(f"launched: {path}")
    except Exception as e:
        return False, f"failed to start Roblox: {e}"

    deadline = time.time() + max(5.0, wait_seconds)
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        if is_roblox_running():
            _log(f"Roblox process seen (attempt {attempt})")
            time.sleep(1.2)
            if maximize:
                maximize_roblox_aggressive()
            # extra settle so window is fully open
            time.sleep(1.5)
            if maximize:
                maximize_roblox_aggressive(passes=3)
            return True, f"Roblox launched + maximized: {path}"
        time.sleep(0.5)

    # process may still be starting — keep retrying outside pure wait
    for r in range(SETUP_ROBLOX_RETRIES):
        _log(f"retry {r + 1}/{SETUP_ROBLOX_RETRIES} for Roblox window…")
        if is_roblox_running():
            if maximize:
                maximize_roblox_aggressive()
            time.sleep(1.0)
            if maximize:
                maximize_roblox_aggressive(passes=3)
            return True, f"Roblox ready after retry {r + 1}: {path}"
        time.sleep(SETUP_RETRY_GAP_S)

    if maximize:
        maximize_roblox_aggressive()
    if is_roblox_running():
        return True, f"Roblox process up (window may still load): {path}"
    return False, f"Roblox did not become ready in {wait_seconds:.0f}s + retries — open Roblox manually then press START"
