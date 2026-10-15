"""Find and launch Roblox Player on Windows."""
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

def launch_roblox(wait_seconds: float = 6.0) -> Tuple[bool, str]:
    if is_roblox_running():
        return True, "Roblox already running"
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
            return True, f"Roblox launched: {path}"
        time.sleep(0.4)
    return True, f"Roblox start requested: {path} (window may still be loading)"
