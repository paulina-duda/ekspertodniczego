# Brief — @ekspertodniczego

**Read this before proposing anything.** Capped at 150 lines: nothing here that isn't a rule a piece obeys or a test it passes.

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

**Three standing bans.** `learned-editions/` is **parked** — one piece shipped
and failed, objection in T4. The **Lenia genetic-algorithm run has had three
tellings** (`descent`, `cohort`, `shoal`), all rejected — the next Lenia idea
must be a different subject, not a fourth camera. And **a reveal is not a
piece**: the account films something computing, not something being unveiled.
`venation`, `descent` and `ridge` were three subjects and one clip, banned
however well they measure — **a subject already famous as a still is the
warning sign**, its endpoint existing before the clip does.

---

## The four tests

**Run all four before writing render code.** Each exists because a finished
render was rejected for failing it. A candidate that fails any of them goes in
[`REJECTED.md`](REJECTED.md) naming the test, so the class does not come back.

### 1. Change profile — does it hold eight seconds?

A process that relaxes to an equilibrium always looks like nothing is
happening: coarsening, filling, settling and remodelling are fast at the start
and logarithmically slow after, at any clip length.

**Measure the process's own quantity at ¼, ½, ¾ and full length — starting
after the opening cover hold, not at frame 0**, which is the finished object.
Three ways to fail, and each has caught a different piece:

- **front-loaded** — two thirds of the change is done by the first quarter.
- **it stops** — the last quarter adds under ~10%. `venation` passes the first
  check at 32% and dies here: 508 at ¾ and 509 at the end.
- **flat** — total change is near zero. `shoal` reads 683/683/678/682/683 at
  a comfortable 4.2% still frames, because swimming is motion without an arc.
  **A motion measurement cannot see this; only the profile can.**

Pass looks like `comet` — 12% of the change in the first quarter, **48% in the
last** — or `phyllotaxis`, 29% and 23%, growing evenly throughout. Corollary: a
relaxation process needs an external clock — a drive that keeps injecting, or a
beat — or nothing rescues it.

### 2. Something to watch — is there an event or a beat?

`somite` is why this is separate: a monotone elongation passes T1 and is still
boring. The piece needs **a rhythm, an event or a transition** — a segment
stamped every 1.1 s, a collision, a tear that heals, chaos snapping into order.
**Fail if the honest one-line description is "it gets bigger".**

**Self-similar growth passes T1's numbers and is still "it gets bigger".**
`sector` grows at a flat, honest 25/25/25/25% and still reads as one disc
inflating: the wedge pattern is set almost at once and the real competition is
a front too thin to see at video scale. Check the *shape* across the quarters,
not only the pixel count.

### 3. Density — is it many interacting parts?

Additive splatting, log-density tone mapping, multi-scale bloom:
**brightness is how much stuff is there.** A process converging to one clean
object gives that machinery nothing to work on. **Fail if it makes one
object.** The fix, twice, was *more of them* — and only if they **share a
world**: `cohort` has twenty in twenty panels and is the stillest cut here.

### 4. Legibility — does it read cold, at 200 px?

The subject is the process; the unit Instagram deals in is the first
half-second and the grid thumbnail. **Show frame one to somebody who has not
been told what it is, before the render, not after** — *unnamed*, or you are
asking "is that a good spindle," which only somebody already told can answer;
`spindle` passed a T4 run that way and was rejected on sight anyway. **Two
ways to fail: they cannot say what it is** (`regrowth`, three purple shapes)
**or they can, and it is not worth looking at.**

**A wetware piece additionally has to change shape, not just contents** —
`trabecula` refines a fixed silhouette, which reads as the wrong kind of motion.

**The method has to be visible in the output.** If a viewer cannot tell
expensive machinery from a hand-written rule, it bought a sentence in the
caption and nothing on screen — `regrowth` fit a network to a target picture
and reproduced the picture it was given. **Anything fitted, trained or
searched must produce something you did not specify**; `affinity`'s table was
found by search and passes, because nobody chose the animals' look.

### Reusing an engine — a `2.0`

**An engine that has already shipped may carry a second reel** — the same rule
under a different palette, shape and hook is a different visual experience.
**Only on Paulina's explicit instruction**, never proposed unprompted or to
dodge a new subject's work. **At least two must change**: shape, palette
family, look, what the colour *means*, scale, the hook. A hue rotation isn't one.

Skips **T1**/**T3** — the engine proved both — but passes **T2**/**T4** afresh,
and answers *what does someone who saw the first one get from this one?* — "it
is prettier" is not an answer. Output is suffixed `_v2`, never on top.

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
   where dense, not garish.
7. **No camera turn on plane processes** — things in a plane have no far side.

Numbers, margins, shapes and confinement are **not here** — the `reel` skill is
the single source. Never copy them into this file.

## Where everything lives

| | |
| --- | --- |
| copy-paste prompts to start a reel | [`PROMPTS.md`](PROMPTS.md) |
| the tests, run on a candidate | `/pitch` skill |
| shapes, margins, typography, confinement | `/reel` skill |
| hook, data block, caption (EN + PL) | `/hook` skill |
| verifying a finished mp4 | `/check` skill |
| what is decided, queued, proposed, or turned down (and why) | [`PLAN.md`](PLAN.md), [`REJECTED.md`](REJECTED.md) |
| what has been published, in order | [`INSTAGRAM.md`](INSTAGRAM.md) |
| what a piece cost to get right | that edition's `README.md` |
