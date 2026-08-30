# Learned Editions

> **This edition is parked.** It shipped one piece, `regrowth`, and it failed
> the account's legibility test. Nothing new is proposed into it. The code and
> both weight files stay so the finding below remains reproducible; the render
> is deleted, like every other rejected cut.
>
> The reason is structural and is now part of T4 in [`BRIEF.md`](../../BRIEF.md):
> **fitting a rule to a target picture cannot show a viewer anything.** You
> hand the network the answer and it reproduces the answer. `pelt` — fitting to
> a *statistic* rather than a picture — is the one idea that escapes that, and
> it is recorded in [`PLAN.md`](../../PLAN.md) rather than queued.

Rules that were fitted, not written.

Every other rule in this project was written down by somebody. Gray-Scott is two
diffusion constants and a feed rate. Lenia is a kernel and a growth curve. The
abelian sandpile is one sentence about integers. Somebody chose each of them,
and what they do is a consequence of a choice a person can read.

This edition films the other kind: a cellular automaton whose update rule is a
small network, fitted by gradient descent until a grid of identical cells
reliably assembles one particular animal out of one lit cell (Mordvintsev,
Randazzo, Niklasson and Levin, *Growing Neural Cellular Automata*, Distill
2020).

It is worth being precise about what is and is not different. The rule is
exactly as **local** as the others — a cell sees itself and its immediate
neighbours, and updates itself. It is exactly as **uniform** — every cell runs
the same rule, simultaneously, with nobody in charge. What changed is only the
provenance: nobody wrote these 8,320 numbers down, and nobody can read them.

That is the edition's whole claim, and it is a modest one. This is not a new
kind of process. It is the same kind of process with an unreadable rule, which
turns out to be enough to make it do something nobody asked for.

| Edition | Rule | What it is |
| --- | --- | --- |
| `regrowth_neural-ca_learned` | growing neural CA | a flatworm grown from one cell, beheaded, and rebuilt |

Rendered as `..._1080x1920_8s_30fps_hook_plex.mp4`. Hook: *"It was shown the
wound, never the repair."*

> **`regrowth` is built and is not going on the grid.** Everything documented
> below is true and none of it rescues the picture: to anyone who has not been
> told what they are looking at, it is three purple shapes that get slightly
> shorter and then slightly taller again. The finding is real and worth keeping;
> the piece is not a piece.
>
> The cause is structural rather than a tuning miss, and it is now house rule 10
> in `PLAN.md`. A rule fitted to **one picture** converges — it makes one clean
> object and stops — which leaves most of the frame black and fills the rest
> with a flat interior that the density pipeline has nothing to do with. Going
> from one specimen to three helped and did not cure it.
>
> What this edition keeps from it: the trainer with its three divergence guards,
> the renderer, the house layout, the age-colouring, and two fitted rules. The
> next piece (`pelt`, proposed in `PLAN.md`) is chosen on the opposite
> property — fitted to a *statistic* rather than a picture, so it has no fixed
> point and never settles — and is built on top of this rather than from
> scratch.

## Regrowth

### The loss only ever asks for a picture

The fitting says one thing and one thing only: **after some number of steps, the
grid should look like this.** There is no term for holding still, none for
stopping at the right size, and none whatsoever for repair. Nothing in the
training describes a wound, a signal, a blastema or a polarity — the words the
regeneration literature is made of do not appear, because there is nothing in
the loss for them to attach to.

The piece is what happens when the organism is then cut, which the training
never did.

### Why a planarian

Because it is the animal the regeneration literature is *about*. Cut one across
and the head end grows a tail while the tail end grows a head, eyes and brain
included; the experiment is nearly two hundred years old and it is still the
reference case for how a body knows what is missing.

Nothing here is a model of a planarian. The target is a silhouette — the
truncated head, the two auricles, the pinch behind them, the pharyngeal swell,
the tapering tail — and the automaton has never been told any of those are
parts. It has been shown a picture.

**The eyespots are holes, and they are the sharpest test in the frame.** Every
other feature the automaton builds by growing. The eyes it has to build by *not*
growing, in two places it knows about only because the picture is dark there.

They had to be **enlarged before the automaton would build them at all**. At a
radius of 2.6 cells they are one fifty-seventh of the body length, and the
fitted rule ignored them — 84 cells out of 20,832 is worth almost nothing to a
mean squared error, whatever it is a picture of. The Distill paper's emoji carry
their details at nearer one thirteenth. At 3.4 cells the eyes appear, and the
renderer's alpha floor is set where it is for the same reason: the rule holds
them at about 0.2 rather than at 0, which is close enough for the loss and not
close enough to read as holes once the bloom has been over them.

### What a step is

Sixteen numbers per cell. The first is visible — alpha, how much organism is
here — and the other fifteen are hidden with no assigned meaning at all:
whatever the fitting decided to keep there. Chemical gradients, a coordinate
system, a clock; nobody knows, and nothing in the training says.

1. **Perceive.** Each channel is convolved with three fixed 3×3 stencils: the
   cell itself, and the Sobel derivatives across and down. That is the whole
   neighbourhood — a cell knows its own state and which way each of its channels
   is sloping. The stencils are not learned, which is what keeps this comparable
   to Gray-Scott, whose cells also only ever see a Laplacian.
2. **Update.** Two 1×1 convolutions, which is a two-layer dense network applied
   identically at every position. It outputs a *change*, and the second layer
   starts at zero — so the automaton begins life as the do-nothing rule, and
   every behaviour in it was put there by fitting.
3. **Fire, sometimes.** Each cell updates with probability ½. Cells have no
   shared clock, and a synchronous automaton can exploit one: the parity of the
   step number is free information and a network will happily build a rule that
   depends on it. Dropping half the updates at random removes that, at the cost
   of nothing.

Then the alive mask — a cell may hold state only if it or a neighbour has alpha
above 0.1. That is what keeps the empty grid empty rather than filling with
faint arithmetic, and it is the only reason the black around the organism is
black.

### The pool is what makes it stop

Training only on runs that start from the seed teaches the automaton to look
right at step 80 and says nothing whatsoever about step 300. What that produces
is an organism that assembles beautifully and then boils.

So the states a batch ended on are kept and later batches start from them, which
repeatedly asks the rule to still be right after a number of steps it was never
trained for. The worst sample in each batch is thrown out and replaced with a
fresh seed, or the pool drifts away from ever having to grow at all.

Learning to **stop** is a separate achievement from learning to grow, and it is
measured separately below.

### What was actually measured

The piece was queued on the claim that regeneration falls out of learning to
grow — that a rule fitted only to build the animal would repair it for free.
**That is false here, and finding out is most of what this piece is.**

Two rules were fitted, identical in every respect except one: whether any
organism was ever cut during the fitting. Both ran 20,000 iterations with a
sample pool, 80–130 steps per rollout.

| | grown | persisted | regrown | eyespots, grown → regrown |
| --- | --- | --- | --- | --- |
| **grow-only** — never cut, not once | 0.0106 | 0.0150 | **0.033** | 0.22 → **−0.22** |
| **damage in the loop** — 3 of every 8 cut | 0.0185 | 0.0129 | **0.0102** | −0.11 → **0.42** |

Error is mean squared against the target; the eyespot figure is how much darker
the two holes are than the head around them, so a negative number means there
are no eyes there at all.

**The grow-only rule builds a correct animal and cannot repair it.** It grows a
proper planarian, holds it for 600 further steps untouched, and then, beheaded,
seals the stump into a smooth eyeless lens and stops — error settling at 0.033
and staying there for as long as you run it. What it does is **wound healing**,
which is not regeneration, and animals make that distinction too.

**The damage-trained rule regenerates better than it grows.** 0.0102 against
0.0185, and the eyespots come back deeper than they were built the first time.
Nothing mysterious in that: regeneration starts from most of a body and gets its
full 220 steps to settle, where growth starts from one cell and spends most of
its budget getting there.

Both weight files are kept — `weights/grow-only.npz` beside
`weights/regrowth-planarian.npz` — so the comparison can be re-run rather than
taken on trust.

### So what is the piece allowed to say

Not "it learned to heal on its own", which is what the queue entry hoped for and
what the measurement refuses. The honest claim is narrower and survives contact
with the numbers:

**The loss only ever describes the finished picture.** Damaged states go in, but
nothing is ever compared against anything except the final frame. There is no
intermediate target, no wound signal, no notion of a blastema or a polarity —
none of the vocabulary regeneration biology is made of. The rule was shown the
wound and never the repair, and the repair is what it invented to satisfy the
only question it was ever asked.

### Fitting it is not stable, and the failure is silent

The first damage run diverged at iteration 7,200: a pooled state ran away, one
gradient came back non-finite, and that poisoned every weight in the rule
permanently. It then ran another 12,800 iterations producing `nan`, reported
`fitted 8,320 numbers in 2425s`, and wrote the weights out as if nothing had
happened.

**A pool is a memory, and that is exactly what makes it fragile** — a runaway
state does not merely score badly and get dropped, it sits in the pool and takes
out every batch it is drawn into. Three guards, all of them in `train()`:

- a step whose gradient is not finite is **skipped**, because one infinite
  gradient is permanent and one skipped iteration costs nothing;
- any pooled sample scoring worse than 1.0 goes back as a **fresh seed** — a
  blank grid scores about 0.21 against this target, so past 1.0 is not a bad
  attempt at the animal, it is a diverging one;
- the weights kept are the **best 200-iteration mean**, not whatever the last
  iteration happened to leave behind.

The clean run reseeded 165 samples out of 160,000 and skipped no steps at all.

### Colour is when a cell was built

The same scheme as `hyphae`, and the only one that survives the cut.

The obvious choice was activity — how much a cell's state changed this step,
carried on a decaying phosphor the way `reentry` carries its wake. It was tried
first and it is wrong here, for a reason worth writing down: **the last frame of
this piece is a settled organism.** Activity fades as the automaton finishes, so
the new head cools to exactly the same violet as the body it is attached to, and
the frame loses its entire subject. Measured on the first cut: by the closing
frame the regrown head was indistinguishable from three-second-old tissue.

Age does not fade. The body sits at the dark end of the ramp because it was
built first; the head runs bright because it was built second; and the scar
stays visible for as long as the clip runs.

Two things this needed:

- **Birth is recorded once and only the amputation resets it.** The first
  version forgot a cell whenever its alpha dipped below a floor, which hands the
  newest colour in the ramp to every cell that flickers across the threshold and
  paints a rim of white speckle round the whole organism — a fact about the
  threshold, not about the animal.
- **The scale is the clip's own length**, fixed for every frame. Ranking per
  frame is the house answer to a skewed scalar and it is exactly wrong here: it
  would rescale each frame to use the whole ramp and destroy the one thing the
  colour has to say, which is that the head is younger than the body.

### Three, not one

The first cut filmed a single organism and it was the wrong picture, for a
reason worth writing down because it is about this whole style rather than about
this piece.

**One specimen leaves 92% of the frame black, and the body itself is flat.** The
alpha this rule settles on is very nearly binary, so there is no density
gradient anywhere inside the animal — and the house pipeline is *built* on
density: additive splatting into a float buffer, log tone mapping, bloom over
the bright cores. Handed a uniform paddle it has nothing to do. Every piece on
this account that works has many interacting parts filmed at density; a neural
CA fitted to one target shape is the opposite, a convergent low-entropy process
that makes one clean object and stops.

Three run in parallel, seeded identically, cut in the same frame. What that buys:

- **The frame is full**, and the early growth — three speckled blobs, then three
  ragged spindles overshooting and pulling back — has the texture the render
  wants.
- **The amputation becomes a mass event.** Three flat cuts at the same height in
  the same frame is the strongest image in the piece.
- **They come out different**, and nothing differs between them except which
  cells happened to fire. Worst pairwise difference between the three finished
  animals: 0.97. That divergence is the only thing on screen that shows the rule
  is stochastic rather than a recording, and one specimen cannot show it.

Each keeps its **own** 124 × 168 grid rather than sharing a wider one. The rule
was fitted with that boundary and against zero padding; three animals in one
grid would be three animals in a world none of them was fitted in. They batch,
so the cost is nothing.

Only the middle 60 columns of each grid are drawn. That is not cropping the
process: the organism never reaches past column 37 or 88 of 124, so the
discarded margin is measured-empty, and dropping it buys the magnification the
eyespots need to survive a phone. The renderer refuses to run if any specimen
ever reaches outside the drawn window.

### Nothing is confined

`dish` and `slide` exist because a process left alone fills the frame and leaves
the typography nothing to sit on. This one needs neither. The organism stops at
its own boundary because stopping is what it was fitted to do, and the black
around it is black because the rule declines to grow there.

That is a stronger version of what a dish buys by fiat, and it is also the
edition's one structural risk: an overgrown rule would be cropped by the edge of
its own grid and draw a straight line nobody's rule ever made. The renderer
prints the furthest the organism ever reaches, in cells and in frame rows, so
this is checked rather than assumed.

### The run length is not the clip length, and this one converges

No scheduler — the automaton does the same work per step from beginning to end,
so equal steps of the clock already are equal steps of the process. That is
`reentry`'s argument, and the opposite of `condensate`'s.

But it was still wrong the first time, in a way none of the other pieces can be.
**This rule was fitted to stop, and it does.** Growth is finished at about 220
steps and the regrowth at about 220 more, and the first cut kept stepping to 578
— so its last four and a half seconds were a still photograph of a finished
animal. Measured: 78% of transitions frozen, longest run 142 frames.

The fix is `soliton`'s separation of the two knobs. The run is a fixed 440 steps,
the frame count only decides how fast it is played, and the cut is placed **where
growth finishes** rather than at a round fraction of the clip.

Which is also why the piece is 8 s and not 10. The 10 s cut was rendered and is
worse: a longer clip does not show more process, it shows the same 440 steps more
slowly, and every extra frame lands on the settled animal at the end.

| | still, inside the organism | longest still run |
| --- | --- | --- |
| 10 s | 28% | 49 frames |
| **8 s** | **18%** | **21 frames** |

Two notes on measuring that, because the house threshold does not transfer
here. Only 9 of 239 transitions are *literally* identical, and all nine are
inside the deliberate opening hold — there are no true freezes in this cut. And
the full-frame figure reads far worse than the piece looks, because colour here
is age: a settled cell's colour **cannot** change by construction, so the body's
interior is constant while its rim moves, and a mean taken over the whole frame
is mostly measuring black. The organism's own bounding box is the honest number.

## Rendering

Fitting the rule (about an hour on an RTX 5090; the weights are committed, so
this is only needed to fit a different animal):

```bash
python3 on-growth-and-form/learned-editions/source/neuralca.py --iterations 20000 --steps 80 130
```

Cutting the reel:

```bash
python3 on-growth-and-form/learned-editions/source/render_learned.py
```

A still instead of a clip while tuning:

```bash
python3 on-growth-and-form/learned-editions/source/render_learned.py --preview
```

Exports are `9:16`, `1080 × 1920`, `30 FPS`, MP4/H.264, written to
`instagram/phone-9x16/` alongside a `.cover.png`. Requires `numpy`, `Pillow`,
`torch`, and a system `ffmpeg` with an H.264 encoder. The fitting needs a GPU
to be tolerable; the render does not.

## House layout

Identical to the substrate and alife sets: IBM Plex Mono throughout, spaced bold
title 240 px from the top, data block 190 px from the bottom, hook centred at
34 px with its lowest ink 82 px clear of the block, soft scrim at both edges.
The organism is centred in what the typography leaves rather than in the frame —
computed from the hook's ink, so a two-line hook moves the animal instead of
putting it under the text.
