# FruitFly Roblox Agent — 98k FAST (video-style)

Whole-brain-style fly agent: **vision in → 98,304 neurons → ultra-fast keys/mouse out**.
Same idea as the connectome-in-a-game clips (FlyWire / MaleCNS controlling a body through a keyboard) — not their game, your Roblox loop.

## Scale

| Spec | Value |
|------|-------|
| Neurons | **98,304** (12 × 8192 block-sparse LIF) |
| MaleCNS reference | ~140k–167k |
| This build | ≈60–70% of whole-brain count, live on CPU |
| Dense full brain | Needs GPU connectome kernels (not this app) |
| Sensory | 384-D screen features |
| Motors | 26 (WASD, look, LMB/RMB, Esc, scroll, abilities) |
| Look | sens 78, max 140 px/tick, 6 ms interval |

## Behavior

- **Portal-first** — no combat until portal/arena; portal ≠ danger
- **LEARN FROM ME** — keys **and** eyes (`fly_eye_memory.npz`)
- **Leave / join** — Esc when bored/hurt/dead; scroll + UI + click to join
- **Explore** — rails, parkour, freelook, lobby browse
- **Permanent memory** — brain weights + skill JSON + eye pairs

## Run

```bash
git clone https://github.com/someone405-ship-it/fruitfly-roblox-agent.git
cd fruitfly-roblox-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_app.py
```

First launch after pull re-bootstraps (~1 min).

**START** · **LEARN FROM ME** · **F9** emergency + save

Files: `fly_brain_weights.npz` · `fly_skill_memory.json` · `fly_eye_memory.npz`

MIT. Absolute olliE.
