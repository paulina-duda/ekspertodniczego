# Trace Editions

The same three attractors as [`emergence-editions/`](../emergence-editions/), cut
the same way, but drawn as continuous traces instead of accumulating density.

| Edition | Palette |
| --- | --- |
| `lorenz_ember-spectrum_trace` | ember → spectrum |
| `aizawa_orchid-gold_trace` | orchid gold |
| `halvorsen_electric-citrus_trace` | electric citrus |

## The problem this fixes

`emergence-editions` splats one point per integration step. Measured at the
shipped framing, consecutive steps land a median of **3.3 px apart on Lorenz and
up to 20 px** in the fast outer excursions — so every individual trajectory is
drawn as a *dotted trail*. The picture only looks continuous because twelve
hundred of them overlap.

That is why it reads as accumulating density rather than as lines being drawn:
there are no lines in it. There is a cloud of points arranged along lines.

Here each step is subdivided until successive splats land about a pixel apart,
so a trajectory is a genuine unbroken filament. Segment counts vary — a slow
stretch needs one piece, a fast excursion twenty — so the subdivided samples are
sorted by age afterwards, which the renderer wants anyway: with ages ascending,
everything drawn by a given moment is a prefix, found by binary search.

The subdivision target is derived from the cloud's own radius against the frame,
so it stays correct at any output size without the renderer handing back its
projection scale.

## Far fewer strands

Subdivision multiplies samples by roughly four, so the trajectory count comes
down hard — 72 instead of 1200. This costs nothing: at 9000 steps the finished
frame lights 41.8% at forty strands and 43.1% at three hundred and twenty. The
attractor fills in either way, and with fewer strands the individual bands stay
readable, which is the entire point.

## What was tried and dropped

A bright head on each strand's leading edge, to show where the integrator has
actually reached. It does not work at this strand count. A head spanning few
enough steps to read as a point contributes too few samples to survive the
bloom; one wide enough to survive covers roughly 160 px of arc and reads as a
brighter stretch of ribbon, not a pen tip. At a gain of 25 it moved 2.2% of the
frame's pixels without ever looking like the place the drawing was happening, so
it was removed rather than shipped as a parameter that does nothing legible.

## Notation

Greek where the literature is Greek — σ, ρ, β for Lorenz, α for Halvorsen, as
the original [`equation-editions/`](../equation-editions/) had them. Aizawa's
a…f really are Latin in the standard formulation, so they stay. Superscripts are
typeset (z³, x²) rather than written `z^3`.

## Everything else is inherited

One 360° turn with a tilt sway, the luminous palettes, colour by speed against
the luminous editions' own bounds, additive glow, bloom, log-density tone
mapping, the measured growth schedule, and a cover frame of the finished
attractor for the Instagram grid — saved beside each clip as a `.cover.png`.

These do not loop: they start nearly empty, end full, and open on a cover frame.

## Layout

```text
trace-editions/
├── README.md
├── source/
│   ├── glow.py           # unchanged from luminous-editions
│   ├── systems.py        # integration plus segment subdivision
│   └── render_traces.py  # growth schedule, cover frame, export
└── instagram/phone-9x16/ # 1080×1920 H.264 exports and cover stills
```

## Run

```bash
python3 attractors/trace-editions/source/render_traces.py
```

One edition, or a fast preview (dimensions must be even — H.264 chroma
subsampling):

```bash
python3 attractors/trace-editions/source/render_traces.py --edition aizawa
```

```bash
python3 attractors/trace-editions/source/render_traces.py --width 300 --height 532 --duration 3 --fps 10 --trajectories 40 --steps 4000
```

Exports are `1080 × 1920`, 12 s, 30 fps, H.264, no audio.
