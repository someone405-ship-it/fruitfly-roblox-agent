# FruitFly Roblox Agent — ADVANCED

**8192-unit dual-timescale fruit-fly brain plays Roblox autonomously.**

## What's new

- **Brain:** 8192 LIF reservoir neurons (practical advanced scale), expanded 256-D sensory, 22 motor channels
- **Full Roblox window:** launches and **maximizes** Roblox so the page is fully open on run/start
- **RMB look:** fruitfly holds **right mouse button** while looking around for freelook
- **Learn from you forever:** `LEARN FROM ME` tracks keys + LMB/RMB; skills written to `fly_skill_memory.json` and reused forever
- **Permanent memory:** nearest-neighbor skill recall biases motor online; autosave every ~200 steps + on stop/F9
- **Brain weights:** `fly_brain_weights.npz` saved/loaded automatically
- **Smarter autonomy:** kill/loot, death hurt, character kits, predictive dodge, power tiers, circuit bias

> Note: a literal dense 80k×80k reservoir needs tens of GB of RAM. 8192 is the advanced practical size that still runs live on a normal PC.

## Download EXE

Actions → Build Windows EXE → artifact **FruitFlyRoblox-windows**

https://github.com/someone405-ship-it/fruitfly-roblox-agent/actions

## Run

```bash
git clone https://github.com/someone405-ship-it/fruitfly-roblox-agent.git
cd fruitfly-roblox-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_app.py
```

**START** — autonomy (Roblox maximized)  
**LEARN FROM ME** — you play, he copies keys/RMB and saves skills forever  
**F9** — emergency stop + save  
**Esc** — quit

Files created next to the app:
- `fly_brain_weights.npz` — synaptic weights
- `fly_skill_memory.json` — permanent host-learned skills

MIT. Absolute olliE.
