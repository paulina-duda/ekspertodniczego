# Prompts

## Just make me a reel

Open a new conversation, copy one of these four, send it. **Nothing to fill
in.** The model reads `CLAUDE.md` by itself, `/pitch` looks up what already
exists and what has been rejected, and `/reel` holds every number.

It stops twice: once for you to pick the candidate, once for you to look at
frame one. Those two stops are the only reason this is not a one-liner.

**You get four things back:** the mp4, a `.cover.png` for the grid, the on-frame
hook and data block, and **the caption to paste under the post — in English and
Polish, printed in the reply and filed in the edition's `CAPTION.md`.**

### Artificial Life

> Read `BRIEF.md`. Make a new **Artificial Life** reel.
>
> Run `/pitch` on three candidates and **stop** — I pick the one to build. Then
> build the model, cut it with `/reel`, write the text with `/hook` — hook, data
> block, and the caption in English and Polish — verify with `/check`, and file
> one row in `PLAN.md` plus the long-form in the edition's `README.md`.
>
> **Stop again after the first render and show me frame one** before writing any
> copy. Report measurements as numbers, and if something fails say so with the
> output instead of calling it minor.

### Wetware

> Read `BRIEF.md`. Make a new **Wetware** reel.
>
> Run `/pitch` on three candidates and **stop** — I pick the one to build. Then
> build the model, cut it with `/reel`, write the text with `/hook` — hook, data
> block, and the caption in English and Polish — verify with `/check`, and file
> one row in `PLAN.md` plus the long-form in the edition's `README.md`.
>
> **Stop again after the first render and show me frame one** before writing any
> copy. Report measurements as numbers, and if something fails say so with the
> output instead of calling it minor.

### Substrate

> Read `BRIEF.md`. Make a new **Substrate** reel.
>
> Run `/pitch` on three candidates and **stop** — I pick the one to build. Then
> build the model, cut it with `/reel`, write the text with `/hook` — hook, data
> block, and the caption in English and Polish — verify with `/check`, and file
> one row in `PLAN.md` plus the long-form in the edition's `README.md`.
>
> **Stop again after the first render and show me frame one** before writing any
> copy. Report measurements as numbers, and if something fails say so with the
> output instead of calling it minor.

### Biomorph

> Read `BRIEF.md`. Make a new **Biomorph** reel.
>
> Run `/pitch` on three candidates and **stop** — I pick the one to build. Then
> build the creature as its own script beside `fish.py` (this edition has no
> `EDITIONS` registry), cut it with `/reel`, write the text with `/hook` — hook,
> data block, and the caption in English and Polish — verify with `/check`, and
> file one row in `PLAN.md` plus the long-form in the edition's `README.md`.
>
> **Stop again after the first render and show me frame one** before writing any
> copy. Report measurements as numbers, and if something fails say so with the
> output instead of calling it minor.

`learned-editions/` is parked — there is deliberately no prompt for it.

---

## A `2.0` off an engine that has already shipped

**Only you can start this one** — the rule in `BRIEF.md` is that a `2.0` never
gets proposed unprompted. But naming the engine is all you have to decide.
**What changes is the model's proposal, not yours to specify** — a `2.0` is
only worth doing if it is a genuinely different visual experience, and asking
for one while dictating the shape and the look defeats the point: you would
just be describing the render yourself and having it typed out.

> Read `BRIEF.md`. I want a **`reentry` 2.0** — same engine, genuinely
> different visual experience.
>
> Propose three different ways to re-cut it. Each has to change at least two
> of: shape, palette family, look (`bloom` ↔ `sharp`), what the colour means,
> scale, the hook — say which two and what each does to the picture. For each,
> answer in one sentence: what does someone who already saw the original get
> out of this one? **Stop** — I pick one.
>
> Then run `/pitch`'s `2.0` path on it (T1 and T3 are already proven by the
> engine; confirm T2 and T4 hold for this cut), build it with `/reel`, write
> the text with `/hook`, verify with `/check` — output tagged `_v2`, never over
> the original — and file it as its own row in `PLAN.md`.
>
> **Stop again after the first render and show me frame one** before writing
> any copy.

Only fill in **which engine**, named exactly as it appears in `PLAN.md`'s Built
tables. If you already know exactly what you want changed, say so instead of
asking for proposals — but that is you making the creative call, not the
model, and it is worth noticing which one you are doing.

## If you already know the subject

Skip the survey. The only thing you write is the subject:

> Read `BRIEF.md`. Make a **Substrate** reel about **bacterial swarming on an
> agar plate**. Run `/pitch` on it first and stop if it fails — I would rather
> hear that than see a render.
>
> If it passes: build it, cut it with `/reel`, `/hook` for the text, `/check` to
> verify, one row in `PLAN.md` and the long-form in the edition's `README.md`.
> Show me frame one before writing any copy.

## If you want to steer the look

Add one line to any prompt above. These four are the per-piece judgement calls
and nothing else in the prompt implies them:

> Cut it as a **dish** in the **sharp** look, colour by **age**, and make it
> 10 s.

Leave any of them out and the model decides and tells you why. **Say nothing
about margins, type sizes or geometry** — those are in `/reel` and repeating
them creates a second source that drifts.

---

## Steering it stage by stage

The single prompt runs all five stages. Send them separately when you want to
redirect between them — the model remembers the earlier turns, so later prompts
do not repeat what earlier ones established.

```
1  pitch   →  you pick a candidate
2  build   →  model only, measured
3  cut     →  the mp4
4  text    →  hook, data block, caption
5  check   →  measurements, then filed
```

**1 · Pitch**

> Read `BRIEF.md`, then run `/pitch` on three new **Substrate** candidates.
> T1 and T2 only. Do not write render code and do not pick a palette.

**2 · Build**

> `ripple` passed. Build the model in `substrate-editions/source/`, following
> how the existing models there are laid out, and add its `EDITIONS` entry.
> Model only — no palette, no hook, no caption. Re-measure T1 on the real model
> rather than the sketch and give me the five numbers.

**3 · Cut**

> Read `/reel` and cut `ripple`. Shape **dish**, look **bloom**, colour is the
> time since a cell last reversed. Length is your call between 8, 10 and 12 s —
> say which and why.

**4 · Text**

> Run `/hook` for `ripple` — hook, data block, and caption in English and
> Polish. The paradox is that the bands pass straight through each other
> because nothing is actually travelling, only the agreement to reverse.

**5 · Check**

> Run `/check` on the mp4. Every measurement as a number, including the T1
> profile after the opening hold — not just the frozen-frame count.

---

## What you can turn

**Turn freely.** Edition · subject · **shape** (`field` `dish` `slide` `lane`) ·
**look** (`bloom` `sharp`) · length (8, 10, 12 s) · what the colour means · the
paradox · how many subjects are on screen.

Shape is the biggest lever: `field` when the texture *is* the piece, `slide`
when text has to sit on black, `dish` for anything growing from a seed, `lane`
only to compare separate runs.

**Ask before changing.** Palette is chosen against a tone curve, so changing the
look means re-looking at the palette. Confinement is decided by what the model
carries — a spring for velocity, reflection for a bare heading — not by taste.
`scrim` defaults to 0.95 and veils the top 384 px; `somite` and `trabecula` set
0.55 because their subject runs to the top edge.

**Never put in a prompt.** Margins 240 / 190 · left inset 64 · title Plex bold
30 px · data block 27 px · hook 34 px at an 82 px gap · dish radius 0.44 × short
side · 1080 × 1920, 30 fps, H.264, yuv420p · the fonts · the directory layout ·
the four tests. All of it is in `/reel` and `/check`. **If your prompt and the
skill disagree, the model has to guess which is current.**

## What goes wrong when the prompt is loose

Each of these has actually happened.

| Loose prompt | What you get |
| --- | --- |
| "make a nice alife reel" | a subject picked for how it sounds, rejected after the render |
| "make it look good" | a palette chosen against the wrong tone curve |
| pasting `PLAN.md` in | 3,700 tokens of history, and a model that thinks the queue is a list of ideas |
| "check it works" | frozen-frame count only — and a flat piece passes |
| your own hook in the prompt | five rewrites of your line, no alternatives |
| no shape named | `field` by default, and the text lands on texture |
| no stop named | a finished reel including the parts you would have redirected |
