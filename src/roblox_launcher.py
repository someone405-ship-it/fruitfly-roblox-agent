"""Find, launch, and fully open Roblox Player on Windows."""
from __future__ import annotations
import os
import time
import subprocess
from pathlib import Path
from typing import Optional, Tuple

try:
    import psutil
except ImportError:
    psutil = None


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
    """Bring Roblox to foreground and maximize so the page is fully open."""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        SW_RESTORE = 9
        SW_MAXIMIZE = 3
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
        user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.15)
        user32.ShowWindow(hwnd, SW_MAXIMIZE)
        user32.SetForegroundWindow(hwnd)
        # force top-level activation
        try:
            user32.BringWindowToTop(hwnd)
        except Exception:
            pass
        return True
    except Exception:
        return False


def launch_roblox(wait_seconds: float = 6.0, maximize: bool = True) -> Tuple[bool, str]:
    if is_roblox_running():
        if maximize:
            maximize_roblox_window()
        return True, "Roblox already running (maximized)" if maximize else "Roblox already running"
    path = find_roblox_player()
    if not path:
        return False, "Roblox Player not found under %LOCALAPPDATA%\\Roblox\\Versions"
    try:
        subprocess.Popen([path], shell=False)
    except Exception as e:
        return False, f"failed to start Roblox: {e}"
    deadline = time.time() + max(1.0, wait_seconds)
    while time.time() < deadline:
        if is_roblox_running():
            time.sleep(0.8)
            if maximize:
                maximize_roblox_window()
            return True, f"Roblox launched + maximized: {path}"
        time.sleep(0.4)
    if maximize:
        maximize_roblox_window()
    return True, f"Roblox start requested: {path} (window may still be loading)"
