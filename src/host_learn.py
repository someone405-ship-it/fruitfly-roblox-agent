"""Host key + mouse capture for LEARN FROM ME imitation mode."""
from __future__ import annotations
import threading
from typing import List, Set, Optional, Tuple

_lock = threading.Lock()
_keys: Set[str] = set()
_mouse_buttons: Set[str] = set()
_mouse_delta: Tuple[int, int] = (0, 0)
_listener = None
_mouse_listener = None
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


def mouse_state() -> dict:
    with _lock:
        return {
            "buttons": list(_mouse_buttons),
            "dx": int(_mouse_delta[0]),
            "dy": int(_mouse_delta[1]),
        }


def consume_mouse_delta() -> Tuple[int, int]:
    global _mouse_delta
    with _lock:
        d = _mouse_delta
        _mouse_delta = (0, 0)
        return d


def start() -> bool:
    global _listener, _mouse_listener, _active
    with _lock:
        if _active:
            return True
        try:
            from pynput import keyboard, mouse
            from pynput.keyboard import Key
            from pynput.mouse import Button

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

            def on_click(x, y, button, pressed):
                name = None
                if button == Button.left:
                    name = "lmb"
                elif button == Button.right:
                    name = "rmb"
                if name is None:
                    return
                with _lock:
                    if pressed:
                        _mouse_buttons.add(name)
                        if name == "rmb":
                            _keys.add("rmb")
                    else:
                        _mouse_buttons.discard(name)
                        if name == "rmb":
                            _keys.discard("rmb")

            def on_move(x, y):
                # relative deltas tracked via last absolute — best-effort
                pass

            _listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            _mouse_listener = mouse.Listener(on_click=on_click, on_move=on_move)
            _listener.start()
            _mouse_listener.start()
            _active = True
            return True
        except Exception:
            _active = False
            return False


def stop() -> None:
    global _listener, _mouse_listener, _active
    with _lock:
        for lst in (_listener, _mouse_listener):
            if lst is not None:
                try:
                    lst.stop()
                except Exception:
                    pass
        _listener = None
        _mouse_listener = None
        _keys.clear()
        _mouse_buttons.clear()
        _active = False
