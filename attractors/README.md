# Attractors

Generators, parameter studies, colour variants, and source exports, plus two
curated collections built from them for Instagram: the seamless
[`luminous-editions/`](luminous-editions/) and the line-drawn
[`trace-editions/`](trace-editions/). See each project's own README for what
it does differently and why.

```text
attractors/
├── README.md
├── IDEAS.md
├── luminous-editions/
├── trace-editions/
├── lorenz/
│   ├── README.md
│   ├── source/lorenz_instagram.py
│   └── instagram/phone-9x16/*.mp4
├── aizawa/
│   ├── README.md
│   ├── source/aizawa_instagram.py
│   └── instagram/phone-9x16/*.mp4
├── de-jong/
│   ├── README.md
│   ├── source/de_jong_instagram.py
│   └── instagram/phone-9x16/*.mp4
├── halvorsen/
│   ├── README.md
│   ├── source/halvorsen_instagram.py
│   └── instagram/phone-9x16/*.mp4
├── parametric-sculptures/
│   ├── README.md
│   ├── source/twisted_crescent_instagram.py
│   ├── previews/*.png
│   └── instagram/phone-9x16/*.mp4
├── clifford/
    ├── README.md
    ├── source/clifford_instagram.py
    ├── classic-butterfly/phone-9x16/*.mp4
    ├── ribbon/, shell/, orbit/, mask/
    ├── organic-flower/, double-knot/, ring/
    └── */phone-9x16/*.mp4
└── hopfield/
    ├── README.md
    ├── source/hopfield_instagram.py
    └── instagram/phone-9x16/*.mp4
```

## Instagram exports

The Lorenz exports use the full phone frame: `9:16`, `1080 × 1920`, `12 s`,
`30 FPS`, and MP4/H.264. They are meant for Reels, Stories, or a full-screen
preview in the Instagram app.

The renderer requires Python with `numpy` and `Pillow`, plus a system `ffmpeg`
installation with an H.264 encoder.

Render all four colour variants:

```bash
python3 attractors/lorenz/source/lorenz_instagram.py --all-palettes
```

Render one variant:

```bash
python3 attractors/lorenz/source/lorenz_instagram.py --palette velvet-signal
```

## Aizawa and Clifford videos

Aizawa and Clifford use the same four palettes as Lorenz. Their exports are
`9:16`, `1080 × 1920`, `12 s`, `30 FPS`, and MP4/H.264.

```bash
python3 attractors/aizawa/source/aizawa_instagram.py --all-palettes
python3 attractors/clifford/source/clifford_instagram.py --all-palettes
```

The generated MP4 files stay local because media files are ignored by Git.
