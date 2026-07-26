# Clifford Attractor

Each parameter preset has its own `phone-9x16` directory. The user-defined
presets are `ribbon`, `shell`, `orbit`, `mask`, `organic-flower`,
`double-knot`, and `ring`. `classic-butterfly` remains as the original
baseline.

Render all colour variants for one preset with:

```bash
python3 attractors/clifford/source/clifford_instagram.py \
  --preset organic-flower \
  --all-palettes \
  --output-dir attractors/clifford/organic-flower/phone-9x16
```

Render the additional 15-second formation animation for every preset:

```bash
python3 attractors/clifford/source/clifford_formation_instagram.py --all-presets
```

The formation edition uses the `spectrum-ribbon` colour sequence. Scattered
points become layered fibres, the fibres close into a dense three-dimensional
volume, and the completed body makes a perspective half-turn around its
vertical axis during the final five seconds. These exports have `formation` in
their filenames and do not replace the earlier, non-formation videos.
