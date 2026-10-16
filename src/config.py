"""FruitFly — FlyWire-scale 139,255 LIF units (block-sparse) + ultra-fast I/O."""

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

# Official FlyWire FAFB v783 whole-brain neuron count (Dorkenwald et al. 2024):
# 139,255 proofread neurons. We run that many LIF units block-sparse.
# This is NOT the real synapse graph (50M synapses need specialized sparse kernels);
# it is the same *count* of units, live on a laptop.
N_HIDDEN = 139255
COL_SIZE = 8192
N_COLS = (N_HIDDEN + COL_SIZE - 1) // COL_SIZE  # 17 columns (last partial)
N_SENSORY = 384
N_MOTOR = 26
DT_MS = 5.0
TAU_MEM = 9.0
TAU_SLOW = 50.0
V_THRESH = 1.0
V_RESET = 0.0
NOISE_SCALE = 0.016
SPARSITY = 0.035
INTER_SPARSITY = 0.003
SPECTRAL_RADIUS = 0.93

CAPTURE_W = 480
CAPTURE_H = 270
FPS_TARGET = 60

MOTOR_NAMES = [
    "forward", "back", "left", "right", "jump", "sprint",
    "look_left", "look_right", "look_up", "look_down",
    "interact", "chat_toggle", "ui_up", "ui_down", "ui_select", "reset",
    "crouch", "emote", "camera", "secondary", "rmb_look", "ability_f",
    "escape", "menu", "scroll_up", "scroll_down",
]

MOTOR_LABELS = {
    "forward": "W", "back": "S", "left": "A", "right": "D",
    "jump": "Space", "sprint": "Shift",
    "look_left": "Look L", "look_right": "Look R", "look_up": "Look Up", "look_down": "Look Dn",
    "interact": "E", "chat_toggle": "Chat", "ui_up": "UI Up", "ui_down": "UI Dn",
    "ui_select": "Enter", "reset": "R", "crouch": "Ctrl", "emote": "Emote",
    "camera": "Q", "secondary": "LMB", "rmb_look": "RMB", "ability_f": "F",
    "escape": "Esc", "menu": "M", "scroll_up": "Wheel+", "scroll_down": "Wheel-",
}

WINDOW_W = 1500
WINDOW_H = 920
MONITOR_W = 640
MONITOR_H = 360
LOG_LINES = 300
WEIGHTS_PATH = "fly_brain_weights.npz"
SKILL_MEMORY_PATH = "fly_skill_memory.json"
EYE_MEMORY_PATH = "fly_eye_memory.npz"

# Ultra-fast mouse / keys (human-plus snap)
LOOK_SENSITIVITY = 95.0
LOOK_MAX_PX = 165
LOOK_INTERVAL = 0.004
LOOK_DEADZONE = 0.025

# Setup waits (long = higher success chance)
SETUP_ROBLOX_WAIT_S = 45.0
SETUP_ROBLOX_RETRIES = 12
SETUP_RETRY_GAP_S = 3.5
SETUP_MAXIMIZE_PASSES = 5

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
