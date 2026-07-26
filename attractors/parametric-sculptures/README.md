# Parametric Sculptures

This collection is for visual, formula-driven three-dimensional objects rather
than dynamical-system attractors. The first work is **Twisted Crescent**: an
asymmetric torus whose tube contracts into a bitten crescent and twists around
its own circular path. It is based on the colourful point-surface study shared
for the project.

Create a still preview:

```bash
python3 attractors/parametric-sculptures/source/twisted_crescent_instagram.py --preview
```

Create a four-stage storyboard of the formation process:

```bash
python3 attractors/parametric-sculptures/source/twisted_crescent_instagram.py --storyboard
```

Render a 9:16 Instagram MP4 in one palette:

```bash
python3 attractors/parametric-sculptures/source/twisted_crescent_instagram.py --palette spectrum-ribbon
```

Render all palette variants:

```bash
python3 attractors/parametric-sculptures/source/twisted_crescent_instagram.py --all-palettes
```

Across the 12-second animation, sparse luminous seeds appear first, fibres grow
between them, and successive strands close into the complete surface. The
camera remains almost still so the formation process is the main action.

The exports use `1080 × 1920`, 12 seconds, and a 30 FPS H.264 MP4. The
renderer creates 15 distinct frames per second and repeats them cleanly in the
30 FPS export, keeping the animation smooth while avoiding a wasteful render.
