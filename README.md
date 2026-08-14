# Expert at Nothing

Generative science animations built with Python, NumPy, Pillow, and FFmpeg.

## Collections

- [`generative-science-art/`](generative-science-art/) — five projects over the same material: the original [`equation-editions/`](generative-science-art/equation-editions/), the seamless [`luminous-editions/`](generative-science-art/luminous-editions/), [`emergence-editions/`](generative-science-art/emergence-editions/), [`palette-editions/`](generative-science-art/palette-editions/), and [`trace-editions/`](generative-science-art/trace-editions/).
- [`attractors/`](attractors/) — generators, parameter studies, colour variants, previews, and source exports.
- [`on-growth-and-form/`](on-growth-and-form/) — D'Arcy Thompson-inspired biomorph studies, including an Instagram-ready v3 MP4.
- [`libra/`](libra/) — PDB chain/domain data plus a downloader and Cα-trace renderer.

## Run

```bash
pip install -r requirements.txt
python3 generative-science-art/equation-editions/source/clifford_science_art.py
```

FFmpeg with an H.264 encoder is required for video export.
