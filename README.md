# FruitFly Roblox Agent

**Fruit fly brain plays Roblox on your PC.**

Auto-launches Roblox → live vision monitor → 3D fly on keyboard (keys light up) → action log → train mode (imitation / reward).

Download the **Windows `.exe`** from [Actions artifacts](https://github.com/someone405-ship-it/fruitfly-roblox-agent/actions) after a green build, or from a Release.

## Quick use

1. Install / log into **Roblox Player** on Windows.
2. Download `FruitFlyRoblox.exe` from the latest workflow run (Actions → Build Windows EXE → Artifacts).
3. Run the exe. It finds Roblox under `%LOCALAPPDATA%\\Roblox\\Versions` and starts it.
4. Join any experience (or leave the fly on the home/menu — it still acts).
5. Press **F8** — the fly plays. Keys light on the 3D keyboard; the left panel is live Roblox vision.
6. **T** = train on/off. Imitation: hold WASD/Space/E to teach. Reward: `+` / `-` reinforce last moves.
7. **F9** emergency stop. **Esc** quit.

## Run from source

```bash
git clone https://github.com/someone405-ship-it/fruitfly-roblox-agent.git
cd fruitfly-roblox-agent
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python run_app.py
```

## Build exe locally

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name FruitFlyRoblox --paths . --collect-all PyQt6 run_app.py
```

## Workflow download

Every push to `main` runs `.github/workflows/build-exe.yml` on `windows-latest`.

- Open **Actions** → latest **Build Windows EXE** → **FruitFlyRoblox-windows** artifact → download zip → extract `FruitFlyRoblox.exe`.

## Layout

| Panel | Content |
|-------|---------|
| Left | Live Roblox capture (what the fly sees) + action log |
| Right | Animated 3D fruit fly on mechanical keyboard; active keys glow cyan |

## Train

| Mode | How |
|------|-----|
| imitation | Train ON + hold WASD/Space/E while the fly runs — readout learns your policy |
| reward | Train ON + press `+` or `-` to reward/punish recent motor |

## Stack

- Vision: `mss` + OpenCV features  
- Brain: LIF-style reservoir (Shiu / MaleCNS-inspired)  
- Motor: `pydirectinput` (Windows)  
- UI: PyQt6 dark glass  
- Launch: auto-detect `RobloxPlayerBeta.exe`

MIT. Absolute olliE.
