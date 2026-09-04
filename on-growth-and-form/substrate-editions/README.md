# Substrate Editions

Eight cuts of seven processes on a medium, six of them alive.

`substrate-editions/` is about *where* a process happens. The sibling set in
[`../source/`](../source/) runs two mathematical processes against one
biological one — Gray-Scott and differential growth against a slime mould. This
set inverts the ratio: six of these are things a microscope can be pointed at,
and **Sandpile** is a rule about integers that has no business producing an
organism and produces one anyway. That contrast is the edition's whole
argument — the substrate does the computing, and it need not be alive to look
like it.

Six of the seven make something out of nothing; **Condensate** only rearranges
what is already in the dish.

| Edition | Field | What it is |
| --- | --- | --- |
| `hyphae_mycelial-network_substrate` | biology | fungal mycelium: extend, branch, fuse |
| `cleavage_embryonic-packing_substrate` | biology | an embryo dividing at constant volume |
| `reentry_excitable-medium_substrate` | biology | spiral waves in excitable tissue (Barkley) |
| `condensate_phase-separation_substrate` | biology | liquid-liquid phase separation (Cahn-Hilliard) — **rejected**, T1/T2 |
| `sandpile_abelian-lattice_substrate` | mathematics | grains toppling on a lattice |
| `sector_range-expansion_substrate` | biology | a colony spreading on a plate, drawing its own genealogy |
| `syncytium_hyphal-fusion_substrate` | biology | `hyphae` 2.0 — six spores fusing into one network |
| `culture_cortical-network_substrate` | biology | dissociated cortical neurons wiring themselves up (Wagenaar 2006) — **rejected**, T4 |

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
| `sector` | colonised area | equal area per frame is equal newly-lit pixels per frame |

For `hyphae` the front is also lit brighter than the rest — the advancing tips
are the only part of the frame doing anything, and giving the eye something to
track is most of what keeps a growth clip watchable.

## The seven processes

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


### Sector

**Rejected for the grid (T2), 2026-09-01.** The measurements are clean — a flat
25/25/25/25% profile, 5.4% still frames — and the cut still reads as one
coloured disc inflating: the wedge layout is set almost at once and everything
after is the same pattern at a larger radius, because the real competition
(boundaries wandering, lineages going extinct) plays out on a front too thin to
see at video scale. Numbers passed; the shape never did anything the eye could
follow. Kept because two things in it are worth reusing — see below and
[`REJECTED.md`](../../REJECTED.md).

A colony spreads on a plate and only its edge can divide. Everything inland is
jammed against its neighbours and has stopped, so the interior is not a
population — it is a record of who was at the front when that ring was laid
down. Label the founders and the plate draws its own genealogy: the wedges are
clones, their boundaries wander as one side or the other gains a few cells of
frontage, and when two boundaries meet the lineage between them is gone from
the front forever while every one of its cells is still alive inland. Mutation
is what stops the picture settling — a few new lineages divide fractionally
faster, push their arc of the front ahead of their neighbours, and a bulging
front captures more of the circumference as it goes. Hook *"Not one cell moved.
Every border did."*

- **The eight-neighbour rule grows a diamond, not a plate.** Asking "is any of
  my eight neighbours occupied" lets the diagonals advance √2 too fast, and the
  colony comes out square with its corners on the diagonals. Measured as the
  cos(4θ) component of the front radius, as a fraction of the mean radius:
  **7.43% on eight neighbours, 4.80% on four, 2.99% on a disc of radius 1.9,
  1.35% on a disc of radius 6.0 — and 0.98% here.** What ships asks a different
  question: how much colony *surrounds* this site, measured with a Gaussian at
  σ 2.0, which has no preferred direction. Cells still only ever appear one
  lattice cell outside the colony, so lineage boundaries stay pixel-sharp; a
  fat structuring element buys isotropy by letting cells jump six pixels from
  their parent, which blurs the one structure the piece is about. Same lesson
  as the isotropic nine-point laplacian in
  [`../source/CLAUDE.md`](../source/CLAUDE.md).

- **Nothing is banked.** The lattice is written once and never rewritten, so a
  state is not stored — it is recovered exactly by taking the cells whose
  arrival step is at or below the one wanted. One `int32` array holds the whole
  clip, against the 184 MB banking every labelled state would have cost.

- **Radius pacing is the prettier idea and the wrong one.** Paced by equal
  radius increments the front advances at a steady speed and the change profile
  comes out comet-shaped — **9.5% of the growth in the first quarter and 40.4%
  in the last**, which is the profile the account explicitly values. It also
  spends the opening two seconds on a dot, and a dot advancing one cell of
  radius changes almost no pixels: **22.6% frozen frames, 52 of the 54 inside
  the first two seconds**, longest run 21. Equal *area* per frame is equal
  newly-lit pixels per frame, which is the thing the frozen-frame test actually
  measures: **5.4%, and 1.3% once the 11-frame cover hold is discounted**, at
  the cost of a flat 25.1 / 24.7% profile. The intermediate, area^0.75, splits
  it at 7.9%. The comet profile was worth giving up; a stall in the first two
  seconds is not recoverable.

- **The default bloom made a pastel sticker of it.** A colony is a solid mass,
  so `bloom` is the nominal choice, and it bleached every wedge towards white
  and lifted the black into a mid-tone veil. This ships on **`sharp`**, and the
  look is recorded in the edition's `EDITIONS` entry as well as in the
  filename — `venation` shipped on `sharp` with nothing recording it and
  re-rendering silently changed the cut.

- **`LINEAGE` is the one palette in the set that does not darken at its low
  end**, and that is deliberate. Hue here is an identity, not an amount, so
  dimming the first stop would say a wedge was less of something. Brightness is
  carried by the density channel instead, which is why the plate is still black
  where nothing has grown and why the rim is the brightest part of it. The arc
  runs violet to gold and never reaches cyan or green: `cleavage` owns the cold
  end of this edition.

- **A mutation moves its lineage 0.26 of the ramp from its parent.** At the
  honest 0.075 the sub-wedges were invisible — everything descending from one
  founder read as a single flat colour. At 0.26 relatives still look related
  and a wedge inside a wedge is legible as what it is: a mutation that happened
  inside a clone that was already winning.

- **Drift alone does not carry eight seconds, and this was measured before any
  render code existed.** Neutral founders coarsen and then stop: 21 lineages on
  the front at the start, 9 by the quarter mark, and **9 / 9 / 9 for the rest
  of the clip — 12 extinctions in the first quarter and zero after**. Sector
  boundaries diffuse as √t while the circumference grows as t, so once they are
  apart they never meet again; this is physics, not tuning. Mutation is the
  external clock the brief calls for, and with it the front holds 48 / 31 / 33 /
  34 lineages across the quarters. 444 lineages are founded over the run, 46
  reach the rim, and 38 of those did not exist when it started. Of the 48
  founders in the drop, **8**.

### Syncytium — `hyphae` 2.0

Built 2026-09-02. Same engine as `hyphae`, four things changed: the look
(`bloom` → `sharp`), the scale of the mesh, the shape (`dish` → `field`) and
what the colour means (age → which spore). Hook *"A tree only branches apart. /
These branched into each other."*, a deliberate second half to the first cut's
*"A tree branches. A fungus branches back."*

- **The shipped `hyphae` never shows the fusion its hook is about.** At
  `sensor 7` and `branch_rate 0.030` the colony fills **72.1% of the dish with
  1.4 px between filaments** — finer than a pixel, so the mesh tone-maps into a
  lamp and every loop in it is gone. Opening the avoidance radius to 20 and
  cutting the branch rate to 0.009 gives **8% coverage at ~14 px spacing**,
  which is what makes the network legible as a network. Measured on the way:
  `sensor 16` → 8.2% / 12.3 px, `sensor 20 branch 0.010` → 10.7% / 9.3 px
  (solid again once the grid downscales it), `sensor 28` → 3.7% and the fusion
  rate *falls* in the last quarter, which would have failed T2.

- **The dish was never the fix; the density was.** The note further down this
  file says the mycelium had to be given a plate because unbounded it ran off
  every edge, filled the frame corner to corner, blew out to white and put the
  caption on a bright field. All three of those are consequences of 72%
  coverage. At 8% the frame keeps its black and `bound="frame"` is safe, so
  this cut is the same colony let out to the frame edge.

- **`field` still costs what the `reel` skill says it costs.** On the finished
  frame the title band is **42.5% covered**, the hook band 57.7%, the data
  block 48.4% — but at mean luminance 0.12–0.16 under each. The scrim and the
  hook's stroke carry it and the text reads; this is mitigated, not solved, and
  it is the reason `slide` exists.

- **One spore is a disc for half the clip whatever it is bounded to.** Six
  spores on a jittered grid fix that and buy the piece its event: colonies meet.
  Random scatter was not used — it clumps, and a clump merges before either
  colony has visibly been a colony.

- **The event is measured, not asserted.** First fusion joining two different
  spores at simulation step 347, which is **frame 78 — 2.60 s**. Grafts per
  quarter of the clip after the cover hold: **0 / 31 / 104 / 271**, i.e. 0 →
  16.2 → 54.5 → 142.0 per second. The first quarter is six organisms and the
  last is one. 1,520 segments over the run, 1,312 fuse, 407 of those join two
  spores.

- **Colour is identity, so the palette has one stop per spore.** Six stops,
  six spores, a segment lands exactly on its own and there are no in-between
  colours to go muddy — the same argument as `LATTICE`'s four stops for four
  states. Brightness is carried by density instead, as in `LINEAGE`. `FLUORO`
  is the reading a fluorescence microscope gives with strains on separate
  channels and the channels summed; two calmer candidates were rendered
  alongside it and turned down for less impact.

- **`sharp` at `venation`'s exposure, not `sector`'s.** A frame 8% covered by
  one-pixel filaments has a fraction of the density a solid plate has, and at
  the nominal `1.00 / 1.05` the mesh came out bone-white and lost most of its
  colour to the 200 px downscale. Ships at `1.10 / 1.20`.

- **The model change is transparent to the parent cut.** `Hyphae` now carries
  segment identity, a fusion step, a founder and a pixel-ownership map, and
  none of it draws from the generator, so `hyphae` re-renders to md5
  `69e8f4e86a5882b5c4589531ba66d6f1` — byte-identical to the posted cover.

### Culture

**Rejected for the grid (T4), 2026-09-04.** Shown cold, it reads as blinking
dots — the wiring-up and the burst it develops into, which is the entire
point of the piece, never becomes visible. Kept below because the model and
the splatting fix are real; see [`REJECTED.md`](../../REJECTED.md).

A cortical culture is plated as a suspension of single dissociated cells, every
connection they had destroyed in the process, and left to wire itself: over
the days that follow each cell puts out neurites, and a synapse switches on
wherever one cell's reach passes another's — nobody specifies the wiring, it
is a consequence of where each cell happened to land (Wagenaar, Pine & Potter
2006). The rule per cell is integrate-and-fire with short-term depression: a
cell charges, fires, empties, and a cell that just fired has less to give,
which is what stops a wave rather than letting it burn across the whole field.
Nothing is fitted, trained or searched. Eight seconds here stand for roughly
the first three weeks of a real culture — isolated spikes at the start, then
patches firing together, then dish-wide bursts nobody wired and nobody
triggers, as the neurites simply get long enough to reach further.

- **A neuron is one point, and a point is one pixel — the mistake that sank
  `aggregation` and `nematic`.** At 12,000 neurons the mean spacing is 7.7 px,
  so cells drawn a pixel wide stay separate specks at any size and tone-map
  into grey speckle at the grid thumbnail. Splatted as a small disc of samples
  instead, so neighbours fuse into mass wherever the tissue is actually active.
- **No floor under a cell that has never fired.** A flat floor over all 12,000
  covers three quarters of the frame in dust — the first cut's mistake — and
  buries the structure it was meant to sit under. Brightness is spike plus a
  slow decaying trace, and nothing else.
- **Colour is recency, ranked over every spike in the clip rather than per
  frame** — a long thin tail of cells go over on almost nothing, so a linear
  map would put four spikes in five on one palette stop. Ranking once, over
  the whole run, is what keeps an early frame genuinely sitting at the cold
  end of the ramp (house rule 2's case for ranking a skewed scalar).
- **Banked one state per frame and played straight through, not paced by
  measurement.** Every other process in this edition is paced because it
  creeps and then floods; this one carries its own beat — the developmental
  arc from isolated spikes to dish-wide bursts — and re-timing that clock
  would destroy the thing worth watching.

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
