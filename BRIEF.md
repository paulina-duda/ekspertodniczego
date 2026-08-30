# Brief — @ekspertodniczego

**Read this before proposing anything.** Capped at 150 lines and it stays
capped: nothing goes in that is not a rule a piece obeys or a test it passes.

> **Biology is the original algorithm** · Bioinformatician
> · wetware in motion · artificial life

Every piece is a process that computes something — a form, a network, a
decision about where to grow — running on wet matter rather than silicon and
filmed as it computes. That is the only opinion a piece may have.

---

## The four editions

| Edition | Directory | The process is | The claim |
| --- | --- | --- | --- |
| **Wetware** | `wetware-editions/` | morphogenesis — how a body builds itself | this is biology, filmed as the algorithm it is |
| **Substrate** | `substrate-editions/` | something a microscope can be pointed at, on a medium | the medium is the computer |
| **Biomorph** | `biomorph-editions/` | a parametric equation, not a simulation | it only *looks* alive — and that is the point |
| **Artificial Life** | `alife-editions/` | a rule invented inside a computer | being alive may be organisation, so it can be built from numbers |

Keep the claims apart and do not let copy inflate them: alife argues
organisation *is* what being alive consists of; Biomorph claims nothing.

**Two standing bans.** `learned-editions/` is **parked** — one piece shipped, it
failed, and the objection is in T4. And the **Lenia genetic-algorithm run has
had three tellings** (`descent`, `cohort`, `shoal`), all rejected: the next
Lenia idea must be a different subject, not a fourth camera on that run.

---

## The four tests

**Run all four before writing render code.** Each exists because a finished
render was rejected for failing it. A candidate that fails any of them goes in
[`REJECTED.md`](REJECTED.md) naming the test, so the class does not come back.

### 1. Change profile — does it hold eight seconds?

A process that relaxes to an equilibrium always looks like nothing is
happening. Coarsening, filling, settling and remodelling are fast at the start
and logarithmically slow after, so the change crowds into the first second and
the rest is a still — at any clip length.

**Measure the process's own quantity at ¼, ½, ¾ and full length — starting
after the opening cover hold, not at frame 0**, which is the finished object.
Three ways to fail, and each has caught a different piece:

- **front-loaded** — two thirds of the change is done by the first quarter.
- **it stops** — the last quarter adds under ~10%. `venation` passes the first
  check at 32% and dies here: 508 at ¾ and 509 at the end.
- **flat** — total change is near zero. Things move and nothing develops.
  `shoal` reads 683 / 683 / 678 / 682 / 683 and still measures only 4.2% still
  frames, because swimming is motion without an arc. **A motion measurement
  cannot see this; only the profile can.**

Pass looks like `comet` — 12% of the change in the first quarter, **48% in the
last** — or `phyllotaxis`, 29% and 23%, growing evenly throughout. Corollary: a
relaxation process needs an external clock — a drive that keeps injecting, or a
beat — or nothing rescues it.

### 2. Something to watch — is there an event or a beat?

`somite` is why this is separate: a monotone elongation passes T1 and is still
boring. The piece needs **a rhythm, an event or a transition** — a segment
stamped every 1.1 s, a collision, a tear that heals, chaos snapping into order.
**Fail if the honest one-line description is "it gets bigger".**

### 3. Density — is it many interacting parts?

The pipeline is additive splatting into a float buffer, log-density tone
mapping, multi-scale bloom: **brightness is how much stuff is there.** A
process converging to one clean object leaves the frame black and gives that
machinery nothing to work on. **Fail if it makes one object.** The fix, twice,
was *more of them* — and only if they **share a world**: `cohort` has twenty in
twenty panels and is the stillest cut in the account.

### 4. Legibility — does it read cold, at 200 px?

The subject is the process; the unit Instagram deals in is the first
half-second and the grid thumbnail. **Show frame one to somebody who has not
been told what it is, before the render, not after.** Fail if they cannot say
what they are looking at — `regrowth` is the worked example: measurements
sound, finding real, three purple shapes on screen.

**A wetware piece additionally has to change shape, not just contents** —
`trabecula` refines a fixed silhouette, which reads as the wrong kind of motion.

**And the method has to be visible in the output.** If a viewer cannot tell
expensive machinery from a rule written by hand, it bought a sentence in the
caption and nothing on screen — which is what this test says does not rescue a
piece. `regrowth` is the case: fit a network to a target picture and it
reproduces the picture you already had. **Anything fitted, trained or searched
must produce something you did not specify** — `affinity`'s table was found by
search and passes, because nobody chose what the animals would look like.

### Reusing an engine — a `2.0`

**An engine that has already shipped may carry a second reel.** This is
generative art: the same rule under a different palette, shape and hook is a
different visual experience, and that is enough to make it a new piece.

Two hard conditions. **Only on Paulina's explicit instruction** — she names it,
*"I want `reentry` 2.0"*; never propose one unprompted, and never reach for an
existing engine because a new subject is turning out to be work. And **at least
two of these must change**: shape, palette family, look (`bloom` ↔ `sharp`),
what the colour *means*, scale or density, the hook. A hue rotation is not one.

It skips **T1** and **T3** — the engine proved both — but passes **T2** and
**T4** afresh, and answers one extra question: *what does someone who saw the
first one get out of this one?* "It is prettier" is not an answer. Output is
suffixed `_v2`, never on top of the original.
---

## House rules

1. **Black field.** Brightness comes from how much stuff is there.
2. **Colour means something measured** — intrinsic to the subject, independent
   of the camera, never decoration. Skewed scalar → **rank** it, don't scale it.
3. **Frame one is the finished object** — the grid thumbnail. Check which end
   of the timeline is the better picture (`affinity` is densest at the *start*).
4. **1080 × 1920, 30 fps, H.264, no audio. 8, 10 or 12 s** — decided per reel,
   not per edition.
5. **Two fonts, one job each.** IBM Plex Mono for everything; DejaVu Sans Mono
   *only* for the data block when it needs Greek. **Greek stays Greek** — σ, ρ,
   β, α, not `s`, `r`, `b`, `a`.
6. **Palettes stay in the family.** Neon on black, dark low end, bright only
   where dense, not garish. **Blue is an accent, never a whole piece.**
7. **No camera turn on plane processes.** Things in a plane have no far side.

Numbers, margins, shapes and confinement mechanics are **not here** — the
`reel` skill is the single source for them. Never copy them into this file.

## Where everything lives

| | |
| --- | --- |
| copy-paste prompts to start a reel | [`PROMPTS.md`](PROMPTS.md) |
| the tests, run on a candidate | `/pitch` skill |
| shapes, margins, typography, confinement | `/reel` skill |
| hook, data block, caption (EN + PL) | `/hook` skill |
| verifying a finished mp4 | `/check` skill |
| what is decided, queued, proposed | [`PLAN.md`](PLAN.md) |
| what was rejected and which test it failed | [`REJECTED.md`](REJECTED.md) |
| what has been published, in order | [`INSTAGRAM.md`](INSTAGRAM.md) |
| what a piece cost to get right | that edition's `README.md` |
