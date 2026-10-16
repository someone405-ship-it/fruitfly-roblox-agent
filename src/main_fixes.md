# Main fixes applied locally

If main.py still shows 98k after pull, the following must be true in src/main.py:

1. Title / labels say 139255
2. import maximize_roblox_aggressive
3. launch_roblox(maximize=True) without short wait override (launcher enforces 45s min)
4. Before online_step: motor, actions, banned = self.trainer.apply_mistake_filters(...)
5. bootstrap_explore(500)

Motor + trainer already enforce mistake bans via runtime_bans even without apply_mistake_filters.
