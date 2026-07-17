#!/usr/bin/env python3
"""Generate review GIFs for Lorenz attractor color palettes."""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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
    "velvet_signal": [
        (79, 255, 209),
        (27, 191, 255),
        (96, 96, 255),
        (218, 72, 255),
        (255, 75, 156),
        (255, 183, 77),
        (255, 255, 245),
    ],
    "copper_lagoon": [
        (64, 255, 188),
        (18, 215, 189),
        (0, 142, 176),
        (96, 93, 255),
        (255, 92, 151),
        (255, 145, 59),
        (255, 237, 184),
        (255, 255, 255),
    ],
}

BACKGROUNDS = {
    "black": (0, 0, 0),
    "steel": (22, 29, 36),
    "deep_teal": (4, 30, 34),
    "graphite": (14, 16, 21),
}

REVIEW_PRESETS = [
    ("electric_citrus", "steel"),
    ("solar_spectrum", "steel"),
    ("velvet_signal", "deep_teal"),
    ("copper_lagoon", "steel"),
]


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


def render_frame(
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


def run_rawvideo_ffmpeg(
    command: list[str],
    points: np.ndarray,
    palette_array: np.ndarray,
    args: argparse.Namespace,
) -> None:
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    stream_frames_to_ffmpeg(process, points, palette_array, args)
    return_code = process.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)


def write_gif(
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

    with tempfile.TemporaryDirectory(prefix="lorenz_palette_review_") as temp_dir:
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
            "-frames:v",
            "1",
            "-update",
            "1",
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


def print_color_list() -> None:
    print("Palety:")
    for name, stops in PALETTE_STOPS.items():
        hex_colors = ["#%02X%02X%02X" % color for color in stops]
        print(f"- {name}: {', '.join(hex_colors)}")

    print("\nTla:")
    for name, color in BACKGROUNDS.items():
        print("- %s: #%02X%02X%02X" % (name, *color))


def parse_args() -> argparse.Namespace:
    default_output_dir = ROOT_DIR / "gify"
    parser = argparse.ArgumentParser(description="Create Lorenz palette review GIFs.")
    parser.add_argument("-o", "--output-dir", type=Path, default=default_output_dir)
    parser.add_argument("--palette", choices=sorted(PALETTE_STOPS), default="electric_citrus")
    parser.add_argument("--background", choices=sorted(BACKGROUNDS), default="steel")
    parser.add_argument("--all-presets", action="store_true")
    parser.add_argument("--list-colors", action="store_true")
    parser.add_argument("--width", type=int, default=720)
    parser.add_argument("--height", type=int, default=1280)
    parser.add_argument("--frames", type=int, default=180)
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.list_colors:
        print_color_list()
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_points = integrate_lorenz(steps=args.steps + args.warmup_steps, dt=args.dt)
    points = normalize_points(raw_points[args.warmup_steps :])

    presets = REVIEW_PRESETS if args.all_presets else [(args.palette, args.background)]
    for palette_name, background_name in presets:
        output = args.output_dir / f"lorenz_{palette_name}_{background_name}.gif"
        palette = build_neon_palette(palette_name, background_name)
        write_gif(output, points, palette, args)
        print(f"Zapisano GIF: {output}")


if __name__ == "__main__":
    main()
