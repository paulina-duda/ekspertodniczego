---
name: check
description: Verify a rendered @ekspertodniczego reel before it goes out — dimensions, frame count, duration, loop seam, whether text sits on black, and whether frame one is the intended state. Use after any render, and before publishing or replacing an existing cut.
---

# Checking a cut

Every item here has caught a real defect at least once. Run them against the
finished mp4, not against the preview.

## 1. The container

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,nb_frames,codec_name,pix_fmt \
  -of default=nw=1 FILE.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 FILE.mp4
```

Expect `1080 × 1920`, `h264`, `yuv420p`, `nb_frames = duration × 30`, and a
duration that is exactly what was asked for.

Odd dimensions fail yuv420p with a message that says nothing about the cause.

## 2. Frame one is the intended state

Pull it and look at it:

```bash
ffmpeg -hide_banner -loglevel error -y -i FILE.mp4 \
  -vf "select=eq(n\,0)" -vframes 1 /tmp/f0.png
```

It is the grid thumbnail, so it has to be the best frame in the piece — not
merely the last state the simulation reached. Check whether the process is
densest at the start or the end; `affinity` is densest at the start, and its
cover was silently the *sparsest* frame in the clip until that was caught.

## 3. The loop seam

```python
first = np.asarray(Image.open("f0.png").convert("RGB")).astype(int)
last  = np.asarray(Image.open("flast.png").convert("RGB")).astype(int)
print(np.abs(first - last).mean())
```

Under ~3.0 is compression noise — the loop closes. Much above that and the
clip visibly cuts on repeat, which is fine only if it was a deliberate choice.

**3.0 is not the test on a fast piece.** Frame 239 is one frame *before* the
loop closes, so the seam is an ordinary adjacent pair — and on a piece with
many small bright elements moving quickly, an ordinary adjacent pair is
already well over 3.0. `quorum` measures 6.24 at the seam and 6.23 between
frames 0 and 1, which means it closes exactly. Compare the seam against
`|f1 − f0|` from the same clip; if they match, the loop is closed whatever the
absolute number. Only fall back to the 3.0 figure when you have not measured
the adjacent pair.

## 4. It actually moves

The loop-seam test compares the first frame to the last and says nothing about
the 238 in between. A clip can pass every other check here and still sit frozen
for most of a second.

```bash
ffmpeg -hide_banner -loglevel error -y -i FILE.mp4 -vf "scale=135:240" /tmp/mf/f%03d.png
```

```python
frames = [np.asarray(Image.open(f).convert("L")).astype(float) for f in sorted(glob.glob("/tmp/mf/*.png"))]
delta = np.array([np.abs(frames[i + 1] - frames[i]).mean() for i in range(len(frames) - 1)])
frozen = delta < 0.15
run = longest_true_run(frozen)
```

Report the fraction and the per-second breakdown — freezes cluster, and where
they land matters as much as how many.

**Calibrated against shipped cuts**, so these are measurements rather than
guesses:

| Cut | frozen | longest run |
| --- | --- | --- |
| `hyphae`, `reentry`, `affinity_neon` | **4%** | 10 |
| `condensate`, first attempt | 29% | 10 |

- **fraction under 0.15** — 4% is the house norm. Over ~10% is a defect.
- **longest run is not the test.** Every cut shows 10, because `--hold 11`
  deliberately holds the cover frame open at the start. Ignore the opening
  hold and look at what happens after it.
- **frozen count per second** — a freeze in second 0 or 1 is far worse than the
  same freeze at the end, because that is where the viewer decides.

### It is the scheduler, not the encoder

Every version of this bug came from `even_schedule`, and each fix taught the
same thing from a different angle.

**A scheduler can only repeat a state or skip one.** It has no intermediate
states to hand out, so wherever it decides more frames are deserved, it
delivers the same picture several times — which is the stutter itself.

`condensate` went through all three:

1. **Paced by a physical scalar**, states banked at equal time intervals.
   Coarsening is a t^(1/3) law, so the droplet scale spent most of its range in
   the first few states and the scheduler held one of them for 22 frames.
   117 of 239 transitions frozen, the worst inside the opening two seconds.
2. **Paced by measured picture-change.** Fixed the late clip, broke the early
   one: "equal change per frame" wants to insert frames where change is
   largest, and with nothing to insert it repeated instead — dwelling exactly
   on the fastest-moving part. 22%.
3. **Banked on a cube-root spacing and played straight through.** 5%.

**Put the pacing in how the states are banked, then play them in order.** If
the banking is right, consecutive states already differ by roughly equal
amounts and no scheduler is needed. Check the floor directly before blaming
anything else — bank the states, measure the change between consecutive ones,
and see what fraction falls under the threshold. For `condensate` that floor
was 1%, which said plainly that everything above it was the scheduler's doing.

## 5. Text sits on black

For **dish** and **slide** cuts, measure rather than eyeball. The text layer
itself is lit, so measure the *model*, not the rendered frame:

```python
# worst excursion over the whole clip, not just the final state
worst_top, worst_bottom = 1e9, 0
for _ in range(frames):
    model.step(1)
    rows = model.position[:, 1]
    worst_top = min(worst_top, rows.min())
    worst_bottom = max(worst_bottom, rows.max())
```

Clearances to keep:

- title ink ends at **row 270** — nothing above that
- hook's first line starts near **row 1460** (one line) — nothing below that
- a two-line hook starts higher; compute it with `glow.caption_ink_top`

Allow for bloom bleeding ~10–20 px past the model's own extent.

## 6. Typeface

If the piece was rendered before the DejaVu → Plex fix, or by a renderer that
was never moved off it, the caption is in the wrong face. Confirm the render
used `IBMPlexMono` from `on-growth-and-form/fonts/`, and that any Greek in the
data block came through `equation_face` rather than dragging the whole layer
onto DejaVu.

Empty boxes in the caption mean a glyph is missing from Plex — check the cmap
before assuming the font path is wrong.

## 7. It went to the right place

`render_biomorphs.py` wrote to `on-growth-and-form/instagram/` instead of
`wetware-editions/instagram/` for a while. The render succeeds either way; it
just lands a level too high. Confirm the file is next to its siblings.

## 8. Nothing was overwritten

A variant cut must not replace the cut it varies. Check the intended
neighbours are all still present — `--tag` exists precisely so a variant lands
alongside rather than on top.

## Reporting

Say what was measured and what the number was. If something failed, say so
plainly with the output rather than describing it as a minor issue.
