# Harmonic Roulettes

Three editions about one question: **does the curve ever come home?**

A roulette is the path of a pen fixed to a circle that rolls without slipping
along another circle. One pen, one unbroken line, no randomness anywhere. The
ratio of the two radii decides the whole fate of the drawing — a rational ratio
closes into a finite rosette, an irrational ratio never closes at all.

That makes this collection the counterpart to `attractors/`. Those trajectories
never repeat because they are chaotic; these never repeat — or repeat exactly —
for a reason from number theory instead.

## The three editions

| Edition | Rolls | Ratio | Fate |
| --- | --- | --- | --- |
| `hypotrochoid` | inside | `233/144` (Fibonacci) | closes after 144 turns |
| `epitrochoid` | outside | `199/64` | closes after 64 turns |
| `golden-roulette` | inside | `φ = (1+√5)/2` | never closes |

The first and the last are the same argument twice. `233/144` are consecutive
Fibonacci numbers, so the ratio is the best rational approximation of φ that
numbers that size can give — near enough that the figure looks like the golden
one, rational enough that it must eventually shut. The golden edition uses φ
itself and keeps missing its own starting point forever. It is the rational
shadow standing next to the thing that casts it.

`d` is the pen's distance from the rolling circle's centre. It sets the
silhouette: `d < r` fills the disc and lights a core, `d > r` opens a void and
throws the caustic ring outward.

## Rendering

```bash
python3 spirograph/harmonic-roulettes/source/harmonic_roulettes.py --all-pieces
```

Still previews instead of MP4 files, which is much faster while tuning:

```bash
python3 spirograph/harmonic-roulettes/source/harmonic_roulettes.py --all-pieces --preview
```

One edition on its own:

```bash
python3 spirograph/harmonic-roulettes/source/harmonic_roulettes.py --piece golden-roulette
```

Exports are `9:16`, `1080 × 1920`, `12 s`, `30 FPS`, MP4/H.264, written to
`instagram/phone-9x16/`. The renderer draws 15 distinct frames per second and
lets ffmpeg repeat them into the 30 FPS file. Requires `numpy`, `Pillow`, and a
system `ffmpeg` with an H.264 encoder.

## How the light is built

The curve is sampled at constant steps in `t`, the turning angle of the rolling
circle — equal steps in *time*, not in distance. The pen therefore leaves more
samples where it moves slowly, and those crowded samples are what burn the
bright caustics into the figure. The physics does the shading; nothing is
painted on by hand.

Two buffers accumulate at double resolution. One counts how much ink landed on
each pixel, the other banks the shade that ink carried. Colour is only resolved
at the very end, as a density-weighted average rather than a sum — adding
colours channel by channel would let crossing strands add their way to a muddy
white, which is exactly what flattens a dense weave. Hue stays as pure as a
single strand no matter how many cross it, and density alone decides how
brightly that hue burns. Only the very densest crossings bleach out to white.

Colour follows **radius**, not progress along the curve. Every strand crosses
the entire figure, so colouring by progress just averages the whole palette
into mud; the radius is the coordinate the rolling circle actually modulates,
so it lays the spectrum down in clean concentric bands.

Each palette holds one restrained hue family — violet, verdigris, brass — and
every stop in it stays luminous. Darkness in these frames comes from strands
thinning out, never from a dark colour.
