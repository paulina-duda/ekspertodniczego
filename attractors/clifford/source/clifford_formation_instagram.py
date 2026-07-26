#!/usr/bin/env python3
"""Render 15-second Clifford formation animations for Instagram."""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


PROJECT_DIR = Path(__file__).resolve().parents[1]

CLIFFORD_PRESETS = {
    "ribbon": (-1.7, 1.3, -0.1, -1.21),
    "shell": (1.7, 1.7, 0.6, 1.2),
    "orbit": (-1.8, -2.0, -0.5, -0.9),
    "mask": (-1.9, 1.9, -1.2, 0.8),
    "organic-flower": (1.5, -1.8, 1.6, 0.9),
    "double-knot": (-1.3, 1.7, 1.8, 0.6),
    "ring": (-1.7, 1.8, -1.9, -0.4),
    "classic-butterfly": (-1.4, 1.6, 1.0, 0.7),
}

SPECTRUM_RIBBON = [
    (255, 44, 129),
    (255, 113, 41),
    (255, 238, 64),
    (68, 255, 156),
    (37, 188, 255),
    (113, 76, 255),
    (255, 58, 203),
]


def smoothstep(edge_start: float, edge_end: float, value: float) -> float:
    position = np.clip((value - edge_start) / (edge_end - edge_start), 0, 1)
    return float(position * position * (3 - 2 * position))


def build_palette(stops: list[tuple[int, int, int]]) -> np.ndarray:
    positions = np.linspace(0, len(stops) - 1, 1024)
    lower = np.floor(positions).astype(int)
    upper = np.minimum(lower + 1, len(stops) - 1)
    fraction = (positions - lower)[:, None]
    return ((1 - fraction) * np.asarray(stops)[lower] + fraction * np.asarray(stops)[upper]).astype(np.uint8)


def generate_clifford(steps: int, parameters: tuple[float, float, float, float], warmup_steps: int) -> np.ndarray:
    points = np.empty((steps + warmup_steps, 2), dtype=np.float64)
    a, b, c, d = parameters
    x, y = 0.1, 0.1
    for index in range(len(points)):
        x, y = math.sin(a * y) + c * math.cos(a * x), math.sin(b * x) + d * math.cos(b * y)
        points[index] = (x, y)
    points = points[warmup_steps:]
    centre = (points.min(axis=0) + points.max(axis=0)) * 0.5
    span = max(np.ptp(points[:, 0]), np.ptp(points[:, 1]))
    return (points - centre) / max(span * 0.5, 1e-9)


def make_volume(points: np.ndarray) -> np.ndarray:
    """Give a planar Clifford cloud real depth instead of rotating a flat card."""
    ranks = deterministic_ranks(points)
    radius = np.clip(np.linalg.norm(points, axis=1) / 1.45, 0, 1)
    half_depth = 0.22 + 0.16 * (1 - radius)
    depth = (2 * ranks - 1) * half_depth + 0.035 * np.sin(7 * points[:, 0] - 5 * points[:, 1])
    return np.column_stack((points, depth))


def build_fibres(points: np.ndarray, fibre_count: int = 110) -> list[tuple[np.ndarray, float]]:
    """Turn density slices into layered strands spanning a real 3D volume."""
    y_min, y_max = points[:, 1].min(), points[:, 1].max()
    edges = np.linspace(y_min, y_max, fibre_count + 1)
    fibres: list[tuple[np.ndarray, float]] = []
    for fibre_index in range(fibre_count):
        selected = points[(points[:, 1] >= edges[fibre_index]) & (points[:, 1] < edges[fibre_index + 1])]
        if len(selected) < 5:
            continue
        selected = selected[np.argsort(selected[:, 0])]
        # Keep rendering predictable while preserving the shape of every slice.
        if len(selected) > 320:
            selected = selected[np.linspace(0, len(selected) - 1, 320, dtype=int)]
        gaps = np.linalg.norm(np.diff(selected, axis=0), axis=1)
        split_points = np.flatnonzero(gaps > 0.095) + 1
        for strand in np.split(selected, split_points):
            if len(strand) >= 5:
                base_rank = (fibre_index + 0.5) / fibre_count
                radius = np.clip(np.linalg.norm(strand, axis=1) / 1.45, 0, 1)
                half_depth = 0.22 + 0.16 * (1 - radius)
                for layer_index, layer in enumerate(np.linspace(-1, 1, 7)):
                    depth = layer * half_depth + 0.025 * np.sin(6 * strand[:, 0] + 4 * strand[:, 1] + layer)
                    fibre_3d = np.column_stack((strand, depth))
                    rank = np.mod(base_rank + layer_index * 0.053, 1)
                    fibres.append((fibre_3d, rank))
    return fibres


def rotation_matrix(yaw: float) -> np.ndarray:
    tilt = math.radians(18)
    roll = math.radians(-7)
    cosine_x, sine_x = math.cos(tilt), math.sin(tilt)
    cosine_y, sine_y = math.cos(yaw), math.sin(yaw)
    cosine_z, sine_z = math.cos(roll), math.sin(roll)
    rotate_x = np.array(((1, 0, 0), (0, cosine_x, -sine_x), (0, sine_x, cosine_x)))
    rotate_y = np.array(((cosine_y, 0, sine_y), (0, 1, 0), (-sine_y, 0, cosine_y)))
    rotate_z = np.array(((cosine_z, -sine_z, 0), (sine_z, cosine_z, 0), (0, 0, 1)))
    return rotate_z @ rotate_y @ rotate_x


def camera_coordinates(points: np.ndarray, matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rotated = points @ matrix.T
    perspective = 1 / (4.6 - rotated[:, 2])
    return np.column_stack((rotated[:, 0] * perspective, rotated[:, 1] * perspective)), rotated[:, 2]


def projection_context(points: np.ndarray, yaw: float, width: int, height: int) -> tuple[np.ndarray, float, np.ndarray]:
    matrix = rotation_matrix(yaw)
    camera, _ = camera_coordinates(points, matrix)
    minimum, maximum = camera.min(axis=0), camera.max(axis=0)
    margin = int(width * 0.065)
    scale = min((width - 2 * margin) / max(maximum[0] - minimum[0], 1e-9), (height - 2 * margin) / max(maximum[1] - minimum[1], 1e-9))
    return matrix, scale, (minimum + maximum) * 0.5


def project_3d(points: np.ndarray, context: tuple[np.ndarray, float, np.ndarray], width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    matrix, scale, centre = context
    camera, depth = camera_coordinates(points, matrix)
    screen = np.column_stack((width * 0.5 + (camera[:, 0] - centre[0]) * scale, height * 0.5 - (camera[:, 1] - centre[1]) * scale))
    return screen.astype(np.int32), depth


def point_phases(points: np.ndarray) -> np.ndarray:
    angle = np.arctan2(points[:, 1], points[:, 0]) / math.tau + 0.5
    radius = np.linalg.norm(points[:, :2], axis=1)
    depth = points[:, 2] if points.shape[1] == 3 else 0
    return np.mod(angle + 0.16 * radius + 0.10 * depth, 1)


def deterministic_ranks(points: np.ndarray) -> np.ndarray:
    values = np.sin(points[:, 0] * 1234.57 + points[:, 1] * 7829.31) * 43758.5453
    return np.mod(values, 1)


def render_frame(
    points: np.ndarray,
    ranks: np.ndarray,
    phases: np.ndarray,
    fibres: list[tuple[np.ndarray, float]],
    palette: np.ndarray,
    progress: float,
    width: int,
    height: int,
) -> np.ndarray:
    # Formation occupies the first ten seconds; the completed shape then makes
    # one measured half-turn during the final five seconds.
    turn = smoothstep(0.67, 1.0, progress)
    yaw = math.radians(-28) + math.pi * turn
    context = projection_context(points, yaw, width, height)
    projected, point_depth = project_3d(points, context, width, height)

    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    canvas[:, :, :] = (2, 3, 9)
    flat = canvas.reshape(-1, 3)

    seed_density = 0.003 + 0.075 * smoothstep(0.0, 0.24, progress)
    cloud_density = seed_density + (1 - seed_density) * smoothstep(0.30, 0.67, progress)
    selected = ranks < cloud_density
    visible_points = projected[selected]
    visible_depth = point_depth[selected]
    selected_phases = phases[selected]
    colours = palette[(selected_phases * (len(palette) - 1)).astype(int)]
    valid = (
        (visible_points[:, 0] >= 1)
        & (visible_points[:, 0] < width - 1)
        & (visible_points[:, 1] >= 1)
        & (visible_points[:, 1] < height - 1)
    )
    visible_points, colours, visible_depth = visible_points[valid], colours[valid], visible_depth[valid]
    depth_light = 0.62 + 0.38 * (visible_depth - visible_depth.min()) / max(np.ptp(visible_depth), 1e-9)
    colours = np.clip(colours.astype(np.float32) * depth_light[:, None], 0, 255).astype(np.uint8)
    depth_order = np.argsort(visible_depth)
    visible_points, colours = visible_points[depth_order], colours[depth_order]
    indices = visible_points[:, 1] * width + visible_points[:, 0]
    flat[indices] = colours
    halo = 0.68 - 0.36 * smoothstep(0.42, 0.70, progress)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        neighbours = (visible_points[:, 1] + dy) * width + visible_points[:, 0] + dx
        flat[neighbours] = np.maximum(flat[neighbours], (colours * halo).astype(np.uint8))

    # Fibres start after the seed cloud. They appear in staggered slices and
    # lengthen from one end until the local points read as connected lines.
    line_progress = smoothstep(0.18, 0.64, progress)
    image = Image.fromarray(canvas)
    draw = ImageDraw.Draw(image)
    active_fibres: list[tuple[float, np.ndarray, float]] = []
    for fibre, rank in fibres:
        local_progress = np.clip((line_progress - 0.28 * rank) / 0.72, 0, 1)
        visible_count = int(len(fibre) * local_progress)
        if visible_count < 2:
            continue
        strand = fibre[:visible_count]
        strand_projected, strand_depth = project_3d(strand, context, width, height)
        active_fibres.append((float(np.mean(strand_depth)), strand_projected, float(np.mean(strand_depth))))

    active_fibres.sort(key=lambda item: item[0])
    matrix = context[0]
    all_rotated_depth = (points @ matrix.T)[:, 2]
    depth_min, depth_span = all_rotated_depth.min(), max(np.ptp(all_rotated_depth), 1e-9)
    for _, strand_projected, strand_depth in active_fibres:
        midpoint_x = np.mean(strand_projected[:, 0]) / max(width, 1)
        phase = np.mod(midpoint_x + 0.38, 1)
        light = 0.62 + 0.38 * (strand_depth - depth_min) / depth_span
        colour = tuple(int(channel * light) for channel in palette[int(phase * (len(palette) - 1))])
        draw.line([tuple(point) for point in strand_projected], fill=colour, width=1)
    return np.asarray(image)


def write_all(stream: object, data: bytes) -> None:
    remaining = memoryview(data)
    while remaining:
        written = stream.write(remaining)  # type: ignore[attr-defined]
        if written is not None:
            remaining = remaining[written:]


def start_encoder(output: Path, args: argparse.Namespace) -> subprocess.Popen[bytes]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to export MP4 files.")
    encoders = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, check=True).stdout
    if " libx264 " in encoders:
        codec = ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high"]
    elif " libopenh264 " in encoders:
        codec = ["-c:v", "libopenh264", "-threads", "1", "-b:v", "12M", "-maxrate", "16M"]
    else:
        raise RuntimeError("No H.264 encoder is available in ffmpeg.")
    output.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{args.width}x{args.height}", "-r", str(args.animation_fps), "-i", "-", "-an", *codec, "-r", str(args.fps), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)],
        stdin=subprocess.PIPE,
    )


def output_path(preset: str, args: argparse.Namespace) -> Path:
    directory = args.output_dir if args.output_dir is not None else PROJECT_DIR / preset / "phone-9x16"
    return directory / f"clifford_{preset}_formation-spectrum-ribbon_black_{args.width}x{args.height}_{args.duration:g}s_{args.fps}fps.mp4"


def render_preset(preset: str, args: argparse.Namespace) -> Path:
    planar_points = generate_clifford(args.steps, CLIFFORD_PRESETS[preset], args.warmup_steps)
    points = make_volume(planar_points)
    ranks = deterministic_ranks(points)
    phases = point_phases(points)
    fibres = build_fibres(planar_points, args.fibres)
    palette = build_palette(SPECTRUM_RIBBON)
    output = output_path(preset, args)
    encoder = start_encoder(output, args)
    try:
        for frame_index in range(args.animation_frames):
            progress = frame_index / max(args.animation_frames - 1, 1)
            assert encoder.stdin is not None
            write_all(encoder.stdin, render_frame(points, ranks, phases, fibres, palette, progress, args.width, args.height).tobytes())
    finally:
        assert encoder.stdin is not None
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError(f"ffmpeg failed while rendering {preset}.")
    return output


def render_preview(preset: str, args: argparse.Namespace) -> Path:
    planar_points = generate_clifford(args.steps, CLIFFORD_PRESETS[preset], args.warmup_steps)
    points = make_volume(planar_points)
    frame = render_frame(
        points,
        deterministic_ranks(points),
        point_phases(points),
        build_fibres(planar_points, args.fibres),
        build_palette(SPECTRUM_RIBBON),
        args.preview_progress,
        args.width,
        args.height,
    )
    output = args.preview_output or Path("/tmp") / f"clifford_{preset}_formation-{round(args.preview_progress * 100):03d}.png"
    Image.fromarray(frame).save(output)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", choices=sorted(CLIFFORD_PRESETS), default="classic-butterfly")
    parser.add_argument("--all-presets", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--preview-progress", type=float, default=0.50)
    parser.add_argument("--preview-output", type=Path)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--duration", type=float, default=15)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--animation-fps", type=int, default=8)
    parser.add_argument("--steps", type=int, default=32000)
    parser.add_argument("--warmup-steps", type=int, default=1000)
    parser.add_argument("--fibres", type=int, default=72)
    args = parser.parse_args()
    args.animation_frames = round(args.duration * args.animation_fps)
    return args


if __name__ == "__main__":
    options = parse_args()
    if options.preview:
        print(f"Saved {render_preview(options.preset, options)}")
    else:
        presets = sorted(CLIFFORD_PRESETS) if options.all_presets else [options.preset]
        for preset_name in presets:
            print(f"Saved {render_preset(preset_name, options)}")
