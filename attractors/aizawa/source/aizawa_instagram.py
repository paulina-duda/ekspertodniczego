#!/usr/bin/env python3
"""Render full-screen 9:16 Aizawa attractor MP4 videos for Instagram."""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "instagram" / "phone-9x16"

PALETTES = {
    "ember-garden": [
        (71, 255, 48), (172, 255, 38), (255, 239, 45), (255, 172, 26),
        (255, 83, 34), (255, 34, 96), (255, 236, 192), (255, 255, 255),
    ],
    "orchid-gold": [
        (246, 255, 72), (255, 210, 50), (255, 143, 35), (255, 72, 64),
        (255, 38, 137), (214, 58, 196), (255, 208, 135), (255, 255, 255),
    ],
    "electric-citrus": [
        (0, 255, 126), (106, 255, 0), (246, 255, 0), (255, 150, 0),
        (255, 24, 112), (184, 42, 255), (84, 236, 255), (255, 255, 255),
    ],
    "velvet-signal": [
        (79, 255, 209), (27, 191, 255), (96, 96, 255), (218, 72, 255),
        (255, 75, 156), (255, 183, 77), (255, 255, 245),
    ],
}


def build_palette(stops: list[tuple[int, int, int]]) -> np.ndarray:
    palette = np.zeros((256, 3), dtype=np.uint8)
    for index in range(1, 256):
        position = (index - 1) / 254
        segment = min(int(position * (len(stops) - 1)), len(stops) - 2)
        local_position = position * (len(stops) - 1) - segment
        start, end = stops[segment], stops[segment + 1]
        palette[index] = [
            int(start[channel] + (end[channel] - start[channel]) * local_position)
            for channel in range(3)
        ]
    return palette


def aizawa_derivative(point: np.ndarray) -> np.ndarray:
    x, y, z = point
    a, b, c, d, e, f = 0.95, 0.7, 0.6, 3.5, 0.25, 0.1
    return np.array((
        (z - b) * x - d * y,
        d * x + (z - b) * y,
        c + a * z - z**3 / 3 - (x**2 + y**2) * (1 + e * z) + f * z * x**3,
    ))


def integrate_aizawa(steps: int, dt: float) -> np.ndarray:
    points = np.empty((steps, 3), dtype=np.float64)
    points[0] = (0.1, 0.0, 0.0)
    for index in range(1, steps):
        point = points[index - 1]
        k1 = aizawa_derivative(point)
        k2 = aizawa_derivative(point + 0.5 * dt * k1)
        k3 = aizawa_derivative(point + 0.5 * dt * k2)
        k4 = aizawa_derivative(point + dt * k3)
        points[index] = point + (dt / 6) * (k1 + 2 * k2 + 2 * k3 + k4)
    return points


def normalise(points: np.ndarray) -> np.ndarray:
    minimum, maximum = points.min(axis=0), points.max(axis=0)
    return (points - (minimum + maximum) * 0.5) / (np.max(maximum - minimum) * 0.5)


def project_to_phone(points: np.ndarray, angle: float, width: int, height: int) -> np.ndarray:
    x, y, z = points.T
    cosine, sine = math.cos(angle), math.sin(angle)
    rotated_x, rotated_y = x * cosine - y * sine, x * sine + y * cosine
    tilt_cosine, tilt_sine = math.cos(math.radians(28)), math.sin(math.radians(28))
    screen_y = rotated_y * tilt_cosine - z * tilt_sine
    depth = rotated_y * tilt_sine + z * tilt_cosine
    perspective = 1 / (1 + 0.18 * depth)
    projected_x, projected_y = rotated_x * perspective, -screen_y * perspective
    margin = int(min(width, height) * 0.07)
    scale = min(
        (width - 2 * margin) / (projected_x.max() - projected_x.min()),
        (height - 2 * margin) / (projected_y.max() - projected_y.min()),
    )
    return np.column_stack((
        width * 0.5 + (projected_x - (projected_x.max() + projected_x.min()) * 0.5) * scale,
        height * 0.5 + (projected_y - (projected_y.max() + projected_y.min()) * 0.5) * scale,
    )).astype(np.int32)


def render_mask(points: np.ndarray, frame_index: int, frame_count: int, width: int, height: int) -> np.ndarray:
    progress = (frame_index + 1) / frame_count
    path = project_to_phone(points, math.radians(35) + math.tau * progress, width, height)
    path = path[: max(3, int(progress * (len(path) - 1)) + 1)]
    image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(image)
    boundaries = np.linspace(0, len(path) - 1, 33, dtype=int)
    for index, (start, end) in enumerate(zip(boundaries[:-1], boundaries[1:])):
        intensity = 25 + int(125 * index / 31)
        if index >= 25:
            intensity = 150 + int(105 * (index - 25) / 6)
        draw.line([tuple(point) for point in path[start : end + 1]], fill=intensity, width=2)
    head_x, head_y = path[-1]
    draw.ellipse((head_x - 3, head_y - 3, head_x + 3, head_y + 3), fill=255)
    return np.asarray(image)


def write_all(stream: object, data: bytes) -> None:
    """Write a complete raw-video frame even if the pipe accepts it in chunks."""
    remaining = memoryview(data)
    while remaining:
        written = stream.write(remaining)  # type: ignore[attr-defined]
        if written is None:
            continue
        remaining = remaining[written:]


def write_frames(process: subprocess.Popen[bytes], points: np.ndarray, colour_map: np.ndarray, args: argparse.Namespace) -> None:
    assert process.stdin is not None
    try:
        for frame_index in range(args.frames):
            mask = render_mask(points, frame_index, args.frames, args.width, args.height)
            write_all(process.stdin, colour_map[mask].tobytes())
    finally:
        process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError("ffmpeg failed while exporting the MP4.")


def write_mp4(output: Path, points: np.ndarray, colour_map: np.ndarray, args: argparse.Namespace) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to export MP4 files.")
    encoders = subprocess.run(
        [ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, check=True
    ).stdout
    if " libx264 " in encoders:
        codec_options = ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high"]
    elif " libopenh264 " in encoders:
        codec_options = ["-c:v", "libopenh264", "-threads", "1", "-b:v", "12M", "-maxrate", "16M"]
    else:
        raise RuntimeError("No H.264 encoder is available in ffmpeg.")
    output.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{args.width}x{args.height}", "-r", str(args.fps), "-i", "-", "-an", *codec_options,
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
        ],
        stdin=subprocess.PIPE,
    )
    write_frames(process, points, colour_map, args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--palette", choices=sorted(PALETTES), default="ember-garden")
    parser.add_argument("--all-palettes", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--duration", type=float, default=12)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--steps", type=int, default=30000)
    parser.add_argument("--warmup-steps", type=int, default=5000)
    parser.add_argument("--dt", type=float, default=0.003)
    args = parser.parse_args()
    args.frames = round(args.duration * args.fps)
    return args


if __name__ == "__main__":
    options = parse_args()
    trajectory = normalise(integrate_aizawa(options.steps + options.warmup_steps, options.dt)[options.warmup_steps :])
    selected_palettes = sorted(PALETTES) if options.all_palettes else [options.palette]
    for palette_name in selected_palettes:
        output_path = options.output_dir / f"aizawa_{palette_name}_black_{options.width}x{options.height}_{options.duration:.0f}s_{options.fps}fps.mp4"
        write_mp4(output_path, trajectory, build_palette(PALETTES[palette_name]), options)
        print(f"Saved {output_path}")
