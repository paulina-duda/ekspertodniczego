#!/usr/bin/env python3
"""Generate a full-HD vertical neon Lorenz attractor GIF.

This fifth variant is independent from `lorenz_gif_guided_phone.py`: it uses a
1080x1920 phone frame, configurable dark background, and neon palettes. GIF
encoding is streamed through ffmpeg, so it avoids writing thousands of large
temporary frame files.
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from lorenz_gif_basic import draw_line, integrate_lorenz, normalize_points, set_pixel
from lorenz_gif_guided_phone import project_phone_points


PALETTE_STOPS = {
    "electric_citrus": [
        (0, 255, 126),
        (106, 255, 0),
        (246, 255, 0),
        (255, 150, 0),
        (255, 24, 112),
        (184, 42, 255),
        (84, 236, 255),
        (255, 255, 255),
    ],
    "solar_spectrum": [
        (255, 0, 128),
        (255, 46, 64),
        (255, 126, 0),
        (255, 232, 48),
        (132, 255, 56),
        (0, 246, 255),
        (255, 255, 255),
    ],
}

BACKGROUNDS = {
    "black": (0, 0, 0),
    "steel": (22, 29, 36),
    "deep_teal": (4, 30, 34),
    "graphite": (14, 16, 21),
}


def build_neon_palette(name: str, background: str) -> list[tuple[int, int, int]]:
    palette = [BACKGROUNDS[background]]
    stops = PALETTE_STOPS[name]

    for i in range(255):
        t = i / 254.0
        segment = min(int(t * (len(stops) - 1)), len(stops) - 2)
        local_t = t * (len(stops) - 1) - segment
        start = stops[segment]
        end = stops[segment + 1]
        palette.append(
            tuple(
                int(start[channel] + (end[channel] - start[channel]) * local_t)
                for channel in range(3)
            )
        )

    return palette


def render_hd_frame(
    points: np.ndarray,
    frame_index: int,
    frame_count: int,
    width: int,
    height: int,
    line_thickness: int,
    focus_tail: int,
    start_angle: float,
    rotation_angle: float,
    tilt: float,
    phone_roll: float,
) -> np.ndarray:
    canvas = np.zeros((height, width), dtype=np.uint8)
    progress = (frame_index + 1) / frame_count
    angle = start_angle + rotation_angle * progress
    projected = project_phone_points(points, angle, tilt, phone_roll, width, height)
    end = max(2, int(progress * (len(projected) - 1)))
    path = projected[: end + 1]
    segment_count = max(1, len(path) - 1)

    for i in range(segment_count):
        age = i / segment_count
        color = 20 + int(age * 118)
        draw_line(
            canvas,
            (int(path[i, 0]), int(path[i, 1])),
            (int(path[i + 1, 0]), int(path[i + 1, 1])),
            min(color, 148),
            line_thickness,
        )

    tail_start = max(0, segment_count - focus_tail)
    tail_count = max(1, segment_count - tail_start)
    for local_index, i in enumerate(range(tail_start, segment_count)):
        age = local_index / tail_count
        color = 145 + int(age * 110)
        draw_line(
            canvas,
            (int(path[i, 0]), int(path[i, 1])),
            (int(path[i + 1, 0]), int(path[i + 1, 1])),
            min(color, 255),
            line_thickness + int(age > 0.80),
        )

    head_x, head_y = path[-1]
    set_pixel(canvas, int(head_x), int(head_y), 255, max(6, line_thickness + 4))
    return canvas


def stream_frames_to_ffmpeg(
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
            frame = render_hd_frame(
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


def run_rawvideo_ffmpeg(command: list[str], points: np.ndarray, palette_array: np.ndarray, args: argparse.Namespace) -> None:
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    stream_frames_to_ffmpeg(process, points, palette_array, args)
    return_code = process.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)


def write_hd_gif(
    output: Path,
    points: np.ndarray,
    palette: list[tuple[int, int, int]],
    args: argparse.Namespace,
) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("Nie znaleziono ffmpeg.")

    palette_array = np.array(palette, dtype=np.uint8)
    frame_size = f"{args.width}x{args.height}"

    with tempfile.TemporaryDirectory(prefix="lorenz_phone_hd_") as temp_dir:
        palette_path = Path(temp_dir) / "palette.png"

        palette_command = [
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
            "-vf",
            "palettegen=max_colors=256:reserve_transparent=0",
            str(palette_path),
        ]
        run_rawvideo_ffmpeg(palette_command, points, palette_array, args)

        gif_command = [
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
            "-i",
            str(palette_path),
            "-filter_complex",
            "paletteuse=dither=sierra2_4a",
            str(output),
        ]
        run_rawvideo_ffmpeg(gif_command, points, palette_array, args)


def parse_args() -> argparse.Namespace:
    default_output = Path(__file__).with_name("lorenz_attractor_guided_phone_hd.gif")
    parser = argparse.ArgumentParser(description="Create a full-HD vertical neon Lorenz GIF.")
    parser.add_argument("-o", "--output", type=Path, default=default_output)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--frames", type=int, default=360)
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--steps", type=int, default=11000)
    parser.add_argument("--warmup-steps", type=int, default=1500)
    parser.add_argument("--dt", type=float, default=0.006)
    parser.add_argument("--angle-degrees", type=float, default=180.0)
    parser.add_argument("--rotation-degrees", type=float, default=180.0)
    parser.add_argument("--tilt-degrees", type=float, default=58.0)
    parser.add_argument("--phone-roll-degrees", type=float, default=-90.0)
    parser.add_argument("--line-thickness", type=int, default=1)
    parser.add_argument("--focus-tail", type=int, default=420)
    parser.add_argument("--palette", choices=sorted(PALETTE_STOPS), default="electric_citrus")
    parser.add_argument("--background", choices=sorted(BACKGROUNDS), default="steel")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    raw_points = integrate_lorenz(steps=args.steps + args.warmup_steps, dt=args.dt)
    points = normalize_points(raw_points[args.warmup_steps :])
    write_hd_gif(args.output, points, build_neon_palette(args.palette, args.background), args)
    print(f"Zapisano GIF: {args.output}")


if __name__ == "__main__":
    main()
