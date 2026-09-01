# Rejected, and which test it failed

Tests are the four in [`BRIEF.md`](BRIEF.md), applied by `/pitch`: **T1**
change profile · **T2** something to watch · **T3** density · **T4**
legibility. `subject` means it failed the account's premise rather than a test.

**This is a record, not a brief.** `/pitch` does not read it up front — the
failure patterns live in BRIEF's tests and the standing bans in BRIEF's
editions section, so a growing file is not paid for on every pitch. It is
grepped when a surviving candidate looks like a relative of something here.

### How it stays small — capped at 80 lines

- **One table row per rejection**, and that row is permanent. It is cheap.
- **Prose only for a lesson that changed a rule**, and once the rule is written
  into `BRIEF.md` or a skill, cut the prose here down to a sentence.
- **Never restate a test.** The tests live in `BRIEF.md`.

| Name | What it was | Failed | Why, in one clause |
| --- | --- | --- | --- |
| `regrowth` | neural CA fitted to a planarian, beheaded and rebuilt | **T3, T4** | converges to one clean object; cold viewers see three purple shapes |
| `trabecula` | bone remodelling under three load cases | **T1, T4** | silhouette fixed from frame one — it refines an interior rather than growing |
| `somite` | the vertebrate segmentation clock, 16,500 cells | **T4** | the beat is real and the clip still reads as a weak stripe pattern; judged on the cut, not the model |
| `venation` | space-colonisation leaf veins | **T1** | a reveal: branches uncover and nothing moves — **44.4% still frames**, 29 of the first 30 |
| `sorting` | differential adhesion, domains coarsening | **T1** | sorted by step 8, then four identical frames |
| `condensate` | Cahn-Hilliard phase separation, droplets coarsening | **T1, T2** | droplets get fatter and nothing else happens; blobs are off-register for the account's look |
| `descent` | the pedigree of a 40-generation genetic algorithm | **T2, T4** | a reveal — the tree uncovers and nothing moves; a phylogeny diagram does not sit on Instagram |
| `cohort` | 20 Lenia genomes, one per panel | **T2, T3** | a panel caps travel — 78% still frames against a house norm of 4% |
| `shoal` | the same Lenia run as four lanes racing | **T1, T2** | flat profile 683 / 683 / 678 / 682 / 683 — the creatures swim and the piece has no arc |
| `liesegang` | periodic precipitation rings | **build** | eight parameter sweeps never separated into bands; first precipitate drains the dish |
| Spirographs / harmonic roulettes | parametric curves, incl. a Venus-resonance and phyllotaxis draft | **subject** | nothing emerges — the only edition with no surprise about the world in it |
| Conway's Life | the classic binary automaton | **T3** | sparse binary cells have no mass and no density gradient; Lenia does the job |
| `kaleidoscope` | Nowak & May's spatial prisoner's dilemma, cooperators against defectors | **T3, T4** | two states and no gradient — the churn field is a flat grey square, the state field is static in a box |
| `aggregation` | *Dictyostelium* cAMP relay, T1–T3 all measured clean | **T4** | first cut clashed house rule 6 (magenta vs lime); re-cut fixed the palette and it still reads as flowers, not cells — `cell_radius` too small for the strokes to fuse into mass under either look. The blocked-anisotropy fix and the model are real; the picture never was |
| `sector` | microbial range expansion, sector boundary competition, T1 measured flat and clean | **T2** | 25/25/25/25% profile and 5.4% frozen, and it still reads as one colour wedge disc inflating — the wedge layout is set almost at once and the real competition (boundaries wandering, lineages going extinct) is a front too thin to see at video scale. Numbers passed; the shape never changed, only its radius |
| `ripple` | *Myxococcus* counter-propagating wave trains | **T1** | ordered by step 60 of 1200 and only decays after — 0.082 / 0.734 / 0.520 / 0.424 / 0.388 |
| `nematic` | a rod-shaped bacterial monolayer ordering itself as it grows | **T4** | coloured confetti at full size, grey-green speckle at 200 px — `aggregation`'s failure, strokes too small to fuse |
| `stripe` | zebrafish pigment cells, Turing with cells as the morphogens | **T1, T4** | 88.1% of the change in the first quarter, 0.8% in the last; the still is a labyrinth of filaments, not stripes |
| `swarm` | *Proteus mirabilis* terraced swarming, the consolidate-and-migrate cycle | **T2, T4** | two formulations and 24 parameter sets gave one flood and never a staircase — a delayed excitable front in a continuum is a travelling wave, not a beat — and the finished frame is a featureless disc, interior density p90/p10 2.85 |
| `mega` | the MEGA-plate: a colony evolving its way across bands of rising antibiotic | **T4** | T1 is comet-clean (38.3% first quarter, 14.7% last, 0.4% frozen) and the breakthroughs are real events, but each band is founded by one mutant whose clone then sweeps it, so the finished plate is 90–100% lit in four flat colour bars; no mutation rate buys both the event and the texture |
| `band` | Budrene-Berg chemotactic spot arrays in *E. coli* | **build** | 42 parameter sets over four formulations gave two outcomes and nothing between — one smooth disc, or 400–1,500 blobs 1–3 px across; scaling `Dn` and χ together to resolve a wavelength deletes the instability rather than widening the spots |
| Segment edition | `segment-editions/` | **subject** | ugly; dropped entirely |
| Attractors, proteins | posted early, since taken down | **subject** | mathematics and structural biology, not biology-as-algorithm |

A dozen further candidates were dropped on **T1** alone in the 2026-08
shortlist and are not listed: the pattern is always coarsening, filling,
settling or remodelling.

**`condensate` is the one worth remembering.** It was pushed from 146k steps to
1.2M and given three pacing schemes; the stutter went 29% → 5% and the droplets
really do end up fat. All of that engineering was correct and none of it changed
what the clip is. **A T1 failure is not a bug to be fixed by working harder on
the render** — the process is the problem.

---

## Kept as groundwork rather than deleted

A rejection is about the grid, not the code. What survived, and why:

| From | What is reusable |
| --- | --- |
| `regrowth` | trainer, renderer, and both weight files (64 KB). The grow-only vs damage-in-the-loop comparison is the parked edition's one real finding and stays reproducible |
| `venation` | the space-colonisation model and `tree_samples` — `comet` reuses the segment splat wholesale, which is most of what the piece was worth |
| `trabecula` | the FE solve and the two-channel warm/cool render path |
| `somite` | the oscillator and determination-front model, the cyclic `PULSE` palette, and the per-edition `scrim` override it forced. **The beat is the axis worth reusing** |
| `condensate` | `growths.Condensate`, the cube-root state banking that is now the house answer to scheduler stutter, and the timestep bound `dt < 2/(8·(8ε²−1))` |
| `shoal` | the sliding-lane camera and the trajectory survey. The **lane** shape stays in the `reel` skill and may yet carry a different subject |
| `cohort` | the arithmetic: moving pixels are *creatures × body area × body-lengths travelled*, and isolated panels make that product flat |
| `descent` | the genetic algorithm itself. The search was worth running; none of its three tellings became a reel |
| `aggregation` | the isotropic nine-point laplacian, now in `on-growth-and-form/source/CLAUDE.md` — it fixed a real grid artefact and outlives this piece |
| `sector` | the Gaussian-neighbourhood isotropic growth rule and the O(1) frame recovery by arrival-step (one `int32` array for the whole clip, no per-state banking) |

## Delete the render, keep the code

A rejected cut does not stay on disk. The mp4 and its cover come off; the
model, the renderer and any weights stay, and the row above is the record. Disk
is not an archive — `REJECTED.md` is.
