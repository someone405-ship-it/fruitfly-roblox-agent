"""Selective watch-only lock: block user keys/clicks only while Roblox is focused.

F9 always passes. Mouse *movement* is never suppressed so agent camera (SendInput)
still works; user clicks/keys into Roblox are blocked.
"""
from __future__ import annotations
import threading

_lock = threading.Lock()
_locked = False
_kb = None
_mouse = None


def is_locked() -> bool:
    return _locked


def _foreground_is_roblox() -> bool:
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = (buf.value or "").lower()
        return "roblox" in title and "fruitfly" not in title
    except Exception:
        return False


def lock() -> bool:
    global _locked, _kb, _mouse
    with _lock:
        if _locked:
            return True
        try:
            from pynput import keyboard, mouse
            from pynput.keyboard import Key

            def on_press(key):
                try:
                    if key == Key.f9:
                        return True
                except Exception:
                    pass
                if _foreground_is_roblox():
                    return False
                return True

            def on_release(key):
                try:
                    if key == Key.f9:
                        return True
                except Exception:
                    pass
                if _foreground_is_roblox():
                    return False
                return True

            def on_click(x, y, button, pressed):
                if _foreground_is_roblox():
                    return False
                return True

            def on_move(x, y):
                # NEVER suppress movement — agent look uses relative mouse
                return True

            def on_scroll(x, y, dx, dy):
                if _foreground_is_roblox():
                    return False
                return True

            _kb = keyboard.Listener(on_press=on_press, on_release=on_release, suppress=True)
            _mouse = mouse.Listener(
                on_click=on_click, on_move=on_move, on_scroll=on_scroll, suppress=True
            )
            _kb.start()
            _mouse.start()
            _locked = True
            return True
        except Exception:
            _locked = False
            return False


def unlock() -> None:
    global _locked, _kb, _mouse
    with _lock:
        for lst in (_kb, _mouse):
            if lst is not None:
                try:
                    lst.stop()
                except Exception:
                    pass
        _kb = None
        _mouse = None
        _locked = False
