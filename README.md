# Atraktory i animacje Manim

Zbior skryptow Pythona do tworzenia wizualizacji atraktorow, oscylatora
glikolitycznego Selkova i sieci Hopfielda oraz animacji Manim.

## Instalacja

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Do eksportu GIF i MP4 potrzebny jest takze `ffmpeg` dostepny w systemie.

## Struktura

- `atraktory/` — skrypty Lorentza oraz wygenerowane lokalnie GIF-y;
- `atraktory/skrypty/` — skrypty do eksportu MP4 dla Instagrama;
- `atraktory/final*/` — opisy wariantow finalnych; same MP4 sa ignorowane przez Git;
- `densenet_manim.py` — scena Manim przedstawiajaca DenseNet.

Wyniki renderowania (`.gif`, `.mp4` i katalog `media/`) pozostaja lokalnie i
nie sa wersjonowane. Mozna je odtworzyc skryptami opisanymi w README w
katalogach wynikowych.
