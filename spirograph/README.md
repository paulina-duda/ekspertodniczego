# Spirograph

Roulettes: curves drawn by a pen fixed to a circle rolling on another circle.
Where `attractors/` collects trajectories that never repeat because they are
chaotic, this collection is about curves whose repetition is settled by
arithmetic — by the ratio of the two radii, rational or not.

```text
spirograph/
├── README.md
└── harmonic-roulettes/
    ├── README.md
    ├── source/harmonic_roulettes.py
    ├── previews/*.png
    └── instagram/phone-9x16/*.mp4
```

## Harmonic Roulettes

Three editions — `hypotrochoid`, `epitrochoid`, `golden-roulette` — built as a
single argument about whether a curve ever comes home. See
[`harmonic-roulettes/`](harmonic-roulettes/) for the full note.

```bash
python3 spirograph/harmonic-roulettes/source/harmonic_roulettes.py --all-pieces
```

Exports are `9:16`, `1080 × 1920`, `12 s`, `30 FPS`, MP4/H.264. The generated
media stays local because media files are ignored by Git.
