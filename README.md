# FruitFly Roblox Agent — 139,255 + Potential Unlock + Reflex

**139,255 LIF units** (FlyWire FAFB v783 count) · block-sparse · Windows laptop.

## Potential unlock (permanent)

Saved in `fly_potential.json`. XP from play time, kills, portals, joins, mistakes.

| Unlock | Effect |
|--------|--------|
| reflex_water / portal / loom | Instant reactions from vision |
| snap_aim | Higher mouse sensitivity |
| fast_decide | Lower action threshold |
| overdrive / limit_break | Stronger motor + aim |

## Reflex pack (research-inspired reactive vision→motor)

- **Water** → block forward, force back/jump  
- **Portal** → sprint in  
- **Loom/threat** → jump + strafe  
- **Arena threat** → commit attack  
- **Threat outside arena** → flee, no fight  

## Fast I/O

- Look sens **110**, max **185px**, interval **3ms**  
- Tick **4ms** brain DT  

## Other memory

- `fly_mistake_memory.json` — never repeat failures  
- `fly_win_memory.json` — reinforce wins  
- `fly_eye_memory.npz` / `fly_skill_memory.json`  

## Run

```bash
git pull
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_app.py
```

Optional: `python -m src.sanity_check`

**Windows only** (not Android/iPhone).

MIT.
