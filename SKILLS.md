# Skills — @ekspertodniczego

Three skills live in this repo. This file explains what a skill is, what each
one carries, and when to reach for it.

The other two documents: [`PLAN.md`](PLAN.md) is what has been decided and what
is queued; [`INSTAGRAM.md`](INSTAGRAM.md) is what has been published.

---

## What a skill actually is

A folder under `.claude/skills/` containing a `SKILL.md` — a markdown file with
a short YAML header (`name`, `description`) and instructions underneath.

```
.claude/skills/
├── reel/SKILL.md
├── hook/SKILL.md
└── check/SKILL.md
```

**How it gets used.** Type `/reel` and that file's contents load into the
conversation at that moment. It can also fire on its own when what you ask for
matches its `description` — which is why the descriptions are written as "use
when you are doing X" rather than as titles.

**What it is not.** A skill is not code and nothing executes when it loads. It
is the instruction — the numbers, the procedure, the things that have already
been decided — handed over at the moment it is needed instead of re-derived.

**Why it lives in the repo.** `.claude/skills/` is committed, so it travels
with the project and works on any machine that clones it.

### Skills versus the other two files

They answer different questions, and it is worth keeping them apart:

| | Question it answers |
| --- | --- |
| `PLAN.md` | **why**, and what exists — reasoning, history, what is built and queued |
| `INSTAGRAM.md` | **what went out** — the log of published reels and their formats |
| a skill | **how, now** — the procedure and the numbers, nothing else |

When something is settled, it belongs in a skill. When something is an argument
or a record, it belongs in `PLAN.md`. A rule that is still being decided stays
in `PLAN.md` until it stops moving.

---

## The three

### `/reel` — cutting a piece

The house format. Reach for it when making a new reel, re-cutting an old one,
or deciding how a process should sit in the frame.

Carries:

- the three shapes — **field** (fills the frame), **dish** (a disc),
  **slide** (a horizontal band) — and which to pick
- how to confine a simulation to a shape without wrecking it: a **spring** for
  anything with velocity, **reflection** for anything with only a heading, plus
  the four consequences that always follow (clamp sensing, rescale density,
  re-rank anything found by search, leave room for excursion)
- the **hook** and **card** add-ons, with their geometry
- typography: which of the two fonts, when, at what size, at what margin
- why palette and bloom are one decision rather than two

### `/hook` — writing the text

The words. Reach for it when a piece is rendered and needs its hook, its data
block, or its caption.

Carries:

- what makes a hook work, with the shipped ones as worked examples, and the
  length limit that comes from the typography
- the data block's three-line shape, and that citations go in-frame there
  rather than in the caption
- how a caption is built — what it is, what the surprise is, why it is true —
  in English and Polish, and where the line on cynicism sits

### `/check` — verifying before it goes out

The pass before publishing. Every item in it has caught a real defect.

Carries:

- container checks: dimensions, frame count, duration, pixel format
- whether frame one is genuinely the best frame rather than just the last state
- the loop seam, measured rather than eyeballed
- whether text actually sits on black, measured against the **model** and its
  worst excursion over the whole clip, not against one rendered frame
- typeface, output location, and that no variant overwrote the cut it varies

---

## Using them

```
/reel     when the question is how the frame should be built
/hook     when the question is what it should say
/check    when the file exists and is about to go out
```

They chain in that order for a new piece, but each stands alone — `/check` on
an old cut, or `/hook` on something already rendered, both make sense.

If a skill turns out to be wrong or incomplete, edit its `SKILL.md` directly.
They are meant to accumulate what has been learned, the same way `PLAN.md`
does — the difference is only that a skill holds the settled part.
