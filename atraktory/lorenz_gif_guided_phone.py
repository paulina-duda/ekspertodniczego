#!/usr/bin/env python3
"""Generate a vertical neon phone GIF of a guided Lorenz attractor.

This is a separate fourth variant. It keeps the guided line-following idea, but
uses a 9:16 frame, pure black background, and a neon palette.
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


def build_neon_palette() -> list[tuple[int, int, int]]:
    palette = [(0, 0, 0)]
    stops = [
        (0, 245, 255),
        (0, 108, 255),
        (142, 40, 255),
        (255, 0, 190),
        (255, 65, 70),
        (255, 238, 0),
        (255, 255, 255),
    ]

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


def project_phone_points(
    points: np.ndarray,
    angle: float,
    tilt: float,
    phone_roll: float,
    width: int,
    height: int,
) -> np.ndarray:
    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]

    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    rotated_x = x * cos_a - y * sin_a
    rotated_y = x * sin_a + y * cos_a

    cos_t = math.cos(tilt)
    sin_t = math.sin(tilt)
    tilted_y = rotated_y * cos_t - z * sin_t
    tilted_z = rotated_y * sin_t + z * cos_t

    perspective = 1.0 / (1.0 + 0.22 * tilted_z)
    projected_x = rotated_x * perspective
    projected_y = -tilted_y * perspective

    cos_r = math.cos(phone_roll)
    sin_r = math.sin(phone_roll)
    phone_x = projected_x * cos_r - projected_y * sin_r
    phone_y = projected_x * sin_r + projected_y * cos_r

    margin = max(28, int(min(width, height) * 0.07))
    span_x = float(phone_x.max() - phone_x.min())
    span_y = float(phone_y.max() - phone_y.min())
    scale = min((width - 2 * margin) / span_x, (height - 2 * margin) / span_y)

    center_x = (phone_x.max() + phone_x.min()) * 0.5
    center_y = (phone_y.max() + phone_y.min()) * 0.5
    screen_x = width * 0.5 + (phone_x - center_x) * scale
    screen_y = height * 0.5 + (phone_y - center_y) * scale
    return np.column_stack((screen_x, screen_y)).astype(np.int32)


def render_phone_frame(
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
        color = 24 + int(age * 118)
        draw_line(
            canvas,
            (int(path[i, 0]), int(path[i, 1])),
            (int(path[i + 1, 0]), int(path[i + 1, 1])),
            min(color, 154),
            line_thickness,
        )

    tail_start = max(0, segment_count - focus_tail)
    tail_count = max(1, segment_count - tail_start)
    for local_index, i in enumerate(range(tail_start, segment_count)):
        age = local_index / tail_count
        color = 148 + int(age * 107)
        draw_line(
            canvas,
            (int(path[i, 0]), int(path[i, 1])),
            (int(path[i + 1, 0]), int(path[i + 1, 1])),
            min(color, 255),
            line_thickness + int(age > 0.76),
        )

    head_x, head_y = path[-1]
    set_pixel(canvas, int(head_x), int(head_y), 255, max(5, line_thickness + 4))
    return canvas


def write_streamed_gif(
    output: Path,
    points: np.ndarray,
    palette: list[tuple[int, int, int]],
    args: argparse.Namespace,
) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("Nie znaleziono ffmpeg.")

    palette_array = np.array(palette, dtype=np.uint8)
    start_angle = math.radians(args.angle_degrees)
    rotation_angle = math.radians(args.rotation_degrees)
    tilt = math.radians(args.tilt_degrees)
    phone_roll = math.radians(args.phone_roll_degrees)

    with tempfile.TemporaryDirectory(prefix="lorenz_phone_frames_") as temp_dir:
        temp_path = Path(temp_dir)
        frame_pattern = str(temp_path / "frame_%04d.ppm")
        palette_path = temp_path / "palette.png"

        for index in range(args.frames):
            frame = render_phone_frame(
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
            rgb_frame = palette_array[frame]
            frame_path = temp_path / f"frame_{index:04d}.ppm"
            with frame_path.open("wb") as handle:
                handle.write(f"P6\n{args.width} {args.height}\n255\n".encode("ascii"))
                handle.write(rgb_frame.tobytes())

        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(args.fps),
                "-i",
                frame_pattern,
                "-vf",
                "palettegen=max_colors=256:reserve_transparent=0",
                str(palette_path),
            ],
            check=True,
        )
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(args.fps),
                "-i",
                frame_pattern,
                "-i",
                str(palette_path),
                "-filter_complex",
                "paletteuse=dither=sierra2_4a",
                str(output),
            ],
            check=True,
        )


def parse_args() -> argparse.Namespace:
    default_output = Path(__file__).with_name("lorenz_attractor_guided_phone.gif")
    parser = argparse.ArgumentParser(description="Create a vertical neon Lorenz attractor GIF.")
    parser.add_argument("-o", "--output", type=Path, default=default_output)
    parser.add_argument("--width", type=int, default=720)
    parser.add_argument("--height", type=int, default=1280)
    parser.add_argument("--frames", type=int, default=480)
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
    args.output.parent.mkdir(parents=True, exist_ok=True)

    raw_points = integrate_lorenz(steps=args.steps + args.warmup_steps, dt=args.dt)
    points = normalize_points(raw_points[args.warmup_steps :])
    write_streamed_gif(args.output, points, build_neon_palette(), args)
    print(f"Zapisano GIF: {args.output}")


if __name__ == "__main__":
    main()
