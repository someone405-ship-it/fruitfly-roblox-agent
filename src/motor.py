"""Motor — ultra-fast SendInput + ESC leave + scroll join + RMB look."""
from __future__ import annotations
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

from .config import LOOK_SENSITIVITY, LOOK_MAX_PX, LOOK_INTERVAL, LOOK_DEADZONE

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002
WHEEL_DELTA = 120

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
    "ctrl": 0x11, "b": 0x42, "f": 0x46, "/": 0xBF, "m": 0x4D,
    "up": 0x26, "down": 0x28, "enter": 0x0D, "esc": 0x1B,
}
KEY_MAP = {
    "forward": "w", "back": "s", "left": "a", "right": "d",
    "jump": "space", "sprint": "shift", "interact": "e",
    "chat_toggle": "/", "ui_up": "up", "ui_down": "down",
    "ui_select": "enter", "reset": "r", "crouch": "ctrl",
    "emote": "b", "camera": "q", "secondary": None, "rmb_look": None,
    "ability_f": "f", "escape": "esc", "menu": "m",
    "scroll_up": None, "scroll_down": None,
}
PULSE_ACTIONS = {
    "chat_toggle", "interact", "reset", "emote", "camera", "ui_select",
    "ability_f", "escape", "menu", "scroll_up", "scroll_down",
}
KIT_ACTIONS = {"interact", "reset", "camera"}

def _si_move(dx, dy):
    if _SendInput is None or INPUT is None:
        return False
    inp = INPUT(); inp.type = 0
    inp.union.mi = MOUSEINPUT(dx, dy, 0, MOUSEEVENTF_MOVE, 0, None)
    return _SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 1

def _si_key(vk, up=False):
    if _SendInput is None or INPUT is None:
        return False
    scan = _MapVirtualKey(vk, 0)
    flags = KEYEVENTF_KEYUP if up else 0
    inp = INPUT(); inp.type = 1
    inp.union.ki = KEYBDINPUT(vk, scan, flags, 0, None)
    return _SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 1

def _si_mouse_btn(flags, data=0):
    if _SendInput is None or INPUT is None:
        return False
    inp = INPUT(); inp.type = 0
    inp.union.mi = MOUSEINPUT(0, 0, data, flags, 0, None)
    return _SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 1

class MotorController:
    def __init__(self):
        self.active = set()
        self.enabled = True
        self.last_sent = []
        self.last_mouse = (0, 0)
        self.look_sensitivity = float(LOOK_SENSITIVITY)
        self.look_deadzone = float(LOOK_DEADZONE)
        self.max_look_px = int(LOOK_MAX_PX)
        self._last_pulse = {}
        self._pulse_cooldown = 0.35
        self._last_look_t = 0.0
        self._look_interval = float(LOOK_INTERVAL)
        self._rmb_held = False

    def focus_roblox(self, maximize: bool = True):
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
                if maximize:
                    user32.ShowWindow(hwnd, 3)
                user32.SetForegroundWindow(hwnd)
                try:
                    user32.BringWindowToTop(hwnd)
                except Exception:
                    pass
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
            try:
                w.maximize()
            except Exception:
                pass
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
            _si_key(vk, False); time.sleep(0.012); _si_key(vk, True); return True
        if pydirectinput:
            try:
                pydirectinput.press(key); return True
            except Exception:
                return False
        return False

    def _move(self, dx, dy):
        if not dx and not dy:
            return False
        # burst in 2-3 micro steps for smooth ultra-fast turns
        steps = 1
        if abs(dx) > 50 or abs(dy) > 50:
            steps = 3
        elif abs(dx) > 25 or abs(dy) > 25:
            steps = 2
        ok = False
        rdx, rdy = dx, dy
        for i in range(steps):
            sx = rdx // (steps - i) if (steps - i) else rdx
            sy = rdy // (steps - i) if (steps - i) else rdy
            rdx -= sx; rdy -= sy
            if _si_move(sx, sy):
                ok = True
            elif pydirectinput:
                try:
                    pydirectinput.moveRel(sx, sy, relative=True); ok = True
                except Exception:
                    pass
        return ok

    def _left_click(self):
        if _si_mouse_btn(MOUSEEVENTF_LEFTDOWN) and _si_mouse_btn(MOUSEEVENTF_LEFTUP):
            return True
        if pydirectinput:
            try:
                pydirectinput.click(); return True
            except Exception:
                return False
        return False

    def _wheel(self, direction: int):
        # direction +1 up, -1 down
        data = int(direction * WHEEL_DELTA) & 0xFFFFFFFF
        return _si_mouse_btn(MOUSEEVENTF_WHEEL, data)

    def _rmb_down(self):
        if self._rmb_held:
            return True
        ok = _si_mouse_btn(MOUSEEVENTF_RIGHTDOWN)
        if ok:
            self._rmb_held = True
        return ok

    def _rmb_up(self):
        if not self._rmb_held:
            return True
        ok = _si_mouse_btn(MOUSEEVENTF_RIGHTUP)
        self._rmb_held = False
        return ok

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
            if name in ("scroll_up", "scroll_down"):
                gap = 0.12
                if now - self._last_pulse.get(name, 0) < gap:
                    continue
                direction = 1 if name == "scroll_up" else -1
                if self._wheel(direction):
                    self._last_pulse[name] = now
                    sent.append(name)
                continue
            key = KEY_MAP.get(name)
            if not key:
                continue
            if name in PULSE_ACTIONS:
                gap = 0.2 if name in KIT_ACTIONS else (0.45 if name == "escape" else self._pulse_cooldown)
                if now - self._last_pulse.get(name, 0) < gap:
                    continue
                if self._press(key):
                    self._last_pulse[name] = now
                    sent.append(name)
                continue
            if name not in self.active and self._keydown(key):
                self.active.add(name); sent.append(name)

        looking = False
        if motor_scores is not None and len(motor_scores) >= 10 and now - self._last_look_t >= self._look_interval:
            ll, lr = float(motor_scores[6]), float(motor_scores[7])
            lu, ld = float(motor_scores[8]), float(motor_scores[9])
            raw_x, raw_y = (-ll + lr), (-lu + ld)
            if abs(raw_x) < self.look_deadzone: raw_x = 0.0
            if abs(raw_y) < self.look_deadzone: raw_y = 0.0
            dx = int(max(-self.max_look_px, min(self.max_look_px, raw_x * self.look_sensitivity)))
            dy = int(max(-self.max_look_px, min(self.max_look_px, raw_y * self.look_sensitivity * 0.92)))
            want_rmb = "rmb_look" in desired or abs(raw_x) + abs(raw_y) > 0.22
            if want_rmb:
                if self._rmb_down():
                    sent.append("rmb_hold")
            else:
                if self._rmb_held:
                    self._rmb_up()
                    sent.append("rmb_release")
            if (dx or dy) and self._move(dx, dy):
                sent.append(f"look({dx},{dy})")
                self.last_mouse = (dx, dy)
                self._last_look_t = now
                looking = True
        if not looking and self._rmb_held and "rmb_look" not in desired:
            self._rmb_up()

        if "secondary" in desired and now - self._last_pulse.get("secondary", 0) >= 0.15:
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
            time.sleep(0.03)
            self._press("/")
            time.sleep(0.1)
            if pydirectinput:
                pydirectinput.typewrite(str(text)[:40], interval=0.018)
            else:
                for ch in str(text)[:40]:
                    self._press(ch.lower() if ch.isalpha() else ch)
            time.sleep(0.04)
            self._press("enter")
        except Exception:
            pass

    def release_all(self):
        for name in list(self.active):
            key = KEY_MAP.get(name)
            if key:
                self._keyup(key)
        self.active.clear(); self.last_mouse = (0, 0)
        if self._rmb_held:
            self._rmb_up()

    def emergency_stop(self):
        self.enabled = False; self.release_all()

    def resume(self):
        self.enabled = True
