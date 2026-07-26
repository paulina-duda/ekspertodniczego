#!/usr/bin/env python3
"""Render 3D Hopfield memory-basin animations for Instagram.

The x/y axes are the first two PCA components of binary neural states. The
third embedded coordinate is the actual Hopfield energy, so every trajectory
shows a noisy cue descending into a stored memory basin.
"""

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
    "velvet-signal": [(79, 255, 209), (27, 191, 255), (96, 96, 255), (218, 72, 255), (255, 75, 156), (255, 183, 77), (255, 255, 245)],
}

EXPORT_PRESETS = [
    ("ember-garden", (0, 0, 0)),
    ("orchid-gold", (0, 0, 0)),
    ("velvet-signal", (0, 0, 0)),
    ("velvet-signal", (24, 16, 14)),
]


def interpolate(stops: list[tuple[int, int, int]], position: float) -> tuple[int, int, int]:
    position = float(np.clip(position, 0.0, 1.0)) * (len(stops) - 1)
    index = min(int(position), len(stops) - 2)
    fraction = position - index
    return tuple(int(start + (end - start) * fraction) for start, end in zip(stops[index], stops[index + 1]))


def basin_colours(name: str, count: int) -> list[tuple[int, int, int]]:
    positions = [0.12, 0.48, 0.84] if count == 3 else np.linspace(0.12, 0.84, count)
    return [interpolate(PALETTES[name], float(position)) for position in positions]


def weights_from_memories(memories: np.ndarray) -> np.ndarray:
    weights = memories.T @ memories / memories.shape[1]
    np.fill_diagonal(weights, 0.0)
    return weights


def energy(state: np.ndarray, weights: np.ndarray) -> float:
    return float(-0.5 * state @ weights @ state)


def stable(state: np.ndarray, weights: np.ndarray) -> bool:
    fields = weights @ state
    proposed = np.where(fields > 1e-12, 1.0, np.where(fields < -1e-12, -1.0, state))
    return bool(np.array_equal(proposed, state))


def build_network(rng: np.random.Generator, neurons: int, memories: int) -> tuple[np.ndarray, np.ndarray]:
    for _ in range(3000):
        patterns = rng.choice(np.array((-1.0, 1.0)), size=(memories, neurons))
        overlaps = patterns @ patterns.T / neurons - np.eye(memories)
        if np.max(np.abs(overlaps)) > 0.30:
            continue
        weights = weights_from_memories(patterns)
        if all(stable(pattern, weights) for pattern in patterns):
            return patterns, weights
    raise RuntimeError("Could not generate separated stable Hopfield memories.")


def recall(cue: np.ndarray, weights: np.ndarray, rng: np.random.Generator, max_sweeps: int = 36) -> tuple[np.ndarray, np.ndarray]:
    state = cue.copy()
    states, energies = [state.copy()], [energy(state, weights)]
    for _ in range(max_sweeps):
        changed = False
        for neuron in rng.permutation(len(state)):
            field = weights[neuron] @ state
            value = 1.0 if field > 1e-12 else -1.0 if field < -1e-12 else state[neuron]
            if value != state[neuron]:
                state[neuron] = value
                states.append(state.copy())
                energies.append(energy(state, weights))
                changed = True
        if not changed:
            break
    return np.asarray(states), np.asarray(energies)


def recall_paths(rng: np.random.Generator, memories: np.ndarray, weights: np.ndarray, traces_per_memory: int) -> tuple[list[np.ndarray], list[np.ndarray], list[int]]:
    paths: list[np.ndarray] = []
    energies: list[np.ndarray] = []
    targets: list[int] = []
    neurons = memories.shape[1]
    for target, memory in enumerate(memories):
        accepted = 0
        attempts = 0
        while accepted < traces_per_memory:
            attempts += 1
            if attempts > 2000:
                raise RuntimeError("Could not create enough recall paths for a memory.")
            cue = memory.copy()
            flips = int(rng.integers(max(2, round(neurons * 0.18)), max(3, round(neurons * 0.36)) + 1))
            cue[rng.choice(neurons, size=flips, replace=False)] *= -1.0
            states, state_energies = recall(cue, weights, rng)
            if np.array_equal(states[-1], memory):
                paths.append(states)
                energies.append(state_energies)
                targets.append(target)
                accepted += 1
    return paths, energies, targets


def resample(points: np.ndarray, samples: int) -> np.ndarray:
    if len(points) < 2:
        return np.repeat(points[:1], samples, axis=0)
    distances = np.linalg.norm(np.diff(points, axis=0), axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(distances)))
    if cumulative[-1] < 1e-9:
        return np.repeat(points[:1], samples, axis=0)
    desired = np.linspace(0.0, cumulative[-1], samples)
    return np.column_stack([np.interp(desired, cumulative, points[:, dimension]) for dimension in range(points.shape[1])])


def embed(paths: list[np.ndarray], path_energies: list[np.ndarray], memories: np.ndarray, weights: np.ndarray) -> tuple[list[np.ndarray], np.ndarray]:
    states = np.vstack([*paths, memories])
    mean = states.mean(axis=0)
    _, _, vectors = np.linalg.svd(states - mean, full_matrices=False)
    basis = vectors[:2].T
    raw_xy = (states - mean) @ basis
    centre = (raw_xy.min(axis=0) + raw_xy.max(axis=0)) * 0.5
    span = max(float(np.ptp(raw_xy[:, 0])), float(np.ptp(raw_xy[:, 1])), 1e-9)
    all_energies = np.concatenate([*path_energies, np.array([energy(memory, weights) for memory in memories])])
    minimum, maximum = float(all_energies.min()), float(all_energies.max())

    def transform(states_to_embed: np.ndarray, energies_to_embed: np.ndarray) -> np.ndarray:
        xy = ((states_to_embed - mean) @ basis - centre) / span * 2.15
        z = (energies_to_embed - minimum) / max(maximum - minimum, 1e-9) * 1.45
        return np.column_stack((xy, z))

    embedded_paths = [transform(states, state_energies) for states, state_energies in zip(paths, path_energies)]
    memory_energies = np.array([energy(memory, weights) for memory in memories])
    return embedded_paths, transform(memories, memory_energies)


def project(points: np.ndarray, width: int, height: int, yaw_degrees: float = -34.0, pitch_degrees: float = 56.0) -> np.ndarray:
    yaw, pitch = math.radians(yaw_degrees), math.radians(pitch_degrees)
    x, y, z = points.T
    z = z - 0.55
    x_rot, y_rot = math.cos(yaw) * x - math.sin(yaw) * y, math.sin(yaw) * x + math.cos(yaw) * y
    y_tilt, z_tilt = math.cos(pitch) * y_rot + math.sin(pitch) * z, -math.sin(pitch) * y_rot + math.cos(pitch) * z
    depth = 1.0 / np.clip(1.0 + 0.18 * z_tilt, 0.25, None)
    scale = 0.32 * min(width, height)
    return np.column_stack((width * 0.5 + x_rot * depth * scale, height * 0.54 - y_tilt * depth * scale))


def points_for_draw(points: np.ndarray) -> list[tuple[int, int]]:
    return [(int(round(x)), int(round(y))) for x, y in points]


def draw_basin(draw: ImageDraw.ImageDraw, position: np.ndarray, colour: tuple[int, int, int], radius: int, pulse: float) -> None:
    x, y = (int(round(value)) for value in position)
    halo = int(radius * (2.4 + 0.35 * pulse))
    draw.ellipse((x - halo, y - halo, x + halo, y + halo), fill=(*colour, 38))
    draw.ellipse((x - int(radius * 1.4), y - int(radius * 1.4), x + int(radius * 1.4), y + int(radius * 1.4)), fill=(*colour, 190))
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(255, 255, 255, 245))


def make_base(width: int, height: int, background: tuple[int, int, int], paths: list[np.ndarray], memories: np.ndarray, targets: list[int], colours: list[tuple[int, int, int]]) -> Image.Image:
    frame = Image.new("RGBA", (width, height), (*background, 255))
    draw = ImageDraw.Draw(frame, "RGBA")
    for path, target in zip(paths, targets):
        draw.line(points_for_draw(path), fill=(*colours[target], 30), width=2, joint="curve")
    for index, memory in enumerate(memories):
        draw_basin(draw, memory, colours[index], radius=max(5, width // 108), pulse=0.0)
    return frame


def render_frame(base: Image.Image, paths: list[np.ndarray], memories: np.ndarray, targets: list[int], colours: list[tuple[int, int, int]], frame_index: int, frames: int) -> Image.Image:
    frame = base.copy()
    draw = ImageDraw.Draw(frame, "RGBA")
    progress = frame_index / max(frames - 1, 1)
    for index, (path, target) in enumerate(zip(paths, targets)):
        start = index / max(len(paths) - 1, 1) * 0.20
        local = float(np.clip((progress - start) / 0.72, 0.0, 1.0))
        count = max(1, round(1 + local * (len(path) - 1)))
        visible = path[:count]
        colour = colours[target]
        if len(visible) > 1:
            draw.line(points_for_draw(visible), fill=(*colour, 58), width=9, joint="curve")
            draw.line(points_for_draw(visible), fill=(*colour, 235), width=2, joint="curve")
        x, y = (int(round(value)) for value in visible[-1])
        draw.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(*colour, 55))
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 255, 255, 245))
    pulse = 0.5 + 0.5 * math.sin(progress * math.tau)
    for index, memory in enumerate(memories):
        draw_basin(draw, memory, colours[index], radius=max(5, base.width // 108), pulse=pulse)
    return frame


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


def render(presets: list[tuple[str, tuple[int, int, int]]], args: argparse.Namespace) -> None:
    rng = np.random.default_rng(args.seed)
    memories, weights = build_network(rng, args.neurons, args.memories)
    paths, path_energies, targets = recall_paths(rng, memories, weights, args.traces_per_memory)
    paths, memories = embed(paths, path_energies, memories, weights)
    projected_paths = [project(resample(path, args.visual_samples), args.width, args.height) for path in paths]
    projected_memories = project(memories, args.width, args.height)
    for palette_name, background in presets:
        colours = basin_colours(palette_name, args.memories)
        base = make_base(args.width, args.height, background, projected_paths, projected_memories, targets, colours)
        background_name = "black" if background == (0, 0, 0) else "warm-graphite"
        output = args.output_dir / f"hopfield_memory-basins_{palette_name}_{background_name}_{args.width}x{args.height}_{args.duration:.0f}s_{args.fps}fps.mp4"
        encoder = start_encoder(output, args)
        try:
            for frame_index in range(args.frames):
                frame = render_frame(base, projected_paths, projected_memories, targets, colours, frame_index, args.frames)
                write_all(encoder.stdin, frame.convert("RGB").tobytes())
        finally:
            assert encoder.stdin is not None
            encoder.stdin.close()
        if encoder.wait() != 0:
            raise RuntimeError(f"ffmpeg failed while rendering {palette_name}.")
        print(f"Saved {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all-presets", action="store_true")
    parser.add_argument("--palette", choices=sorted(PALETTES), default="velvet-signal")
    parser.add_argument("--background", choices=("black", "warm-graphite"), default="black")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--duration", type=float, default=12)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--neurons", type=int, default=24)
    parser.add_argument("--memories", type=int, default=3)
    parser.add_argument("--traces-per-memory", type=int, default=4)
    parser.add_argument("--visual-samples", type=int, default=140)
    parser.add_argument("--seed", type=int, default=20260703)
    args = parser.parse_args()
    args.frames = round(args.duration * args.fps)
    return args


if __name__ == "__main__":
    options = parse_args()
    background = (0, 0, 0) if options.background == "black" else (24, 16, 14)
    render(EXPORT_PRESETS if options.all_presets else [(options.palette, background)], options)
