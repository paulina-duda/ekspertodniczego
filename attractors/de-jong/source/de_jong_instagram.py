#!/usr/bin/env python3
"""Render airy 9:16 De Jong attractor MP4 videos for Instagram."""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


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


def generate_de_jong(steps: int, a: float, b: float, c: float, d: float) -> np.ndarray:
    points = np.empty((steps, 2), dtype=np.float64)
    x, y = 0.1, 0.1
    for index in range(steps):
        x, y = math.sin(a * y) - math.cos(b * x), math.sin(c * x) - math.cos(d * y)
        points[index] = (x, y)
    return points


def project(points: np.ndarray, width: int, height: int, angle: float) -> np.ndarray:
    x, y = points.T
    cosine, sine = math.cos(angle), math.sin(angle)
    rotated_x, rotated_y = x * cosine - y * sine, x * sine + y * cosine
    margin = int(min(width, height) * 0.09)
    scale = min((width - 2 * margin) / np.ptp(rotated_x), (height - 2 * margin) / np.ptp(rotated_y))
    return np.column_stack((
        width * 0.5 + (rotated_x - (rotated_x.max() + rotated_x.min()) * 0.5) * scale,
        height * 0.5 + (rotated_y - (rotated_y.max() + rotated_y.min()) * 0.5) * scale,
    )).astype(np.int32)


def render_mask(points: np.ndarray, frame_index: int, frame_count: int, width: int, height: int) -> np.ndarray:
    progress = (frame_index + 1) / frame_count
    projected = project(points, width, height, math.radians(8) * math.sin(math.tau * progress))
    visible = projected[: max(120, int(progress * len(projected)))]
    image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(image)
    boundaries = np.linspace(0, len(visible), 33, dtype=int)
    for index, (start, end) in enumerate(zip(boundaries[:-1], boundaries[1:])):
        intensity = 30 + int(125 * index / 31)
        if index >= 25:
            intensity = 160 + int(95 * (index - 25) / 6)
        draw.point([tuple(point) for point in visible[start:end]], fill=intensity)
    return np.asarray(image.filter(ImageFilter.MaxFilter(3)))


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
    points = generate_de_jong(args.steps, args.a, args.b, args.c, args.d)[args.warmup_steps:]
    for name in palettes:
        output = args.output_dir / f"de-jong_classic_{name}_black_{args.width}x{args.height}_{args.duration:.0f}s_{args.fps}fps.mp4"
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
    parser.add_argument("--steps", type=int, default=32000)
    parser.add_argument("--warmup-steps", type=int, default=1000)
    parser.add_argument("--a", type=float, default=-2.0)
    parser.add_argument("--b", type=float, default=-2.0)
    parser.add_argument("--c", type=float, default=-1.2)
    parser.add_argument("--d", type=float, default=2.0)
    args = parser.parse_args()
    args.frames = round(args.duration * args.fps)
    return args


if __name__ == "__main__":
    options = parse_args()
    render(sorted(PALETTES) if options.all_palettes else [options.palette], options)
