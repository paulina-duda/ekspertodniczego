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

Python 3.12, numpy, scipy, pillow, torch 2.11+cu128.

**Two machines, two GPUs.** The env name is the same on both; the card is not.

| GPU | Arch | Watch out for |
| --- | --- | --- |
| RTX 5090 | Blackwell `sm_120` | older torch wheels install fine and only fail on the first GPU call |
| RTX 4070 Laptop | Ada `sm_89` | the smaller card of the two — a grid or particle count that fits the other may not fit here |

Neither is faster in a way that changes a decision here: the renders in
`PLAN.md` and the measurements in `REJECTED.md` are not tied to which machine
made them, and a piece rejected on one card is rejected on the other.

Check which one you are on before trusting a timing or a memory figure:

```bash
python -c "import torch; print(torch.cuda.get_device_name(0), 'sm_%d%d' % torch.cuda.get_device_capability(0))"
```

## Layout

- `on-growth-and-form/source/` — `morphogens.py`, `growths.py`, `swarm.py`,
  `glow.py`, and `render_biomorphs.py`, which renders the **wetware** pieces.
- `on-growth-and-form/<edition>-editions/` — one directory per edition, each
  with its own `README.md` (the long-form record of what each piece cost),
  `CAPTION.md` (the copy that goes under the post), `source/`, and
  `instagram/phone-9x16/` for the cuts. Four are live;
  `learned-editions/` is **parked** — do not propose into it.
- `on-growth-and-form/fonts/` — IBM Plex Mono, vendored so a clone renders
  identically without anyone installing anything.

**`wetware-editions/source/` is empty.** Its renderer lives one level up in
`on-growth-and-form/source/`. A per-edition `source/` does not always hold its
own code.

## Gotchas, learned the hard way

Each of these cost real time at least once.

- **ffmpeg**: a conda build once lacked libx264, advertised libopenh264 and
  failed at render time. The env's current ffmpeg *does* have libx264 (checked
  2026-08-30, and again on the laptop 2026-09-03) and the renderers probe for a
  working encoder themselves, so this is now a thing to check rather than a rule
  — if an encode fails, compare `ffmpeg -encoders | grep libx264` between the
  conda one and `/usr/bin/ffmpeg`. **It is the build string that decides**:
  conda-forge's default ffmpeg is the LGPL one and has only libopenh264, so a
  rebuilt env needs `ffmpeg=*=gpl*` asked for by name.
- **Even dimensions only.** yuv420p subsamples chroma by two; an odd width or
  height fails with a message that says nothing about the cause.
- **`np.roll` is wrong whenever several loops share one array** — it stitches
  the end of one to the start of the next. The model's neighbour links and the
  renderer's segment list both need per-loop wrapping, and the renderer has to
  be told about it separately.
- **float32 `np.mod`** can return exactly the modulus for a value a hair below
  zero, landing one cell past the end of a grid — or exactly *on* the wall of a
  half-open box, at which point `cKDTree(boxsize=...)` refuses the whole array.
  Clamp after wrapping.
- **Bloom pyramids need padding** to a multiple of 2^levels, or the coarse
  levels drift out of alignment and the halo sits visibly offset.
- **Sample lines by length, not by a fixed count per line.** A fixed count
  turns long segments into dotted rules across the frame, and it looks like a
  layout bug rather than a sampling one.
- **A renderer's default output directory can point at the wrong edition.**
  `render_biomorphs.py` wrote to `on-growth-and-form/instagram/` instead of
  `wetware-editions/instagram/` until 2026-08-25. The render still succeeds, it
  just lands a level too high — check `DEFAULT_OUTPUT_DIR` against where the
  sibling cuts already are.
- **Wrap segments have to be dropped** in anything that travels on a torus. A
  subject leaving the right edge and arriving at the left is one object, but the
  line between those two positions is a stripe across the frame that nothing
  travelled.

## Working agreements

- **Measure before building.** Every rejected render in `REJECTED.md` would
  have been caught by ten minutes of measurement. That is what `/pitch` is for.
- **Say what was measured and what the number was.** If something failed, say
  so plainly with the output rather than calling it a minor issue.
