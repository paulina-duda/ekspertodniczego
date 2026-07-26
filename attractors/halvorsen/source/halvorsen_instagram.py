#!/usr/bin/env python3
"""Render 9:16 Halvorsen attractor MP4 videos for Instagram."""

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
    "ember-garden": [(71, 255, 48), (172, 255, 38), (255, 239, 45), (255, 172, 26), (255, 83, 34), (255, 34, 96), (255, 236, 192), (255, 255, 255)],
    "orchid-gold": [(246, 255, 72), (255, 210, 50), (255, 143, 35), (255, 72, 64), (255, 38, 137), (214, 58, 196), (255, 208, 135), (255, 255, 255)],
    "electric-citrus": [(0, 255, 126), (106, 255, 0), (246, 255, 0), (255, 150, 0), (255, 24, 112), (184, 42, 255), (84, 236, 255), (255, 255, 255)],
    "velvet-signal": [(79, 255, 209), (27, 191, 255), (96, 96, 255), (218, 72, 255), (255, 75, 156), (255, 183, 77), (255, 255, 245)],
}


def build_palette(stops: list[tuple[int, int, int]]) -> np.ndarray:
    palette = np.zeros((256, 3), dtype=np.uint8)
    for index in range(1, 256):
        position = (index - 1) / 254
        segment = min(int(position * (len(stops) - 1)), len(stops) - 2)
        fraction = position * (len(stops) - 1) - segment
        palette[index] = [int(start + (end - start) * fraction) for start, end in zip(stops[segment], stops[segment + 1])]
    return palette


def derivative(point: np.ndarray, alpha: float) -> np.ndarray:
    x, y, z = point
    return np.array((
        -alpha * x - 4 * y - 4 * z - y * y,
        -alpha * y - 4 * z - 4 * x - z * z,
        -alpha * z - 4 * x - 4 * y - x * x,
    ))


def integrate(steps: int, dt: float, alpha: float) -> np.ndarray:
    points = np.empty((steps, 3), dtype=np.float64)
    points[0] = (1.0, 0.0, 0.0)
    for index in range(1, steps):
        point = points[index - 1]
        k1 = derivative(point, alpha)
        k2 = derivative(point + 0.5 * dt * k1, alpha)
        k3 = derivative(point + 0.5 * dt * k2, alpha)
        k4 = derivative(point + dt * k3, alpha)
        points[index] = point + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    return points


def normalise(points: np.ndarray) -> np.ndarray:
    minimum, maximum = points.min(axis=0), points.max(axis=0)
    return (points - (minimum + maximum) * 0.5) / (np.max(maximum - minimum) * 0.5)


def project(points: np.ndarray, angle: float, width: int, height: int) -> np.ndarray:
    x, y, z = points.T
    cosine, sine = math.cos(angle), math.sin(angle)
    rotated_x, rotated_y = x * cosine - y * sine, x * sine + y * cosine
    tilt_cosine, tilt_sine = math.cos(math.radians(44)), math.sin(math.radians(44))
    screen_y = rotated_y * tilt_cosine - z * tilt_sine
    depth = rotated_y * tilt_sine + z * tilt_cosine
    perspective = 1 / (1 + 0.18 * depth)
    projected_x, projected_y = rotated_x * perspective, -screen_y * perspective
    margin = int(min(width, height) * 0.08)
    scale = min((width - 2 * margin) / np.ptp(projected_x), (height - 2 * margin) / np.ptp(projected_y))
    return np.column_stack((
        width * 0.5 + (projected_x - (projected_x.max() + projected_x.min()) * 0.5) * scale,
        height * 0.5 + (projected_y - (projected_y.max() + projected_y.min()) * 0.5) * scale,
    )).astype(np.int32)


def render_mask(points: np.ndarray, frame_index: int, frame_count: int, width: int, height: int) -> np.ndarray:
    progress = (frame_index + 1) / frame_count
    path = project(points, math.radians(30) + math.tau * progress, width, height)
    path = path[: max(3, int(progress * len(path)))]
    image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(image)
    boundaries = np.linspace(0, len(path) - 1, 33, dtype=int)
    for index, (start, end) in enumerate(zip(boundaries[:-1], boundaries[1:])):
        intensity = 25 + int(125 * index / 31)
        if index >= 25:
            intensity = 150 + int(105 * (index - 25) / 6)
        draw.line([tuple(point) for point in path[start:end + 1]], fill=intensity, width=3)
    x, y = path[-1]
    draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=255)
    return np.asarray(image)


def write_all(stream: object, data: bytes) -> None:
    remaining = memoryview(data)
    while remaining:
        written = stream.write(remaining)  # type: ignore[attr-defined]
        if written is None:
            continue
        remaining = remaining[written:]


def start_encoder(output: Path, args: argparse.Namespace) -> subprocess.Popen[bytes]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to export MP4 files.")
    encoders = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, check=True).stdout
    codec = ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high"] if " libx264 " in encoders else ["-c:v", "libopenh264", "-threads", "1", "-b:v", "12M", "-maxrate", "16M"]
    output.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{args.width}x{args.height}", "-r", str(args.fps), "-i", "-", "-an", *codec, "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)], stdin=subprocess.PIPE)


def render(palettes: list[str], args: argparse.Namespace) -> None:
    points = normalise(integrate(args.steps + args.warmup_steps, args.dt, args.alpha)[args.warmup_steps:])
    for name in palettes:
        output = args.output_dir / f"halvorsen_alpha-{args.alpha:g}_{name}_black_{args.width}x{args.height}_{args.duration:.0f}s_{args.fps}fps.mp4"
        encoder = start_encoder(output, args)
        palette = build_palette(PALETTES[name])
        try:
            for frame_index in range(args.frames):
                write_all(encoder.stdin, palette[render_mask(points, frame_index, args.frames, args.width, args.height)].tobytes())
        finally:
            assert encoder.stdin is not None
            encoder.stdin.close()
        if encoder.wait() != 0:
            raise RuntimeError(f"ffmpeg failed while rendering {name}.")
        print(f"Saved {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--palette", choices=sorted(PALETTES), default="velvet-signal")
    parser.add_argument("--all-palettes", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--duration", type=float, default=12)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--alpha", type=float, default=1.4)
    parser.add_argument("--steps", type=int, default=32000)
    parser.add_argument("--warmup-steps", type=int, default=2000)
    parser.add_argument("--dt", type=float, default=0.004)
    args = parser.parse_args()
    args.frames = round(args.duration * args.fps)
    return args


if __name__ == "__main__":
    options = parse_args()
    render(sorted(PALETTES) if options.all_palettes else [options.palette], options)
