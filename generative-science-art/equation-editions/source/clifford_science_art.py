#!/usr/bin/env python3
"""Render curated Clifford formation sculptures with subtle early 3D motion."""

from __future__ import annotations

import argparse
import importlib.util
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from equation_overlay import apply_equation_overlay, make_equation_overlay


ART_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = ART_DIR / "instagram" / "phone-9x16"
BASE_RENDERER = REPO_ROOT / "attractors/clifford/source/clifford_formation_instagram.py"
SELECTED_PRESETS = ("classic-butterfly", "ring", "shell")

NEON_RAINBOW = [
    (255, 0, 92),
    (255, 58, 0),
    (255, 225, 0),
    (54, 255, 0),
    (0, 255, 148),
    (0, 218, 255),
    (34, 76, 255),
    (153, 0, 255),
    (255, 0, 205),
]


def load_base_renderer() -> object:
    specification = importlib.util.spec_from_file_location("clifford_formation_base", BASE_RENDERER)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"Cannot load Clifford renderer: {BASE_RENDERER}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


BASE = load_base_renderer()


def equation_for(preset: str) -> tuple[str, ...]:
    a, b, c, d = BASE.CLIFFORD_PRESETS[preset]
    return (
        "x[n+1] = sin(a y[n]) + c cos(a x[n])",
        "y[n+1] = sin(b x[n]) + d cos(b y[n])",
        "",
        f"a = {a:5g}    b = {b:5g}",
        f"c = {c:5g}    d = {d:5g}",
    )


def render_frame(
    points: np.ndarray,
    ranks: np.ndarray,
    phases: np.ndarray,
    fibres: list[tuple[np.ndarray, float]],
    palette: np.ndarray,
    equation_overlay: Image.Image,
    progress: float,
    width: int,
    height: int,
) -> np.ndarray:
    # The seed cloud is still. A complete spatial turn begins exactly when the
    # first fibres appear and eases across the rest of the film.
    turn = BASE.smoothstep(0.18, 1.0, progress)
    yaw = math.radians(-34 + 360 * turn)
    context = BASE.projection_context(points, yaw, width, height)
    projected, point_depth = BASE.project_3d(points, context, width, height)

    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    canvas[:, :, :] = (2, 3, 9)
    flat = canvas.reshape(-1, 3)
    seed_density = 0.003 + 0.075 * BASE.smoothstep(0.0, 0.24, progress)
    cloud_density = seed_density + (1 - seed_density) * BASE.smoothstep(0.30, 0.67, progress)
    selected = ranks < cloud_density
    visible_points = projected[selected]
    visible_depth = point_depth[selected]
    colours = palette[(phases[selected] * (len(palette) - 1)).astype(int)]
    valid = (
        (visible_points[:, 0] >= 1)
        & (visible_points[:, 0] < width - 1)
        & (visible_points[:, 1] >= 1)
        & (visible_points[:, 1] < height - 1)
    )
    visible_points, colours, visible_depth = visible_points[valid], colours[valid], visible_depth[valid]
    depth_light = 0.78 + 0.22 * (visible_depth - visible_depth.min()) / max(np.ptp(visible_depth), 1e-9)
    colours = np.clip(colours.astype(np.float32) * depth_light[:, None], 0, 255).astype(np.uint8)
    depth_order = np.argsort(visible_depth)
    visible_points, colours = visible_points[depth_order], colours[depth_order]
    indices = visible_points[:, 1] * width + visible_points[:, 0]
    flat[indices] = colours
    halo = 0.68 - 0.36 * BASE.smoothstep(0.42, 0.70, progress)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        neighbours = (visible_points[:, 1] + dy) * width + visible_points[:, 0] + dx
        flat[neighbours] = np.maximum(flat[neighbours], (colours * halo).astype(np.uint8))

    line_progress = BASE.smoothstep(0.18, 0.64, progress)
    image = Image.fromarray(canvas)
    draw = ImageDraw.Draw(image)
    active_fibres: list[tuple[float, np.ndarray]] = []
    for fibre, rank in fibres:
        local_progress = np.clip((line_progress - 0.28 * rank) / 0.72, 0, 1)
        visible_count = int(len(fibre) * local_progress)
        if visible_count < 2:
            continue
        strand_projected, strand_depth = BASE.project_3d(fibre[:visible_count], context, width, height)
        active_fibres.append((float(np.mean(strand_depth)), strand_projected))

    active_fibres.sort(key=lambda item: item[0])
    matrix = context[0]
    all_depth = (points @ matrix.T)[:, 2]
    depth_min, depth_span = all_depth.min(), max(np.ptp(all_depth), 1e-9)
    for strand_depth, strand_projected in active_fibres:
        midpoint_x = np.mean(strand_projected[:, 0]) / width
        phase = np.mod(midpoint_x + 0.38, 1)
        light = 0.78 + 0.22 * (strand_depth - depth_min) / depth_span
        colour = tuple(int(channel * light) for channel in palette[int(phase * (len(palette) - 1))])
        draw.line([tuple(point) for point in strand_projected], fill=colour, width=1)
    return apply_equation_overlay(np.asarray(image), equation_overlay)


def render_preset(preset: str, args: argparse.Namespace) -> Path:
    planar_points = BASE.generate_clifford(args.steps, BASE.CLIFFORD_PRESETS[preset], args.warmup_steps)
    points = BASE.make_volume(planar_points)
    ranks = BASE.deterministic_ranks(points)
    phases = BASE.point_phases(points)
    fibres = BASE.build_fibres(planar_points, args.fibres)
    palette = BASE.build_palette(NEON_RAINBOW)
    overlay = make_equation_overlay(args.width, args.height, equation_for(preset), font_size=args.font_size)
    output = args.output_dir / f"clifford_{preset}_rainbow-equation-edition_{args.width}x{args.height}_{args.duration:g}s_{args.fps}fps.mp4"
    encoder = BASE.start_encoder(output, args)
    try:
        for frame_index in range(args.animation_frames):
            progress = frame_index / max(args.animation_frames - 1, 1)
            frame = render_frame(points, ranks, phases, fibres, palette, overlay, progress, args.width, args.height)
            BASE.write_all(encoder.stdin, frame.tobytes())
    finally:
        assert encoder.stdin is not None
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError(f"ffmpeg failed while rendering {preset}.")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", choices=SELECTED_PRESETS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--duration", type=float, default=15)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--animation-fps", type=int, default=15)
    parser.add_argument("--steps", type=int, default=32000)
    parser.add_argument("--warmup-steps", type=int, default=1000)
    parser.add_argument("--fibres", type=int, default=72)
    parser.add_argument("--font-size", type=int, default=22)
    args = parser.parse_args()
    args.animation_frames = round(args.duration * args.animation_fps)
    return args


if __name__ == "__main__":
    options = parse_args()
    presets = [options.preset] if options.preset else list(SELECTED_PRESETS)
    for preset_name in presets:
        print(f"Saved {render_preset(preset_name, options)}")
