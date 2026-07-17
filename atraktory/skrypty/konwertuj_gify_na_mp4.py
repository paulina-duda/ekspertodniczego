#!/usr/bin/env python3
"""Convert already approved Lorenz GIFs to visually identical MP4 files."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = ROOT_DIR / "gify"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "mp4_jak_gify"


def available_encoders(ffmpeg: str) -> str:
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-encoders"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def choose_h264_encoder(ffmpeg: str) -> list[str]:
    encoders = available_encoders(ffmpeg)
    if " libx264 " in encoders:
        return ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high"]
    if " libopenh264 " in encoders:
        return ["-c:v", "libopenh264", "-b:v", "10M", "-maxrate", "14M"]
    raise RuntimeError("Nie znaleziono enkodera H.264: libx264 ani libopenh264.")


def convert_gif(ffmpeg: str, input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-an",
        *choose_h264_encoder(ffmpeg),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Lorenz GIFs to MP4 without changing the animation.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("-o", "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("Nie znaleziono ffmpeg.")

    gifs = sorted(args.input_dir.glob("*.gif"))
    if not gifs:
        raise RuntimeError(f"Nie znaleziono GIF-ow w: {args.input_dir}")

    for gif_path in gifs:
        output_path = args.output_dir / gif_path.with_suffix(".mp4").name
        convert_gif(ffmpeg, gif_path, output_path)
        print(f"Zapisano MP4: {output_path}")


if __name__ == "__main__":
    main()
