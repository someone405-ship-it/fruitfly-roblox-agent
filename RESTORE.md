# Full audit status (2026-10-16)

## Tests passed (pure Python)
- config 139255 / 26 motors / STAT_MAX
- stats: 0 → HURT, 1+ → lose, max cap
- runtime bans + reflex publish/look scale
- potential + reflex portal force
- mistake/win/skill/eye memory save-load
- loot on_kill
- circuit step
- behavior modulate + death notes

## Not run here (needs Windows + RAM/GPU)
- FruitFlyBrain full 139k init (OOM on tiny CI; fine on laptop GPU/CPU with 16GB+)
- PyQt GUI / SendInput / Roblox window

## If main/behavior empty after pull
```powershell
Copy-Item artifacts\main.py.fixed src\main.py -Force
Copy-Item artifacts\behavior.py.fixed src\behavior.py -Force
Copy-Item artifacts\stats.py.fixed src\stats.py -Force
Copy-Item artifacts\motor.py.fixed src\motor.py -Force
python run_app.py
```

Or: `python -m src._rebuild_core` if artifacts are next to the repo.
