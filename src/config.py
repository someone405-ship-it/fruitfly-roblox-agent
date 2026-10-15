"""Dark-theme tokens and runtime constants — Figma-inspired glass dark."""

from dataclasses import dataclass
from typing import Tuple

# ---------------------------------------------------------------------------
# Theme (Figma dark glass)
# ---------------------------------------------------------------------------
BG_DEEP = "#0B0E14"
BG_PANEL = "#12161F"
BG_CARD = "#1A1F2B"
BG_ELEVATED = "#222833"
BORDER = "#2A3140"
ACCENT = "#00E5FF"
ACCENT_DIM = "#00A8B8"
ACCENT_GLOW = "rgba(0, 229, 255, 0.25)"
TEXT_PRIMARY = "#E8ECF4"
TEXT_SECONDARY = "#8B95A8"
TEXT_MUTED = "#5A6578"
DANGER = "#FF4D6A"
SUCCESS = "#3DFF9A"
WARNING = "#FFC14D"

FONT_UI = "Segoe UI, Inter, system-ui, sans-serif"
FONT_MONO = "Cascadia Code, Consolas, monospace"

# ---------------------------------------------------------------------------
# Brain
# ---------------------------------------------------------------------------
N_SENSORY = 64
N_HIDDEN = 512
N_MOTOR = 16  # WASD, Space, Shift, mouse dx/dy, jump, interact, chat, look, ...
DT_MS = 20.0  # simulation step
TAU_MEM = 20.0
V_THRESH = 1.0
V_RESET = 0.0
NOISE_SCALE = 0.05

# ---------------------------------------------------------------------------
# Vision
# ---------------------------------------------------------------------------
CAPTURE_W = 320
CAPTURE_H = 180
FPS_TARGET = 30

# ---------------------------------------------------------------------------
# Motor mapping (index → action name)
# ---------------------------------------------------------------------------
MOTOR_NAMES = [
    "forward",
    "back",
    "left",
    "right",
    "jump",
    "sprint",
    "look_left",
    "look_right",
    "look_up",
    "look_down",
    "interact",
    "chat_toggle",
    "ui_up",
    "ui_down",
    "ui_select",
    "reset",
]

# ---------------------------------------------------------------------------
# UI layout
# ---------------------------------------------------------------------------
WINDOW_W = 1280
WINDOW_H = 800
MONITOR_W = 640
MONITOR_H = 360
LOG_LINES = 200

@dataclass
class Theme:
    bg_deep: str = BG_DEEP
    bg_panel: str = BG_PANEL
    bg_card: str = BG_CARD
    accent: str = ACCENT
    text: str = TEXT_PRIMARY
    text_sec: str = TEXT_SECONDARY
    border: str = BORDER
    danger: str = DANGER
    success: str = SUCCESS


THEME = Theme()
