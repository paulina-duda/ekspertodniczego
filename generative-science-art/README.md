# Generative Science Art

A curated collection of the most polished, publication-ready generative
science animations in the repository. Each piece includes a small monospace
equation caption in the bottom-right corner.

```text
generative-science-art/
├── README.md
├── source/
│   ├── equation_overlay.py
│   ├── continuous_equation_editions.py
│   └── clifford_science_art.py
└── instagram/phone-9x16/
    ├── lorenz_ember-garden_equation-edition_1080x1920_12s_30fps.mp4
    ├── halvorsen_electric-citrus_equation-edition_1080x1920_12s_30fps.mp4
    ├── aizawa_orchid-gold_equation-edition_1080x1920_12s_30fps.mp4
    ├── clifford_classic-butterfly_rainbow-equation-edition_1080x1920_15s_30fps.mp4
    ├── clifford_ring_rainbow-equation-edition_1080x1920_15s_30fps.mp4
    └── clifford_shell_rainbow-equation-edition_1080x1920_15s_30fps.mp4
```

Render the three continuous-system editions:

```bash
python3 generative-science-art/source/continuous_equation_editions.py
```

Render the three selected Clifford sculptures:

```bash
python3 generative-science-art/source/clifford_science_art.py
```

The Clifford seed cloud remains still. A complete 360-degree 3D turn begins
together with the first fibres, then continues smoothly while the layered body
becomes dense. Its rainbow palette uses fully saturated neon colour stops.
Equation blocks use a compact 22 px monospace layout. All exports use a
full-phone `1080 × 1920` H.264 MP4 composition.
