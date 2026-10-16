"""Motor — SendInput keys/mouse + attack click. Q=dash."""
from __future__ import annotations
from typing import Set
import time
import ctypes
from ctypes import wintypes

try:
    import pydirectinput
    pydirectinput.FAILSAFE = False
    pydirectinput.PAUSE = 0.0
except ImportError:
    pydirectinput = None
try:
    import pygetwindow as gw
except ImportError:
    gw = None

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
KEYEVENTF_KEYUP = 0x0002

if hasattr(ctypes, "windll"):
    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                     ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                     ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                     ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                     ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]
    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]
    class INPUT_UNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]
    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]
    _SendInput = ctypes.windll.user32.SendInput
    _MapVirtualKey = ctypes.windll.user32.MapVirtualKeyW
else:
    INPUT = None
    _SendInput = None

VK = {
    "q": 0x51, "w": 0x57, "s": 0x53, "a": 0x41, "d": 0x44,
    "space": 0x20, "shift": 0x10, "e": 0x45, "r": 0x52,
    "ctrl": 0x11, "b": 0x42, "f": 0x46, "/": 0xBF,
    "up": 0x26, "down": 0x28, "enter": 0x0D,
}
KEY_MAP = {
    "forward": "w", "back": "s", "left": "a", "right": "d",
    "jump": "space", "sprint": "shift", "interact": "e",
    "chat_toggle": "/", "ui_up": "up", "ui_down": "down",
    "ui_select": "enter", "reset": "r", "crouch": "ctrl",
    "emote": "b", "camera": "q", "secondary": None,
}
PULSE_ACTIONS = {"chat_toggle", "interact", "reset", "emote", "camera", "ui_select"}
KIT_ACTIONS = {"interact", "reset", "camera"}

def _si_move(dx, dy):
    if _SendInput is None or INPUT is None:
        return False
    inp = INPUT(); inp.type = INPUT_MOUSE
    inp.union.mi = MOUSEINPUT(dx, dy, 0, MOUSEEVENTF_MOVE, 0, None)
    return _SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 1

def _si_key(vk, up=False):
    if _SendInput is None or INPUT is None:
        return False
    scan = _MapVirtualKey(vk, 0)
    flags = KEYEVENTF_KEYUP if up else 0
    inp = INPUT(); inp.type = INPUT_KEYBOARD
    inp.union.ki = KEYBDINPUT(vk, scan, flags, 0, None)
    return _SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 1

class MotorController:
    def __init__(self):
        self.active = set()
        self.enabled = True
        self.last_sent = []
        self.last_mouse = (0, 0)
        self.look_sensitivity = 14.0
        self.look_deadzone = 0.12
        self.max_look_px = 28
        self._last_pulse = {}
        self._pulse_cooldown = 0.9
        self._last_look_t = 0.0
        self._look_interval = 0.03

    def focus_roblox(self):
        """Bring Roblox to foreground so SendInput hits the game."""
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
            if found:
                hwnd = found[0]
                user32.ShowWindow(hwnd, 9)
                user32.SetForegroundWindow(hwnd)
                return True
        except Exception:
            pass
        if gw is None:
            return False
        try:
            wins = [w for w in gw.getAllWindows()
                    if w.title and "roblox" in w.title.lower() and "fruitfly" not in w.title.lower()
                    and w.width >= 200 and w.height >= 150]
            if not wins:
                return False
            w = max(wins, key=lambda x: max(0, x.width) * max(0, x.height))
            if w.isMinimized:
                w.restore()
            w.activate()
            return True
        except Exception:
            return False

    def _keydown(self, key):
        vk = VK.get(key)
        if vk is not None and _si_key(vk, False):
            return True
        if pydirectinput:
            try:
                pydirectinput.keyDown(key); return True
            except Exception:
                return False
        return False

    def _keyup(self, key):
        vk = VK.get(key)
        if vk is not None and _si_key(vk, True):
            return True
        if pydirectinput:
            try:
                pydirectinput.keyUp(key); return True
            except Exception:
                return False
        return False

    def _press(self, key):
        vk = VK.get(key)
        if vk is not None:
            _si_key(vk, False); time.sleep(0.03); _si_key(vk, True); return True
        if pydirectinput:
            try:
                pydirectinput.press(key); return True
            except Exception:
                return False
        return False

    def _move(self, dx, dy):
        if not dx and not dy:
            return False
        if _si_move(dx, dy):
            return True
        if pydirectinput:
            try:
                pydirectinput.moveRel(dx, dy, relative=True); return True
            except Exception:
                return False
        return False

    def _left_click(self):
        if _SendInput is not None and INPUT is not None:
            for flags in (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP):
                inp = INPUT(); inp.type = INPUT_MOUSE
                inp.union.mi = MOUSEINPUT(0, 0, 0, flags, 0, None)
                _SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
            return True
        if pydirectinput:
            try:
                pydirectinput.click(); return True
            except Exception:
                return False
        return False

    def apply(self, actions, motor_scores=None):
        if not self.enabled:
            return []
        now = time.time()
        desired = set(actions)
        for a, b in (("forward", "back"), ("left", "right")):
            if a in desired and b in desired:
                for x in actions:
                    if x == a:
                        desired.discard(b); break
                    if x == b:
                        desired.discard(a); break
        sent = []
        for name in list(self.active):
            if name not in desired and KEY_MAP.get(name):
                self._keyup(KEY_MAP[name]); self.active.discard(name)
        for name in desired:
            key = KEY_MAP.get(name)
            if not key:
                continue
            if name in PULSE_ACTIONS:
                gap = 0.4 if name in KIT_ACTIONS else self._pulse_cooldown
                if now - self._last_pulse.get(name, 0) < gap:
                    continue
                if self._press(key):
                    self._last_pulse[name] = now
                    sent.append(name)
                continue
            if name not in self.active and self._keydown(key):
                self.active.add(name); sent.append(name)
        if motor_scores is not None and len(motor_scores) >= 10 and now - self._last_look_t >= self._look_interval:
            ll, lr = float(motor_scores[6]), float(motor_scores[7])
            lu, ld = float(motor_scores[8]), float(motor_scores[9])
            raw_x, raw_y = (-ll + lr), (-lu + ld)
            if abs(raw_x) < self.look_deadzone: raw_x = 0.0
            if abs(raw_y) < self.look_deadzone: raw_y = 0.0
            dx = int(max(-self.max_look_px, min(self.max_look_px, raw_x * self.look_sensitivity)))
            dy = int(max(-self.max_look_px, min(self.max_look_px, raw_y * self.look_sensitivity * 0.85)))
            if (dx or dy) and self._move(dx, dy):
                sent.append(f"look({dx},{dy})")
                self.last_mouse = (dx, dy)
                self._last_look_t = now
        if "secondary" in desired and now - self._last_pulse.get("secondary", 0) >= 0.35:
            if self._left_click():
                sent.append("attack_click")
                self._last_pulse["secondary"] = now
        self.last_sent = sent
        return sent

    def type_text(self, text):
        if not self.enabled or not text:
            return
        try:
            self.release_all()
            time.sleep(0.05)
            self._press("/")
            time.sleep(0.18)
            if pydirectinput:
                pydirectinput.typewrite(str(text)[:40], interval=0.04)
            else:
                for ch in str(text)[:40]:
                    self._press(ch.lower() if ch.isalpha() else ch)
            time.sleep(0.08)
            self._press("enter")
        except Exception:
            pass

    def release_all(self):
        for name in list(self.active):
            key = KEY_MAP.get(name)
            if key:
                self._keyup(key)
        self.active.clear(); self.last_mouse = (0, 0)

    def emergency_stop(self):
        self.enabled = False; self.release_all()

    def resume(self):
        self.enabled = True
