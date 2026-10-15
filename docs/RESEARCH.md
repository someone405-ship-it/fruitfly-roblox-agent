# Research basis — FruitFly Roblox Agent

## Connectome sources

- **MaleCNS v1.0** — complete adult male *Drosophila melanogaster* central nervous system  
  (~166 700 neurons, ~125 million synapses).  
  Produced by HHMI Janelia FlyEM, University of Cambridge, MRC LMB, Google Research.  
  Released 8 June 2026, CC-BY 4.0.  
  https://male-cns.janelia.org/  
  Download: `gs://flyem-male-cns/v1.0/connectome-data/flat-connectome/`

- **FlyWire / FAFB** — adult female whole-brain connectome (~139 k neurons).  
  Used in many published LIF simulations (Shiu et al.).

## Dynamics model

Neuron dynamics follow the leaky-integrate-and-fire parameterisation published in:

> Shiu et al., *A leaky integrate-and-fire computational model based on the connectome of the entire adult Drosophila brain*, Nature 2024.

This project uses a reduced real-time reservoir (512 units) with sensory drive and linear motor readout so the closed loop can run at 30 Hz on consumer hardware while preserving the “fruit-fly-brain-as-controller” identity.

## Prior art (connectome → game / robot)

Public projects that wire real or reduced Drosophila graphs into games or robots:

- Doodle Fly — full FlyWire brain plays a Doodle-Jump style game in browser  
- Fly Brain Plays Doom / DOOMFLY  
- FlySweeper — MaleCNS subcircuit plays Minesweeper  
- Fly Brain Bridge — MaleCNS → physical robot  
- Embodied NeuroMechFly + connectome simulations  

These demonstrate the same architectural pattern used here: visual (or other) sensory features → connectome / reservoir → motor commands → environment.

## Mapping used in this agent

| Fly concept              | Implementation in agent                          |
|--------------------------|--------------------------------------------------|
| Photoreceptors / optic   | VisionEncoder (hist, edges, motion, CoM)         |
| Central / descending     | FruitFlyBrain recurrent LIF reservoir            |
| Motor neurons / VNC      | MotorController → WASD / Space / mouse           |
| Body                     | Local Windows PC + Roblox Player                 |

Full MaleCNS matrices are not redistributed; the agent is self-contained and ready to run without downloading the 1 GB+ feather tables.
