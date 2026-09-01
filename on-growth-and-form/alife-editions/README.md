# Artificial Life Editions

Rules that were found, not written.

Every other set in this project films something biology already knows about —
a mycelium, an embryo, a sheet of heart muscle. This one goes the other way.
The rules here were invented inside a computer, and the claim being made about
them is the one artificial life has been making since Langton: that what is
alive about a living thing might be the *organisation* rather than the
chemistry, in which case it can be built out of anything, including numbers.

That claim is arguable. Everything else in the account is a fact about the
world with a picture attached; this is a picture with an argument attached, and
it is the only place the account has an opinion.

| Edition | Rule | What it is |
| --- | --- | --- |
| `affinity_particle-life_alife` | particle life | four species, sixteen numbers, and nothing else |
| `soliton_lenia_alife` | Lenia | twelve copies of one creature, and what one collision does |
| `highway_langtons-ant_alife` | Langton's ant | nine words of rule, twenty-four ants, and the road none of them was told to build |
| `protocell_particle-motion_alife` | primordial particle system | one turning rule, and bodies with skins condensing out of a soup |
| `descent_genetic-algorithm_alife` | genetic algorithm | the pedigree of a real run: 64 founders, 40 generations, one ancestor |
| `cohort_genetic-algorithm_alife` | genetic algorithm | the same run, seen as the animals it made rather than as a tree |
| `shoal_genetic-algorithm_alife` | genetic algorithm | the same run as a race: four generations, four lanes, one winner |

## Affinity

Give every particle a species. Give every *ordered* pair of species one number,
saying whether the first is drawn to the second or pushed away. Add one rule
that ignores species entirely — close in, everything repels everything, because
two things cannot be in the same place. That is the whole model. There is no
cell in it, no membrane, no organism, no metabolism, no goal, and no notion
anywhere of a thing being alive.

What comes out are bodies: cores wrapped in a skin of another species, swimmers
that hold a shape while they travel, pairs that chase each other across the
frame and knots that throw particles out and pull them back in.

The reason is the one asymmetry. **The table does not have to agree with
itself.** If magenta chases mint while mint flees magenta, neither can settle,
and the pair keeps going — a predator and its prey written as two numbers that
disagree. Symmetric tables make crystals. The tables worth filming are the ones
that cannot make up their mind, and the piece has one of those: the whole
population is bound into bodies, and those bodies are moving at two and a half
pixels a step.

### The table was found by search

It is not designed and it is not hand-tuned. Twenty tables are drawn at random,
each is run for a couple of hundred steps at the density the finished piece
uses, and each is scored on three things at once:

| Term | Measured as | Why |
| --- | --- | --- |
| assembly | fraction of particles inside a packed neighbourhood | a gas scores zero |
| motility | mean speed **of the particles that are assembled** | a crystal scores zero |
| coverage | fraction of a 32 × 32 grid with anything in it | one big lump scores badly |

Speed measured over everything cannot tell a swimmer from a gas: loose
particles rattle around faster than anything organised ever moves. Speed
measured only over particles that are *part of something* can, and that
distinction — between a pattern and an animal — is the only judgement in the
search. The winner is kept in `render_alife.py` as `FOUND_MATRIX` so the piece
renders the same thing twice; `--search` looks for another one and saves the
whole ranking, and `--matrix-rank 1` renders the runner-up.

### A band, not a torus

The frame wraps left to right; top to bottom the population is held by a soft
spring that only pulls once a particle is outside the band. The reason is
typography: a swarm spread corner to corner leaves the title and the hook
nothing to sit on. A spring rather than a wall, so the population *thins* into
the margin instead of stacking against a line — a hard edge would draw a bright
rim across the frame, and a rim is a structure the rule did not make.

Two things had to follow from that change, and neither is optional:

- **The count is scaled to the band, not to the frame.** These rules do not
  care about area, they care about how many neighbours a particle has. Keeping
  20 000 particles while cutting the area by two fifths would have handed the
  piece a denser world and a different answer; 11 667 keeps the density the
  table was chosen under.
- **The table was ranked again in the new geometry.** A matrix is only best in
  the world it was scored in — the coverage term alone means something
  different in a band. The same twenty candidates were re-run against the band
  at the same density, and the incumbent won there too (1.016, ahead of 0.903;
  it scored 1.459 on the torus). It stays because it was re-tested, not because
  it was already there.

The band is set well inside the clearance it needs, because a cluster
straddling the edge drags its own members out however stiff the spring is.
Measured over a whole clip the furthest excursion is about 90 px: with the
shipped numbers the highest any particle ever gets is row 293 and the lowest is
1424, against a title whose ink ends at 270 and a hook whose first line starts
near 1460.

## Soliton

Conway's Life counts eight neighbours, compares the count to two integers, and
switches a cell on or off. Lenia (Bert Wang-Chak Chan, 2019) keeps the shape of
that idea and makes every part of it continuous: a cell holds a real number
instead of a bit, the neighbourhood becomes a smooth ring instead of a square of
eight, the birth and survival intervals become one smooth growth curve, and time
is divided so a step moves the field by a tenth of the growth instead of all of
it. Four changes, none of them clever.

What comes out are not blinkers and gliders but **solitons**: lumps of
continuous field, smooth-edged and internally structured, that hold themselves
together while they travel. The one in this piece is a ring with a core, about
sixty cells across, and it swims at a third of a cell per step.

### Found by search, and then found again

Nothing here is designed. A creature in Lenia is a point in a space of
parameters and initial conditions, and almost all of that space is lethal in one
of two ways: the field collapses to nothing, or it grows without limit until it
fills the world. Everything interesting is in the narrow band between.

The search draws a growth curve, a kernel of one to three rings and an arc to
start from, runs it alone in a small world, and asks whether it is still alive,
still an individual, and whether it went anywhere. **The audition has to be
long.** A three-hundred-step window passes slowly-expanding colonies as if they
were creatures; only the second window, three hundred steps later, shows that
their mass never stopped rising.

Then every survivor is **re-run at the size it will be filmed at**, because
Lenia is only approximately scale-invariant: the same equations discretised
twice as finely are not quite the same equations. Of 105 survivors found at
radius 18, 98 were still self-limiting at radius 30 and seven were not. The one
in the piece is the furthest traveller of those.

Because the arc is six numbers rather than a bitmap, the whole creature — kernel
rings, growth curve, seed — is seven parameters in `render_alife.py`, and can be
read, changed and rebuilt exactly.

### The collision is the piece

Twelve copies of that one animal, each turned a different way, dealt out with a
minimum separation so they are seen swimming before anything happens.

Then two of them touch. Neither survives as an individual, and what replaces
them is not a bigger creature but a **colony**: a spreading disc of the same
lattice texture, with a bright growing rim, that does not stop. Every creature
in the frame was stable on its own for as long as anyone cared to run it. The
rule that keeps one of them self-limiting has nothing to say about two.

Colour is the growth term — near-black through the wake a creature is leaving,
deep magenta through the body that is holding steady, amber to white along the
edge it is advancing into. It is the one field in the model that says which way
the thing is going, and without it a still frame of a soliton is a doughnut.

## Highway

The whole rule is: **right on white, left on black, flip, step forward.** Nine
words. An ant on a grid of two-coloured cells reads the cell underneath it,
turns one way or the other, flips that cell and moves on. No memory beyond its
heading, no randomness anywhere, nothing to tune. Chris Langton wrote it down
in 1986 and it is the smallest thing in this account by a wide margin — Lenia
has seven parameters, particle life has sixteen numbers, this has none.

For about ten thousand steps the ant makes a small symmetric mess. Then it
starts building a **highway**: a 104-step cycle that translates the pattern two
cells diagonally and repeats without end. Nothing about the rule changes at
that moment and nothing is added to the grid. That the trail can never stay
bounded is a theorem; that the highway always appears is not — it has only ever
been observed, in every starting configuration anyone has tried, and that gap
between what is proved and what is seen is the reason the piece exists.

### What the gate measured

The scalar is cells ever stepped on, over the 229 growing frames at 260 steps
each:

```
0 / 52,208 / 94,116 / 117,740 / 144,574     first quarter 36%, last 19%
```

Comparable to `phyllotaxis` (29% / 23%) and nothing like a relaxation. Two
other candidates went through the same gate on the same day and neither
survived: the primordial particle system passes T1 and T4 at scales that
exclude each other, and Nowak and May's spatial prisoner's dilemma has the best
profile of the three (5% / 45%) and is still television static in a box. That
one is in `REJECTED.md`; it is Conway's row restated.

**Conway's row is the objection this piece had to answer too**, since this is
also a two-state automaton. It answers it with the field it renders. The state
of a cell is a bit, but *how many times it has been stepped on* is not: median
8, ninety-second percentile 23, maximum 87 in the shipped cut. That is a range
the log-density map was built for, and it is why a highway — one visit per cell
— reads as a thin dim line against cores that have been trampled eighty times.

### Colour is recency, and it is what rescued the cut

Rendered as pure accumulation — every cell that has ever been touched, lit
forever — the clip measures **43.9% frozen frames**. `venation` was rejected at
44.4%. It is the same failure exactly: a structure uncovering while nothing
moves, because a cumulative field can only ever add a rim.

So the model also carries `last_seen`, the step at which each cell was last
stepped on, and the palette runs on the age of that: violet for everything
already built, white for where an ant is standing now, fading over about eight
thousand steps. This is not a second decoration on top of the first. It is the
only quantity in the model that separates a road being laid right now from one
abandoned four seconds ago, which on the cumulative field are the same picture.
With it, the same clip measures **0.0% frozen after the opening hold**, with
per-frame change between 0.38 and 0.92 against a threshold of 0.15.

### Twenty-four, on one grid

One ant is a demonstration. A population is the piece, and the number was
measured rather than picked: at 60 ants the chaotic cores merge into a single
grey mass well before the clip ends and the roads have nothing to be seen
against; at 24 they stay separable for all eight seconds, and 7 of them are
already travelling in the first second against 18.5 in the last.

**The ants never touch each other.** The only thing an ant can read is the cell
under it and the only thing it can change is that same cell, so everything they
do to each other goes through the floor — a road driven into another ant's
rubbish reads the wrong colours and collapses back into chaos, and a patch
another ant has tidied can launch a road early. That is the whole interaction
and there is no term for it anywhere in the rule.

### Three decisions, and why

**field, not slide.** A highway is a straight line that never stops, so on a
finite grid it either wraps or it hits a wall the rule knows nothing about.
Confining the ants would mean bouncing roads off a boundary that is not part of
the model. The cost is the text sitting on texture: measured over the whole
clip, the worst coverage under the title is 23.2% of cells touched and under
the hook 15.4%, against 27.9% for the grid as a whole. The scrim and the
stroked type carry it, and the top-left corner where the title sits stays black
because the ants start in a central band.

**`sharp`, not `bloom`, and it is in the filename.** A highway is one cell
wide. Under the default bloom every road becomes a glowing tube and the frame
turns into haze; at `--bloom-threshold 0.55 --bloom-strength 0.25` the roads
stay lines and the black stays black.

**Paced by the clock**, like `soliton` and for a plainer reason: an ant takes
one step per step. There is no scalar that accelerates or stalls, so equal
counts of steps already are equal amounts of process. The states are banked one
per played frame and played straight through — no scheduler, and none of the
stutter a scheduler is there to cause.

## Protocell

Schmickl, Stefanec and Crailsheim, 2016: *How a life-like system emerges from a
simple particle motion law*. A particle counts the neighbours inside its radius,
splits them left and right of where it is pointed, turns by 180° plus 17° for
every neighbour it can see — towards the emptier side — and steps forward. No
force, no attraction, no species, no chemistry, and nothing that says the word
cell. What comes out are cells: bounded bodies with a dense core, a ring holding
them closed, and free particles drifting between them.

### It was rejected at the gate first, and why

The pitch verdict was **REWORK**, and the finding is worth keeping because it is
about scale rather than about the model. A cell is about four interaction radii
across, so the radius alone decides how large it is on screen — and the two
tests pull that number in opposite directions:

```
world 360x640, 8,324 particles     cells 1 / 20 / 37 / 53 / 60     T1 passes
                                   a cell is a 12 px speck         T4 fails
world 90x160, 704 particles        a cell is 240 px, legible       T4 passes
                                   cells 3 / 2 / 3 / 1             T1 fails
```

The second line is `shoal`: things moving and nothing accumulating. There is no
radius that satisfies both, because the quantity T1 measures — how many cells
there are — is the quantity T4 wants fewer of.

**The drive is what breaks the tie**, and `BRIEF.md` allows exactly this against
a T1 failure: something that keeps injecting material. Three new particles every
ten steps, dropped in at random, at a radius of 30 px where a cell is about
120 px:

```
cells 3 / 8 / 13 / 15 / 22          first quarter 26%, last 37%
```

Which is `comet`'s shape. Without the drive at that same scale the count stalls
— 13 at the halfway point and 13 at the end. At three times the drive the world
floods and the cells merge back into mush: 3 / 17 / 11 / 5. The rate is not a
taste decision; it is the only one of the three that keeps cells condensing for
the whole clip.

### They do not divide

The pitch line for T2 said "the cells split", and that claim did not survive
being measured. Every new cell was matched against the cells that existed a
hundred steps earlier:

```
median distance from a new cell to the nearest existing one   42.6 units
cell diameter                                                 ~20 units
new cells appearing within one diameter of an existing cell   3%
the same measurement at the paper's own density (0.08)        0%
```

New cells condense out of the soup on their own account. They are not children
of the ones beside them, and neither the caption nor the hook says they are.
This matters more than it looks: the whole literature around this system invites
the reader to see reproduction in it, so a piece that stays quiet on the point
would be letting the viewer assume something the measurement refuses.

What is left for T2 is a transition rather than a beat — loose dust curling up
into a body, one after another, all the way through the clip. That is weaker
than `soliton`'s collision and it is honest about what is on screen.

### Colour is the only thing the rule reads

A particle senses one number: how many others are inside its radius. That number
is also the entire anatomy of a cell — free in the soup, in the wall, in the
core — so the palette runs on it and on nothing else. Ranked rather than scaled:
the count runs 0 to 75 with a median of 12, and scaled, everything but a few
cores would be one flat violet. The rank is built once from the final frame and
applied to every frame, so a particle's colour changes when its own
neighbourhood does and not because the rest of the world moved.

### The numbers the cut shipped with

3,515 particles by the end, 3,000 steps at 13.1 a frame, 22 cells, neighbour
count median 12 and maximum 75. Loop seam 1.13. Frozen frames 4.2% — ten of
them, all inside the opening hold, which is the house norm exactly. Per-frame
change after the hold runs 1.87 to 7.75 with a median of 5.60: this is a busy
picture, in the same range `quorum` measured at 6.24, and nothing like a still.
Text sits on cleaner black than `highway` does — worst mean 22.5/255 under the
title and 20.8/255 under the hook.

## Descent

`soliton` found its animal the way the field usually does: nine thousand
independent draws, keep whatever is still alive. That is **search**. This piece
is **selection**, and the difference is the whole of it — nothing here is
cleverer than random sampling at any single step. The only change is that the
draws stop being independent. Whatever survived one round is what the next round
is drawn from, with mistakes.

The genome is the same seven numbers `soliton` ships as a creature: the growth
curve, the kernel's rings, and the arc it starts from. The fitness is the same
question the audition asked — still alive, still an individual, went somewhere.
Same space, same target, different method.

### What the run actually did

| Generation | What happened |
| --- | --- |
| 0 | **none of the 64 random genomes scored at all** |
| 1 | one lucky mutation lands; 2 alive |
| 5 | 23 alive, best fitness 2.3 |
| 9 | **one founder line left**; every individual alive descends from founder 19 |
| 39 | 21 alive, best fitness 5.4 |

The first generation is worth sitting with. Sixty-four independent draws and not
one of them was viable, which means selection had nothing whatsoever to work
with on the first round: the parents of generation 1 were chosen between equals,
at random, and the first living thing in the piece is a mutation of something
dead. After that the algorithm is only ever improving on a lucky accident.

### The picture is the pedigree, not the creature

Every individual of every generation, joined to its parent, growing upward.

Laying that out is most of the work. Plotting a gene on the horizontal draws the
population converging into a thread up the middle of the frame — true, and an
empty picture. Spreading each generation evenly across the width fills the frame
but hides the only thing worth seeing, because a line that has just ended looks
exactly like one that is about to go somewhere.

So the last generation is dealt across the width in order of ancestry, every
earlier individual that still has descendants sits at the mean of its own, and
everything else — which is the overwhelming majority — hangs off its parent and
stops. What that draws is a canopy over a trunk, standing in a scrub of dead
lines. Colour is which of the 64 founders an individual came from, brightness is
its fitness, so the coloured undergrowth at the bottom of the frame is the
sixty-three founder lines that left nothing behind.

Two small things that decide whether it reads at all: lines are sampled by
**length** rather than by a fixed count, or the long ones come out as dotted
rules across the frame; and each is drawn as three offset copies, because a line
one pixel wide has no mass and this house gets its brightness from how much of
something is there.

## Cohort

The same run as `descent`, and the same seed. That piece draws the pedigree —
who came from whom — and in doing so never shows a single creature. This one
shows the creatures and never draws a line: twenty panels, each an individual
of the run, alone in its own small world, seeded from its own arc and stepped
alongside the other nineteen.

A row is a generation. Reading down the frame: generation 0, 1, 4, 12, 39, and
in each row the four that scored highest.

### The top row is the argument

Generation 0 is sixty-four independent random draws and **not one of them
scored at all**, so the four best of it are a tie between four zeros. What that
row shows instead is the two ways a Lenia genome fails, which are the only two
ways there are: a field that collapses to nothing, and a field that never stops
growing. One of each is on screen, and the runaway is still there in the second
row because elitism copied it forward — with everything scoring zero, the
algorithm had nothing better to carry.

So the first parents were chosen between equals at random, and the first living
thing in the run is a mutation of something dead. Everything in the four rows
below descends from one of those sixty-four.

### The camera cannot follow the creature

A soliton is a steady travelling wave. Filmed in its own moving frame it is a
photograph — the first cut pinned each panel to its creature's centre of mass,
which gave a beautifully sharp grid in which 195 frames out of 239 changed by
less than a sixth of a percent, and two panels froze into a static crystal
lattice. Anything that keeps a constant-velocity creature inside a fixed panel
eventually stops it dead; a lagging tracker only moves the freeze a second
later. **It has to swim across something.**

Letting it swim in a small torus instead puts creatures across their own seam
for about a third of the clip, which does not read as a wrapped world, it reads
as a broken render.

The way out is to measure first. A survey run puts every genome in a world far
too big to wrap, keeps the highest value each cell ever held, and reads off the
box the creature actually used over the length of the clip. That box answers
everything at once:

- **The world is made just big enough for the largest of them** — 59 cells here,
  so 68 — which is the most magnification available without anything touching
  an edge.
- **Every seed is placed so its own box is centred**, which is not a physical
  choice: the rule is a convolution on a torus, so a run started elsewhere is
  the same run carried along, and the offset only decides which cut of the
  world the panel shows.
- **The fitness becomes visible.** The box *is* the travel that was being
  selected for, so a poor genome jiggles in the corner of its world and a good
  one crosses it.

### Two things that had to be checked rather than assumed

**The world is half the size the fitness used, and that is safe.** Genomes were
scored at radius 13 in a 128-cell world; the piece films them at 68. The domain
is not the discretisation — the radius is — so this is not the change Lenia is
fragile about, and at 68 a creature is still 50 cells clear of its own image.
Run at 128, 96 and 64 the twelve genomes come out with the same fates and the
same masses; at 48 the seed starts to see itself.

**A finer timestep is not safe, and would have been the obvious fix.** Dividing
time more finely would stretch the transient over more frames at no cost to the
geometry. It changes the answer: at `steps_per_time` 30 instead of 10, run to
the same simulated time, a genome that had died is still dying. Deaths are the
fastest thing in the model and the coarse step is part of what was selected on.
So the clip runs at exactly one step per frame, and the run is 240 steps because
that is how many frames there are.

### What a grid of separate worlds costs

It is the stillest cut in the account, and that is a property of the format
rather than a setting that was got wrong. Measured the way `check` measures —
mean frame-to-frame change at 135 × 240 — this cut has **78% of its frames
under the 0.15 threshold, with a longest run of 45**, against 4% for `hyphae`,
`reentry` and `affinity_neon`, 3% for `soliton`, and 65% for `descent`.

The arithmetic behind that is worth keeping, because it says the knobs are not
the answer. The moving pixels in a clip are

    creatures × body area × body-lengths travelled

and in a grid of isolated panels none of the three can be raised without
lowering another. More steps per frame means more travel, which means a bigger
world to hold the track, which means a smaller creature: at one step per frame
the product is 27.8, at two it is 20.6, at a third of a step it is 28. More
panels means smaller panels, and the product is exactly flat. Filming at a
larger radius scales the creature and its track together and changes nothing.

The one arrangement that escapes it is many creatures sharing one large world,
where travel is not capped by a panel — which is `soliton`, and is why that cut
measures 3%. **A grid of separate worlds buys the comparison and pays for it in
motion.** What moves here is the first two seconds: twenty arcs collapsing,
four of them going out, two running away. After that the survivors drift about
two thirds of a panel over the remaining six.

### Colour is fitness, ranked

Not the growth term the other Lenia piece uses: at this size a creature is
sixteen cells across and its growth is ±1 in a one-cell rim and near zero
everywhere else, so the whole grid came out one flat magenta. Fitness is
ranked rather than scaled because the scores in a converged run are hopelessly
bunched — four zeros at one end, 5.39, 5.39, 5.38, 5.38 at the other — and
dividing by the best would spend a fifth of the ramp on four of the five rows
and say the run stopped improving at generation four. A tournament compares and
never asks by how much, so the order is the honest thing to colour by.

The ramp never reaches black, unlike `PLASMA`. A genome that scored nothing is
not a wake to be swallowed by the background; it is one of the two ways of
failing, and it has to be visible.

### The copy that goes with it

> Twenty small worlds, one genome each, all running at once. A row is a
> generation of a genetic algorithm; a panel is one individual of it, alone in
> its own world, exactly as it was when it was scored.
>
> The top row is generation zero — sixty-four random draws, and not one of them
> was alive. Both ways of failing are up there: a genome that collapses to
> nothing, and a genome that never stops growing. Which means selection began
> with nothing to select. The first parents were drawn between equals at random,
> and the first living thing in the run is a mutation of something dead.
>
> After that the whole mechanism is: copy with mistakes, compare three at
> random, keep the winner. The genome is seven numbers — a growth curve, the
> rings of a kernel, and the arc it starts from — and the fitness only asks
> whether the thing is still alive, still one thing, and whether it went
> anywhere. That last one is on screen: the weak ones jiggle in a corner of
> their world, the ones at the bottom cross theirs.
>
> Forty generations later the bottom row is four animals, and nobody wrote them.

> Dwadzieścia małych światów, w każdym jeden genom, wszystkie liczone naraz.
> Wiersz to jedno pokolenie algorytmu genetycznego, kafelek to jeden osobnik z
> tego pokolenia — sam w swoim świecie, dokładnie tak, jak wtedy, gdy dostawał
> ocenę.
>
> Górny wiersz to pokolenie zerowe: sześćdziesiąt cztery losowania i ani jedno
> żywe. Są tam obie drogi porażki — genom, który zapada się do zera, i genom,
> który nigdy nie przestaje rosnąć. Czyli selekcja zaczynała od materiału, w
> którym nie było czego selekcjonować. Pierwszych rodziców wylosowano spośród
> równych sobie, a pierwsze żywe stworzenie w całym przebiegu jest mutacją
> czegoś martwego.
>
> Dalej cały mechanizm to: kopiuj z błędami, porównaj trzy losowe, zostaw
> zwycięzcę. Genom to siedem liczb — krzywa wzrostu, pierścienie jądra splotu i
> łuk, od którego się zaczyna — a funkcja dopasowania pyta tylko, czy to wciąż
> żyje, czy wciąż jest jednym obiektem i czy gdziekolwiek dotarło. To ostatnie
> widać na ekranie: słabe drgają w rogu swojego świata, te z dołu przemierzają
> swój w całości.
>
> Czterdzieści pokoleń później dolny wiersz to cztery zwierzęta, których nikt
> nie napisał.

## Shoal

**Rejected (T1, T2), 2026-08-30.** Measured on the finished cut: total ink
683 / 683 / 678 / 682 / 683 across the quarters — completely flat. The
creatures swim, so the motion count is a comfortable 4.2%, and the piece still
has no arc over eight seconds. It was queued on that 4.2% for weeks, which is
why T1 now tests the profile as well as the front-loading.

The **lane** shape and the sliding-window camera stay documented in the `reel`
skill — the mechanism is sound and may carry a different subject. The record
below is what it cost to get right.

`cohort` again, rebuilt around the one thing it could not do. Four lanes, one
generation each — 0, 5, 8 and 39 — and in every lane five copies of that
generation's best genome, swimming together.

Copies of one genome may share a field. They are the same rule, so there is no
question about what an overlap obeys, which is exactly the question that keeps
two *different* genomes in two different worlds. Seeded abreast and identical,
they hold formation, so nothing collides and the lane reads as a shoal.

What the lanes show is the thing the fitness actually paid for. Travel is two
thirds of the score, and it separates cleanly:

| Lane | Generation | Fitness | Speed |
| --- | --- | --- | --- |
| 1 | 0 | 0.00 | runaway — fills its world and stops |
| 2 | 5 | 2.32 | 0.073 cells/step |
| 3 | 8 | 4.61 | 0.170 |
| 4 | 39 | 5.39 | 0.203 |

### The lane follows them across, and never along

A panel caps how far anything can travel, which is why `cohort` is still: these
creatures move a fifth of a cell per step, and a panel is forty cells wide. A
lane lifts the cap in one direction — it runs the full width of the frame and
wraps there, the way `soliton` wraps.

That is not enough on its own, because **nothing here swims along an axis**.
Every fast champion goes off at 27 to 44 degrees, and over a clip that is about
130 cells of wander sideways for a body 16 cells across. A lane tall enough to
contain the wander leaves the creature a third of the size it could be — the
first cut of this piece came out at 34 px a creature.

So the lane is a **window that slides sideways with the shoal**. On a torus that
is a change of origin and nothing else. It cancels exactly the component of the
motion that is not the race, and leaves the component along the lane — the one
being compared, the one the fitness paid for — untouched. The world is 209 cells
tall and 56 of them are ever on screen, which is what buys 69 px a creature and
2.1 px a frame.

Measured against `check`: **4.2% of frames under the freeze threshold, longest
run 10** — which is the opening hold and nothing else, zero frozen frames after
it. The house norm is 4%. `cohort`, the same run in panels, measures 78%.

### Three things that had to be verified, and one that failed

- **The seed's orientation is a gene, not a free parameter.** `soliton` deals
  twelve copies of one animal each turned a different way; that cannot be done
  here. Swept through 24 orientations in a world too big to wrap, the generation
  12 champion survives all of them, the generation 1 champion 19, and **the
  generation 39 champion none** — it holds together at the orientation it was
  selected at and at no other. So each lane swims whichever way its genome does,
  and the lane is built around that.
- **The early champions are metastable, and that is why they are not in the
  piece.** Generation 1's best passes the 500-step audition and then, run on,
  either grows or dies depending on nothing that can be pointed at: seeded at
  seven different heights in the same lane it ends with between 1.1 and 6.3
  copies' worth of mass. Generation 5 onwards holds every copy at every one of
  those placements. The lanes are picked from the genomes that are *stably*
  alive, and the count is checked against the survey at the end of every render.
- **A lane has to be sized in the lane.** These creatures are chaotic enough
  that the same genome in a different world takes a different path, so a band
  measured in a square survey does not transfer — sized from a 192² probe, the
  shoal came out straddling its own lane edge, drawn twice, once along each
  margin. The survey is now re-run in the geometry it is sizing until the answer
  stops changing.

### The copy that goes with it

> Four lanes, one generation each, out of the same run. Every lane holds five
> copies of the best genome that generation had, and they are running the same
> rule they were scored under.
>
> The top lane is generation zero — sixty-four random draws, none of them alive.
> Its best does the only thing it can: it fills its world and stops. Below it,
> generation 5, generation 8, generation 39. What separates them is the thing
> the fitness actually paid for, which is travel: 0.073 cells a step, then
> 0.170, then 0.203. The bottom lane crosses the frame while the second is still
> getting started.
>
> Nothing was designed at any point. The genome is seven numbers — a growth
> curve, the rings of a kernel, the arc it starts from — and the whole mechanism
> is copy with mistakes, compare three at random, keep the winner. Forty rounds
> of that, and the difference between the top lane and the bottom one is the
> difference between filling a world and crossing it.

> Cztery tory, w każdym jedno pokolenie z tego samego przebiegu. W każdym torze
> pięć kopii najlepszego genomu, jaki to pokolenie miało, liczonych tą samą
> regułą, pod którą dostawały ocenę.
>
> Górny tor to pokolenie zerowe: sześćdziesiąt cztery losowania i ani jedno
> żywe. Jego najlepszy robi jedyne, co potrafi — wypełnia swój świat i staje.
> Niżej pokolenia 5, 8 i 39. Różni je to, za co funkcja dopasowania naprawdę
> płaciła, czyli przebyta droga: 0,073 komórki na krok, potem 0,170, potem
> 0,203. Dolny tor przemierza kadr, zanim drugi zdąży się rozpędzić.
>
> Nikt tu niczego nie zaprojektował. Genom to siedem liczb — krzywa wzrostu,
> pierścienie jądra splotu i łuk, od którego się zaczyna — a cały mechanizm to:
> kopiuj z błędami, porównaj trzy losowe, zostaw zwycięzcę. Czterdzieści rund
> tego i różnica między górnym torem a dolnym jest różnicą między wypełnieniem
> świata a przebyciem go.

## What is different about this edition

**The subject is a population, not an organism.** The substrate set composes one
thing in the middle of a black field. There is no middle here: these pieces wrap
at the edges, so nothing on screen was built against a boundary. `soliton` wraps
both ways; `affinity` wraps left to right and is held vertically in a band, for
the typography's sake — see above.

**It is paced by the clock.** Everywhere else, frames are placed at equal
intervals of a measured progress, because those processes accelerate and stall.
This one condenses out of the gas in the first second and then simply swims at
a speed the friction fixes, so equal steps of the clock already are equal steps
of the process. A progress schedule would spend seven of the eight seconds
parked on the flat part of the curve — which is exactly the part where all the
swimming happens.

**It stops at the top of the population.** Left running, the swimmers meet,
merge and thin out, and the frame empties. True, and a worse picture.

**Each particle is splatted as a small body with a short tail.** A particle is
a point, and a point is one pixel that the bloom turns into a smudge with no
core; fifteen fractional offsets give it a bright middle and a soft edge that
does not snap to the pixel grid as it moves. The tail is three fading copies of
where the thing just was, because particle life is only legible in motion and a
still frame of it is a scatter of dots.

**It runs on the GPU.** Twenty thousand particles is four hundred million
pairs, and evaluating every one of them — multiplying the out-of-range ones by
zero — is about twenty times faster on the card than being clever about it on
the processor. The neighbour-tree implementation is still there and still
correct, and the two agree to a ten-thousandth of a pixel; without CUDA the
piece renders from that instead, slowly.

## Rendering

```bash
python3 on-growth-and-form/alife-editions/source/render_alife.py
```

A still instead of a clip while tuning, and a fresh search:

```bash
python3 on-growth-and-form/alife-editions/source/render_alife.py --preview --search
```

`soliton` runs 10 s rather than the house 8; the others are 8 s. Its run length
and its clip length are set separately — `--lenia-total` decides how far the
process gets, the frame count decides how fast it plays — because where it
stops is a composition decision. The shipped cut is `--duration 10
--lenia-total 600`: the original 8 s pace, carried two seconds further.

Exports are `9:16`, `1080 × 1920`, `30 FPS`, MP4/H.264, written to
`instagram/phone-9x16/` alongside a `.cover.png`. Requires `numpy`, `scipy`,
`Pillow`, a system `ffmpeg` with an H.264 encoder, and optionally `torch`.

## House layout

Identical to the substrate set, deliberately: IBM Plex Mono throughout, spaced
bold title 240 px from the top, data block 190 px from the bottom, hook centred
34 px in the strip above it with its lowest ink 82 px clear of the block, soft
scrim at both edges. A piece that looks nothing like its neighbours still has
to be read as coming from the same account.
