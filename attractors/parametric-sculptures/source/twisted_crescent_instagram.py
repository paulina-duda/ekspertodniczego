#!/usr/bin/env python3
"""Render a rotating 9:16 parametric crescent sculpture for Instagram."""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "instagram" / "phone-9x16"
DEFAULT_PREVIEW_DIR = PROJECT_DIR / "previews"

# These are deliberately vivid; the object is a dense point sculpture rather
# than a shaded mesh, so colour can travel across its continuously curved skin.
PALETTES = {
    "spectrum-ribbon": [(255, 44, 129), (255, 113, 41), (255, 238, 64), (68, 255, 156), (37, 188, 255), (113, 76, 255), (255, 58, 203)],
    "electric-orchid": [(43, 242, 255), (80, 130, 255), (177, 78, 255), (255, 58, 177), (255, 123, 92), (255, 224, 108), (105, 255, 209)],
    "solar-silk": [(255, 245, 167), (255, 204, 61), (255, 117, 37), (255, 57, 91), (220, 70, 238), (123, 95, 255), (109, 255, 235)],
    "ocean-prism": [(61, 255, 202), (42, 208, 255), (59, 118, 255), (113, 68, 255), (241, 58, 240), (255, 103, 181), (255, 224, 130)],
}


def rotation_x(angle: float) -> np.ndarray:
    cosine, sine = math.cos(angle), math.sin(angle)
    return np.array(((1, 0, 0), (0, cosine, -sine), (0, sine, cosine)))


def rotation_y(angle: float) -> np.ndarray:
    cosine, sine = math.cos(angle), math.sin(angle)
    return np.array(((cosine, 0, sine), (0, 1, 0), (-sine, 0, cosine)))


def rotation_z(angle: float) -> np.ndarray:
    cosine, sine = math.cos(angle), math.sin(angle)
    return np.array(((cosine, -sine, 0), (sine, cosine, 0), (0, 0, 1)))


def build_palette(stops: list[tuple[int, int, int]]) -> np.ndarray:
    positions = np.linspace(0, len(stops) - 1, 1024)
    lower = np.floor(positions).astype(int)
    upper = np.minimum(lower + 1, len(stops) - 1)
    fraction = (positions - lower)[:, None]
    return ((1 - fraction) * np.asarray(stops)[lower] + fraction * np.asarray(stops)[upper]).astype(np.uint8)


def smoothstep(edge_start: float, edge_end: float, value: float) -> float:
    position = np.clip((value - edge_start) / (edge_end - edge_start), 0, 1)
    return float(position * position * (3 - 2 * position))


def make_sculpture(u_count: int, v_count: int) -> tuple[np.ndarray, ...]:
    """Create a deliberately imperfect torus with a bitten, crescent-like side."""
    u = np.linspace(0, math.tau, u_count, endpoint=False)
    v = np.linspace(0, math.tau, v_count, endpoint=False)
    u_grid, v_grid = np.meshgrid(u, v)

    major_radius = 2.18
    tube_radius = 1.02 - 0.28 * np.cos(u_grid - 0.3) - 0.57 * np.exp(-((u_grid - math.pi) / 0.78) ** 2)
    twist = 0.84 * np.sin(u_grid) + 0.13 * np.sin(3 * u_grid)
    phase = v_grid + twist

    x = (major_radius + tube_radius * np.cos(phase)) * np.cos(u_grid)
    y = 0.82 * (major_radius + tube_radius * np.cos(phase)) * np.sin(u_grid)
    z = 1.15 * tube_radius * np.sin(phase) + 0.22 * np.sin(2 * u_grid)
    x += 0.12 * np.cos(3 * v_grid) * (0.45 + 0.55 * np.sin(u_grid) ** 2)
    z += 0.08 * np.sin(4 * v_grid)

    points = np.column_stack((x.ravel(), y.ravel(), z.ravel()))
    colour_phase = ((u_grid / math.tau) + 0.18 * np.sin(v_grid) + 0.035 * np.sin(3 * v_grid - u_grid)) % 1
    # Fine highlight variation follows the short circumference of the form.
    sheen = 0.74 + 0.26 * np.maximum(0, np.cos(v_grid - 0.6 * u_grid))
    u_index = np.broadcast_to(np.arange(u_count), (v_count, u_count))
    v_index = np.broadcast_to(np.arange(v_count)[:, None], (v_count, u_count))
    particle_rank = np.mod(np.sin(u_index * 12.9898 + v_index * 78.233) * 43758.5453, 1)
    strand_rank = np.mod(np.sin((v_index + 1) * 31.137) * 9182.731, 1)
    # Each strand starts from a slightly different place, so the surface grows
    # from many luminous seeds instead of being revealed by a flat wipe.
    growth_rank = np.mod(u_grid / math.tau + 0.11 * np.sin(2 * v_grid) + 0.035 * np.sin(5 * v_grid), 1)
    return (
        points,
        colour_phase.ravel(),
        sheen.ravel(),
        particle_rank.ravel(),
        strand_rank.ravel(),
        growth_rank.ravel(),
    )


def project(points: np.ndarray, progress: float, width: int, height: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pose and project the sculpture, keeping it tall in a full phone frame."""
    base = rotation_z(math.radians(15)) @ rotation_y(math.radians(-50)) @ rotation_x(math.radians(72))
    # Only a restrained camera drift remains. The visual action is the surface
    # assembling itself, not a finished object spinning around its axis.
    camera_settle = smoothstep(0.48, 1.0, progress)
    camera = rotation_z(math.radians(-3 + 6 * camera_settle)) @ rotation_y(math.radians(2.5 * math.sin(math.pi * camera_settle)))
    rotated = points @ (camera @ base).T

    depth = rotated[:, 2] + 9.1
    projected_x = 9.7 * rotated[:, 0] / depth
    projected_y = 9.7 * rotated[:, 1] / depth
    scale = min(width / 1.34 / np.ptp(projected_x), height / 1.72 / np.ptp(projected_y))
    screen_x = width * 0.5 + (projected_x - np.mean((projected_x.min(), projected_x.max()))) * scale
    screen_y = height * 0.5 - (projected_y - np.mean((projected_y.min(), projected_y.max()))) * scale
    return screen_x.astype(np.int32), screen_y.astype(np.int32), rotated[:, 2]


def formation_mask(particle_rank: np.ndarray, strand_rank: np.ndarray, growth_rank: np.ndarray, progress: float) -> tuple[np.ndarray, float]:
    """Reveal seeds, growing fibres, and finally the complete point surface."""
    seed_density = 0.004 + 0.052 * smoothstep(0.0, 0.24, progress)
    seeds = particle_rank < seed_density

    fibre_progress = smoothstep(0.18, 0.70, progress)
    strand_density = 0.035 + 0.63 * fibre_progress
    # A soft moving front lengthens individual fibres across the curved form.
    fibre_front = np.clip(fibre_progress * 1.18, 0, 1)
    fibres = (strand_rank < strand_density) & (growth_rank < fibre_front)

    skin_progress = smoothstep(0.60, 0.94, progress)
    skin = (strand_rank < skin_progress) & (growth_rank < np.clip(0.35 + 0.8 * skin_progress, 0, 1))
    return seeds | fibres | skin, smoothstep(0.78, 0.97, progress)


def rasterise(surface: tuple[np.ndarray, ...], palette: np.ndarray, progress: float, width: int, height: int) -> np.ndarray:
    points, phases, sheen, particle_rank, strand_rank, growth_rank = surface
    x, y, depth = project(points, progress, width, height)
    formed, completion = formation_mask(particle_rank, strand_rank, growth_rank, progress)
    visible = formed & (x >= 1) & (x < width - 1) & (y >= 1) & (y < height - 1)
    x, y, depth = x[visible], y[visible], depth[visible]
    palette_index = (phases[visible] % 1 * (len(palette) - 1)).astype(int)
    light = sheen[visible] * (0.68 + 0.32 * (depth - depth.min()) / max(np.ptp(depth), 1e-6))
    # The earliest seeds flare up; as fibres connect, they settle into the
    # finished surface and stop competing with its geometry.
    seed_flare = 1.0 + (particle_rank[visible] < 0.056) * (0.34 * (1 - completion))
    light *= seed_flare
    colours = np.clip(palette[palette_index].astype(float) * light[:, None], 0, 255).astype(np.uint8)

    # Back-to-front overwrite gives a small amount of real depth without a mesh.
    order = np.argsort(depth)
    x, y, colours = x[order], y[order], colours[order]
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    canvas[:, :, :] = (2, 3, 9)
    flat = canvas.reshape(-1, 3)
    index = y * width + x
    flat[index] = colours
    # A tiny halo makes isolated surface dots feel luminous, without softening
    # the graphic point-cloud texture.
    halo_strength = 0.72 - 0.37 * completion
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        neighbour = (y + dy) * width + x + dx
        existing = flat[neighbour].astype(np.float32)
        flat[neighbour] = np.maximum(existing, colours.astype(np.float32) * halo_strength).astype(np.uint8)
    return canvas


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
    codec = ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high"] if " libx264 " in encoders else ["-c:v", "libopenh264", "-threads", "1", "-b:v", "12M", "-maxrate", "16M"]
    output.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{args.width}x{args.height}", "-r", str(args.animation_fps), "-i", "-", "-an", *codec, "-r", str(args.fps), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)], stdin=subprocess.PIPE)


def render_preview(surface: tuple[np.ndarray, ...], args: argparse.Namespace) -> Path:
    palette = build_palette(PALETTES[args.palette])
    image = Image.fromarray(rasterise(surface, palette, args.preview_progress, args.width, args.height))
    progress_label = round(args.preview_progress * 100)
    output = args.preview_dir / f"twisted-crescent_formation-{progress_label:03d}_{args.palette}_{args.width}x{args.height}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return output


def render_storyboard(surface: tuple[np.ndarray, ...], args: argparse.Namespace) -> Path:
    palette = build_palette(PALETTES[args.palette])
    samples = (0.10, 0.38, 0.68, 0.98)
    tile_width, tile_height = args.width // 2, args.height // 2
    storyboard = Image.new("RGB", (args.width, args.height), (2, 3, 9))
    for index, progress in enumerate(samples):
        frame = Image.fromarray(rasterise(surface, palette, progress, args.width, args.height))
        frame.thumbnail((tile_width, tile_height), Image.Resampling.LANCZOS)
        x = (index % 2) * tile_width + (tile_width - frame.width) // 2
        y = (index // 2) * tile_height + (tile_height - frame.height) // 2
        storyboard.paste(frame, (x, y))
    output = args.preview_dir / f"twisted-crescent_formation-storyboard_{args.palette}_{args.width}x{args.height}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    storyboard.save(output)
    return output


def render_video(surface: tuple[np.ndarray, ...], palette_name: str, args: argparse.Namespace) -> Path:
    output = args.output_dir / f"twisted-crescent_{palette_name}_black_{args.width}x{args.height}_{args.duration:g}s_{args.fps}fps.mp4"
    encoder = start_encoder(output, args)
    palette = build_palette(PALETTES[palette_name])
    try:
        for frame_index in range(args.animation_frames):
            progress = frame_index / args.animation_frames
            write_all(encoder.stdin, rasterise(surface, palette, progress, args.width, args.height).tobytes())
    finally:
        assert encoder.stdin is not None
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError(f"ffmpeg failed while rendering {palette_name}.")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--palette", choices=sorted(PALETTES), default="spectrum-ribbon")
    parser.add_argument("--all-palettes", action="store_true")
    parser.add_argument("--preview", action="store_true", help="Write one PNG instead of an MP4.")
    parser.add_argument("--storyboard", action="store_true", help="Write a four-stage formation preview instead of an MP4.")
    parser.add_argument("--preview-dir", type=Path, default=DEFAULT_PREVIEW_DIR)
    parser.add_argument("--preview-progress", type=float, default=0.18)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--duration", type=float, default=12)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--animation-fps", type=int, default=15, help="Unique rendered frames per second; output remains at --fps.")
    parser.add_argument("--u-count", type=int, default=960)
    parser.add_argument("--v-count", type=int, default=180)
    args = parser.parse_args()
    args.animation_frames = round(args.duration * args.animation_fps)
    return args


if __name__ == "__main__":
    options = parse_args()
    sculpture = make_sculpture(options.u_count, options.v_count)
    if options.preview:
        print(f"Saved {render_preview(sculpture, options)}")
    elif options.storyboard:
        print(f"Saved {render_storyboard(sculpture, options)}")
    else:
        palette_names = sorted(PALETTES) if options.all_palettes else [options.palette]
        for palette_name in palette_names:
            print(f"Saved {render_video(sculpture, palette_name, options)}")
