# On Growth and Form

Named for D'Arcy Thompson's 1917 argument that the shapes living things take are
set by physics and mathematics rather than by descent alone — that a jellyfish
is the shape of a drop falling through water, and a bone the shape of the loads
it carries. Both of those have since been made: the jellyfish as `medusa`, the
bone as `trabecula`.

Each process here is a rule short enough to state in a sentence and rich enough
that something appears to be alive inside it.

## The four editions

| Edition | The process is | The claim |
| --- | --- | --- |
| [`wetware-editions/`](wetware-editions/) | morphogenesis — how a body builds itself | this is biology, filmed as the algorithm it is |
| [`substrate-editions/`](substrate-editions/) | something a microscope can be pointed at, on a medium | the medium is the computer |
| [`biomorph-editions/`](biomorph-editions/) | a parametric equation, not a simulation | it only *looks* alive — and that is the point |
| [`alife-editions/`](alife-editions/) | a rule invented inside a computer | being alive may be organisation, so it can be built from numbers |

A fifth, [`learned-editions/`](learned-editions/), is **parked** — it shipped
one piece and that piece failed; its README says why.

Each edition's own README is the long-form record of what its pieces cost to get
right. [`../PLAN.md`](../PLAN.md) is what is built and what is next;
[`../BRIEF.md`](../BRIEF.md) is the standing brief and the tests a candidate has
to pass first.

## Running a render

```bash
conda activate ekspertodniczego

# wetware — Turing, Physarum, Folding, Somite, Phyllotaxis, Comet, Trabecula
python3 on-growth-and-form/source/render_biomorphs.py

# substrate — Hyphae, Cleavage, Reentry, Condensate, Sandpile
python3 on-growth-and-form/substrate-editions/source/render_substrate.py

# artificial life — Affinity, Soliton, Descent, Cohort, Shoal
python3 on-growth-and-form/alife-editions/source/render_alife.py
```

Biomorph is the exception: one script per creature rather than a registry,
because each is its own parametric equation.

```bash
python3 on-growth-and-form/biomorph-editions/source/generate_growth_mp4_v3_titled.py  # cosine-creature
python3 on-growth-and-form/biomorph-editions/source/generate_medusa_mp4_titled.py     # medusa
python3 on-growth-and-form/biomorph-editions/source/generate_quorum_mp4_titled.py     # quorum
```

`--edition <name>` picks one; `--preview` writes a still instead of a clip while
tuning.

Everything exports `9:16`, `1080 × 1920`, `30 fps`, MP4/H.264 with no audio, to
that edition's `instagram/phone-9x16/` alongside a `.cover.png` for the grid.
Clips are 8 s unless a piece has a reason to be longer. All of it needs `numpy`,
`Pillow` and a system `ffmpeg` with an H.264 encoder; most also need `scipy`,
and the parked `learned-editions` needs `torch`.

Fonts are vendored in [`fonts/`](fonts/) — nothing to install.
