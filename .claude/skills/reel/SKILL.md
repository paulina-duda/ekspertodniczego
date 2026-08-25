---
name: reel
description: Cut or re-cut a reel for @ekspertodniczego. Carries the house format — the three shapes (field, dish, slide), the hook and card add-ons, typography, margins, and how to confine a simulation to a shape without wrecking it. Use when making a new piece, re-cutting an old one, changing which shape a process sits in, or deciding how a process should fill the frame.
---

# Cutting a reel

Everything here is settled. Reuse the numbers rather than re-deriving them —
they were measured off shipped cuts, pixel by pixel.

Reasoning and history live in `PLAN.md`; this is the operational version.

## Fixed for every piece

- **1080 × 1920, 30 fps, H.264, no audio, 8 s** unless there is a reason.
- **Black field.** Additive splatting into a float buffer, multi-scale bloom,
  log-density tone mapping. Brightness = how much stuff is there.
- **Colour means something measured**, intrinsic to the subject and independent
  of the camera. Never decoration. Skewed scalar → rank it, don't scale it, or
  the frame comes out one flat colour.
- **Frame one is the finished object** — Instagram takes it as the grid
  thumbnail. But check which end of the timeline is actually the better
  picture: in `affinity` the population is densest at the *start* and thins as
  it settles, so frame one is the first simulated state instead.
- **No camera turn on plane processes.** Things in a plane have no far side.

## The three shapes

Pick one. The name is the whole instruction.

### field
The process fills the frame edge to edge. No confinement, nothing to do.

Cost: title and hook end up on texture. The scrim softens that; it does not
solve it. If the text has to be readable over a busy process, use **slide**.

### dish
Confine the model to a disc, radius ≈ **0.44 × the short side**, centred.
Black all around it.

Right for anything growing outward from a seed. Also honest: a mycelium or a
colony is normally looked at in a plate.

### slide
Confine the model to a horizontal band. Black above and below, so the title and
the hook sit on black rather than texture.

Shipped numbers (`affinity`): band **385–1345**, `wall 0.25`. Worst-case
excursion over a whole clip: rows 293 and 1424.

## Confining a model

Confine the **simulation**, not the render. Cropping the drawing leaves
structures sliced off mid-stride; confining the model means the black is black
because nothing was ever allowed to be there.

Two mechanisms — pick by what state the model carries:

| Model has | Use | Why |
| --- | --- | --- |
| velocity (`swarm.ParticleLife`) | **spring** — restoring force that only switches on outside the band | population thins into the margin instead of stacking against a line |
| only a heading (`morphogens.Physarum`) | **reflection** — mirror position back inside, flip the heading component | nothing to decelerate; bouncing is what a wall does to something that walks |

A hard wall on a velocity model draws a bright rim across the frame — a
structure the rule never made. Don't.

### Four things that follow, none optional

1. **Clamp sensing at the boundary, never wrap it.** Otherwise the population
   smells or sees through the black margin and stitches structure across it.
   This bit `physarum`, whose trail sensor still treated the frame as periodic
   in the direction the band had just closed.
2. **Rescale the population to the band's area.** These rules react to density
   — neighbour count — not to area. Same count in a smaller frame = a denser
   world than the piece was tuned for. `affinity`: 20 000 → 11 667.
3. **Re-rank anything chosen by search.** A matrix or table is only best in the
   world it was scored in. Re-run the search under the new geometry and check
   the incumbent still wins. Verify, don't assume.
4. **Set the band well inside the clearance it needs.** A cluster straddling
   the edge drags its own members out however stiff the spring is — allow
   ~90 px of excursion.

## The two add-ons

Both work on any shape.

### hook
One line, at most two, in the black strip between the form and the data block.

- Plex **regular 34 px**, centred on the frame.
- Its **lowest ink 82 px above the data block's first line of ink**.
- Max width ≈ **952 px** — at 34 px Plex Mono that is ~46 characters per line.
- Louder than the data block and no louder than that.

It states the paradox and never explains it. For writing the line itself, use
the `hook` skill.

Geometry lives in code — `build_overlay` in
`substrate-editions/source/render_substrate.py`, mirrored in
`alife-editions/source/render_alife.py` and `source/render_biomorphs.py`.
Files carrying it are suffixed `_hook_plex`.

### card
An opening title card held a few seconds then faded (`--title-card` in the
biomorph renderers, output suffixed `_titlecard`). Costs the opening of the
clip, which is the most valuable part — needs a reason.

## Typography

Two fonts, one job each.

- **IBM Plex Mono** — the default for everything: title, data block, hook.
  Vendored in `on-growth-and-form/fonts/`, so a clone renders identically.
  **Bold for the title only**, regular everywhere else; mixing weights inside
  one text layer reads as two typefaces.
- **DejaVu Sans Mono** (`/usr/share/fonts/truetype/dejavu/`) — fallback **only**
  where the caption needs Greek. Plex has no σ, ρ, β, α; they render as empty
  boxes. Set **only the data block** in it, via `make_caption`'s
  `equation_face`, or one Greek glyph drags the whole layer onto the fallback.
  `°`, `·`, `³`, `²` are fine in Plex — checked.

Layout:

- Spaced bold title top-left, **30 px**, at **top margin 240 px**.
- Data block bottom-left, **27 px**, at **bottom margin 190 px**.
- Left inset **64 px**.
- Soft scrim top and bottom, strongest at the edge, gone before the middle.
  Never reading as a box.

240 and 190 are not symmetric and not optional: the Reel player's chrome covers
roughly the top 120–140 px and the bottom 150 px.

## Palette and bloom are one decision

The soft haloed glow the account shares comes from the **render**, not the
palette: multi-scale bloom over a log-density map.

Low-bloom ("sharp") settings, as shipped on `affinity_..._neon`:

```
--bloom-threshold 0.55 --bloom-strength 0.25 --exposure 1.00 --boost 1.05
```

**Changing one means re-looking at the other.** A palette is chosen against a
tone curve. `affinity`'s original hues included a pale near-white species and a
muted amber, which worked only because bloom bleached every core towards white
anyway; with the halo down they read as pastel.

Palette rules: neon on black, deep dark low end, bright only where the process
is dense, **not garish**. Blue is fine as an accent, never as a whole piece.

## Before shipping

Run the `check` skill.
