# Palette Editions

The same three attractors as [`emergence-editions/`](../emergence-editions/), cut
the same way — a cover frame of the finished attractor, then the formation over
one 360° turn — but finishing on exactly the colours of
[`luminous-editions/`](../luminous-editions/), and offering alternative palettes
for the other two.

| Edition | Palette |
| --- | --- |
| `lorenz_ember_emergence` | `ember` — locked; the luminous Lorenz palette, byte for byte |
| `aizawa_glacier_emergence` | `glacier` — magenta cores through blue to pale mint |
| `halvorsen_reef_emergence` | `reef` — teal cores through gold to a magenta rim |

## Why this project exists

`emergence-editions` and `luminous-editions` use a byte-identical Lorenz palette
and still do not look the same. The palette was never the problem: the
**distribution** was.

`emergence-editions` starts every trajectory from the same state so the growth
reads as a single thread, and it runs roughly twice as long to make up the
coverage that clustered trajectories fail to paint. That longer run reaches
further into the attractor's fast outer excursions — the fraction of samples
above the luminous 98th-percentile speed goes from 2% to over 6%. Colour follows
speed, so those excursions arrive at the violet end of the ramp. Hence a lavender
fringe where the luminous edition has a magenta one.

Here the sampling *is* the luminous sampling, untouched: 1200 trajectories,
3800 steps, 1400 warm-up, spread 0.55, and colour normalised against the run's
own percentiles exactly as the luminous editions do it. Same cloud, same speeds,
same bounds, same hues.

This is verified rather than assumed. Rendering the finished cloud through this
project and through the luminous modules gives `max|diff| = 0` across the whole
1080×1920 frame, exposure calibration included.

## What it costs

The growth changes character. With the trajectories already spread across the
attractor there is no single thread to follow — the piece blooms from many
threads at once. On Lorenz that reads as the two wing cores lighting up as
magenta rings and opening outwards into the butterfly, which is arguably the
better animation, but it is a different one.

If the single-thread growth matters more than matching the luminous colours,
that is `emergence-editions`. The two projects are the two sides of that trade.

## Palettes

All six ramps are built the same way as the originals — a full neon spectrum on
black — but enter it at a different point, so the fast outer shells and the slow
cores land on different hues.

| Name | Character |
| --- | --- |
| `ember` | The luminous original: magenta cores, gold body, cyan shells |
| `aurora` | Cool entry, warm tail: blue-violet cores warming to rose |
| `magma` | Everything hot; breaks to white only at the very top |
| `reef` | Tropical: teal cores through gold to a magenta rim |
| `glacier` | Cold and jewelled: magenta cores falling away through blue to mint |
| `iris` | Warm-led, resolving into gold rather than violet |

Any palette can be put on any edition:

```bash
python3 generative-science-art/palette-editions/source/render_palettes.py --edition aizawa --variant magma
```

Cover stills of every palette an edition offers, side by side, for choosing:

```bash
python3 generative-science-art/palette-editions/source/render_palettes.py --edition halvorsen --variant-sheet
```

## Layout

```text
palette-editions/
├── README.md
├── source/
│   ├── glow.py             # unchanged from luminous-editions
│   ├── systems.py          # unchanged from emergence-editions
│   └── render_palettes.py  # palettes, growth schedule, cover frame, export
└── instagram/phone-9x16/   # 1080×1920 H.264 exports and cover stills
```

## Run

```bash
python3 generative-science-art/palette-editions/source/render_palettes.py
```

Dimensions must be even — H.264 chroma subsampling. Exports are `1080 × 1920`,
12 s, 30 fps, H.264, no audio. These do not loop: they start nearly empty, end
full, and open on a cover frame.
