# Generative Science Art — Luminous Editions

A second take on the six pieces in [`equation-editions/`](../equation-editions/).
Same systems, same equations, same 9:16 phone format — rebuilt around how the
clips actually behave in a feed rather than how they look as stills.

## What changed, and why

**They open on the finished sculpture.** The originals fade up from an empty
black frame and take two or three seconds to resolve. That is the entire window
you get to stop a scroll, spent on nothing. Here frame one is already the full
structure.

**The loop is seamless.** The camera completes exactly one 360° turn over the
clip, so the last frame meets the first and Instagram's auto-repeat has no seam.
Any secondary motion is whole-cycle periodic for the same reason: the flows get
a small tilt sway, the Clifford clouds a full hue revolution that reads as light
travelling around the shell.

**They emit light instead of drawing lines.** The originals plot one-pixel
polylines — neon-*coloured* rather than neon-*glowing*, and thin lines are the
first thing a social codec destroys. Every sample here lands in a float
accumulation buffer with bilinear sub-pixel weights, so overlapping trajectories
genuinely add up, and a multi-scale bloom pass bleeds the bright cores outward.

**Density is tone mapped logarithmically.** An attractor's density spans orders
of magnitude — Lorenz spends almost all its time in the two wing cores. Mapping
that linearly blows the cores to featureless white and leaves the surrounding
filigree in the dark. Taking the log compresses the range so faint structure
reads while the cores stay bright; dividing the colour sum by the density keeps
hues saturated instead of washing everything towards white.

**They fill the frame.** Two framing fixes did most of the work. Lorenz and
Aizawa are far taller in *z* than they are wide, so they now stand on that axis
instead of lying down in a tall crop. The Clifford `ring` preset is wide and
squat; rolling it upright more than doubles the frame height it uses.

**A surface, not a curve.** Each flow integrates several hundred neighbouring
trajectories at once with vectorised RK4, so the attractor resolves as a surface
whose density carries the image. The Clifford map is elementwise, so tens of
thousands of orbits advance in a single vectorised step.

## Layout

```text
luminous-editions/
├── README.md
├── source/
│   ├── glow.py             # HDR splatting, bloom, tone mapping, captions
│   ├── systems.py          # attractor sampling and camera projection
│   └── render_editions.py  # the six editions
└── instagram/phone-9x16/   # 1080×1920 H.264 exports
```

## Run

```bash
python3 generative-science-art/luminous-editions/source/render_editions.py
```

One edition at a time, or a fast preview:

```bash
python3 generative-science-art/luminous-editions/source/render_editions.py --edition lorenz
```

```bash
python3 generative-science-art/luminous-editions/source/render_editions.py --width 360 --height 640 --duration 2 --fps 12
```

Requirements are unchanged — `numpy`, `Pillow`, and an FFmpeg with an H.264
encoder. Note that conda environments often ship an FFmpeg built without
libx264; it advertises `libopenh264` and then fails at runtime, so the renderer
probes every FFmpeg it can find and picks one that actually works.

## The six

| Edition | System | Palette |
| --- | --- | --- |
| `lorenz_ember-spectrum_luminous` | Lorenz | ember → spectrum |
| `halvorsen_electric-citrus_luminous` | Halvorsen | electric citrus |
| `aizawa_orchid-gold_luminous` | Aizawa | orchid gold |
| `clifford_classic-butterfly_rainbow_luminous` | Clifford map | neon rainbow |
| `clifford_ring_rainbow_luminous` | Clifford map | neon rainbow |
| `clifford_shell_rainbow_luminous` | Clifford map | neon rainbow |

All exports are `1080 × 1920`, 10 s, 30 fps, H.264, no audio.
