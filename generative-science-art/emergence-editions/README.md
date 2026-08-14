# Emergence Editions

Three attractors forming, rendered in the house style of
[`luminous-editions/`](../luminous-editions/) and cut for Instagram.

This project goes back to the idea behind [`equation-editions/`](../equation-editions/)
— letting the attractor build rather than presenting it finished — and keeps
everything the luminous edition established: the same single 360° turn and tilt
sway, the same palettes, the same additive glow, bloom and log-density tone
mapping. Only the growth is new.

| Edition | Palette |
| --- | --- |
| `lorenz_ember-spectrum_emergence` | ember → spectrum |
| `aizawa_orchid-gold_emergence` | orchid gold |
| `halvorsen_electric-citrus_emergence` | electric citrus |

## Cut for the grid

Frame one is the **finished** attractor, at whichever turn angle fills the frame
best, because Instagram takes the first frame as the grid thumbnail. From frame
two the formation plays from almost nothing to complete. The cover is also saved
beside each clip as a `.cover.png`, in case setting it as a custom cover is
easier than relying on the first frame.

## The growth is physical, not a wipe

Nothing is masked or faded in. Every trajectory starts from essentially the same
state — an initial spread of 0.02 — so the opening seconds show a single thread.
Chaos pulls the trajectories apart, and the sculpture is what that divergence
leaves behind. Sensitive dependence *is* the animation.

Three things had to be measured rather than guessed.

**The trajectories must start on the attractor.** Launching them from off it
sends a very fast transient sweeping across the frame, and since colour follows
speed, that transient arrives violet. It is what made the first Lorenz emergence
read cold and purple next to its warm luminous counterpart, even though the two
use a byte-identical palette. A luminous-length warm-up fixes it.

**Colour needs borrowed bounds.** Speed is normalised against the sample
population, so a run with different parameters maps the same physical speed onto
a different part of the palette — Lorenz's 98th percentile moves from 182 to 241
without the warm-up. Each edition therefore takes its bounds from a reference run
in the luminous configuration. That reference is run at full length on purpose: a
cheap approximation does not converge for Lorenz, whose heavy speed tail comes
out at 52 instead of 182 while the trajectories are still clustered.

**The run must be about twice as long.** While the trajectories are still bunched
their samples all retrace one curve and add no coverage, so the luminous step
count would finish on a visibly thinner attractor — 5.9% of the frame lit against
25.4%. At 9000 steps all three systems land within a point or two of their
luminous counterparts.

## Pacing

Revealing samples at a steady rate looks terrible. Measured on the finished
Lorenz run: the first half of the samples paint about a seventh of the final
image, then a seventh of them paint four fifths of it as the trajectories come
apart, and the last third lights no new pixels at all. Played back linearly that
is a crawl, a bang, and a freeze.

So the schedule is measured. During setup the samples are splatted in age order
into a running density buffer and the mean log density is recorded as it climbs —
one full splat, not one per probe. Inverting that curve gives the age to draw up
to at each moment, which makes the attractor fill the frame at an even rate. The
metric is mean *log* density rather than covered area because the tone mapper is
logarithmic: coverage alone would write off the last third of the samples as
worthless and dump them in at once as a visible pop, when they are in fact what
thickens the wings.

`--growth-shape` bends the result. At `1.0` growth is strictly even; the default
`1.5` buys the opening single-thread phase more time than evenness would give it.

## These do not loop

The luminous editions loop seamlessly. These cannot — they start nearly empty and
end full, and they open on a cover frame besides. The turn still completes
exactly once.

## Layout

```text
emergence-editions/
├── README.md
├── source/
│   ├── glow.py              # unchanged from luminous-editions
│   ├── systems.py           # flow sampler, plus per-sample age and speed bounds
│   └── render_emergence.py  # growth schedule, cover frame, export
└── instagram/phone-9x16/    # 1080×1920 H.264 exports and cover stills
```

## Run

```bash
python3 generative-science-art/emergence-editions/source/render_emergence.py
```

One edition, or a fast preview (dimensions must be even — H.264 chroma
subsampling):

```bash
python3 generative-science-art/emergence-editions/source/render_emergence.py --edition aizawa
```

```bash
python3 generative-science-art/emergence-editions/source/render_emergence.py --width 300 --height 532 --duration 3 --fps 10 --steps 4000
```

Exports are `1080 × 1920`, 12 s, 30 fps, H.264, no audio.

## Also tried

The Thomas attractor was rendered as a fourth candidate and dropped. It resolves
as thin open loops rather than a dense surface — 29% of the frame lit against
40–50% for the other three — and its wireframe character broke the set's
coherence. Its coefficients are still in `systems.py` if it is worth revisiting.
