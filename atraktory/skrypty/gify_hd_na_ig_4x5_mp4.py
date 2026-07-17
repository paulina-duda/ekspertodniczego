#!/usr/bin/env python3
"""Convert selected HD Lorenz GIFs to 4:5 Instagram MP4 files."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT_DIR / "ig_4x5_ultra_hd"
DEFAULT_INPUTS = [
    ROOT_DIR / "lorenz_attractor_guided_phone_hd.gif",
    ROOT_DIR / "lorenz_attractor_guided_phone_hd_synthwave.gif",
]


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
        return ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high"]
    if " libopenh264 " in encoders:
        return ["-c:v", "libopenh264", "-b:v", "24M", "-maxrate", "32M"]
    raise RuntimeError("Nie znaleziono enkodera H.264: libx264 ani libopenh264.")


def read_frame_count(ffprobe: str, input_path: Path) -> int:
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=nb_frames",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(input_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip())


def convert_gif(
    ffmpeg: str,
    ffprobe: str,
    input_path: Path,
    output_path: Path,
    args: argparse.Namespace,
) -> None:
    frame_count = read_frame_count(ffprobe, input_path)
    thumbnail_number = max(1, frame_count - args.thumbnail_from_end + 1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="lorenz_ig_4x5_") as temp_dir:
        temp_path = Path(temp_dir)
        extracted_dir = temp_path / "extracted"
        ordered_dir = temp_path / "ordered"
        extracted_dir.mkdir()
        ordered_dir.mkdir()

        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(input_path),
                str(extracted_dir / "frame_%04d.png"),
            ],
            check=True,
        )

        extracted_frames = sorted(extracted_dir.glob("frame_*.png"))
        if len(extracted_frames) != frame_count:
            raise RuntimeError(
                f"Oczekiwano {frame_count} klatek, znaleziono {len(extracted_frames)}: {input_path}"
            )

        ordered_sources = [
            extracted_dir / f"frame_{thumbnail_number:04d}.png",
            *[extracted_dir / f"frame_{index:04d}.png" for index in range(2, frame_count + 1)],
        ]

        for index, source in enumerate(ordered_sources, start=1):
            target = ordered_dir / f"frame_{index:04d}.png"
            try:
                os.link(source, target)
            except OSError:
                try:
                    target.symlink_to(source)
                except OSError:
                    shutil.copy2(source, target)

        filter_graph = (
            f"scale={args.width}:{args.height}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={args.width}:{args.height}:(ow-iw)/2:(oh-ih)/2:color={args.background},"
            "setsar=1,format=yuv420p"
        )

        command = [
            ffmpeg,
            "-y",
            "-framerate",
            str(args.fps),
            "-i",
            str(ordered_dir / "frame_%04d.png"),
            "-vf",
            filter_graph,
            "-frames:v",
            str(frame_count),
            "-an",
            *choose_h264_encoder(ffmpeg),
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create 4:5 IG MP4 files from selected HD Lorenz GIFs.")
    parser.add_argument("inputs", nargs="*", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("-o", "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--width", type=int, default=2160)
    parser.add_argument("--height", type=int, default=2700)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--thumbnail-from-end", type=int, default=20)
    parser.add_argument("--background", default="black")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None:
        raise RuntimeError("Nie znaleziono ffmpeg.")
    if ffprobe is None:
        raise RuntimeError("Nie znaleziono ffprobe.")

    for input_path in args.inputs:
        duration = read_frame_count(ffprobe, input_path) / args.fps
        size_label = f"{args.width}x{args.height}_{duration:.0f}s"
        output_path = args.output_dir / f"{input_path.stem}_ig_4x5_{size_label}.mp4"
        convert_gif(ffmpeg, ffprobe, input_path, output_path, args)
        print(f"Zapisano MP4: {output_path}")


if __name__ == "__main__":
    main()
