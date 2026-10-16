# FruitFly Roblox Agent — 139,255 (FlyWire scale)

**139,255 LIF units** — the official FlyWire FAFB v783 whole-brain neuron count (Dorkenwald et al. 2024).
Block-sparse dynamics so it runs live on a Windows laptop. Not the real 50M-synapse graph (that needs specialized sparse GPU kernels); same **unit count**, real-time vision → keys/mouse.

## This update

| Feature | Detail |
|---------|--------|
| Neurons | **139,255** (FlyWire published count) |
| Setup | **45s** Roblox wait + **12 retries** + multi-pass maximize |
| Packages | Auto-install missing deps on start (skips if already installed) |
| Mouse | sens **95**, max **165px**, **4ms** ticks |
| Keys | short pulse, low latency SendInput |
| Learn | keys + eyes → permanent files |
| Leave/join | Esc, scroll, UI select |

## Run (Windows laptop)

```bash
git clone https://github.com/someone405-ship-it/fruitfly-roblox-agent.git
cd fruitfly-roblox-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_app.py
```

`run_app.py` installs any **missing** packages automatically; already-installed ones are ignored.

First brain build can take **1–3 minutes** (139k units). Wait for the green ready line.

**START** · **LEARN FROM ME** · **F9** emergency

Saves: `fly_brain_weights.npz` · `fly_skill_memory.json` · `fly_eye_memory.npz`

Optional NVIDIA: `pip install cupy-cuda12x`

**Not on iPhone/Android** — needs Windows desktop input + screen capture.

MIT. Absolute olliE.
