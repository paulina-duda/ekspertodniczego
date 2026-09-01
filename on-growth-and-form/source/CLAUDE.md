# Writing a model or a renderer

Read this before touching `morphogens.py`, `growths.py`, `swarm.py`, `glow.py`
or any `render_*.py`. Each item cost real time at least once.

## Numerics

- **`np.roll` is wrong whenever several loops share one array** — it stitches
  the end of one to the start of the next. The model's neighbour links and the
  renderer's segment list both need per-loop wrapping, and the renderer has to
  be told about it separately.
- **float32 `np.mod`** can return exactly the modulus for a value a hair below
  zero, landing one cell past the end of a grid — or exactly *on* the wall of a
  half-open box, at which point `cKDTree(boxsize=...)` refuses the whole array.
  Clamp after wrapping.
- **A five-point laplacian carries the square grid's own anisotropy** into
  whatever it propagates: waves run faster along the axes and radial structures
  come out as four-pointed stars. The isotropic nine-point stencil
  `(1/6)[[1,4,1],[4,-20,4],[1,4,1]]` is not a refinement, it is the removal of
  an artefact. `aggregation` was blocked on this.

## Drawing

- **Bloom pyramids need padding** to a multiple of 2^levels, or the coarse
  levels drift out of alignment and the halo sits visibly offset.
- **Sample lines by length, not by a fixed count per line.** A fixed count
  turns long segments into dotted rules across the frame, and it looks like a
  layout bug rather than a sampling one.
- **Wrap segments have to be dropped** in anything travelling on a torus. A
  subject leaving the right edge and arriving at the left is one object, but the
  line between those two positions is a stripe across the frame that nothing
  travelled.
- **Even dimensions only.** yuv420p subsamples chroma by two; an odd width or
  height fails with a message that says nothing about the cause.

## Wiring

- **Check `DEFAULT_OUTPUT_DIR` against where the sibling cuts already are.**
  `render_biomorphs.py` wrote to `on-growth-and-form/instagram/` instead of
  `wetware-editions/instagram/` until 2026-08-25. The render succeeds either
  way; it just lands a level too high.
- **This directory renders the wetware pieces**, even though
  `wetware-editions/source/` exists and is empty. A per-edition `source/` does
  not always hold its own code.
- **An edition's `EDITIONS` entry carries its own overrides** — `exposure`,
  `boost`, `steps_per_frame`, `settle`, `scrim`, palette. Put per-piece
  decisions there rather than in the shared code path, and say in a comment
  what was measured to justify the number.

The house format — margins, shapes, typography, confinement — is in the `reel`
skill, not here. This file is only about code that has bitten.
