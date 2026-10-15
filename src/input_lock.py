"""Watch-only input lock. Physical keyboard/mouse swallowed while fly runs."""

from __future__ import annotations

import threading

_lock = threading.Lock()
_locked = False
_kb_listener = None
_mouse_listener = None


def is_locked() -> bool:
    return _locked


def lock() -> bool:
    global _locked, _kb_listener, _mouse_listener
    with _lock:
        if _locked:
            return True
        try:
            from pynput import keyboard, mouse

            def on_key(_key):
                return False

            def on_click(_x, _y, _button, _pressed):
                return False

            def on_move(_x, _y):
                return False

            def on_scroll(_x, _y, _dx, _dy):
                return False

            _kb_listener = keyboard.Listener(
                on_press=on_key, on_release=on_key, suppress=True
            )
            _mouse_listener = mouse.Listener(
                on_click=on_click, on_move=on_move, on_scroll=on_scroll, suppress=True
            )
            _kb_listener.start()
            _mouse_listener.start()
            _locked = True
            return True
        except Exception:
            try:
                import ctypes
                ctypes.windll.user32.BlockInput(True)
                _locked = True
                return True
            except Exception:
                _locked = False
                return False


def unlock() -> None:
    global _locked, _kb_listener, _mouse_listener
    with _lock:
        if _kb_listener is not None:
            try:
                _kb_listener.stop()
            except Exception:
                pass
            _kb_listener = None
        if _mouse_listener is not None:
            try:
                _mouse_listener.stop()
            except Exception:
                pass
            _mouse_listener = None
        try:
            import ctypes
            ctypes.windll.user32.BlockInput(False)
        except Exception:
            pass
        _locked = False
