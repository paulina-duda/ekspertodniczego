# Wetware Editions

`wetware-editions/` · morphogenesis — how a body builds itself · colour = when
it grew, or which species.

Real developmental biology, filmed as the algorithm it is. Nothing here is
invented: reaction-diffusion laying a pattern down, a slime mould solving a
transport problem, a clock counting out a spine, a load carving a bone.

The renderer is `on-growth-and-form/source/render_biomorphs.py` — one level up,
not in this directory's own `source/`, which is empty. The models live in
`on-growth-and-form/source/morphogens.py`.

The tests a piece has to pass before it is built are in
[`BRIEF.md`](../../BRIEF.md); the queue and the decisions are in
[`PLAN.md`](../../PLAN.md). This file is the long-form record — what each piece
cost to get right, kept so nobody re-learns it.

---

## Folding

Differential growth, four closed curves. **Posted.** `field`, no hook,
DejaVu-era layout.

## Physarum

Slime mould transport network, two species, 600 000 agents. Reworked
2026-08-25 into `slide` + hook + Plex: the band is 330–1400, held by
**reflection** (it has a heading, not a velocity), and the trail sensor is
clamped at the boundary or the two-species braid stitches itself across the
black margin. Hook *"No brain. One cell. Still finds a way."* The old
DejaVu-era cut is kept alongside.

## Turing

Gray-Scott reaction-diffusion, four seeds. Still on the pre-rework layout; its
data block carries Greek, so a re-cut needs the DejaVu `equation_face`
override.

## Somite

**Rejected for the grid (T4).** The beat is real and the model is sound; the
cut still reads as a weak stripe pattern to someone who has not been told what
a segmentation clock is. Judged on the cut, not the science. The one thing
worth carrying forward is the axis — this was the account's first piece with a
**beat**, and that is reusable.

The vertebrate segmentation clock, cell by cell: 16,500 cells in two bands of
presomitic mesoderm, each running the same oscillator, whose period lengthens
with distance from the tail. A determination front sits a fixed distance ahead
of the tail and recedes with it; the moment it passes a cell, that cell stops
oscillating and keeps the phase it was holding. One turn of the clock at the
tail is one segment. Built 2026-08-29, `field` + hook, 8 s. Hook *"Your spine
was counted, not measured."* Not posted.

- **It is the first piece in the account with a beat.** Everything else is
  continuous growth; this one stamps a segment out every 1.1 s, six or seven
  times in the clip, and the rhythm is most of why it holds. Worth remembering
  as an axis the account had not used.

- **Colour is the clock phase, and the palette therefore has to be cyclic** —
  `PULSE` returns to its first stop, or the wrap shows as a seam the process
  never made. Luminance rides round with the hue, which is honest here: a
  clock reporter really is dark for half of every turn, and it is what makes
  the bands read as bands. Each formed segment spans exactly one full turn, so
  every block is a complete sweep of the ramp and the boundary is where the
  ramp wraps.

- **The waves carry nothing.** The band that sweeps forward is a phase lag,
  not a signal — the stadium-wave trick — and that is the piece's paradox
  rather than a simplification. The one real interaction is local coupling
  between neighbours, which is what keeps the bud in step; without it the
  cells added at the tail drift apart and the segments come out ragged, which
  is also what happens to an embryo that loses Delta–Notch.

- **A block has to be contracted as a whole.** Pulling whatever lies outside a
  target circle onto it is what a surface tension does to a block that is
  already the right size, and it empties the middle out into a ring. Scaling
  the whole block towards a target area keeps the arrangement and just makes
  it denser. Two renders were rings.

- **Pressure is the gradient of the excess over the resting density, not of
  the density.** The gradient of density itself puts an outward force on every
  edge in the picture and walks the population into the walls. A packed tissue
  only resists being *over*filled.

- **The scrim can eat the piece.** At the house 0.95 the top 384 px are
  veiled, and this column runs to the top edge, so the oldest and most
  finished segments — the best part of the thumbnail — were being swallowed.
  It ships at 0.55, which it can afford because its text sits on black anyway.
  `build_overlay` now takes a per-edition `scrim` override.

## Trabecula

**Rejected for the grid (T1, T4).** The silhouette is fixed from frame one, so
the clip refines an interior rather than developing a form. Worth stating as a
rule, and it is now in `BRIEF.md`: **a wetware piece has to change shape, not
just contents.** The axis worth keeping is that this was the first
**subtractive** piece in the account.

Bone as a map of its own loads. A coronal section of the proximal femur,
loaded the three ways one leg is loaded, with one rule running everywhere
inside its cortex: measure the strain energy this patch is storing per unit of
its own mass, deposit above a set point and resorb below it. Frost's
mechanostat — Wolff's law written as something an osteocyte could actually
execute. Built 2026-08-29, `field` + hook, 8 s. Hook *"No one drew this. The
load did."* Not posted.

- **It closes the sentence the repo opened with.** `on-growth-and-form`'s
  README gives two of D'Arcy Thompson's examples: a jellyfish is the shape of
  a falling drop, and a bone is the shape of the loads it carries. The
  jellyfish got made as `medusa`. The bone had been sitting there unbuilt
  since the first commit.

- **It is the first subtractive piece in the account.** Everything else
  accumulates into black; this one opens on a filled section and carves itself
  hollow. Worth remembering as an axis the account had not used.

- **One load case gives a truss, not a bone.** The first build minimised
  compliance under midstance alone and returned a minimal three-bar truss with
  a hollow head — correctly, because one load has exactly one cheapest path
  and nothing has to be spent covering the others. The arcades only appear
  under the three-stance history (Carter, Orr & Fyhrie 1989, weighted 6:2:2).
  **The load history is the subject, not a parameter.**

- **An optimiser is the wrong model, and it fails visibly.** Minimising global
  compliance under a fixed volume migrates every spare element onto the inside
  of the cortex — a sandwich panel is stiffer than a network — and the
  interior empties. The mechanostat is local: no budget is held, so how much
  bone ends up in the section is an outcome. That is both the honest biology
  and the thing that produces a network at all. Two renders were lost to this.

- **The cortex has to be held solid or the bone stops looking like one.** The
  rule is quite right that a cortical shell earns nothing under three tidy
  load cases, deletes it, and takes the silhouette with it. Real cortical bone
  turns over on a different clock, so pinning it is honest — and it is the
  only reason the frame reads as a femur rather than a diagram of one. Thick
  down the shaft, thin over the head.

- **E goes as the cube of density, and that is measured** (Carter & Hayes
  1977), not a numerical convenience. It is also what makes the rule unstable
  in the useful direction: a strut that thickens takes a disproportionate
  share of the load, which is how a smooth sheet of tissue breaks into
  separate struts instead of staying a sheet.

- **The set point is read off the section's own first state**, as a quantile
  of the starting stimulus. A body weight and a frame width do not between
  them fix what "worked hard" means, so a hard-coded threshold is a number in
  units nobody has.

- **A high set point hangs the solve.** Push the quantile up and the tissue
  drops to floor density over most of the interior, the stiffness matrix
  degenerates and `splu` stops returning. A parameter sweep died on it. If a
  run stops printing, that is what happened.

- **The black under it is anatomy.** The section is cut flat below the lesser
  trochanter at y 1404, which is where a section of this bone is actually cut,
  and the hook's first ink is at 1473. Same argument as `somite`: clearance
  from the subject's own shape rather than from a band.

- Colour is which of the two trabecular groups an element belongs to — warm
  where it is being pushed, cool where it is being pulled — carried as two
  summed channels on the `physarum` two-species render path, so a crossing
  reads as a crossing instead of one group painting over the other.

- **Still open:** the greater trochanter comes out empty (it is barely loaded
  in all three stances, which is true but reads as a blank balloon), and the
  struts are softer than real trabeculae. Both point at the sensing distance,
  the one length in the rule — a shorter one should give more and finer
  struts. Not yet verified.

- **Set aside for the grid, and the reason is the useful part.** The
  silhouette is fixed from frame one, so the clip *refines an interior* rather
  than developing a form — and next to `folding` and `turing`, which both
  visibly grow, that reads as the wrong kind of motion. Worth stating as a
  rule: **a wetware piece has to change shape, not just contents.**

## Phyllotaxis

A shoot apex placing organs where the ones already there object least. One
rule per plastochrone: look round the rim and start the next primordium at
whatever angle is furthest, in the inhibitory sense, from the primordia
already down; then let the tissue underneath expand, which carries everything
outwards and clears the rim for the next. Douady & Couder 1992. Built
2026-08-29, `field` (a disc that fills the frame width), 8 s. Hook *"The plant
is not counting. You are."* Not posted.

- **It is `folding` and `turing`'s actual sibling.** Same colour rule — when
  it grew — and it grows edge to edge over the clip from a single organ. Runs
  the other way round from those two, though: the youngest organ is in the
  middle, so the bright end of the palette is the core and the rim is the
  oldest thing in the picture.

- **Constant density forces r ∝ √age, and that has a consequence.** Organs are
  added at a steady rate, so area has to be added at a steady rate. The law
  that does it makes the whole head self-similar, which means there is exactly
  *one* divergence angle for every organ ever placed. Any hope of the angle
  drifting during the run is misplaced — it is fixed on the first few organs
  and never moves.

- **The apex radius is the parameter and it is not forgiving.** The rule has
  ordered windows separated by disordered ones, and each ordered window sits
  on a different angle. At one spacing the pattern locks near 5/13 of a turn
  and throws the organs into thirteen separate arms with wide gaps — pretty,
  but not a flower head. At 1.2 it locks onto another fraction; above ~1.4 the
  placement stops settling at all. **0.8 is the golden-angle window.**

- **The angle is measured, never assumed.** Nothing in the rule refers to an
  angle, so the only way to know which window a setting is in is to run it and
  take the median divergence. This one gives 137.37°, which is the golden
  angle to within a seventh of a degree, and the spread over the last 400
  organs is 0.12°.

- **The Fibonacci climb is real and it is in the render.** Parastichy numbers
  measured off the finished head: 8, 13, 21 near the centre and 21, 34, 55
  further out. The divergence angle never changes — what changes is which
  spiral family is the conspicuous one, because the radial spacing shrinks as
  1/√n while the angular spacing does not. Played back, the head grows through
  those counts, which is most of why the clip holds.

- The outermost band measures 76 and 152 rather than 55 and 89. That is the
  boundary: the last ring has no neighbours outside it, so the nearest-
  neighbour test picks up harmonics. Not a defect in the pattern.

- **The candidate ring is rotated by a fraction of its own spacing each
  turn.** Without it the answer can only ever be one of a fixed set of angles
  and the pattern locks to the sampling grid rather than to the rule. Seeded,
  so both passes agree.

- Reuses the `cells` render path wholesale — a floret is a blob like a somite
  cell, just an order of magnitude bigger, so `cell_samples` now takes the
  radius and sample count from the edition.

## Comet

*Listeria* in the cytoplasm nucleates a branched actin network on one face and
is pushed away by the thing it is making. No motor anywhere: the tail is the
ground, built in one direction only, depolymerising from the far end at the
rate the near end is laid down. Every cell divides on its own clock, so ten
bacteria become 160 over the clip. Built 2026-08-30, `field` + hook, 8 s. Hook
*"No motor. It is pushed by what it builds."* Not posted.

- **The first piece chosen by the test rather than by taste**, and the test
  was run before any render code was written. Measured tail length: 128 px at
  frame 1, then 3,885 / 8,966 / 20,634 / 44,781. The change is *biggest in the
  last quarter*, which is the opposite of the three pieces that failed, and
  speed is constant at 19.2 px/frame because the motion is ballistic and has
  nothing to relax to. Ten minutes of measurement would have saved
  `trabecula`, `venation` and `sorting`.

- **The heads are what make it a comet.** Drawn as blobs at 2.6× the weight of
  any tail sample. Without them the frame is a tangle of glowing arcs and
  reads as light-painting; with them every arc has an object at one end and
  the picture is a hundred and sixty things travelling. It cost one render to
  find out.

- **Density is a real trade.** 160 bacteria on a 66-step tail is a scribble;
  dropping the tail to 52 steps and adding heads makes the same count read
  cleanly. Founders matter separately: starting at five leaves the middle of
  the clip nearly empty (20 comets at frame 120), which is the failure the
  piece was built to avoid, so it ships from ten.

- **Weight tapers with the age of the actin as well as hue** (`taper 2.0`), so
  a tail thins towards its far end instead of stopping on a flat stub. That is
  also what depolymerisation looks like.

- **Wrap segments have to be dropped.** A comet leaving the right edge and
  arriving at the left is one bacterium, but the line between those two
  positions is a stripe across the frame that nothing travelled. Segments
  longer than 3× the step are discarded, as are the ones older than the cell
  that owns them — a daughter has no tail because it has built no ground.

- Colour is the age of the actin: white at the bacterium, magenta a moment
  later, gone at the far end. Same quantity as `folding` and `turing`, on the
  shortest timescale in the account — a tail is a third of a second old.

- Reuses the `vein` draw path; `tree_samples` and the segment splat were
  already there from `venation`, which is most of what that piece was worth.

## Venation

**Rejected (T1), re-measured 2026-08-30 and confirmed, render deleted.** The
re-render in `sharp` gives **44.4% still frames, longest run 74** — 29 of the
first 30 frames and the whole last three seconds — against a house norm of 4%.
The profile stops dead at three quarters: 508 at ¾, 509 at the end. Watched
again on 2026-08-30 and the verdict stands: it is an ordinary tree being
uncovered.

**rejected for the grid.** It is a reveal: over eight seconds branches uncover
and nothing moves. See the change-profile test in [`BRIEF.md`](../../BRIEF.md) — it is the same failure
as `trabecula`, one class of process further on. The model and the render path
are kept because the space-colonisation code and `tree_samples` are reusable,
and because the growing-lamina finding below is worth not re-learning.

A vein network growing towards whatever is not yet drained. Auxin is made all
over a young leaf and has to leave it, and every route that carries some
becomes better at carrying it. Sachs called it canalisation; the discrete form
is Runions & Prusinkiewicz's space colonisation. One step: every source still
waiting pulls on the nearest tip within reach, each tip advances along the sum
of its pulls, and any source a vein has arrived at stops existing. Built
2026-08-29, `field`, 8 s. Hook *"The vein is not a route. It is a leftover."*
Not posted.

- **Shipped at low bloom** — `--bloom-threshold 0.55 --bloom-strength 0.25`,
  with `exposure 1.10` and `boost 1.20` in the edition. The piece is tens of
  thousands of thin lines and the house halo turns them into a haze. **The
  filename does not record this**, so re-render it with those flags or the cut
  changes under you. Second piece in the account on the sharp look after
  `affinity`; it is now worth deciding whether that is a house option.

- **A still lamina gives a brush, not a leaf.** Scatter the sources over a
  fixed frame and every tip races the same direction at the same speed: what
  comes out is a fan of near-parallel filaments, no midrib, no secondaries,
  nothing to branch around, and the colour degenerates into a vertical
  gradient because age and height become the same variable. The fix is that
  the blade *grows*: sources only become live once the expanding outline has
  reached them, so the veins keep having to reach sideways into tissue that
  was not there a moment ago. That is what puts the order in.

- **The blade's growth is front-loaded** (`eagerness 0.55`) and starts at a
  third of full size. Linear from near-zero spends the first quarter of the
  clip on an almost empty frame, which is the part anyone watches.

- **Pacing is the parameter that matters**, and it is stride and blade
  schedule together: at `stride 2.9` the veins only reach the top of the frame
  at frame 215 and the piece is two-thirds black for most of its length. At
  `stride 4.0, span 500` they arrive around frame 155 and the last third fills
  in reticulation everywhere at once, which is the better picture.

- **Measure the text bands over the whole clip, not on the cover.** On the
  cover the hook sits on a background of 60; at frame 80 the bright growing
  margin sweeps straight through that row and takes it to 151 — brighter than
  anything else in the account. Neither pulling the palette short of white nor
  dropping the bloom moved it (151 → 145 → 142): the front is genuinely dense
  there, and no render setting fixes a geometry problem. It ships because the
  band is mostly black with thin bright lines through it and the stroked hook
  reads, but it is the piece's weak second.

- **~810 sources are never reached.** They sit in the frame corners, outside
  the blade outline, which is honest — a leaf margin is where venation stops.
  The data block said "every one reached" until that was checked.

- Colour is when it grew, ranked: magenta at the base, gold at the tips.
  Ranked rather than scaled because the tip count grows with the front's
  length, so raw age piles most of the network into the top of the ramp.

## Stripe

Zebrafish pigment pattern on skin that keeps growing. Built 2026-09-04.
`dish` + hook, `bloom`, 8 s. Model `morphogens.Stripe`, render kind `skin`.
Hook *"Turing predicted chemicals. These are cells."*

The subject is the correction to `turing` next door. Gray-Scott is two
substances diffusing at different rates; the zebrafish was the textbook case
for that story and turned out not to run on it. The interaction has the shape
Turing needed — support your own kind close in, suppress it further out — but
the morphogens are whole cells, black melanophores and yellow xanthophores,
measured by Nakamasu and colleagues in 2009 by killing cells with a laser and
watching what grew back.

### The pitch was accepted with two known defects, and both were real

`stripe` went through the gate against `spindle` and `aggregation` and was the
only one of the three whose T1 was both passing and not blocked on a broken
model. It was accepted with two objections recorded against it, and building it
meant answering both rather than discovering them late.

**The stripes were stretching, not splitting.** The first passing profile —
boundary length 22.0% first quarter, 28.0% last — was mostly measuring *the
disc getting bigger*. The diagnostic that separates the two is boundary length
over radius: flat means the pattern is being scaled up, rising means it is
being recomputed. It read 12.8 → 14.6 across the clip, a rise of 1.20× where
stripes perfectly holding their width would give 2.16×. **A scalar that passes
T1 is not the same as a scalar that measures the process**, and the ratio
against a geometric baseline is what tells them apart. Two changes fixed it:

* **Growth linear in radius, not exponential.** The number of stripes the disc
  can hold goes as the radius, so only a linear radius spreads the splitting
  evenly. Exponential growth puts two thirds of the splits in the last quarter.
* **Long-range inhibition at 1.70.** Below about 1.45 the pattern is stable to
  stretching and the stripes simply fatten. 1.25 → 1.38×, 1.45 → 1.62×,
  1.70 → 1.80×.

Anisotropy is the third number and it is a taste one: at 7.0 the bands are
straight, parallel and read as a barcode — which is `cooperation`'s "frame one
reads as a QR code" arriving from a different direction. 3.5 keeps them
horizontal and lets them wander, which is what an animal looks like.

**The `somite` objection.** `somite` was rejected for reading as a weak stripe
pattern, and this piece is literally a stripe pattern. `dish` is the answer:
the disc is centred with radius 0.44 × 1080 = 475, so every line of text sits
on black rather than competing with the subject. Measured on the finished
frame, background luminance under the title, hook and data block is 0.57, 2.16
and 0.42 against glyphs at 243–251.

### Two-valued cells give the density pipeline nothing

`cooperation` was rejected mid-build for exactly this: a two-valued lattice at
one areal density hands the log-density map a flat block. The skin has the same
problem — the disc is uniformly full of cells, so density carries no
information at all.

The answer is **recency**. Age since a cell last switched type is the one thing
about a cell that is neither its type nor its position, it is intrinsic, and it
is concentrated exactly where the pattern is being decided. It drives both
channels: per-cell weight (a cell that has just changed its mind is worth 3.4×
one that has settled) and shade. That is what makes the stripe borders glow,
and the borders are the event.

A consequence worth knowing before touching the palettes: **shade is recency,
so a settled cell sits at the very bottom of its ramp — the first stop is the
colour of a stripe's interior**, which is most of the frame, and the upper
stops only appear along a border currently being argued over. At `(28, 8, 0)`
the xanthophore interiors came out a desaturated brown, blue/red 0.42 against
0.35 once the stop was opened to `(92, 38, 0)`.

The two ramps are deliberately **not** matched in luminance — violet measures
60 against the gold's 109. A melanophore is a black cell and a xanthophore a
yellow one, so the dark band belongs darker. Balancing them would have meant
pushing the melanophore toward magenta to buy luminance that blue cannot carry,
which is fighting the animal to satisfy a number.

### Two things that cost a re-render each

* **The settle steps grow the disc too.** Solving the growth increment over
  `steps_per_frame × (frames − 1)` and forgetting the 260 settle steps
  overshoots: the skin hits the dish radius at frame 207 of 240 and the last
  second is a disc that has stopped growing.
* **A two-line hook does not fit a dish.** The first draft hook was two lines,
  which starts at row 1420 against a disc bottom of 1435 — a 15 px overlap
  before bloom, and bloom bleeds ~24 px past the model's own extent. Every
  shipped dish hook in the account is one line and this is why. The fix was the
  hook, not the geometry: `centre = (width/2, height/2)` with radius
  `0.44 × min(w, h)` is what every other dish uses and is not worth breaking
  for one piece.

### Measured on the shipped cut

Boundary is stripe border in pixels, sampled after the settle:

| | frame 1 | 60 | 120 | 180 | 239 |
| --- | --- | --- | --- | --- | --- |
| cells | 32,862 | 49,309 | 69,082 | 92,180 | 118,136 |
| radius px | 250.5 | 306.9 | 363.2 | 419.6 | 475.0 |
| border px | 3,324 | 4,485 | 5,916 | 7,497 | 9,450 |
| bands | 9 | 9 | 9 | 11 | 11 |

**T1: 18.9% first quarter, 31.9% last** — alongside `comet` (12/48) and
`phyllotaxis` (29/23). Border/radius rises 13.3 → 19.9, a factor of 1.50
against the 1.90 that perfect splitting would give at this growth: **most of
the change is genuine insertion, and some of it is still stretch.** That is the
honest number and the place to start if the piece is ever reworked.

`check`: 0.0% frozen frames against a house norm of 4%, longest run 0, minimum
inter-frame delta 0.832. Loop seam 9.38 against an adjacent-pair 9.25, so it
closes exactly. 5m31s for the render on the 4070 laptop.

### What is reusable

The `skin` render kind is the account's first **two palettes chosen per
subject rather than per channel** — one additive splat with the ramp picked per
cell, instead of `physarum`'s two summed density fields. Right whenever the two
populations are exclusive rather than overlapping, and it keeps a border a
border instead of a seam where one layer paints over the other.

Filenames now record the look when an edition names one (`"look": "bloom"`),
which is the standing `venation` problem — it shipped on `sharp` and its
filename does not say so, so re-rendering it without the flags silently changes
the cut.
