# Substrate Editions

Five processes on a medium, four of them alive.

`substrate-editions/` is about *where* a process happens. The sibling set in
[`../source/`](../source/) runs two mathematical processes against one
biological one — Gray-Scott and differential growth against a slime mould. This
set inverts the ratio: four of these are things a microscope can be pointed at,
and **Sandpile** is a rule about integers that has no business producing an
organism and produces one anyway. That contrast is the edition's whole
argument — the substrate does the computing, and it need not be alive to look
like it.

Four of the five make something out of nothing; **Condensate** only rearranges
what is already in the dish.

| Edition | Field | What it is |
| --- | --- | --- |
| `hyphae_mycelial-network_substrate` | biology | fungal mycelium: extend, branch, fuse |
| `cleavage_embryonic-packing_substrate` | biology | an embryo dividing at constant volume |
| `reentry_excitable-medium_substrate` | biology | spiral waves in excitable tissue (Barkley) |
| `condensate_phase-separation_substrate` | biology | liquid-liquid phase separation (Cahn-Hilliard) — **rejected**, T1/T2 |
| `sandpile_abelian-lattice_substrate` | mathematics | grains toppling on a lattice |

The tests a piece has to pass before it is built are in
[`BRIEF.md`](../../BRIEF.md); the queue and the decisions are in
[`PLAN.md`](../../PLAN.md).

Everything structural is inherited from the attractor, protein and morphogen
pieces: black field, additive accumulation into a float buffer, log-density tone
mapping, multi-scale bloom, spaced title, monospace caption, and a cover frame
of the finished form for the grid. Two things are not.

## Eight seconds, and the clip is a loop

It opens on the finished organism, cuts to a single seed, and grows back to
exactly the frame it opened on.

The first thing anyone sees is the payoff, which is what buys the second of
attention a feed gives you. The cut turns that into a question. And because the
last frame *is* the first frame, the loop closes with no seam, so the answer
starts playing again before anyone notices it has — which is the whole trick,
since watch time is counted in loops.

## Growth paced by measurement, not by the clock

Every one of these processes runs on its own schedule. A mycelium creeps and
then floods. An embryo doubles, so the first division takes as long as the last
thousand. A sandpile's edge slows as the square root of its grain count. Put any
of them on a linear timeline and the clip crawls and then bolts.

So each model reports a scalar for how far along it is, and frames are placed at
equal intervals of *that* rather than of time:

| Edition | Progress measured by | Why that one |
| --- | --- | --- |
| `hyphae` | pixels ever colonised | the picture is the colonised area |
| `cleavage` | √(cell count) | wall length at fixed area rises with the root |
| `sandpile` | grains ∝ t² | area rises with grains, so the radius rises linearly |

For `hyphae` the front is also lit brighter than the rest — the advancing tips
are the only part of the frame doing anything, and giving the eye something to
track is most of what keeps a growth clip watchable.

## The five processes

### Hyphae

A hypha only ever extends at its tip. It wanders, it branches, and
when it runs into another hypha it fuses with it and stops. That fusion is
anastomosis, and it is the whole difference between a fungus and a tree: a
mycelium is a *network*, with loops in it, able to route around damage and move
material between distant points. Tips also turn away from ground already
colonised, which is the cheapest honest stand-in for growing down a nutrient
gradient — the substrate behind the front is spent. The colony is bounded like a
plate culture, and it ends when every tip has either fused or reached the rim,
which is why the finished frame is where the process actually stops rather than
where the clock ran out.

### Cleavage

The one kind of growth that does not grow. A fertilised egg
divides and divides without gaining mass, so each round halves the cells rather
than enlarging the animal; the disc here never widens, it only gets finer.
Between divisions the cells relax towards the centroids of their own Voronoi
regions, which is Lloyd's algorithm and also, near enough, what surface tension
does to a packed sheet — the reason a real epithelium looks like a honeycomb
that has been sat on rather than like a random scatter. Colour is division
depth, so the lighter patches are the parts of the tissue that have divided most.

### Sandpile

A cell holding four grains gives one to each neighbour. That is
the entire rule. Drop a hundred and fifty thousand grains on a single square of
an empty lattice and what stabilises is not a heap but a sharply bounded fractal
of straight-edged regions — the same one every time, whatever order the grains
arrived in, which is what *abelian* means here. It is in this set as the
mathematics, and it earns its place by looking like a radiolarian while
containing no biology whatsoever.

### Reentry

Spiral waves in excitable tissue, Barkley's model. A sheet fires once and
cannot fire again until it recovers; waves annihilate on each other's wakes
and nothing in the rule says *spiral*. A spiral needs a wave with a free end,
so the piece induces one the way a cardiology lab does — a premature beat into
the tail of the wave before it, half onto tissue that has recovered and half
onto tissue that has not. Four of those plus a deliberately non-uniform
excitability field (`roughness 0.016` — the one number that decides the piece:
below it the dish stays orderly, above it the first wave shatters before it
has been a wave). Colour is time since firing, carried by a decaying phosphor
(`afterglow`); without it the excited state is two cells wide and gone, and
the frame holds no record of where the wave has been. Hook *"Nothing in the
rule says spiral."*

### Condensate

**Rejected for the grid (T1, T2)** — the clip is droplets getting fatter and
nothing else, and the blobs are off-register for the account's look. The model
and the state-banking method are kept; see [`REJECTED.md`](../../REJECTED.md).
The record below is what it cost to get right, which is worth not re-learning.


Liquid-liquid phase separation, Cahn-Hilliard, `growths.Condensate`. **Built,
not posted.** The edition's fifth, and the only one that adds no material
after the first step: it just rearranges what is already in the dish.
Membraneless organelles — the cell builds a compartment out of nothing but a
preference for its own company.

- **A conserved field is what makes it separate.** Anything between the two
  wells of the free energy is unstable, and because material moves rather than
  appears, noise cannot fade — it has to go somewhere.

- **The timestep is not a free choice.** With `dx = 1` the fourth-order term
  needs `dt < 2/(8·(8ε²−1))`, about 0.017 at ε 1.4. Overrun it and the field
  does not wobble, it saturates on the first few steps and freezes into a
  speckle that never coarsens — while conserving mass perfectly, so every
  summary statistic still looks plausible. Shipped at ε 1.0, `dt 0.01`.

- **Simulated at a quarter of the frame and upsampled fourfold.** Coarsening
  is a t^(1/3) law, so doubling the grid costs eight times the steps to reach
  the same droplet size; and droplets are smooth blobs, which enlarge far
  better than anything with a filament in it.

- **Colour is the radius of the drop a pixel belongs to**, against a fixed
  reference (12 cells reads white), not ranked per frame — a per-frame rank
  would hide the one thing worth seeing, which is that at the end every drop
  is genuinely bigger. Age was tried first and reads worse: it records where a
  drop has *drifted*, so each ends up with a hard bright crescent on the side
  it grew into, which looks like a rendering fault.

- **It needs no scheduler at all, and finding that out took three goes.** A
  scheduler can only repeat a state or skip one; it has no intermediate states
  to hand out, so wherever it decides more frames are deserved it shows the
  same picture several times, which *is* the stutter. Pacing by droplet scale
  froze 117 of 239 transitions (0.70 s dead inside the opening two seconds)
  because coarsening is t^(1/3) and the scale spends its range in the first
  few states. Pacing by measured picture-change fixed the late clip and broke
  the early one, 22%. What works: **bank the states on a cube-root spacing so
  consecutive ones differ by roughly equal amounts, then play them straight
  through** — 5%, against a house norm of 4%. The floor, measured by comparing
  consecutive banked states directly, was 1%.

- **Ripening is slow, and stopping early is what made it look like nothing was
  happening.** 199 droplets at 20k steps, 22 at 1.2M. The shipped cut runs
  1.2M steps after a 4k settle, so the dish goes from a fine dense posy to a
  couple of dozen fat drops. The first attempt stopped at 146k and the whole
  transformation was droplets getting about twice as fat. Hook *"Nothing was
  built. It only stopped mixing."*

- Rejected on the way: **Liesegang rings**. Periodic precipitation would have
  filled the same gap, but eight parameter sweeps never separated into bands —
  the first precipitate becomes a permanent sink and drains the product from
  the whole dish, leaving one solid disc that fades outward. Worth another
  attempt only with a model that limits the sink explicitly.


## Rendering

```bash
python3 on-growth-and-form/substrate-editions/source/render_substrate.py
```

One edition, and a still instead of a clip while tuning:

```bash
python3 on-growth-and-form/substrate-editions/source/render_substrate.py --edition hyphae --preview
```

Exports are `9:16`, `1080 × 1920`, `8 s`, `30 FPS`, MP4/H.264, written to
`instagram/phone-9x16/` alongside a `.cover.png`. Requires `numpy`, `scipy`,
`Pillow`, and a system `ffmpeg` with an H.264 encoder.

## Notes on what had to be fixed

**The mycelium had to be given a dish.** Unbounded, it ran off all four edges,
filled the frame corner to corner, blew out to white and put the caption on a
bright field. Bounding it to a disc restores the black the house style is
composed on, and a plate culture is what a mycelium is usually looked at in
anyway.

**The sandpile needed a four-stop palette.** The process has exactly four
states, and a six-stop ramp samples them at 0, ⅓, ⅔ and 1 — landing three of
the four between stops and muddying the only thing the picture has to say, which
is how many grains are on each cell. One stop per state, and the regions
separate cleanly.

**The sandpile is simulated once and banked.** Animating it means stabilising
after every batch of grains, and a stabilisation cascades through the whole pile;
simulating it twice, once for the cover and once for the clip, costs minutes for
nothing. Each state is a quarter of a megabyte as `int8`, so the entire run fits
in about thirty-five megabytes of memory instead.
