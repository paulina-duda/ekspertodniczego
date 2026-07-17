#!/usr/bin/env python3
"""Generate a raster GIF of a Lorenz attractor without Manim.

This is the earlier lightweight generator: NumPy integrates the Lorenz system,
Python rasterizes the line, and ImageMagick (`magick` or `convert`) assembles
the frames into a GIF.
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np


def lorenz_derivative(point: np.ndarray, sigma: float, rho: float, beta: float) -> np.ndarray:
    x, y, z = point
    return np.array(
        [
            sigma * (y - x),
            x * (rho - z) - y,
            x * y - beta * z,
        ],
        dtype=np.float64,
    )


def integrate_lorenz(
    steps: int,
    dt: float,
    sigma: float = 10.0,
    rho: float = 28.0,
    beta: float = 8.0 / 3.0,
) -> np.ndarray:
    points = np.empty((steps, 3), dtype=np.float64)
    points[0] = np.array([0.1, 0.0, 0.0], dtype=np.float64)

    for i in range(1, steps):
        point = points[i - 1]
        k1 = lorenz_derivative(point, sigma, rho, beta)
        k2 = lorenz_derivative(point + 0.5 * dt * k1, sigma, rho, beta)
        k3 = lorenz_derivative(point + 0.5 * dt * k2, sigma, rho, beta)
        k4 = lorenz_derivative(point + dt * k3, sigma, rho, beta)
        points[i] = point + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

    return points


def normalize_points(points: np.ndarray) -> np.ndarray:
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    center = (mins + maxs) * 0.5
    scale = np.max(maxs - mins) * 0.5
    return (points - center) / scale


def project_points(
    points: np.ndarray,
    angle: float,
    tilt: float,
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

    margin = max(24, int(min(width, height) * 0.06))
    span_x = float(projected_x.max() - projected_x.min())
    span_y = float(projected_y.max() - projected_y.min())
    scale = min((width - 2 * margin) / span_x, (height - 2 * margin) / span_y)

    center_x = (projected_x.max() + projected_x.min()) * 0.5
    center_y = (projected_y.max() + projected_y.min()) * 0.5
    screen_x = width * 0.5 + (projected_x - center_x) * scale
    screen_y = height * 0.5 + (projected_y - center_y) * scale
    return np.column_stack((screen_x, screen_y)).astype(np.int32)


def build_palette() -> list[tuple[int, int, int]]:
    palette = [(4, 5, 8)]
    stops = [
        (18, 70, 150),
        (38, 205, 214),
        (255, 228, 86),
        (255, 98, 128),
        (245, 248, 255),
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


def set_pixel(canvas: np.ndarray, x: int, y: int, color: int, thickness: int) -> None:
    height, width = canvas.shape
    radius = thickness // 2

    for yy in range(y - radius, y + radius + 1):
        if yy < 0 or yy >= height:
            continue
        for xx in range(x - radius, x + radius + 1):
            if 0 <= xx < width:
                canvas[yy, xx] = color


def draw_line(
    canvas: np.ndarray,
    start: tuple[int, int],
    end: tuple[int, int],
    color: int,
    thickness: int,
) -> None:
    x0, y0 = start
    x1, y1 = end
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    error = dx + dy

    while True:
        set_pixel(canvas, x0, y0, color, thickness)
        if x0 == x1 and y0 == y1:
            break

        twice_error = 2 * error
        if twice_error >= dy:
            error += dy
            x0 += sx
        if twice_error <= dx:
            error += dx
            y0 += sy


def render_frame(
    points: np.ndarray,
    frame_index: int,
    frame_count: int,
    width: int,
    height: int,
    line_thickness: int,
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

    for i in range(segment_count):
        age = i / segment_count
        color = 45 + int(age * 210)
        draw_line(
            canvas,
            (int(path[i, 0]), int(path[i, 1])),
            (int(path[i + 1, 0]), int(path[i + 1, 1])),
            min(color, 255),
            line_thickness,
        )

    head_x, head_y = path[-1]
    set_pixel(canvas, int(head_x), int(head_y), 255, max(3, line_thickness + 2))
    return canvas


def write_gif(
    path: Path,
    frames: list[np.ndarray],
    palette: list[tuple[int, int, int]],
    fps: int,
) -> None:
    height, width = frames[0].shape
    delay = max(1, round(100 / fps))
    encoder = shutil.which("magick") or shutil.which("convert")
    if encoder is None:
        raise RuntimeError("Nie znaleziono ImageMagick. Zainstaluj polecenie 'magick' albo 'convert'.")

    palette_array = np.array(palette, dtype=np.uint8)

    with tempfile.TemporaryDirectory(prefix="lorenz_frames_") as temp_dir:
        temp_path = Path(temp_dir)
        frame_paths = []

        for index, frame in enumerate(frames):
            frame_path = temp_path / f"frame_{index:04d}.ppm"
            rgb_frame = palette_array[frame]
            with frame_path.open("wb") as handle:
                handle.write(f"P6\n{width} {height}\n255\n".encode("ascii"))
                handle.write(rgb_frame.tobytes())
            frame_paths.append(str(frame_path))

        command = [
            encoder,
            "-delay",
            str(delay),
            "-loop",
            "0",
            *frame_paths,
            "-layers",
            "Optimize",
            str(path),
        ]
        subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    default_output = Path(__file__).with_name("lorenz_attractor_basic.gif")
    parser = argparse.ArgumentParser(description="Create a raster GIF of the Lorenz attractor.")
    parser.add_argument("-o", "--output", type=Path, default=default_output)
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--frames", type=int, default=200)
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--steps", type=int, default=11000)
    parser.add_argument("--warmup-steps", type=int, default=1500)
    parser.add_argument("--dt", type=float, default=0.006)
    parser.add_argument("--angle-degrees", type=float, default=180.0)
    parser.add_argument("--rotation-degrees", type=float, default=180.0)
    parser.add_argument("--tilt-degrees", type=float, default=58.0)
    parser.add_argument("--line-thickness", type=int, default=1)
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
        render_frame(
            points,
            i,
            args.frames,
            args.width,
            args.height,
            args.line_thickness,
            start_angle,
            rotation_angle,
            tilt,
        )
        for i in range(args.frames)
    ]

    write_gif(args.output, frames, palette, fps=args.fps)
    print(f"Zapisano GIF: {args.output}")


if __name__ == "__main__":
    main()
