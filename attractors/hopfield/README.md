# Hopfield Attractor

This animation shows noisy binary states descending into three stored Hopfield
memories. The scene is a 3D embedding: x/y are the first two PCA coordinates
of neural-state space, while the vertical component is the true Hopfield
energy. Bright nodes mark stable memory basins.

Render all four composed variants:

```bash
python3 attractors/hopfield/source/hopfield_instagram.py --all-presets
```

Render one chosen variant:

```bash
python3 attractors/hopfield/source/hopfield_instagram.py \
  --palette velvet-signal \
  --background black
```
