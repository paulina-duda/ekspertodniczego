# Plan — @ekspertodniczego

Profile bio, as it reads on the account:

> **Biology is the original algorithm**
>
> Bioinformatician
>
> wetware in motion · artificial life

The through-line of the whole account is that first line. Every piece is a
process that computes something — a form, a network, a decision about where to
grow — running on wet matter instead of silicon, and filmed as it computes.
Where a piece has an opinion, that opinion is the one: the algorithm came
first, and biology has been running it far longer than we have.

This file records what has been **decided** — the rules a piece obeys, the
formats it can be cut in, what is built and how, and what is still queued.
[`INSTAGRAM.md`](INSTAGRAM.md) records only what has been **published**.

---

## The four editions

Each edition takes one class of process and asks the same question of it: what
is the thing actually doing, and can that be the picture? They differ in where
the process comes from, and how strong a claim the piece is making.

| Edition | Directory | The process is | The claim |
| --- | --- | --- | --- |
| **Wetware** | `on-growth-and-form/wetware-editions/` | morphogenesis — how a body builds itself | this is biology, filmed as the algorithm it is |
| **Substrate** | `on-growth-and-form/substrate-editions/` | something a microscope can be pointed at, on a medium | the medium is the computer |
| **Biomorph** | `on-growth-and-form/biomorph-editions/` | a parametric equation, not a simulation | it only *looks* alive — and that is the point |
| **Artificial Life** | `on-growth-and-form/alife-editions/` | a rule invented inside a computer | being alive may be organisation, so it can be built from numbers |

**Wetware** films real developmental biology: reaction-diffusion laying down a
pattern, a slime mould solving a transport problem, a sheet growing faster than
its own boundary can absorb. Nothing is invented; these are the algorithms
bodies actually run.

**Substrate** is about *where* a process happens. A mycelium in a plate, an
embryo cleaving at constant volume, a wave in excitable tissue — plus one rule
about integers (`sandpile`) that has no biology in it at all and produces a
radiolarian anyway. That contrast is the edition's whole argument: the
substrate does the computing, and it need not be alive to look it.

**Biomorph** is the honest odd one out. These are creatures drawn from harmonic
and parametric maths — nothing emerges, nothing is simulated, and the piece
makes no claim that anything is alive. It earns its place because *apparent*
life from a closed-form equation is a real and slightly uncomfortable fact
about how readily we read intention into motion.

**Artificial Life** is the only edition whose subject is an *argument* rather
than a fact. Everything else films something the world already does; this films
the claim, made since Langton, that what is alive about a living thing might be
the organisation rather than the chemistry — in which case it can be built out
of anything, including numbers. Worth keeping that distinction in the copy.

---

## Formats

Three shapes, two add-ons. The names are the vocabulary — ask for a piece "in
**dish** with a **hook**" and everything below is implied.

The shape names are microscopy, deliberately: they are the three ways you
actually look at something small.

### The three shapes

| Name | What it is | Used by |
| --- | --- | --- |
| **field** | the process fills the frame edge to edge | `folding`, `turing`, `soliton`, `medusa`, `cosine-creature` |
| **dish** | the process is confined to a disc, black all around | `hyphae`, `cleavage`, `sandpile`, `reentry` |
| **slide** | the process is confined to a horizontal band, black above and below | `physarum`, `affinity` |

**field** is the default and needs no work: the process is simply allowed to
fill the frame. Its cost is that the title and the hook end up sitting on
texture, which the scrim can soften but not solve.

**dish** suits anything that grows outwards from a seed. Bound the model to a
disc of radius ≈ 0.44 × the short side, centred. It is not only typographic —
a mycelium or a colony *is* normally looked at in a plate, so the frame is
honest as well as convenient.

**slide** is what to reach for when a process would otherwise cover everything
and there is text that needs black underneath it. Hold the population inside a
horizontal band well clear of the caption.

### Confining the model, not the drawing

For **dish** and **slide**, confine the *simulation*, not the render. Cropping
what gets drawn leaves structures sliced off mid-stride at the boundary;
confining the model means the black is black because nothing was ever allowed
to be there. Two ways, depending on what state the model carries:

- **A spring**, for anything with velocity (`affinity`, `swarm.ParticleLife`):
  a restoring force that only switches on once something is outside the band,
  so the population *thins* towards the margin. A hard wall draws a bright rim
  across the frame — a structure the rule itself never made.
- **Reflection**, for anything with only a heading and no velocity (`physarum`,
  `morphogens.Physarum`): there is nothing to decelerate, so the honest
  equivalent is to mirror the position back inside and flip the heading's
  component across the boundary. That is what bouncing *is*, for something that
  walks rather than falls.

Three things that follow, none of them optional:

1. **Clamp sensing at the boundary, do not wrap it.** Otherwise the population
   smells or sees straight through the black margin and stitches structure
   across it. Found in `physarum`, whose trail sensor still read the frame as
   periodic in the direction the band had just closed off.
2. **Rescale the population to the band's area.** These rules react to density
   — how many neighbours a thing has — not to raw area. Shrinking the usable
   frame without shrinking the count quietly hands the piece a denser world
   than it was tuned for (`affinity`: 20 000 → 11 667).
3. **Re-rank anything that was chosen by search.** A table or a matrix is only
   best in the world it was scored in. `affinity`'s matrix was re-searched
   under the band and won again — verified, not assumed.
4. **Set the band well inside the clearance it needs.** A cluster straddling
   the edge drags its own members out however stiff the spring is; measured
   over a whole clip the excursion is ~90 px. `affinity` ships band 385–1345,
   `wall 0.25`, worst-case rows 293 and 1424 against a title whose ink ends at
   270 and a hook whose first line starts near 1460.

### The two add-ons

Both work on any of the three shapes.

**hook** — one line, at most two, in the black strip between the form and the
data block. Plex regular 34 px, centred on the frame, its lowest ink 82 px
above the data block's first line of ink. Louder than the block and no louder
than that: every pixel it takes is a pixel the organism gives up. It is the
sentence that turns the payoff into a question, so it states the paradox and
never explains it. Files that carry it are suffixed `_hook_plex`.

The geometry was measured off the `cleavage` cut pixel by pixel and now lives
in code — `substrate-editions/source/render_substrate.py` (`build_overlay`),
mirrored in `alife-editions/source/render_alife.py` and
`source/render_biomorphs.py` — so nobody has to measure a video again.

**card** — an opening title card, held a few seconds and then faded, before the
piece proper starts (`--title-card`, in the biomorph renderers; output suffixed
`_titlecard`). Costs the beginning of the clip, which is the most valuable
part, so it needs a reason.

---

## House rules

Every piece, every edition, no exceptions.

1. **Black field.** Additive splatting into a float buffer, multi-scale bloom,
   log-density tone mapping. Brightness comes from how much *stuff* is there.
2. **Colour means something measured.** Never decoration. It must be intrinsic
   to the subject and independent of the camera — speed for an attractor,
   when-it-grew for a morphogen, which-species for a swarm. If a scalar is
   strongly skewed, **rank it** rather than scaling it, or the whole piece comes
   out one flat colour.
3. **Frame one is the finished object.** Instagram uses it as the grid
   thumbnail; growth plays from frame two. The exception is `affinity`, where
   the population is densest at the *start* and thins as it settles, so frame
   one is the first simulated state instead — check which end of your timeline
   is actually the better picture rather than assuming it is the last.
4. **1080 × 1920, 30 fps, H.264, no audio.** 8 s unless there is a reason.
5. **Two fonts, one job each.**
   - **IBM Plex Mono** (`IBMPlexMono-Regular.ttf` / `-Bold.ttf`, vendored in
     `on-growth-and-form/fonts/` rather than system-installed, so a clone
     renders identically without anyone installing anything) is the default for
     everything: title, data block, hook. **Bold for the title only**, regular
     everywhere else — mixing weights inside one text layer is what made the
     DejaVu-era captions read as two typefaces.
   - **DejaVu Sans Mono** (system, `/usr/share/fonts/truetype/dejavu/`) is the
     fallback **only** where a caption needs Greek or similar symbols. Plex has
     no σ, ρ, β, α (confirmed against its cmap — they render as empty boxes).
     Reach for it for attractor equations and anything rule 6 covers, and set
     *only the data block* in it via `make_caption`'s `equation_face`, so one
     Greek glyph does not drag the whole layer onto the fallback face.
     Superscripts (³, ²) and `°`, `·` are fine in either.
   - Spaced bold title top-left at 30 px, data block bottom-left at 27 px.
     **Top margin 240 px, bottom margin 190 px** — not symmetric, and not
     optional: the Reel player's chrome covers roughly the top 120–140 px and
     the bottom 150 px, so anything closer is clipped by Instagram's UI rather
     than by the render. Reuse these two numbers rather than re-deriving them.
   - Soft scrim at top and bottom edges, strongest at the very edge and gone
     well before the middle. Never reading as a box.
6. **Greek stays Greek.** σ, ρ, β, α — not `s`, `r`, `b`, `a`. Superscripts are
   typeset (z³, x²).
7. **Palettes stay in the family.** Neon on black. Deep, dark low end; bright
   only where the process is dense. **Not garish** — the wetware edition is the
   reference for how far to push it. Knowingly broken once: `affinity`'s neon
   cut runs four fully saturated hues, and `sandpile`'s four-stop `LATTICE` is
   the loudest thing in the account.
8. **Blue is not a favourite.** Fine as an accent or where it is neutral; never
   a whole piece in blue.
9. **No camera turn on plane processes.** Attractors and proteins rotate
   because they are objects with a far side. Fields and curves in a plane do
   not.

### A note on the look

The soft haloed glow the whole account shares comes from the **render**, not
the palette: multi-scale bloom over a log-density map. It can be turned down —
`--bloom-threshold 0.55 --bloom-strength 0.25 --exposure 1.00 --boost 1.05` —
for genuine black instead of a mid-tone haze.

The two decisions are linked, not independent. A palette is chosen against a
tone curve: `affinity`'s original hues included a pale near-white species and a
muted amber, which worked only because the bloom bleached every core towards
white anyway. Turn the halo down and those two read as pastel. **Change one,
re-look at the other.**

Tried once so far, on `affinity` (`_sharp` and `_neon` cuts). Not yet a house
rule — worth deciding, if it comes up again, whether it is a per-edition option
or something to offer everywhere.

---

## Technical gotchas, learned the hard way

- **ffmpeg**: never install it into conda — that build lacks libx264,
  advertises libopenh264 and then fails at render time. Use `/usr/bin/ffmpeg`;
  the renderers probe for a working encoder themselves.
- **Even dimensions only.** yuv420p subsamples chroma by two; an odd width or
  height fails with a message that says nothing about the cause.
- **`np.roll` is wrong whenever several loops share one array** — it stitches
  the end of one to the start of the next. The model's neighbour links and the
  renderer's segment list both need per-loop wrapping, and the renderer has to
  be told about it separately.
- **float32 `np.mod`** can return exactly the modulus for a value a hair below
  zero, landing one cell past the end of a grid — or exactly *on* the wall of a
  box that is meant to be half-open, at which point `cKDTree(boxsize=...)`
  refuses the whole array. Clamp after wrapping.
- **Bloom pyramids need padding** to a multiple of 2^levels, or the coarse
  levels drift out of alignment and the halo sits visibly offset.
- **Sample lines by length, not by a fixed count per line.** A fixed count
  turns long segments into dotted rules across the frame — and it looks like a
  layout bug rather than a sampling one, which cost real time in `descent`.
- **`wetware-editions/source/` is empty.** Its renderer `render_biomorphs.py`
  (Turing, Physarum, Folding) lives in `on-growth-and-form/source/`, one level
  up. A per-edition `source/` does not always hold its own code.
- **A renderer's default output directory can point at the wrong edition.**
  `render_biomorphs.py` wrote to `on-growth-and-form/instagram/` instead of
  `wetware-editions/instagram/` until 2026-08-25. The render still succeeds, it
  just lands a level too high — check `DEFAULT_OUTPUT_DIR` against where the
  sibling cuts already are.
- **Environment**: `conda activate ekspertodniczego` — python 3.12, numpy,
  scipy, pillow, torch 2.11+cu128. RTX 5090 is Blackwell `sm_120`; older torch
  wheels install fine and only fail on the first GPU call.

---

## Built

### Wetware
`wetware-editions/` · morphogenesis · colour = when it grew, or which species.

- **Folding** — differential growth, four closed curves. **Posted.** `field`,
  no hook, DejaVu-era layout.
- **Physarum** — slime mould transport network, two species, 600 000 agents.
  Reworked 2026-08-25 into `slide` + hook + Plex: the band is 330–1400, held by
  **reflection** (it has a heading, not a velocity), and the trail sensor is
  clamped at the boundary or the two-species braid stitches itself across the
  black margin. Hook *"No brain. One cell. Still finds a way."* The old
  DejaVu-era cut is kept alongside.
- **Turing** — Gray-Scott reaction-diffusion, four seeds. Still on the
  pre-rework layout; its data block carries Greek, so a re-cut needs the
  DejaVu `equation_face` override.

### Substrate
`substrate-editions/` · a process on a medium · four cuts, all now sharing the
hooked Plex layout.

- **Cleavage** — an embryo dividing at constant volume. **Posted**, in the
  DejaVu-era `dish` layout; the Plex re-cut exists and needs to replace it.
- **Hyphae** — fungal mycelium: extend, branch, anastomose. **Posted**, `dish`
  + hook. Colour is age — dark where the colony started, white at the front.
  Hook *"A tree branches. A fungus branches back."*
- **Reentry** — spiral waves in excitable tissue, Barkley's model. A sheet
  fires once and cannot fire again until it recovers; waves annihilate on each
  other's wakes and nothing in the rule says *spiral*. A spiral needs a wave
  with a free end, so the piece induces one the way a cardiology lab does — a
  premature beat into the tail of the wave before it, half onto tissue that has
  recovered and half onto tissue that has not. Four of those plus a
  deliberately non-uniform excitability field (`roughness 0.016` — the one
  number that decides the piece: below it the dish stays orderly, above it the
  first wave shatters before it has been a wave). Colour is time since firing,
  carried by a decaying phosphor (`afterglow`); without it the excited state is
  two cells wide and gone, and the frame holds no record of where the wave has
  been. Hook *"Nothing in the rule says spiral."*
- **Sandpile** — four grains topple, one to each neighbour, and 150 000 grains
  on one square stabilise into the same sharply-bounded fractal every time. The
  mathematics of the set, and it earns its place by looking like a radiolarian
  while containing no biology at all. Hook *"One rule about integers. No
  biology at all."*

### Artificial Life
`alife-editions/` · rules invented in a computer · the argument edition. GPU
throughout: big grids, many particles, whole populations.

`soliton` → `descent` is a matched pair — the same genome and the same fitness,
found first by looking and then by breeding. Emergence, then selection. Post
them in that order; `soliton` is already out.

- **Affinity** — particle life. Four species; one number per *ordered* pair
  saying attract or repel; one universal short-range repulsion. Nothing else —
  no cell, no membrane, no goal. Bodies come out anyway, and they swim, because
  the table does not have to agree with itself: if magenta chases mint while
  mint flees magenta, neither can settle. Symmetric tables crystallise.
  **Posted**, `slide` + hook.
  - **The table is found, not designed** — twenty random tables scored on
    assembly × motility × coverage. The measurement that matters is speed *of
    the particles already assembled*: mean speed over everything cannot tell a
    swimmer from a gas, because loose particles rattle faster than anything
    organised. A first attempt scored packing × overall speed and picked tables
    that make round static dots. **The scoring function is the aesthetic** —
    re-read it before re-running the search.
  - **Density and radius decide the rest.** Interaction range sets how big a
    body is; neighbour count decides whether the population condenses into a
    few lumps or thousands of small animals.
  - Hook is the edition's thesis rather than a paradox, over two lines:
    *"Being alive is a matter of organization, / so it can be built from
    numbers."* Data block closes on *"16 numbers are enough to make them
    chase"*. Colour = species.
  - **The `_neon` cut is the one that went out**, not the default: low bloom
    plus four fully saturated hues. So the account's one published example of
    the sharp look is this piece, which is worth remembering when deciding
    whether the rest of the grid should follow.
- **Soliton** — Lenia (Chan 2019). Continuous Life: real-valued cells, a ring
  kernel, one growth curve, divided time. **Posted**, `field` + hook, 10 s.
  Credit is carried in-frame in the data block.
  - **Two failure modes, everything interesting between them.** Almost every
    seed either collapses to nothing or grows without limit. ~1 in 2 000 random
    draws is a self-limiting individual; ~1 in 100 of those travels.
  - **The audition has to be long, and re-run at the render size.** A 300-step
    window passes slowly-expanding colonies off as creatures — the first search
    did exactly that. The fix is a second window 300 steps later checking the
    mass has actually stopped rising. Separately, Lenia is only *approximately*
    scale-invariant: of 105 survivors found at radius 18, seven stopped being
    self-limiting at radius 30. **Never ship on the audition alone.**
  - **The seed is six numbers, not a bitmap** — an arc, a soft annulus with one
    side faded, which is what every traveller in Lenia looks like at the start,
    because a front and a back on step one is all a soliton needs to pick a
    direction. `phase` is that direction.
  - **The collision is the piece.** Twelve copies of one animal, spaced so they
    are seen swimming first; two touch, and what replaces them is not a bigger
    creature but a colony that spreads until it takes the frame. Hook *"Every
    one of these was stable on its own."*
  - **Run length and clip length are separate knobs.** `--lenia-total` fixes
    how far the process gets; the frame count only sets the speed. Tying steps
    to frames silently turns a longer cut into a different picture. Shipped at
    `--duration 10 --lenia-total 600`; past ~720 steps the colonies cover
    everything, the black is gone and the text has nothing to sit on.
- **Descent** — a genetic algorithm over that same genome and fitness. 64
  genomes, 40 generations, tournament of 3, two elites. **Built, not posted.**
  - **The run tells the story by itself.** Generation 0: none of the 64 random
    genomes scored at all — selection had nothing to act on, the first parents
    were chosen between equals at random, and the first living thing in the
    piece is a mutation of something dead. By generation 9 exactly one founder
    line is left; the other 63 leave nothing.
  - **Weak selection on purpose.** Tournament of 3, not best-of-population:
    taking the best every time collapses the pedigree to a single line inside
    three generations — a worse picture *and* worse search.
  - **The picture is the pedigree, not the creature.** Layout decides
    everything: a gene on the horizontal draws the population converging into a
    thread up the middle (true, empty); an even spread per generation fills the
    frame but makes a line that has just ended look identical to one that goes
    on. What works is the phylogeny — last generation dealt across the width by
    ancestry, ancestors at the mean of their descendants, dead ends hung off
    their parent. A canopy over a trunk, standing in coloured scrub.
  - Colour = which founder; brightness = fitness. Hook *"Everything at the top
    has one ancestor."*

### Biomorph
`biomorph-editions/` · parametric creatures · nothing emerges, and that is
stated rather than hidden.

- **Cosine-creature** — **posted**, `field`. Inspired by **yuruyurau**;
  credited on the post.
- **Medusa** — metachronal wave; a bell and fourteen tentacles driven by one
  sine with fourteen phase delays. Built with hook (`HOOK_GAP = 82`, same
  numbers as everywhere else). Its data block carries Greek (ξ, φ), so the
  title stays Plex while the block itself is drawn in DejaVu via
  `equation_face`. Not posted.

---

## Queued

**Ready, not posted** — `descent`, `reentry`, `sandpile`, `medusa`, plus the
Plex re-cut of `cleavage` that should replace the version already on the grid.

**Needs a re-cut before it could go out** — `turing` and `folding` still run
the pre-hook, symmetric-margin, DejaVu-era layout in the same renderer that
`physarum` has already been moved off.

**Open questions**

- `sandpile`'s `LATTICE` palette is four flat stops (one per state, or the only
  fact the picture carries gets muddied) and comes out acid green across most
  of the disc. Worth deciding *once* whether that much green belongs on the
  grid next to the mycelium and the phosphor.
- Whether the low-bloom look is a per-edition option or something to offer
  everywhere.

**Stretch — Neural CA.** A cellular automaton whose rule is a small learned
network: grows a shape from one cell and **regrows after being cut**.
Regeneration is never programmed — it falls out of learning to grow. Feasible
now that torch is installed. Wants its own edition rather than a slot in
Artificial Life.

---

## Rejected, and why

- **Spirographs / harmonic roulettes.** Beautiful, but nothing *emerges* — a
  parametric equation, fully understood, with no surprise about the world in
  it. Every other edition carries a true surprise; this would be the only one
  that does not. A version pointing the geometry at real phenomena (Venus
  resonance, Fourier epicycles, phyllotaxis) was drafted and set aside as too
  astronomical and too backward-looking for an account that should feel
  contemporary.
- **Classic Conway's Life as the visual.** Right idea historically, wrong
  material for this style: sparse binary cells have no mass and no density
  gradient, and the pipeline lives on accumulated density. Its continuous
  descendants (Lenia) do the same job and actually look alive.
- **Segment edition** (`segment-editions/`). Ugly — dropped entirely.
- **Attractors and proteins.** Posted early, since taken down. Mathematics and
  structural biology rather than biology-as-algorithm, and the whole account
  now reads better without them.

---

## Copy for the feed

Written per reel: what it is, what the surprise is, and why it is true. Light
cynicism is welcome **only where it does not shade the science** — if it would
come out limp, neutral is better. Two versions when it is a close call.
