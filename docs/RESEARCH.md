# Research log — sources that shaped this agent

Only items that fit a Windows Roblox vision→motor agent were adopted.

## Primary inspiration
1. DenisSergeevitch/desktop-fly — FlyWire LIF, Giant Fiber escape, 3D fly, brain window
2. desktop-fly/windows — Electron port, 120 Hz body loop
3. somsom10/desktop-fly-linux — 668-neuron extract, loom→GF
4. FlyWire v783 — public Drosophila brain connectome
5. MaleCNS v1.0 — descending motor pathways
6. Shiu et al. Nature 2024 — LIF constants
7. Kakaria & de Bivort 2017 — tau_m / threshold order

## Circuit roles mapped (real-time reduced model)
8. LC4 / LPLC2 loom detectors
9. DNp01 Giant Fiber escape
10. DNa01 / DNa02 steering
11. DNp09 forward walking
12. MDN reverse / moonwalker
13. DNg11 grooming
14. Loom → GF escape chain

## UI / agent engineering
15–30. desktop-fly body cues, brain window rates, scare/loom, watch-only, mss Roblox capture, clamped mouse, pulse keys, food chat, fear, bootstrap train, weight save, homeostasis, dual timescale, spectral radius

## Related (ideas only)
31–40. Lulzx/fly-brain, flybrain-robot-bridge, fly-chess, awesome-fruit-fly, NeuroMechFly, BANC, flyvis, Brian2, three.js Windows port, MaleCNS leg channels

## Not claimed
Full 139k/166k graph in the .exe. We ship a **named reduced circuit** with the same roles and LIF style as desktop-fly docs.
