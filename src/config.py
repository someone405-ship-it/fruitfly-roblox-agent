"""Advanced dark-theme tokens + expanded brain / motor constants."""

from dataclasses import dataclass

BG_DEEP = "#0B0E14"
BG_PANEL = "#12161F"
BG_CARD = "#1A1F2B"
BG_ELEVATED = "#222833"
BORDER = "#2A3140"
ACCENT = "#00E5FF"
ACCENT_DIM = "#00A8B8"
TEXT_PRIMARY = "#E8ECF4"
TEXT_SECONDARY = "#8B95A8"
TEXT_MUTED = "#5A6578"
DANGER = "#FF4D6A"
SUCCESS = "#3DFF9A"
WARNING = "#FFC14D"
MOTOR_POS = "#00E5FF"
MOTOR_NEG = "#FF4D6A"

N_SENSORY = 128
N_HIDDEN = 1024
N_MOTOR = 20
DT_MS = 16.0
TAU_MEM = 18.0
TAU_SLOW = 80.0
V_THRESH = 1.0
V_RESET = 0.0
NOISE_SCALE = 0.04
SPARSITY = 0.12
SPECTRAL_RADIUS = 0.95

CAPTURE_W = 400
CAPTURE_H = 225
FPS_TARGET = 30

MOTOR_NAMES = [
    "forward", "back", "left", "right", "jump", "sprint",
    "look_left", "look_right", "look_up", "look_down",
    "interact", "chat_toggle", "ui_up", "ui_down", "ui_select", "reset",
    "crouch", "emote", "camera", "secondary",
]

MOTOR_LABELS = {
    "forward": "W forward", "back": "S back", "left": "A left", "right": "D right",
    "jump": "Space jump", "sprint": "Shift sprint", "look_left": "Look L",
    "look_right": "Look R", "look_up": "Look Up", "look_down": "Look Dn",
    "interact": "E Air Slash", "chat_toggle": "Chat /", "ui_up": "UI up",
    "ui_down": "UI down", "ui_select": "UI Enter", "reset": "R Combo",
    "crouch": "Ctrl crouch", "emote": "Emote", "camera": "Q Dash", "secondary": "RMB",
}

WINDOW_W = 1440
WINDOW_H = 900
MONITOR_W = 640
MONITOR_H = 360
LOG_LINES = 300
WEIGHTS_PATH = "fly_brain_weights.npz"

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
