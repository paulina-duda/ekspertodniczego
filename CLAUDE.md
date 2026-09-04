# ekspertodniczego

Renders for the Instagram account [@ekspertodniczego](INSTAGRAM.md) — biological
processes filmed as the algorithms they are.

## Read this first

| Doing what | Read |
| --- | --- |
| starting a reel from scratch | [`PROMPTS.md`](PROMPTS.md) — copy-paste prompts |
| proposing a new piece | [`BRIEF.md`](BRIEF.md), then run `/pitch` |
| cutting or re-cutting a reel | `/reel` |
| writing the hook, data block or caption | `/hook` |
| verifying a finished mp4 | `/check` |
| **writing model or renderer code** | [`on-growth-and-form/source/CLAUDE.md`](on-growth-and-form/source/CLAUDE.md) — numerical and drawing gotchas |
| finding out what exists and what is next | [`PLAN.md`](PLAN.md) |
| checking whether an idea was already turned down | [`REJECTED.md`](REJECTED.md) |

**Do not load `PLAN.md` to propose something.** `BRIEF.md` is the brief;
`PLAN.md` is the record. Numbers — margins, geometry, confinement — live only
in the `reel` skill. Nothing gets mirrored between these files.

## Environment

```bash
conda activate ekspertodniczego
```

Python 3.12, numpy, scipy, pillow, torch 2.11+cu128. If an encode fails,
compare `ffmpeg -encoders | grep libx264` between the conda ffmpeg and
`/usr/bin/ffmpeg` — a conda build once lacked it.

**Developed across two machines, same `ekspertodniczego` conda env on both:**
a desktop with an RTX 5090 (Blackwell `sm_120`) and a laptop with an RTX 5070.
Neither is faster in a way that changes any decision here — the renders in
`PLAN.md` and the measurements in `REJECTED.md` are not tied to which machine
made them, and a piece rejected on one card is rejected on the other. Older
torch wheels install fine on either and only fail on the first GPU call.

## Layout

`on-growth-and-form/source/` holds the models and the wetware renderer;
`<edition>-editions/` holds each edition's `README.md` (the long-form record),
`CAPTION.md` (the copy that goes under the post), `source/` and
`instagram/phone-9x16/`. Four editions are live; `learned-editions/` is
**parked** — do not propose into it. Fonts are vendored in
`on-growth-and-form/fonts/`.

## Working agreements

- **Measure before building.** Every rejected render in `REJECTED.md` would
  have been caught by ten minutes of measurement. That is what `/pitch` is for.
- **Say what was measured and what the number was.** If something failed, say
  so plainly with the output rather than calling it a minor issue.
