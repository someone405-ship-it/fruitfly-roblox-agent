# FruitFly Roblox Agent — ADVANCED

**1024-unit dual-timescale fruit-fly brain plays Roblox.**

## New in advanced build

- **Brain:** 1024 hidden units, sparse Dale-like recurrence, fast+slow membrane, homeostasis gain, 128-D vision, 20 motor channels
- **Motor output panel:** live signed bars for every motor channel (+ active highlight)
- **Vision:** prefers Roblox window capture, hist/edges/motion/bright-dark CoM/grid features
- **Motor:** crouch, emote, camera, RMB secondary, auto-focus Roblox, higher look sensitivity
- **Save/Load brain** weights (`fly_brain_weights.npz`)
- **Train:** imitation + reward still present
- **UI:** 3-column layout — live monitor | motor output | 3D fly keyboard

## Download EXE

Actions → Build Windows EXE → artifact **FruitFlyRoblox-windows**

https://github.com/someone405-ship-it/fruitfly-roblox-agent/actions

## Run

```bash
git clone https://github.com/someone405-ship-it/fruitfly-roblox-agent.git
cd fruitfly-roblox-agent
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python run_app.py
```

F8 fly · T train · +/- reward · F9 stop · Esc quit · SAVE/LOAD BRAIN buttons

MIT. Absolute olliE.
