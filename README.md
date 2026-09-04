# ekspertodniczego

Renders for the Instagram account [@ekspertodniczego](https://instagram.com/ekspertodniczego)
— biological processes filmed as the algorithms they are.

> **Biology is the original algorithm**

Every piece is a process that computes something — a form, a network, a decision
about where to grow — running on wet matter rather than silicon, and filmed as it
computes. Reels are 1080 × 1920, 30 fps, H.264, no audio, 8 to 12 seconds,
composed on black with colour that always means something measured.

## The four editions

Named for D'Arcy Thompson's *On Growth and Form* (1917) and its argument that the
shapes living things take are set by physics and mathematics rather than by
descent alone.

| Edition | The process is | The claim |
| --- | --- | --- |
| [`wetware-editions/`](on-growth-and-form/wetware-editions/) | morphogenesis — how a body builds itself | this is biology, filmed as the algorithm it is |
| [`substrate-editions/`](on-growth-and-form/substrate-editions/) | something a microscope can be pointed at, on a medium | the medium is the computer |
| [`biomorph-editions/`](on-growth-and-form/biomorph-editions/) | a parametric equation, not a simulation | it only *looks* alive — and that is the point |
| [`alife-editions/`](on-growth-and-form/alife-editions/) | a rule invented inside a computer | being alive may be organisation, so it can be built from numbers |

A fifth, [`learned-editions/`](on-growth-and-form/learned-editions/), is parked —
it shipped one piece and that piece failed; its README says why.

Each edition's README is the long-form record of what its pieces cost to get
right, and its `CAPTION.md` holds the copy that went under the post.

## Running a render

```bash
conda activate ekspertodniczego
python3 on-growth-and-form/source/render_biomorphs.py --edition comet
```

`render_biomorphs.py` covers the wetware pieces; each other edition has its own
renderer under `<edition>-editions/source/`. `--edition <name>` picks one,
`--preview` writes a still instead of a clip while tuning. Output lands in that
edition's `instagram/phone-9x16/` with a `.cover.png` for the grid.

Needs Python 3.12, `numpy`, `scipy`, `Pillow`, and an `ffmpeg` with an H.264
encoder; `learned-editions` also needs `torch`. Fonts are vendored in
[`on-growth-and-form/fonts/`](on-growth-and-form/fonts/) — nothing to install.

**Rendered video is not committed.** Every clip is reproducible from the source
beside it; what went out is logged in [`INSTAGRAM.md`](INSTAGRAM.md).

## How the work is organised

A piece is measured before it is built, not after. Four acceptance tests decide
whether a process can hold eight seconds, and everything that failed one is
recorded with the test that killed it.

| | |
| --- | --- |
| [`BRIEF.md`](BRIEF.md) | the standing brief and the four tests — read before proposing anything |
| [`PLAN.md`](PLAN.md) | what is built, what is queued, what is proposed |
| [`REJECTED.md`](REJECTED.md) | what was turned down, and which test it failed |
| [`INSTAGRAM.md`](INSTAGRAM.md) | what has been published, in order |
| [`PROMPTS.md`](PROMPTS.md) | ready-made prompts for making a reel with Claude Code |
| [`CLAUDE.md`](CLAUDE.md) | environment, layout, and where everything lives |

The house format — shapes, margins, typography, confinement — lives in the
`reel` skill under [`.claude/skills/`](.claude/skills/), alongside `pitch`,
`hook` and `check`. Those are the single source for every number; nothing is
mirrored between files.
