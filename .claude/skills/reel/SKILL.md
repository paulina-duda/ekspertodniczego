---
name: reel
description: Cut or re-cut a reel for @ekspertodniczego. Carries the house format — the four shapes (field, dish, slide, lane), the hook and card add-ons, typography, margins, the two looks (bloom and sharp), and how to confine a simulation to a shape without wrecking it. Use when making a new piece, re-cutting an old one, building a `2.0` off an engine that has already shipped, changing which shape a process sits in, or deciding how a process should fill the frame.
---

# Cutting a reel

Everything here is settled. Reuse the numbers rather than re-deriving them —
they were measured off shipped cuts, pixel by pixel.

This is the operational version and the **single source for every number in
it** — margins, geometry, confinement. Do not mirror them into `PLAN.md` or
`BRIEF.md`.

**Before cutting anything new, it has to have passed the `pitch` gate.** This
skill is for a piece that is already decided; `pitch` is what decides.

## Fixed for every piece

- **1080 × 1920, 30 fps, H.264, no audio.** **8, 10 or 12 s** — decided per
  reel, not per edition, picked for what the process needs to read. A collision
  that needs room to be seen coming wants longer (`soliton` ships at 10 s so
  the swim reads before the colony does); a process that says everything
  quickly should not be stretched to fill a default.
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

## The four shapes

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

### lane
Several stacked bands, each its own world, wrapping left to right at the frame
edge. For comparing several runs of the same kind of thing in one frame; what
is compared reads off the horizontal — how far each one gets.

Unlike **slide**, nothing is confined: the lane is a *window*, and it may slide
with its subject to cancel motion across the lane while leaving motion along it
alone. That is a camera move and it needs a reason. `shoal` has one — without
it the lane must be tall enough for the subject's whole sideways wander, which
costs two thirds of the magnification (130 cells of wander for a 16-cell body
leaves 34 px; the sliding window gives 69 px).

**This is the way out of `cohort`'s arithmetic.** The moving pixels in a clip
are *creatures × body area × body-lengths travelled*; in isolated panels
raising any one lowers another. The lane stops paying for travel in screen
area.

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

## Two looks: `bloom` and `sharp`

The soft haloed glow the account shares comes from the **render**, not the
palette: multi-scale bloom over a log-density map. It is a **per-piece choice**
with two named settings, not a fixed house look.

| Look | Settings | Reach for it when |
| --- | --- | --- |
| **bloom** | the defaults | the default. Density reads as glow; right for anything with mass — a mycelium, a swarm, a colony |
| **sharp** | `--bloom-threshold 0.55 --bloom-strength 0.25 --exposure 1.00 --boost 1.05` | the subject is **thin lines** the halo would smear into haze, or you want genuine black instead of a mid-tone veil |

Shipped on `sharp`: `affinity`'s `_neon` cut — the account's one published
example of the look — and `venation` (at `exposure 1.10`, `boost 1.20`).
**`venation`'s filename does not record it**, so re-render with the flags or
the cut changes under you. Name the look in the filename on anything new.

**Changing one means re-looking at the other.** A palette is chosen against a
tone curve. `affinity`'s original hues included a pale near-white species and a
muted amber, which worked only because bloom bleached every core towards white
anyway; with the halo down they read as pastel.

Palette rules: neon on black, deep dark low end, bright only where the process
is dense, **not garish**. Blue is fine as an accent, never as a whole piece.

## Re-cutting an engine as a `2.0`

An engine that has already shipped may carry a second reel — **but only when
Paulina asks for it by name** (*"`reentry` 2.0"*). The rule, and what has to
change for it to count, is in [`BRIEF.md`](../../../BRIEF.md); this is the
mechanical side.

- **Change at least two of** shape, palette family, look (`bloom` ↔ `sharp`),
  what the colour means, scale or density. One of those alone is a variant, not
  a piece.
- **A shape change is the strongest lever** and the most work: re-read
  *Confining a model* above. Moving `reentry` from `dish` to `slide` means a
  new confinement, a rescaled population and re-ranked search results — all
  four of the non-optional consequences apply again.
- **Re-tune the palette against the new look**, never port it across. That is
  the same coupling as everywhere: `affinity`'s original hues only worked
  because bloom bleached the cores white.
- **Suffix `_v2`** and use `--tag` so it lands *alongside* the original. It
  must never overwrite the cut it descends from.
- Frame one is chosen fresh. The first piece's best frame is not this one's.

## Before shipping

Run the `check` skill.

## Afterwards

The long-form record — what this piece cost to get right — goes in its
edition's own `README.md`, not in `PLAN.md`. `PLAN.md` gets one table row. A
`2.0` gets its own row, not an edit to its parent's.
