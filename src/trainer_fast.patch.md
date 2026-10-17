# Fast learn settings applied in trainer

If trainer.py on disk is the full version, set:
- lr = 0.28 (was ~0.14)
- imit_lr = 0.55 (was ~0.36)
- eye_lr = 0.35 (was ~0.22)
- bootstrap_explore steps = 1500
- multi-pass outer product updates (2x per tick)
- weight decay 0.99985 (stickier)

RESTORE main/behavior first — see RESTORE.md
