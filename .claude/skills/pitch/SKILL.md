---
name: pitch
description: Put a candidate process through the four acceptance tests before any render code is written, for @ekspertodniczego. Use when proposing a new reel subject, choosing between candidates, deciding whether an idea is worth building, reviving something previously set aside, or when Paulina asks for a `2.0` off an engine that has already shipped. Produces a measured pass/fail verdict, not an opinion.
---

# Putting a candidate through the gate

**This runs before render code, not after.** Every test here exists because a
finished render was rejected for failing it — `trabecula`, `venation`,
`sorting` and `regrowth` were all built first and judged second. Ten minutes of
measurement here is the whole point of the skill.

Read [`BRIEF.md`](../../../BRIEF.md) first if it is not already in context.

**Then read the `## Built` tables in `PLAN.md` — those tables only.** They are
compact and they tell you what already exists, which is how you avoid
re-proposing it. Do not read the rest of that file: it is the record, not the
brief, and the queue is not a list of ideas.

**Do not read `REJECTED.md` up front.** The failure *patterns* are already in
BRIEF's four tests and the standing bans are in BRIEF's editions section, so a
full read costs a growing file every pitch to catch something rare. Instead,
once you have your shortlist down to survivors, **grep it for anything that
looks like a relative of one of them** — same process class, same edition, same
mechanism — and read only those rows.

## What you are allowed to write at this stage

A throwaway measurement script, in the scratchpad, not in the repo. It needs
only enough of the model to produce **the scalar the process is about** — tail
length, organ count, segment count, domain size, network extent. No renderer,
no palette, no overlay, no mp4. If you find yourself picking colours, you have
skipped the gate.

Check first whether the model already exists in
`on-growth-and-form/source/morphogens.py`, `growths.py` or `swarm.py` — several
candidates are half-built already.

---

## Test 1 — change profile

Run the model for the full intended clip length and record the scalar at
**¼, ½, ¾ and full**.

**Start after the opening cover hold, not at frame 0** — frame 0 is the
finished object, so measuring from it inverts the whole profile.

```python
q = [measure(state_at(f)) for f in (h, h+N//4, h+N//2, h+3*N//4, N)]
total = q[-1] - q[0]
first = (q[1] - q[0]) / total     # share of the change in quarter one
last  = (q[4] - q[3]) / total     # share in the last quarter
```

- **`first` > 0.67 → FAIL.** A relaxation process: one second of change and
  seven of a still photograph.
- **`last` < 0.10 → FAIL.** It stops before the clip does. `venation` passes
  the first check at 32% and dies here — 508 at ¾, 509 at the end.
- **`total` ≈ 0 → FAIL.** Nothing accumulates. `shoal` reads 683 / 683 / 678 /
  682 / 683: the creatures swim, so a *motion* measurement is satisfied at 4.2%
  still frames, but across eight seconds the piece has no arc. **This is the
  failure a frozen-frame count cannot see** — always run the profile as well.
- **PASS** looks like `comet` (12% first, 48% last) or `phyllotaxis` (29%, 23%).

Report the raw five numbers, not just the ratios.

**Measure something the viewer can see.** A scalar behind a threshold will
flatter the process: `division` counted particle clumps whose core exceeded a
neighbour count and read 22% first / 36% last across three seeds — a clean pass
— while the number of clumps actually visible on screen read 0 / 50 / 57 / 56 /
55, which is the whole change in quarter one. The detector was measuring
compaction *inside* blobs that were already there. If two frames a quarter apart
look the same, the scalar is wrong, not the eye: **put the quarters side by side
as thumbnails before believing the profile.** That strip costs a minute and it
is the only check on the number.

A fail here is not always fatal: **an external clock rescues it** — a drive
that keeps injecting material, or a beat. If you propose one, it is a different
candidate and it goes through test 1 again with the clock in.

### Then measure how much of the frame is live

**The profile measures accumulation, and a reveal accumulates.** `shoal` is the
warning in one direction — motion passes, only the profile sees the failure.
`ridge` is the warning in the other, and it cost a full build: 23.5% first
quarter against 26.5% last, a textbook pass, and the cut came out **53.1%
frozen with the first three seconds solid**, because the only thing changing was
a front creeping across a picture that was finished behind it.

So ask where the change *is*, not just how much of it there is. On the same run,
record the fraction of the frame that differs between consecutive rendered
steps:

```python
live = np.mean([(np.abs(state[i + 1] - state[i]) > eps).mean()
                for i in range(len(state) - 1)])
```

`ridge` reads **1.6%**. Everything behind the front was final, and nothing paces
that away — the timestep only moves where the live band sits, measured at
1.6 / 1.9 / 1.8% over three values while the print stopped finishing.

**If the live fraction is a thin front and the rest of the frame is done, it is
a reveal: reject it here.** The threshold is not yet calibrated against shipped
pieces — `ridge` is the only measurement in this units so far — so until a
second candidate is measured, treat a moving front with a finished wake as a
fail on the structure rather than on a number.

## Test 2 — something to watch

Write the honest one-line description of what happens over eight seconds, as
somebody who does not care about the science would write it.

**If that line is "it gets bigger" or "it gets finer", FAIL.** Passing test 1
only means the change is spread out; it does not mean there is anything to
look at. `somite` is why this test is separate.

Name the rhythm, the event or the transition:

| kind | example |
| --- | --- |
| a beat | `somite` stamps a segment every 1.1 s |
| an event | `soliton`'s two creatures touch and become a colony |
| a transition | chaos snapping into order |
| a reversal | a tear that heals |

## Test 3 — density

Answer two questions with numbers, not adjectives:

1. **How many interacting parts are on screen at once?** `physarum` 600,000;
   `comet` 160; `soliton` 12. Below about a dozen, say why it still reads.
2. **Do they share one world?** Panels, grids and per-subject frames cap how
   far anything can travel, and travel is where the motion in a clip comes
   from. `cohort` has twenty subjects in twenty panels and measures 78% still
   frames against a house norm of 4%.

**FAIL if the process converges to one clean object.** The pipeline is built on
accumulated density; one flat silhouette gives it nothing to work on. The fix,
both times it has come up, was *more of them in one world*.

## Test 4 — legibility

**Render a single still — not a clip — of the intended frame one, and describe
it to Paulina cold**, without naming the subject. If she cannot say what she is
looking at, it fails, however good the science is.

Then check the thumbnail: downscale that still to 200 px on the long edge and
look again. That is the size the grid actually shows.

For a **wetware** piece there is one extra: **the shape has to change, not just
the contents.** A fixed silhouette whose interior refines reads as the wrong
kind of motion next to `folding` and `turing` — that is `trabecula`.

---

## The `2.0` path

When Paulina asks for a **`2.0`** by name — *"I want `reentry` 2.0"* — she is
naming the engine, not the changes. **Propose three different directions**
before building any of them, the same way a fresh pitch proposes candidates,
and let her pick. Only skip this and cut straight to one direction if she names
it herself — that is her creative call to make, not a default to assume. The
engine has already proven **T1** and **T3**, so skip them. Run **T2** and
**T4** afresh on whichever direction is picked, plus one test that only applies
here:

### T5 — is it a different experience?

**Name the two things that change** (shape, palette family, look, what the
colour means, scale or density) and say what each does to the picture. One
change is a variant, not a piece.

Then answer, in one sentence: **what does someone who already saw the first
one get out of this one?** If the honest answer is "it is prettier" or "it is a
different colour", it fails — go back and change something structural, usually
the shape, which is the strongest lever.

Report it as the same block with `T1 skipped — engine proven by <name>`.

**Never propose a `2.0` unprompted.** The whole point of the rule is that it is
Paulina's call, not a way of avoiding the work of a new subject.

---

## Reporting

One block per candidate. Nothing else — no render plan, no palette, no hook
until it has passed.

```
CANDIDATE   comet — Listeria actin comet tails
EDITION     Wetware
T1 profile  128 / 3,885 / 8,966 / 20,634 / 44,781 px tail — first quarter 8%   PASS
T2 watch    "a hundred bacteria shoot across the frame, dividing as they go"   PASS
T3 density  160 comets sharing one field, no panels                            PASS
T4 legible  frame one reads as comets/sperm to a cold viewer at 200 px         PASS
VERDICT     BUILD
```

Rules for the verdict:

- **Any FAIL → the verdict is not "build with caveats".** It is `REJECT` or
  `REWORK`, and `REWORK` has to name the specific change and re-run the failed
  test.
- **A REJECT is written down.** Append one line to [`REJECTED.md`](../../../REJECTED.md):
  name, one clause of what it was, and **which test it failed**. That line is
  what stops the same class of idea coming back in a month.
- **Only touch `BRIEF.md` or a skill when the piece defeats the test itself** —
  it passed every check and still failed, the way `sector` (flat T1 profile,
  still just a growing disc) and `spindle` (clean T4 run, shown named rather
  than cold) did. An ordinary rejection — a test caught it, or would have if
  run right — is the `REJECTED.md` line and nothing more. Paulina saying a
  piece is ugly is not, by itself, a reason to change a standing rule; a piece
  that was ugly *despite passing every test as written* is.
- **A BUILD adds one line to `PLAN.md`'s queue**, not a section. The long-form
  record is written *after* the piece exists, in its edition's `README.md`.
- **Do not soften a fail.** If the numbers say the change crowds into the first
  quarter, say so with the numbers. A candidate rejected here costs an hour; a
  candidate rejected after rendering has cost several.

When several candidates are on the table, run all of them through T1 and T2
first — those are cheap and kill most things — and only take the survivors
through T3 and T4.
