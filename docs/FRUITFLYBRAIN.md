# Fruit Fly Brain resources used

Taken from fruitflybrain org — only ideas that fit a realtime Roblox agent:

| Repo | What we took |
|------|----------------|
| neuroarch | Graph-of-circuits idea → named LIF modules (GF escape, MDN reverse, DNp09 forward) in circuit.py. Full graph DB not embedded. |
| neu3d | 3D neuron viz inspiration → fly3d keyboard panel is the lightweight stand-in. |
| ffbo.nlp_component | Natural-language self-talk lines via behavior._say / take_line. |
| NeuroinformaticsTutorial | Sensory → circuit → motor pipeline framing. |
| fruitflybrain.github.io / ffbo.launcher | Skipped for runtime (docs/launcher only). |

## 139k neurons

Full adult Drosophila connectome (~139k neurons) cannot run as a dense realtime matrix inside this agent on a normal PC.
What ships: 1024-unit LIF reservoir + small named circuit (connectome roles), ~30 Hz decision loop.
Scale: raise N_HIDDEN in config.py; spectral radius stays ~1 via power iteration.
