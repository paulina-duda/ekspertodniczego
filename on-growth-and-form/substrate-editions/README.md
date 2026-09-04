# Substrate Editions

Eight processes on a medium, six of them alive.

`substrate-editions/` is about *where* a process happens. The sibling set in
[`../source/`](../source/) runs two mathematical processes against one
biological one — Gray-Scott and differential growth against a slime mould. This
set inverts the ratio: most of these are things a microscope can be pointed at,
and **Sandpile** is a rule about integers that has no business producing an
organism and produces one anyway. That contrast is the edition's whole
argument — the substrate does the computing, and it need not be alive to look
like it.

**Defect** is the second piece here that is not alive, and it comes at the
argument from the other side. Sandpile is arithmetic that behaves like an
organism; Defect is an organism's own parts — microtubules, the motor that
walks along them, the fuel — with the organism taken away and the motors left
running. One has no biology in it at all and one is made of nothing else, and
neither is alive.

Six of the eight make something out of nothing; **Condensate** only rearranges
what is already in the dish, and **Defect** rearranges nothing at all — the
film has all its material from the first step and spends the clip destroying
its own order.

| Edition | Field | What it is |
| --- | --- | --- |
| `hyphae_mycelial-network_substrate` | biology | fungal mycelium: extend, branch, fuse |
| `cleavage_embryonic-packing_substrate` | biology | an embryo dividing at constant volume |
| `reentry_excitable-medium_substrate` | biology | spiral waves in excitable tissue (Barkley) |
| `condensate_phase-separation_substrate` | biology | liquid-liquid phase separation (Cahn-Hilliard) — **rejected**, T1/T2 |
| `sandpile_abelian-lattice_substrate` | mathematics | grains toppling on a lattice |
| `packing_monolayer-verticalisation_substrate` | biology | a flat colony that runs out of plane |
| `plaque_luria-delbruck_substrate` | biology | phage clearing a lawn, and the mutants already in it |
| `defect_active-nematic_substrate` | biology, not alive | a film of microtubules and motors tearing itself apart |

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
| `packing` | covered area + cells standing up | two phases, and neither scalar paces both |
| `plaque` | lawn biomass + cleared area + colony area | three phases, weighted 0.6 / 2.2 / 0.7 |
| `defect` | order lost + defect count + total sliding | two phases, and the defect count is an integer |

For `hyphae` the front is also lit brighter than the rest — the advancing tips
are the only part of the frame doing anything, and giving the eye something to
track is most of what keeps a growth clip watchable.

## The processes

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

### Packing

Rod-shaped bacteria growing in a monolayer, `growths.Packing`. Every cell
elongates and splits at twice its birth length, and that is the entire rule:
nothing in it mentions a neighbour, and no cell can sense one. The colony fills
the dish, the growing does not stop, and what gives way is the plane — cells
squeezed harder than adhesion holds them tip out of the monolayer and stand on
end, which is how a flat colony becomes a biofilm.

- **The piece this was pitched as does not exist.** It was pitched on mechanics
  computing alignment — a crowd of rods shoving itself into nematic domains,
  measured at `1.00 → 0.42 → 0.67`. That arc was rods passing through each
  other. With the contact solver fixed, local nematic order is flat at
  `0.573 / 0.565 / 0.576 / 0.535 / 0.521 / 0.533 / 0.560 / 0.538` and domain
  size sits at about ten cells the whole way, free or confined. **A freely
  growing monolayer is self-similar and has no arc in it**; the honest
  one-line description was "it gets bigger", which is T2's fail condition.
  Everything below is what was built after that.

- **A force solver cannot be stiffened into honesty.** It trades stiffness
  against stability and settles wherever the springs and the timestep balance:
  mean contact overlap 27.8% of a cell width, 90th percentile 61.2%, max 91.1%,
  at a packing fraction of 1.02. Stiffening it 6.7× reached 16.5% and no
  further, and the apparent ordering fell with it — which is what identified
  the ordering as interpenetration in the first place. Position-based
  projection replaced it.

- **Projection alone did not fix it either, and the reason is geometric.**
  Local relaxation moves information about one rod per iteration, so pressure
  raised in the middle of a colony forty rods across cannot reach the rim
  inside a step and the interior stays crushed: 300 iterations on a jammed
  state moved mean overlap from 18.90% only to 17.83%. The fix is to grow the
  biomass and then expand the whole colony by the same factor before the solver
  is asked for anything, leaving it only the local rearrangement. **Gated on
  measured density** — applied blind it inflates a two-cell colony into a
  sparse disc, which is what it did on the first attempt. Overlap during free
  growth then holds at **1.4% mean, 3.1% at the 90th percentile, 8.3% max**, at
  density 0.800.

- **Verticalisation is not decoration; it is what makes the packing feasible.**
  It is the only thing in the model that removes area. Without it, growth past
  the full dish drives density to 2.33 — twice as much cell as there is dish —
  and the solver answers a question with no answer by laying rods through each
  other, 26.8% mean overlap and 100% max. Local order climbs from 0.55 to 0.84
  in lockstep with that overlap, which is the same artifact arriving by a
  second route. With cells tipping out, density stays at 0.95 and overlap at
  5.6%.

- **The threshold was measured, not chosen.** Contact load during free growth
  runs at a median of 0.072 and tops out near 0.33; confined, the median rises
  to 0.296. At `adhesion 0.45` nothing tips before the dish is full.

- **A vertical cell has no in-plane angle, and that quietly corrupted two
  measurements.** Zero length makes `arctan2(0, 0)` return 0, so every upright
  cell reads as aligned with every other and they merge into one domain —
  reported as a mass-weighted domain size of 1,900 and an order parameter that
  appeared to rise a second time. Both measures now exclude them. **This is the
  same error as the interpenetration, found twice in one piece**: a number that
  agreed with the story, for a reason that had nothing to do with the biology.

- **Colour is contact load, and orientation was tried first and abandoned.**
  Orientation is cyclic, so its ramp has to return to its first stop; keeping
  luminance level all the way round — which is what stops one arbitrary
  direction reading as a lighting fault — costs the dark low end and with it
  house rule one. The cut came out an evenly lit pastel mosaic in which nothing
  was brighter for being denser and the cells standing up did not separate at
  all. Load has a true zero, so `STRESS` can start at black and mean it, and
  the fixed reference is each cell's own threshold: the top of the ramp means
  one thing all clip, *about to leave the plane*. Cells that have gone are gold,
  off the ramp on purpose.

- **Two phases, and no single scalar paces both.** Cell count is flat at 2 for
  the first ~120 steps while the founders only elongate, and every frame the
  schedule spent in there read as frozen — 5.7% of transitions after the hold,
  **all of them inside the first second**, which is the worst second to lose.
  Area has no such plateau but saturates once the dish is full, giving the
  breakup 72 frames of 229. The schedule advances on both: covered area, plus
  the standing-up count at weight 0.8. That puts the dish full at frame 83 and
  gives the breakup 146, and takes the frozen fraction after the hold to
  **0.4%**, against a house norm of 4%.

- **The colony leaves the plane from the middle outwards**, which is the one
  thing in the piece nobody put there. 70% of the cells in the innermost fifth
  have stood up against 32% in the outermost; mean radius 0.569 for upright
  cells against 0.698 for flat ones; the first twenty to tip sit at radius 17.7
  in a colony already reaching 53.5. A cell at the rim still has somewhere to
  push. Hook *"Room runs out. Growth does not."*

- **The run is banked and reused.** Eight minutes of simulation against seconds
  of drawing, and every look decision wants judging on the same colony rather
  than a fresh one — `--packing-cache` writes the states once. The same reason
  the sandpile is simulated once rather than twice.

### Plaque

A phage epidemic on a bacterial lawn, `growths.Plaque`. Susceptible cells,
infected cells counting down to lysis, free phage that diffuses, and a couple of
hundred resistant cells that were on the plate before any phage landed. It is
the Luria-Delbruck argument as a picture: resistance is not acquired from the
encounter, and the phage only reveals which cells already had it.

- **Seeding the mutants beforehand is the piece, not a convenience.** The first
  version used a smooth mutation rate over the whole plate, and resistance
  appeared everywhere at once and refilled the plate uniformly -- which is the
  opposite argument, and it also looked like nothing. Discrete founders, present
  at step zero, is both the correct claim and the only version that produces
  colonies.

- **One term decides whether a plaque is a plaque.** Phage need a host that is
  dividing, so adsorption is gated on the room left in the lawn. Without it the
  epidemic eats the whole plate: 96% cleared, the plaques merged into three
  connected regions, and the finished frame a black disc with a few colonies on
  it. With it, and with the lawn near confluence when the phage arrives, the
  plaques stop individually -- 80 of them at a radius of about 14 simulation
  units, 48% cleared and half the lawn still standing.

- **How thin the lawn is plated sets the plaque size**, because the phage can
  only exploit the growth the lawn has left. Plated at 0.45 of carrying
  capacity there were 59 plaques; at 0.65, 80; at 0.80, 210 and much smaller.

- **The colonies have to be stopped while they are still dots.** Run to 5% of
  the plate they fill the clearings they grew in and the frame is blobs again,
  which is the register `condensate` was rejected for. Stopped at 2-4% they read
  as colonies sitting inside plaques, and some plaques have none -- which is the
  honest picture, since a resistant cell only ever shows itself if the phage
  happens to clear the ground around it.

- **The lawn is plated as individual cells, not carried as a field.** A lawn at
  carrying capacity is flat, so the tone mapping and the bloom would have had
  nothing to work on across most of the plate; 700,000 plated cells put the
  brightness back where the house style keeps it, on how many cells are on the
  pixel. A plaque is black because it is empty.

- **`sharp`, and the filename says so.** The subject is entirely edges -- a
  plaque is where the lawn stops -- and the default halo smears every one of
  them into smoke. The look is pinned in the edition spec rather than left to
  the flags, because `venation` shipped on `sharp` with a filename that did not
  record it and re-rendering silently changed the cut.

- **The motion check took four goes and the process was the problem each time.**
  Paced on the plaques alone the clip measured **78.7% frozen**, worse than
  `cohort`. The cause is arithmetic: total change across the clip is 40% of the
  dish spread over 229 frames, and the bursting ring is two cells wide, so
  consecutive frames barely differ.

  1. **Light the front.** The ring of cells currently lysing is the only part of
     the plate doing anything, which is the same thing `hyphae` found about its
     advancing tips. 78.7% to **35.1%**.
  2. **Stagger the landings.** Dropped together, every plaque is the same age:
     they open as one wave, stop as one wave, and the last three seconds have
     nothing in them -- seconds 5, 6 and 7 read 18, 25 and 25 frozen frames out
     of 30. Spread over 560 steps, a plaque is always opening somewhere. 35.1%
     to **32.6%**, and the longest frozen run from 15 to 5.
  3. **Widen the ring by lengthening the latent period** -- and this one made it
     **83.7%**, because a longer latent period slows the whole epidemic and the
     clip then covers less ground. Reverted.
  4. **Plate the lawn thin and land the phage late.** The lawn filling in
     changes the entire dish every frame, which is far more total change than
     the plaques can supply, and by the time the phage arrives the lawn is
     confluent so the plaques still stop. **13.8%**.

  Then one measurement error of my own: pacing the fill on the count of pixels
  over a threshold, which saturates about thirty steps in, so a quarter of the
  clip was handed to thirty states and each was shown twice -- 25 frozen
  transitions in second zero, the worst second to lose. Pacing it on biomass
  instead: **10.5% overall, 6.6% after the hold, longest run 2.**

- Hook *"Nothing here learned to survive."*

### Defect

An active nematic, `growths.Nematic`. Microtubules, the kinesin that walks
along them and the ATP that motor runs on, spread into a film one filament
thick. Nothing in it is alive. Kinesin walks along one filament holding
another, so neighbours slide, and a row of filaments sliding along its own
direction pushes fluid along that direction — **alignment is turned into
flow**. The flow then bends the alignment that made it, an aligned film turns
out to be unstable to its own activity at every activity, and a bend that
keeps growing cannot stay a bend. Where the alignment breaks you get a point
around which the director turns by half a turn: a topological defect, `+1/2`
or `-1/2`. Beris-Edwards for the alignment, one elastic constant, Stokes flow
solved spectrally, active stress `sigma = -zeta Q`.

- **It runs at 0.86 ms a step on the GPU**, 21,000 steps in twenty seconds at
  320 × 320. That is the reason this piece could be measured properly instead
  of guessed at: every question below was answered by running it again.

- **The drop is a drop, not a crop.** The mask multiplies the *activity* and
  the ordering, not the drawing, so outside it the Landau term has no well to
  sit in and the alignment decays to isotropic — there is no film out there to
  photograph. The fluid outside is still solved, because a real drop drags its
  bath around. The mask is smoothed over three cells: a step in it is a step
  in the free energy, and the solver answers that with a ring of spurious
  order at the rim.

- **T1 was measured again in the dish**, because the pitch measured a periodic
  square: **0 / 2 / 158 / 358 / 528** defects across 21,000 steps, first
  quarter 0.4%, last 32.2%. The window matters at both ends. Run to 34,000 the
  count saturates near 700 and the last quarter falls to 3.7% — a fail on *it
  stops*. At 18,000 the last quarter is 45.1%. 21,000 buys a dense finished
  frame and still leaves a third of the change in the last quarter.

- **The charge balances, and the rim lies about it.** Over the whole drop the
  count reads +274 against -254, which looks like the pairing is imperfect.
  Inside 0.90 of the radius it is **232 against 234, net -2 of 466**; inside
  0.75 r, 162 against 164. The +20 excess is the mask's edge, where `|Q|` is
  small and the winding is noisy — not physics. Quote the interior number.

- **The flat-white failure, and it took three goes to fix.** Brightness in
  this house is how much stuff is there, and a nematic film is uniformly
  dense: the order parameter reads **p5 0.671, p95 0.710, a ratio of 1.06**.
  Rendered honestly that is a white disc — 23.8% of frame pixels above 0.85
  luminance — which is `plaque`'s flat-lawn problem with the sign reversed.

  1. **Advect a concentration with the flow.** A guaranteed null, and it
     should have been seen before it was run: Stokes flow is incompressible,
     so `div(phi u) = u . grad(phi) = 0` for a uniform `phi`. It measured
     `cv 0.000` for 12,000 steps.
  2. **The curvature current, `J = kappa phi div(Q)`.** The right mechanism
     and a runaway in practice: `cv` 0.065 → 0.086 → 0.325 → 1.376, `phi`
     spanning 0.001 to 29.5, diverged before step 4,300. Tamed to
     `kappa 0.3` it was still climbing when it was abandoned.
  3. **Take the density from the flow speed** — what the activity actually
     generates, the way `reentry` takes its density from what is firing
     rather than from a count of stuff. **p95/p5 = 6.8** against the order
     parameter's 1.06. That is the whole fix, and it needed no extra field.

- **An aligned film generates no flow at all**, so speed alone drew the first
  state of the clip as an entirely black frame and the clip would have opened
  on nothing and faded the drop in — a dead opening second, which is the worst
  one to lose. The density now has a floor: the film is stuff whether or not it
  is moving, and a microscope would see it. Paid past about 0.06 the floor also
  buys back the contrast the tearing is made of, because the log-density map
  has only so much range. **At 0.03** the still film reads as a flat grey disc
  and the turbulence keeps its dark channels.

- **Nine streamlines abreast draw a fringe of hair round the drop.** Strokes
  seeded inside walk out of it, and the fringe was the one thing in the frame
  that looked like a bug. Samples that leave are dropped; seeding further in
  would have thinned the rim instead.

- **The scheduler failed, and the cause was that the defect count is an
  integer.** Paced on order plus defect count the finished cut measured
  **15.4% frozen after the hold** against a house norm of 4%, with 27 of 228
  transitions landing on a state the previous frame had already shown.
  **54.6% of consecutive banked states hold the same defect count**, and the
  longest identical run is 124 states — 3,720 simulation steps of a progress
  curve that does not move. Two fixes, both applied:

  1. **A third, continuous term**: the cumulative mean flow speed, which is
     how far the film has slid in total. It never has a flat stretch, and it
     is still a measurement of the process rather than of the clock. Repeats
     fell from 27 to 8 of 228.
  2. **Bank one state per frame instead of scheduling.** This is
     `condensate`'s lesson applied properly — a scheduler can only repeat a
     state or skip one, so the pacing belongs in the banking. Pass one
     measures the progress curve; pass two re-runs the same deterministic
     simulation and banks at exactly the step each frame wants; the frames
     play straight through. Two passes cost forty seconds against one run's
     twenty, and they cut the memory as well: 229 states instead of 701.

  Together: **6.6% frozen after the hold, longest run 2, and nothing frozen
  at all in seconds one, two or three.** The same figure `plaque` ships on.

- **Colour is how recently a tear went past** — `reentry`'s phosphor on a
  different medium, at a 400-step half-life so a defect leaves a track rather
  than a fleck. Brightness is how fast that patch is moving, against one fixed
  reference for the whole clip, so *brighter* means the same thing in every
  frame. Two channels, both measured, both intrinsic to the film.

- **`FILAMENT` has no dark stop**, for `AGAR`'s reason: almost all of the drop
  has had no tear through it lately, so the low end carries the whole film, and
  a dark low end would black it out. Steel for the untouched film, ember for a
  fresh tear — the temperature contrast *is* the measurement. The low end is
  desaturated so it reads as grey rather than as a blue piece; `TEAR` swaps it
  for petrol and is kept as the alternative, not as a variant, because it sits
  closer to the green `PHOSPHOR` and the cyan `EPITHELIUM` already on the grid.

- Hook *"Nothing here is alive. It still cannot rest."*

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

`packing` simulates for about eight minutes; bank the run and reuse it while
tuning the look:

```bash
python3 on-growth-and-form/substrate-editions/source/render_substrate.py --edition packing --packing-cache /tmp/packing.pkl
```

`defect` uses the GPU if there is one — 21,000 steps twice in about forty
seconds on CUDA, and several minutes on the CPU. It falls back on its own:

```bash
python3 on-growth-and-form/substrate-editions/source/render_substrate.py --edition defect --defect-palette tear
```

Exports are `9:16`, `1080 × 1920`, `8 s`, `30 FPS`, MP4/H.264, written to
`instagram/phone-9x16/` alongside a `.cover.png`. Requires `numpy`, `scipy`,
`Pillow`, and a system `ffmpeg` with an H.264 encoder. `defect` also wants
`torch` for the GPU path.

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
