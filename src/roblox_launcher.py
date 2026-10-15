"""Find and launch Roblox Player on Windows."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Optional, List


def _local_app_data() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", ""))


def find_roblox_player() -> Optional[Path]:
    versions = _local_app_data() / "Roblox" / "Versions"
    if not versions.is_dir():
        return None
    candidates: List[Path] = []
    for folder in versions.iterdir():
        if not folder.is_dir():
            continue
        for name in ("RobloxPlayerBeta.exe", "RobloxPlayer.exe"):
            exe = folder / name
            if exe.is_file():
                candidates.append(exe)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def find_roblox_launcher() -> Optional[Path]:
    versions = _local_app_data() / "Roblox" / "Versions"
    if not versions.is_dir():
        return None
    for folder in sorted(versions.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        for name in ("RobloxPlayerLauncher.exe", "RobloxPlayerBeta.exe"):
            exe = folder / name
            if exe.is_file():
                return exe
    return None


def is_roblox_running() -> bool:
    try:
        import psutil
        for proc in psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").lower()
            if "roblox" in name:
                return True
    except Exception:
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq RobloxPlayerBeta.exe"],
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            return "RobloxPlayerBeta.exe" in out
        except Exception:
            return False
    return False


def launch_roblox(wait_seconds: float = 8.0) -> tuple[bool, str]:
    if is_roblox_running():
        return True, "Roblox already running"
    exe = find_roblox_player() or find_roblox_launcher()
    if exe is None:
        return False, "Roblox Player not found under %LOCALAPPDATA%\\Roblox\\Versions"
    try:
        subprocess.Popen([str(exe)], cwd=str(exe.parent), shell=False)
        time.sleep(wait_seconds)
        if is_roblox_running():
            return True, f"launched {exe.name}"
        return True, f"started {exe.name} (process may still be loading)"
    except Exception as e:
        return False, f"launch failed: {e}"
