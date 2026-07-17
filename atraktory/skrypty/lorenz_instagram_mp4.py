#!/usr/bin/env python3
"""Generate Instagram-ready MP4 variants of the Lorenz attractor."""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parents[0]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from lorenz_gif_basic import integrate_lorenz, normalize_points
from lorenz_palette_gifs import (
    BACKGROUNDS,
    PALETTE_STOPS,
    build_neon_palette,
    render_frame,
)


INSTAGRAM_PRESETS = [
    ("electric_citrus", "steel"),
    ("solar_spectrum", "steel"),
    ("velvet_signal", "deep_teal"),
    ("copper_lagoon", "graphite"),
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
        return [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-profile:v",
            "high",
        ]
    if " libopenh264 " in encoders:
        return [
            "-c:v",
            "libopenh264",
            "-b:v",
            "12M",
            "-maxrate",
            "16M",
        ]
    raise RuntimeError("Nie znaleziono enkodera H.264: libx264 ani libopenh264.")


def stream_rgb_frames(
    process: subprocess.Popen[bytes],
    points: np.ndarray,
    palette_array: np.ndarray,
    args: argparse.Namespace,
) -> None:
    start_angle = math.radians(args.angle_degrees)
    rotation_angle = math.radians(args.rotation_degrees)
    tilt = math.radians(args.tilt_degrees)
    phone_roll = math.radians(args.phone_roll_degrees)

    assert process.stdin is not None
    try:
        for index in range(args.frames):
            frame = render_frame(
                points,
                index,
                args.frames,
                args.width,
                args.height,
                args.line_thickness,
                args.focus_tail,
                start_angle,
                rotation_angle,
                tilt,
                phone_roll,
            )
            process.stdin.write(palette_array[frame].tobytes())
    finally:
        process.stdin.close()


def write_mp4(
    output: Path,
    points: np.ndarray,
    palette: list[tuple[int, int, int]],
    args: argparse.Namespace,
) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("Nie znaleziono ffmpeg.")

    output.parent.mkdir(parents=True, exist_ok=True)
    palette_array = np.array(palette, dtype=np.uint8)
    frame_size = f"{args.width}x{args.height}"
    encoder_args = choose_h264_encoder(ffmpeg)

    command = [
        ffmpeg,
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        frame_size,
        "-r",
        str(args.fps),
        "-i",
        "-",
        "-an",
        *encoder_args,
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    stream_rgb_frames(process, points, palette_array, args)
    return_code = process.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Instagram-ready Lorenz MP4 files.")
    parser.add_argument("-o", "--output-dir", type=Path, default=ROOT_DIR / "instagram_mp4")
    parser.add_argument("--palette", choices=sorted(PALETTE_STOPS), default="electric_citrus")
    parser.add_argument("--background", choices=sorted(BACKGROUNDS), default="steel")
    parser.add_argument("--all-presets", action="store_true")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--duration", type=float, default=6.0)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--steps", type=int, default=11000)
    parser.add_argument("--warmup-steps", type=int, default=1500)
    parser.add_argument("--dt", type=float, default=0.006)
    parser.add_argument("--angle-degrees", type=float, default=180.0)
    parser.add_argument("--rotation-degrees", type=float, default=180.0)
    parser.add_argument("--tilt-degrees", type=float, default=58.0)
    parser.add_argument("--phone-roll-degrees", type=float, default=-90.0)
    parser.add_argument("--line-thickness", type=int, default=2)
    parser.add_argument("--focus-tail", type=int, default=520)
    args = parser.parse_args()
    args.frames = max(1, round(args.duration * args.fps))
    return args


def main() -> None:
    args = parse_args()
    raw_points = integrate_lorenz(steps=args.steps + args.warmup_steps, dt=args.dt)
    points = normalize_points(raw_points[args.warmup_steps :])

    presets = INSTAGRAM_PRESETS if args.all_presets else [(args.palette, args.background)]
    for palette_name, background_name in presets:
        size_label = f"{args.width}x{args.height}_{args.fps}fps"
        output = args.output_dir / f"lorenz_{palette_name}_{background_name}_{size_label}.mp4"
        palette = build_neon_palette(palette_name, background_name)
        write_mp4(output, points, palette, args)
        print(f"Zapisano MP4: {output}")


if __name__ == "__main__":
    main()
