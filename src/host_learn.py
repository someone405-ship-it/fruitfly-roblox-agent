"""Host key capture for LEARN FROM ME imitation mode."""
from __future__ import annotations
import threading
from typing import List, Set, Optional

_lock = threading.Lock()
_keys: Set[str] = set()
_listener = None
_active = False

_CHAR_MAP = {
    "w": "w", "a": "a", "s": "s", "d": "d",
    "q": "q", "e": "e", "r": "r", "f": "f",
    " ": "space",
}


def is_learning() -> bool:
    return _active


def keys_down() -> List[str]:
    with _lock:
        return list(_keys)


def start() -> bool:
    global _listener, _active
    with _lock:
        if _active:
            return True
        try:
            from pynput import keyboard
            from pynput.keyboard import Key

            def on_press(key):
                name = _normalize(key)
                if name:
                    with _lock:
                        _keys.add(name)

            def on_release(key):
                name = _normalize(key)
                if name:
                    with _lock:
                        _keys.discard(name)

            def _normalize(key) -> Optional[str]:
                try:
                    if key == Key.space:
                        return "space"
                    if key in (Key.shift, Key.shift_l, Key.shift_r):
                        return "shift"
                    if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
                        return "ctrl"
                    if hasattr(key, "char") and key.char:
                        return _CHAR_MAP.get(key.char.lower(), key.char.lower())
                except Exception:
                    return None
                return None

            _listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            _listener.start()
            _active = True
            return True
        except Exception:
            _active = False
            return False


def stop() -> None:
    global _listener, _active
    with _lock:
        if _listener is not None:
            try:
                _listener.stop()
            except Exception:
                pass
        _listener = None
        _keys.clear()
        _active = False
