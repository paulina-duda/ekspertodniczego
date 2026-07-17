#!/usr/bin/env python3
"""Generate a slower, guided raster GIF of the Lorenz attractor.

This third version keeps the lightweight renderer from `lorenz_gif_basic.py`,
but changes the pacing and drawing style so the viewer can follow the active
tip of the curve as the attractor forms.
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from lorenz_gif_basic import (
    build_palette,
    draw_line,
    integrate_lorenz,
    normalize_points,
    project_points,
    set_pixel,
)


def render_guided_frame(
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
) -> np.ndarray:
    canvas = np.zeros((height, width), dtype=np.uint8)
    progress = (frame_index + 1) / frame_count
    angle = start_angle + rotation_angle * progress
    projected = project_points(points, angle, tilt, width, height)
    end = max(2, int(progress * (len(projected) - 1)))
    path = projected[: end + 1]
    segment_count = max(1, len(path) - 1)

    # The already-drawn trace stays visible but quieter; the viewer's eye is
    # pulled toward the fresh segment and the bright moving tip.
    for i in range(segment_count):
        age = i / segment_count
        color = 42 + int(age * 115)
        draw_line(
            canvas,
            (int(path[i, 0]), int(path[i, 1])),
            (int(path[i + 1, 0]), int(path[i + 1, 1])),
            min(color, 170),
            line_thickness,
        )

    tail_start = max(0, segment_count - focus_tail)
    tail_count = max(1, segment_count - tail_start)
    for local_index, i in enumerate(range(tail_start, segment_count)):
        age = local_index / tail_count
        color = 155 + int(age * 100)
        draw_line(
            canvas,
            (int(path[i, 0]), int(path[i, 1])),
            (int(path[i + 1, 0]), int(path[i + 1, 1])),
            min(color, 255),
            line_thickness + int(age > 0.72),
        )

    head_x, head_y = path[-1]
    set_pixel(canvas, int(head_x), int(head_y), 255, max(5, line_thickness + 4))
    return canvas


def write_guided_gif(
    path: Path,
    frames: list[np.ndarray],
    palette: list[tuple[int, int, int]],
    fps: int,
) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("Nie znaleziono ffmpeg, a ten wariant używa go do składania dłuższego GIF-a.")

    height, width = frames[0].shape
    palette_array = np.array(palette, dtype=np.uint8)

    with tempfile.TemporaryDirectory(prefix="lorenz_guided_frames_") as temp_dir:
        temp_path = Path(temp_dir)
        frame_pattern = str(temp_path / "frame_%04d.ppm")
        palette_path = temp_path / "palette.png"

        for index, frame in enumerate(frames):
            frame_path = temp_path / f"frame_{index:04d}.ppm"
            rgb_frame = palette_array[frame]
            with frame_path.open("wb") as handle:
                handle.write(f"P6\n{width} {height}\n255\n".encode("ascii"))
                handle.write(rgb_frame.tobytes())

        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(fps),
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
                str(fps),
                "-i",
                frame_pattern,
                "-i",
                str(palette_path),
                "-filter_complex",
                "paletteuse=dither=sierra2_4a",
                str(path),
            ],
            check=True,
        )


def parse_args() -> argparse.Namespace:
    default_output = Path(__file__).with_name("lorenz_attractor_guided.gif")
    parser = argparse.ArgumentParser(description="Create a guided Lorenz attractor GIF.")
    parser.add_argument("-o", "--output", type=Path, default=default_output)
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--frames", type=int, default=480)
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--steps", type=int, default=11000)
    parser.add_argument("--warmup-steps", type=int, default=1500)
    parser.add_argument("--dt", type=float, default=0.006)
    parser.add_argument("--angle-degrees", type=float, default=180.0)
    parser.add_argument("--rotation-degrees", type=float, default=180.0)
    parser.add_argument("--tilt-degrees", type=float, default=58.0)
    parser.add_argument("--line-thickness", type=int, default=1)
    parser.add_argument("--focus-tail", type=int, default=380)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    raw_points = integrate_lorenz(steps=args.steps + args.warmup_steps, dt=args.dt)
    points = normalize_points(raw_points[args.warmup_steps :])
    start_angle = math.radians(args.angle_degrees)
    rotation_angle = math.radians(args.rotation_degrees)
    tilt = math.radians(args.tilt_degrees)
    palette = build_palette()

    frames = [
        render_guided_frame(
            points,
            i,
            args.frames,
            args.width,
            args.height,
            args.line_thickness,
            args.focus_tail,
            start_angle,
            rotation_angle,
            tilt,
        )
        for i in range(args.frames)
    ]

    write_guided_gif(args.output, frames, palette, fps=args.fps)
    print(f"Zapisano GIF: {args.output}")


if __name__ == "__main__":
    main()
