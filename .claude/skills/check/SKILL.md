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

## 4. Text sits on black

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

## 5. Typeface

If the piece was rendered before the DejaVu → Plex fix, or by a renderer that
was never moved off it, the caption is in the wrong face. Confirm the render
used `IBMPlexMono` from `on-growth-and-form/fonts/`, and that any Greek in the
data block came through `equation_face` rather than dragging the whole layer
onto DejaVu.

Empty boxes in the caption mean a glyph is missing from Plex — check the cmap
before assuming the font path is wrong.

## 6. It went to the right place

`render_biomorphs.py` wrote to `on-growth-and-form/instagram/` instead of
`wetware-editions/instagram/` for a while. The render succeeds either way; it
just lands a level too high. Confirm the file is next to its siblings.

## 7. Nothing was overwritten

A variant cut must not replace the cut it varies. Check the intended
neighbours are all still present — `--tag` exists precisely so a variant lands
alongside rather than on top.

## Reporting

Say what was measured and what the number was. If something failed, say so
plainly with the output rather than describing it as a minor issue.
