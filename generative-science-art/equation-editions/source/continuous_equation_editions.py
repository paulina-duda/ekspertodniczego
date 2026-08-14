#!/usr/bin/env python3
"""Create equation-captioned editions of selected continuous attractor MP4s."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from equation_overlay import make_equation_overlay


ART_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = ART_DIR / "instagram" / "phone-9x16"

EDITIONS = {
    "lorenz": {
        "input": REPO_ROOT / "attractors/lorenz/instagram/phone-9x16/lorenz_ember-garden_black_1080x1920_12s_30fps.mp4",
        "output": "lorenz_ember-garden_equation-edition_1080x1920_12s_30fps.mp4",
        "duration": 12,
        "equation": (
            "dx/dt = σ (y - x)",
            "dy/dt = x (ρ - z) - y",
            "dz/dt = x y - β z",
            "",
            "σ = 10    ρ = 28",
            "β = 8/3",
        ),
    },
    "halvorsen": {
        "input": REPO_ROOT / "attractors/halvorsen/instagram/phone-9x16/halvorsen_alpha-1.4_electric-citrus_black_1080x1920_12s_30fps.mp4",
        "output": "halvorsen_electric-citrus_equation-edition_1080x1920_12s_30fps.mp4",
        "duration": 12,
        "equation": (
            "dx/dt = -α x - 4y - 4z - y^2",
            "dy/dt = -α y - 4z - 4x - z^2",
            "dz/dt = -α z - 4x - 4y - x^2",
            "",
            "α = 1.4",
        ),
    },
    "aizawa": {
        "input": REPO_ROOT / "attractors/aizawa/instagram/phone-9x16/aizawa_orchid-gold_black_1080x1920_12s_30fps.mp4",
        "output": "aizawa_orchid-gold_equation-edition_1080x1920_12s_30fps.mp4",
        "duration": 12,
        "equation": (
            "dx/dt = (z-b)x - d y",
            "dy/dt = d x + (z-b)y",
            "dz/dt = c + a z - z^3/3",
            "        - (x^2+y^2)(1+e z) + f z x^3",
            "",
            "a=0.95  b=0.7   c=0.6",
            "d=3.5   e=0.25  f=0.1",
        ),
    },
}


def codec_options(ffmpeg: str) -> list[str]:
    encoders = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, check=True).stdout
    if " libx264 " in encoders:
        return ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high"]
    if " libopenh264 " in encoders:
        return ["-c:v", "libopenh264", "-threads", "1", "-b:v", "12M", "-maxrate", "16M"]
    raise RuntimeError("No H.264 encoder is available in ffmpeg.")


def render_edition(name: str, output_dir: Path, font_size: int) -> Path:
    edition = EDITIONS[name]
    input_path = Path(edition["input"])
    if not input_path.exists():
        raise FileNotFoundError(f"Source MP4 not found: {input_path}")
    output = output_dir / str(edition["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to export MP4 files.")

    with tempfile.TemporaryDirectory(prefix="science-art-equation-") as temporary_dir:
        overlay_path = Path(temporary_dir) / f"{name}.png"
        make_equation_overlay(1080, 1920, edition["equation"], font_size=font_size).save(overlay_path)
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(input_path),
            "-loop",
            "1",
            "-i",
            str(overlay_path),
            "-filter_complex",
            "[0:v][1:v]overlay=0:0:format=auto[v]",
            "-map",
            "[v]",
            "-an",
            *codec_options(ffmpeg),
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-t",
            str(edition["duration"]),
            str(output),
        ]
        subprocess.run(command, check=True)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", choices=sorted(EDITIONS))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--font-size", type=int, default=22)
    return parser.parse_args()


if __name__ == "__main__":
    options = parse_args()
    names = [options.edition] if options.edition else ["lorenz", "halvorsen", "aizawa"]
    for edition_name in names:
        print(f"Saved {render_edition(edition_name, options.output_dir, options.font_size)}")
