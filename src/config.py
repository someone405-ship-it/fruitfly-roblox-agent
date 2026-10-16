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

# Practical advanced scale (full 80k dense reservoir would need ~25GB+ RAM).
# 8192 LIF units + expanded sensory + permanent skill memory = smart fly.
N_SENSORY = 256
N_HIDDEN = 8192
N_MOTOR = 22
DT_MS = 12.0
TAU_MEM = 16.0
TAU_SLOW = 90.0
V_THRESH = 1.0
V_RESET = 0.0
NOISE_SCALE = 0.025
SPARSITY = 0.08
SPECTRAL_RADIUS = 0.97

CAPTURE_W = 480
CAPTURE_H = 270
FPS_TARGET = 30

MOTOR_NAMES = [
    "forward", "back", "left", "right", "jump", "sprint",
    "look_left", "look_right", "look_up", "look_down",
    "interact", "chat_toggle", "ui_up", "ui_down", "ui_select", "reset",
    "crouch", "emote", "camera", "secondary", "rmb_look", "ability_f",
]

MOTOR_LABELS = {
    "forward": "W", "back": "S", "left": "A", "right": "D",
    "jump": "Space", "sprint": "Shift",
    "look_left": "Look L", "look_right": "Look R", "look_up": "Look Up", "look_down": "Look Dn",
    "interact": "E ability", "chat_toggle": "Chat", "ui_up": "UI Up", "ui_down": "UI Dn",
    "ui_select": "Enter", "reset": "R ability", "crouch": "Ctrl", "emote": "Emote",
    "camera": "Q ability", "secondary": "LMB", "rmb_look": "RMB look", "ability_f": "F",
}

WINDOW_W = 1500
WINDOW_H = 920
MONITOR_W = 640
MONITOR_H = 360
LOG_LINES = 300
WEIGHTS_PATH = "fly_brain_weights.npz"
SKILL_MEMORY_PATH = "fly_skill_memory.json"

POWER_TIERS = [
    (0, 1.0, "dormant"),
    (3, 1.08, "awake"),
    (8, 1.16, "charged"),
    (15, 1.28, "ascendant"),
    (25, 1.42, "unlocked"),
    (40, 1.55, "ascended"),
]


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
