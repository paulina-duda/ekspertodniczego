# Biomorph Editions

`biomorph-editions/` · parametric creatures · nothing emerges, and that is
stated rather than hidden.

The honest odd one out. These are drawn from harmonic and parametric maths —
nothing is simulated, nothing emerges, and no piece here claims anything is
alive. The edition earns its place because *apparent* life out of a closed-form
equation is a real and slightly uncomfortable fact about how readily we read
intention into motion. Say so in the copy rather than hiding it.

One script per creature rather than a registry, because each is its own
equation: `generate_growth_mp4_v3_titled.py`, `generate_medusa_mp4_titled.py`,
`generate_ammonite_mp4_titled.py`, `generate_hydrozoa_mp4_titled.py`,
`generate_quorum_mp4_titled.py`. `fish.py` is the edition's shared animal and
`quorum` is the first thing to use it.

The tests a piece has to pass before it is built are in
[`BRIEF.md`](../../BRIEF.md); the queue and the decisions are in
[`PLAN.md`](../../PLAN.md).

---

## The shared animal — `fish.py`

`fish.py` holds the edition's first shared animal, and it is a **surface**,
not an outline. A `Species` is a frozen dataclass of proportions, a `Fish` is
the dotted strokes those proportions generate over that surface, and `pose(t,
phase)` returns them placed, with the lateral offset and the outward lateral
direction reported separately so callers can decide what depth means. Two
species so far — `SARDINE` and `ABYSSAL`. The renderer that uses it knows
nothing about fins; `quorum` only bends the animal onto a latitude and
projects it. Three body coordinates: ξ along the spine, ζ around the
cross-section, and a section that is an ellipse of half-height `d(ξ)` by
half-width `beam·d(ξ)`. `beam` ≈ 0.30 is most of what stops the body reading
as a sausage.

What it settled, all of it the hard way:

- **Draw the animal as curves, not as a filled region.** Filling the
silhouette with random points was the first attempt and comes out as a blimp
with blots where the fins should be. Fins are made of **rays**, which is what
a fin is built from. - **A one-dimensional body cannot have a silhouette.**
Five passes were spent tuning a chain of dots along a curve — longer, shorter,
thicker, denser — and every one read as a worm, a tadpole or a spermatozoon.
Nothing about a curve was ever going to fix it. - **Many meridians, few faint
rings.** The rings are what make the eye read a tube rather than nested
contours, but at equal weight with the meridians the body comes out as a wire
grid from a 3D package. The medusa's proportion is the right one and her note
is the reason — enough hoop to read as a built thing, not enough to read as a
lampshade. - **Two of everything that comes in twos.** Two lateral lines, two
eyes, two pectorals. Dimming the far one of each is a stronger depth cue than
any amount of shading on a single flank. - **The caudal fin needs its own
frame**, rigid on the wrist and pitched by the spine's angle there plus a lag.
Sampling it along the continuing spine skews it into an asymmetric wedge. The
lag is most of what stops the swim reading as a rigid template being waved
about. - **Integrate the tangent to apply the wave.** Adding a sideways offset
to fixed positions is cheaper and stretches the animal, which looks like a
rubber band because it is one. - **`density` has to split between how many
strokes there are and how finely each is drawn** — `sqrt` of it into each.
Scaling only the points per stroke leaves twenty-three sparse meridians
reading as scattered dots at 170 px, where twelve well-drawn ones still read
as a body. - **Jitter has to stay well under the spacing between points**, or
the strokes come apart into caterpillars. 0.0013 × length; it was tried at
0.0035 first.

**The accent is a band, not a switch, and it leans.** `glow` rises and falls
smoothly with the phase and every stroke at that ξ picks it up, so what
travels head to tail is a lit ring around the whole animal rather than a dash
appearing on one line. `glow_twist` leans that ring out of the cross-section,
because a band exactly square to the spine reads as a wipe bar crossing the
animal — the medusa's bell carries the same lean for the same reason, and hers
is the note about the crest sweeping rather than dropping.

This is a **deliberate departure** from the two shipped biomorphs, which
threshold their accent hard (red where k² ≥ 15, green where sin > 0.96). A
hard edge works for a line drawing and does not for a solid. Colour still
means exactly what it means everywhere else in the account: the position of
the wave, right now. Worth deciding, if a fourth biomorph comes up, whether
soft is the house rule for anything with a surface.


---

## Cosine-creature

**posted**, `field`. Inspired by **yuruyurau**; credited on the post.

## Medusa

Metachronal wave; a bell and fourteen tentacles driven by one sine with
fourteen phase delays. Built with hook (`HOOK_GAP = 82`, same numbers as
everywhere else). Its data block carries Greek (ξ, φ), so the title stays Plex
while the block itself is drawn in DejaVu via `equation_face`. Not posted.

## Ammonite

The third coordinate system: the cosine creature read a formula along an axis,
the medusa read one wave radially, this one is the equiangular spiral —
r ∝ e^(0.13 θ), the same shape at every size, which is why a mollusc can live
in one its whole life. The animal sits still at the aperture and lays down one
rib per loop; everything it built recedes down the coil, shrinking by exactly
K = 2.3^(1/16) per rib. Magenta is the living tissue — tentacles, mantle lip,
and the one rib being written now, which materialises dot by dot as it slides
out of the lip; white is shell, dead the moment it was finished. Built with
hook (`HOOK_GAP = 82`), `_hook` cuts at 8 s and 12 s; title and hook Plex,
data block DejaVu via `equation_face` (θ, ∝). Not posted.

- **The loop is seamless *because of* the equation.** Self-similarity means
  the frame after one rib is the frame before it. Verified: last frame vs
  cover, mean pixel difference 0.65/255 — one animation step plus codec noise.
- **The rib conveyor must share one dot pattern across all ribs**, scaled by
  the local tube width, or rib j at the end of the loop lands on rib j+1's
  position with different jitter and the seam pops. Same trick as the fade:
  a rib is born at size 0 at the lip and dies at size 0 in the core, so the
  set of visible ribs is identical across the seam.
- **Rails are static, ribs drift.** The tube envelope is self-similar truth
  and holds still; only the material moves. Animating both reads identically
  and costs the jitter-seam problem twice.
- **Wrap the aperture heading** (`np.angle(np.exp(1j·ang))`) before blending
  tentacle directions, or the blend goes the long way round and the curtain
  rolls into a ball of yarn.
- **Tentacles must start already fanned** and turn at per-tentacle rates
  toward per-tentacle hanging directions — a shared initial heading pinches
  the curtain into a ponytail below the lip, tried twice.
- **Mirrored composition is a font-free way to clear the typography**: mouth
  lower-right, core upper-left, so the data block and hook sit on black and
  the title clears the coil's crown.

## Quorum

**Parked as a sketch.** The idea holds, `fish.py` is solid and the hollow-shell
depth trick works, but what exists is a first pass rather than a finished cut.
Not rejected — it needs the work, not a different idea.

A bait ball: 155 fish on the shell of a hollow spindle, each a
three-dimensional animal out of `fish.py` rather than a streak, each swimming,
the whole crowd turning once over the clip. The crests line up across
neighbours into bands that sweep round the ball, so it reads as collective
behaviour. There is no interaction term — a fish is a pure function of its own
index and `t`, and its phase is just `3θ₀`. Built with hook, `field`, magenta
accent. Not posted.

- **It is the series' third telling of one trick**, and the escalation is the
  point: the cosine creature was a wave pretending to be a body, the medusa
  the same wave pretending to swim, this one the same wave pretending to be a
  society. Worth keeping that order in the copy.

- **The animals come from `fish.py`; this file only places them.** A fish's
  own width becomes radius on the ball — it is thicker than the shell it swims
  on, so it pokes in and out of it — and its near and far flanks have to be
  shaded on their own terms, because ±20 px of body against ±405 px of ball
  disappears otherwise. `DENSITY` 0.20 gives 578 points per fish and 89,590 in
  the frame; the render takes 76 s.

- **The picture is the depth, not the crowd.** The far wall runs at alpha
  0.045 against the near wall's 1.05; at that contrast the shell reads hollow
  and the ball becomes a volume you look into. `TILT` 0.42 and the open ends
  (`U_MIN` 0.10, `U_MAX` 0.95) do the rest — a closed ball has two ragged
  poles and no silhouette.

- **The phase origin is free, so the thumbnail is a choice.** Every term is
  2π-periodic in `t`, so the loop closes at any starting phase. `--phase`
  exists for exactly that: all 240 frames are scored on visible crest plus
  near-wall density minus how clumped the crest is. **Re-run that scoring
  whenever the model changes** — the number moved from 0.1375 to 0.9750 when
  the streaks became fish.

- **`CENTRE_ROW` is not the middle of the frame.** The ball's own extremes are
  asymmetric and the title has less room above it than the hook has below, so
  model y = 0 sits on row 882. Measured extent rows 337–1427, against a title
  whose ink ends at 280 and a hook whose ink starts at 1511.

- Data block carries Greek (ξ, φ, θ) and `∝`, so the same `equation_face`
  split as `medusa`: title and hook Plex, block DejaVu.

- It is the one piece in the account that is a **deliberate fake of a real
  result** — `affinity` next door is a true interaction. Neither is
  distinguishable from the other by looking, which is the whole argument and
  should stay in the copy rather than being softened.

---
