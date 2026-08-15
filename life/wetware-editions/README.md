# Wetware Editions

Conway's Life read three ways. Life is the oldest argument that biology and
computation are the same subject: a rule with no arithmetic in it that
nonetheless builds clocks, memory, guns, and things that copy themselves.

| Edition | Palette | What it is |
| --- | --- | --- |
| `culture_orchid-gold_wetware` | orchid gold | Life relaxed into a continuous field on a colony of cells |
| `gosper_electric-citrus_spacetime` | electric citrus | a Turing-complete machine, recorded in (x, y, t) |
| `ash_ember-spectrum_spacetime` | ember → spectrum | what random noise settles into, recorded the same way |

Same house style as [`../../attractors/`](../../attractors/) and
[`../../libra/solvent-editions/`](../../libra/solvent-editions/): additive
splatting into a float buffer, log-density tone mapping, multi-scale bloom, the
same three palettes, a spaced title and a technical caption, and a cover frame
of the finished object for the Instagram grid.

## Colour means age

The house rule is that colour comes from a scalar belonging to the object rather
than to the camera — speed for an attractor, residue mobility for a protein.
Here it is the **age of a cell**: how many consecutive generations it has held
on.

Age is the right scalar because it is exactly what separates the permanent from
the passing. In `gosper` the two still-life blocks at the ends of the gun are
alive for all six hundred generations and come out violet; every glider cell it
fires lives four generations at most and comes out green. Four cells in that
whole object are permanent, and the picture says so without being told to.

Age spans three orders of magnitude and is heavily skewed towards the transient,
so it is read logarithmically. A linear ramp puts every glider and nearly every
oscillator into a single colour.

## Life as a solid

`gosper` and `ash` run Conway's rule unmodified, `B3/S23`, and record the whole
run as an object: each live cell becomes a unit box in (x, y, t), and the third
axis is time. A history you would otherwise have to sit and watch becomes
something you can turn around and look at from the side.

The two are deliberately opposite. **Gosper's glider gun** is thirty-six cells
placed by hand in 1970, the first pattern shown to grow without bound and the
reason Life is Turing complete; in spacetime it is a braided column with a
perfectly regular fan of parallel rays leaving it, one every thirty generations,
forever. **Ash** starts from a disc of random noise at 38% fill and is left
alone; in spacetime it is a dense chaotic base that thins upward into a forest
of vertical columns — the still lifes and oscillators that random noise reliably
condenses into — with the occasional glider peeling off into empty space.

Each is set on an open board rather than a torus so gliders have somewhere to
go. Seeding `ash` inside a disc rather than filling the board is what turns its
silhouette from a cube into a column and gives the escaping gliders black to
cross.

The tower builds itself upward over the clip while the camera makes one full
turn, because the samples come out of the simulation in generation order and
everything computed by a given moment is therefore a prefix.

## Life as tissue

`culture` is the same idea with the discreteness taken out, on a colony of about
7,400 cells arranged by blue noise rather than on a lattice. State is a real
number in 0..1; the count of eight neighbours becomes a distance-weighted
average over the fourteen nearest cells; and the rule keeps the part that
actually matters — that there is a *window* of neighbourhood activity in which a
cell grows, and outside it, in loneliness or in crowding, it fades.

```text
                     Σ state[j] · w(d(i,j))
neighbour_signal  =  ──────────────────────
                        Σ w(d(i,j))

growth  =  +0.08   if  0.20 < neighbour_signal < 0.45
           −0.04   otherwise

state  ←  clamp(state + growth + diffusion + noise − decay − inhibit · fatigue)
```

### The window alone is not enough

That rule as stated is bistable, not excitable, and it will not animate. Fronts
leave the seeds, sweep the whole colony in about a hundred steps, and then it
sits saturated: a filled disc, uniformly on, with nowhere left to propagate
into. Measured, the first build held **52% of cells above half activation and
stayed there indefinitely** — a still image that happens to be recomputed thirty
times a second.

So each cell also carries a slow **fatigue** that chases its own activity and
subtracts from it. A cell fires, tires, and cannot fire again until it has
rested. Behind a front the tissue is spent, so the front cannot turn back on
itself and has to keep going — which is what makes rings expand, collide,
annihilate, and wind into spirals. It is the second variable every excitable
medium needs, and it is the difference between a wave and a stain.

It has to be tuned rather than guessed. At `inhibit = 0.16` the colony still
floods; at `0.45` it goes extinct within two hundred steps; the waves live at
`0.34` with `recovery = 0.10`. Because every wave eventually annihilates against
another, the colony also reseeds — a fresh ignition now and then, and always one
if the tissue has gone quiet — or the clip ends on an empty dish.

The palette is stretched over the range the rule actually reaches rather than
over 0..1. Activation settles well short of full, so read raw every crest lands
mid-ramp and the whole dish comes out one flat violet.

### Nothing may be redrawn at random

The first working build scattered each cell's splats, each core's halo and each
front's ring with fresh random numbers every frame. It is the obvious way to
write it and it is wrong twice over. On screen the dish boils, because every dot
lands somewhere new thirty times a second; and to the encoder it is fresh noise
in every frame, which took **twelve seconds to 61 MB** against 22 MB for a
comparable attractor piece — and fine per-frame noise is the first thing an
Instagram re-encode destroys.

So every scatter pattern is now drawn once and reused: a fixed unit-disc offset
per cell, one golden-angle sunflower shared by every core, and fronts sampled at
fixed angles with a phase taken from the ring's own centre. Only radius, weight
and colour follow the state. The motion stays in the tissue, where it belongs.

## Rendering

```bash
python3 life/wetware-editions/source/render_life.py
```

One edition, and a still instead of a clip while tuning:

```bash
python3 life/wetware-editions/source/render_life.py --edition culture --preview
```

Exports are `9:16`, `1080 × 1920`, `12 s`, `30 FPS`, MP4/H.264, written to
`instagram/phone-9x16/` alongside a `.cover.png`. Requires `numpy`, `scipy`,
`Pillow`, and a system `ffmpeg` with an H.264 encoder.

## What is and is not claimed

`gosper` and `ash` are Conway's rule exactly, with no tuning available and
nothing to get wrong beyond the seed; the gun was checked by measuring its
output, which is five cells of population every thirty generations.

`culture` is not Conway's Life and does not claim to be. It is a continuous
excitable medium built on Life's one real idea, and it is not a model of any
particular tissue either — the fatigue term is there because waves need a
refractory phase, not because it was fitted to a cell line.
