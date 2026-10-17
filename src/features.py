"""FruitFly feature registry — expanded."""
from __future__ import annotations

FEATURES = [
    "139255_lif_neurons", "block_sparse_columns", "optional_cupy_gpu",
    "portal_first_nav", "water_avoid", "arena_after_portal",
    "escape_menu", "self_join", "explore_world",
    "ultra_fast_mouse", "speed_slider", "micro_burst_look",
    "learn_from_me_keys", "learn_from_eyes", "skill_memory",
    "mistake_memory", "win_memory", "never_repeat_mistake",
    "stats_panel", "stat_rewards", "stat_max_cap",
    "death_unreward", "zero_stat_hurt_rule",
    "potential_unlock", "reflex_layer", "instincts",
    "fast_learn_lr", "multi_pass_train", "heavy_bootstrap",
    "autosave_weights", "f9_emergency", "roblox_focus",
    "host_imitation", "eye_nearest_target", "online_reward",
    "loot_bias", "rail_follow", "predict_dodge",
    "motor_panel", "stats_panel_ui", "circuit_panel",
    "fly3d", "mouse3d",
]

FEATURE_COMPLETE = True

def feature_count() -> int:
    return len(FEATURES)

def feature_list() -> list:
    return list(FEATURES)
