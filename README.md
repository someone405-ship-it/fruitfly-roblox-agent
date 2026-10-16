# FruitFly Roblox Agent — 65k FAST

**Block-sparse 65,536-neuron fruit-fly brain** plays Roblox: portal-first, ultra-fast mouse, learns from your **eyes + keys**, can ESC-leave and self-join games.

## Scale

| Spec | Value |
|------|-------|
| Neurons | **65,536** (8 columns × 8192 LIF) |
| Real MaleCNS | ~140k–167k (full dense needs GPU connectome kernels) |
| This build | Near-full practical CPU scale with sparse columns |
| Sensory | 384-D vision |
| Motors | 26 (incl. ESC, scroll, RMB look) |

Inspired by [Desktop Fly](https://github.com/DenisSergeevitch/desktop-fly), [fly-self-driving](https://github.com/suanmiao/fly-self-driving), FlyWire / MaleCNS research.

## Features

- **Ultra-fast mouse** — sens 62, up to 110px/tick, 8ms interval, micro-step bursts
- **Portal-first** — never combat until portal/arena; portal ≠ danger
- **LEARN FROM ME** — tracks keys **and** screen (eye pairs in `fly_eye_memory.npz`)
- **Permanent skills** — `fly_skill_memory.json` + brain weights
- **Leave / join** — ESC leave when bored/hurt; scroll + UI + click to join new games
- **Explore** — hunt portal, rails, parkour, freelook
- **Maximize Roblox** on launch/start

## Run

```bash
git clone https://github.com/someone405-ship-it/fruitfly-roblox-agent.git
cd fruitfly-roblox-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_app.py
```

**START** — autonomy  
**LEARN FROM ME** — you play; he copies keys + what he sees  
**F9** — emergency stop + save  

Saved next to the app:
- `fly_brain_weights.npz`
- `fly_skill_memory.json`
- `fly_eye_memory.npz`

First run after this upgrade re-bootstraps (architecture changed). Give it ~30–60s on start.

MIT. Absolute olliE.
