# On Growth and Form

Named for D'Arcy Thompson's 1917 argument that the shapes living things take are
set by physics and mathematics rather than by descent alone — that a jellyfish
is the shape of a drop falling through water, and a bone the shape of the loads
it carries.

Each process here is a rule short enough to state in a sentence and rich enough
that something appears to be alive inside it.

## Editions

**[`source/`](source/)** — the first set: Gray-Scott reaction-diffusion
(`Turing`), a slime mould transport network (`Physarum`), and a closed curve
that must lengthen without touching itself (`Folding`). Two mathematical
processes and one biological one, twelve seconds each, in the
violet-magenta-cyan band.

```bash
python3 on-growth-and-form/source/render_biomorphs.py
```

**[`substrate-editions/`](substrate-editions/)** — the ratio inverted: two
biological processes and one mathematical one. A fungal mycelium (`Hyphae`), an
embryo dividing at fixed volume (`Cleavage`), and grains toppling on a lattice
(`Sandpile`). Eight seconds, built as seamless loops that open on the finished
form, and paced by measuring each process rather than by the clock. See its
README for the method.

```bash
python3 on-growth-and-form/substrate-editions/source/render_substrate.py
```

Both sets export `9:16`, `1080 × 1920`, MP4/H.264 with a `.cover.png` for the
grid, and both need `numpy`, `Pillow` and a system `ffmpeg` with an H.264
encoder; `substrate-editions` also needs `scipy`.
