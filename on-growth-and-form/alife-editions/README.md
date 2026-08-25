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
| `descent_genetic-algorithm_alife` | genetic algorithm | the pedigree of a real run: 64 founders, 40 generations, one ancestor |

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
