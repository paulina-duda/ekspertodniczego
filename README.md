# Expert at Nothing

Generative science animations built with Python, NumPy, Pillow, and FFmpeg.

## Collections

- [`attractors/`](attractors/) — generators, parameter studies, colour variants, previews, and source exports, plus two curated 9:16 collections: the seamless [`luminous-editions/`](attractors/luminous-editions/) and the line-drawn [`trace-editions/`](attractors/trace-editions/).
- [`on-growth-and-form/`](on-growth-and-form/) — D'Arcy Thompson-inspired biomorph studies, including an Instagram-ready v3 MP4.
- [`libra/`](libra/) — PDB chain/domain data, a downloader and Cα-trace renderer, and [`solvent-editions/`](libra/solvent-editions/) — protein assemblies rendered with an elastic-network model of their motion.
- [`life/`](life/) — cellular automata, and [`wetware-editions/`](life/wetware-editions/) — Conway's Life as tissue, as a machine, and as what noise settles into, two of them recorded as solids in space and time.

## Run

```bash
pip install -r requirements.txt
python3 attractors/trace-editions/source/render_traces.py
```

FFmpeg with an H.264 encoder is required for video export.
