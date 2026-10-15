# FruitFly Roblox Agent

**A simulated Drosophila melanogaster (fruit fly) central nervous system plays Roblox by itself.**

Live screen monitor · real-time action log · 3D fruit fly on a mechanical keyboard · dark theme desktop UI.

Built on the public MaleCNS v1.0 connectome principles (Janelia / Google Research / Cambridge) with a practical real-time control loop that maps visual features → descending motor commands → keyboard/mouse actions via `pyrobloxbot` / `pydirectinput`.

> Absolute olliE build. The bench ships complete projects.

## Features

- **Autonomous play** — the fly brain decides movement, jump, camera, chat, and UI navigation on any Roblox experience
- **Live monitor** — real-time preview of what the fly “sees” (Roblox window capture)
- **Action output** — timestamped log of every motor decision and key event
- **3D fruit fly on keyboard** — animated Three.js / PyQt3D-style overlay of a fruit fly standing on a mechanical keyboard that lights keys as they are pressed
- **Dark theme UI** — Figma-inspired dark glass panels, cyan accent, zero light-mode
- **Own PC simulation** — the agent treats the local machine as the fly’s body; focus Roblox and let it run
- **Windows `.exe` ready** — PyInstaller one-file build script included

## Architecture

```
Roblox window (capture)
        │
        ▼
Vision encoder (edge / motion / bright regions → sensory vector)
        │
        ▼
FruitFlyBrain (LIF-style recurrent reservoir + linear readout)
        │
        ▼
Motor decoder → WASD / Space / mouse / chat / UI nav
        │
        ▼
pyrobloxbot / pydirectinput  →  Roblox
        │
        ▼
Live Monitor + Action Log + 3D Fly Keyboard overlay
```

The brain is a compact, real-time approximation of connectome-driven control: sensory features drive a recurrent layer whose dynamics are inspired by leaky-integrate-and-fire parameters from published Drosophila models (Shiu et al. Nature 2024 style). A linear readout maps internal state to action probabilities. No training required to start; optional online adaptation is available.

Full MaleCNS (≈167 k neurons) is too heavy for consumer real-time at 30–60 Hz; this project uses a 512-unit reservoir + explicit sensory → descending mapping so the loop stays responsive while still carrying the “fruit fly brain” identity and the research references.

## Quick Start

### Requirements

- Windows 10/11 (pyrobloxbot is Windows-only)
- Python 3.10+
- Roblox Player installed and logged in
- A free experience open (or let the agent join one)

```bash
git clone https://github.com/someone405-ship-it/fruitfly-roblox-agent.git
cd fruitfly-roblox-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.main
```

### Build `.exe`

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name FruitFlyRoblox --icon assets/fly.ico src/main.py
```

The executable lands in `dist/FruitFlyRoblox.exe`.

## Controls (host)

| Key | Action |
|-----|--------|
| `F8` | Start / pause the fly |
| `F9` | Emergency stop (failsafe) |
| `Esc` | Quit app |

The fly itself uses standard Roblox bindings (WASD, Space, mouse look, `/` chat, etc.).

## Project Layout

```
fruitfly-roblox-agent/
├── src/
│   ├── main.py              # entry + dark UI
│   ├── brain.py             # FruitFlyBrain LIF reservoir
│   ├── vision.py            # screen capture + feature encoder
│   ├── motor.py             # action decoder + pyrobloxbot bridge
│   ├── monitor.py           # live preview widget
│   ├── fly3d.py             # 3D fly-on-keyboard widget
│   ├── logger.py            # action log
│   └── config.py            # constants & dark theme tokens
├── assets/
│   └── (icons, keyboard textures)
├── docs/
│   └── RESEARCH.md          # connectome sources & citations
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Research Basis

- MaleCNS v1.0 — complete adult male Drosophila CNS connectome (≈166 700 neurons). Janelia FlyEM + Cambridge + Google Research, CC-BY 4.0.  
  https://male-cns.janelia.org/
- Shiu et al., Nature 2024 — leaky-integrate-and-fire whole-brain model parameters.
- Public demos of connectome-driven game agents (Doom, Doodle Jump, Minesweeper, etc.) demonstrate the same pipeline pattern used here.

See `docs/RESEARCH.md` for full links and how the reduced real-time model maps onto the published circuits.

## License

MIT. Connectome data itself remains under the original CC-BY terms of the MaleCNS release; this repository does not redistribute the full 1 GB+ feather tables.

## Absolute olliE

Built on the bench. The light stays on.
