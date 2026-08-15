#!/usr/bin/env python3
"""Conway's Life read three ways, in the luminous house style.

Life is the oldest argument that biology and computation are the same subject:
a rule with no arithmetic in it that nonetheless builds clocks, memory, and
things that copy themselves. These three editions take the rule at its word and
look at it from three sides.

CULTURE relaxes it into a continuous field on an irregular colony of cells --
Life as tissue. GOSPER and ASH keep Conway's rule exactly and record the whole
run as a solid in (x, y, t): every live cell becomes a unit of volume, and a
history you would otherwise have to watch becomes an object you can turn around.
One is a machine built on purpose, the other is what random noise settles into
when left alone.

Everything else is inherited from the attractor and protein editions: additive
splatting into a float buffer, log-density tone mapping, multi-scale bloom, the
same three palettes, and a cover frame for the Instagram grid. Colour is driven
by a scalar belonging to the object rather than to the camera -- speed for an
attractor, residue mobility for a protein, and here the age of a cell: how many
generations it has held on. Age is what separates a glider from a block.
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

import automata
import glow


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "instagram" / "phone-9x16"

# The luminous palettes, unchanged, so the artificial-life posts rhyme with the
# mathematics and the proteomics rather than merely coexisting with them.
EMBER = [(255, 0, 90), (255, 90, 0), (255, 205, 40), (60, 255, 170), (0, 190, 255), (120, 80, 255)]
CITRUS = [(0, 255, 190), (140, 255, 40), (255, 230, 0), (255, 120, 0), (255, 40, 110), (170, 60, 255)]
ORCHID = [(255, 200, 60), (255, 110, 40), (255, 40, 140), (200, 40, 255), (90, 90, 255), (0, 220, 235)]

SEED = 20260814

EDITIONS: dict[str, dict] = {
    "culture": {
        "kind": "colony",
        "title": "Culture",
        "palette": ORCHID,
        "slug": "culture_orchid-gold_wetware",
        "cells": 7500,
        "neighbours": 14,
        "seeds": 12,
        "inhibit": 0.34,
        "recovery": 0.10,
        "warmup": 160,
        "breaths": 3.0,
        "exposure": 1.22,
        "boost": 1.22,
        "caption": (
            "continuous-state life  ·  k = 14",
            "grow if 0.20 < ⟨neighbours⟩ < 0.45",
            "else decay  ·  blue-noise colony",
        ),
    },
    "gosper": {
        "kind": "spacetime",
        "title": "Gosper",
        "palette": CITRUS,
        "slug": "gosper_electric-citrus_spacetime",
        "board": 168,
        "generations": 600,
        "wrap": False,
        "per_cell": 9,
        "time_scale": 0.52,
        "tilt": 15.0,
        "fill": 0.90,
        "exposure": 1.20,
        "boost": 1.28,
        "caption": (
            "B3/S23  ·  Gosper glider gun, 1970",
            "36 cells  ·  one glider every 30 gen",
            "600 generations stacked along t",
        ),
    },
    "ash": {
        "kind": "spacetime",
        "title": "Ash",
        "palette": EMBER,
        "slug": "ash_ember-spectrum_spacetime",
        "board": 208,
        "seed_radius": 56,
        "density": 0.38,
        "generations": 520,
        "wrap": False,
        "per_cell": 5,
        "time_scale": 0.62,
        "tilt": 15.0,
        "fill": 0.92,
        "exposure": 1.18,
        "boost": 1.24,
        "caption": (
            "B3/S23  ·  random soup, 38% fill",
            "520 generations stacked along t",
            "chaos settles into ash and gliders",
        ),
    },
}


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------


def centre_cloud(points: np.ndarray) -> np.ndarray:
    """Put the solid's own bounding centre on the axis the camera turns about.

    Not the mean: the soup's first generations hold most of the samples, and
    centring on them would hang the whole tower off the bottom of the frame.
    """
    low = np.percentile(points, 0.2, axis=0)
    high = np.percentile(points, 99.8, axis=0)
    return (points - (low + high) * 0.5).astype(np.float32)


def project(
    points: np.ndarray,
    yaw: float,
    tilt: float,
    scale: float,
    width: int,
    height: int,
    centre_y: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    cos_yaw, sin_yaw = math.cos(yaw), math.sin(yaw)
    x = points[:, 0] * cos_yaw + points[:, 2] * sin_yaw
    z = -points[:, 0] * sin_yaw + points[:, 2] * cos_yaw
    cos_tilt, sin_tilt = math.cos(tilt), math.sin(tilt)
    screen_y = points[:, 1] * cos_tilt + z * sin_tilt
    depth = -points[:, 1] * sin_tilt + z * cos_tilt
    middle = height * 0.5 if centre_y is None else centre_y
    screen = np.column_stack((x * scale + width * 0.5, -screen_y * scale + middle))
    span = max(float(np.ptp(depth)), 1e-9)
    return screen.astype(np.float32), ((depth - depth.min()) / span).astype(np.float32)


def turn_extent(points: np.ndarray, tilt: float, samples: int = 24) -> tuple[float, float, float]:
    """Widest half-width and the true top and bottom over a whole revolution.

    Measured rather than assumed symmetric: the glider gun's fan reaches into one
    corner only, so mirroring the larger side would shrink the piece to fit a
    margin that is needed on one edge alone.
    """
    stride = max(1, len(points) // 60000)
    sparse = points[::stride]
    half_width, low, high = 0.0, math.inf, -math.inf
    for index in range(samples):
        screen, _ = project(sparse, 2.0 * math.pi * index / samples, tilt, 1.0, 0, 0, 0.0)
        half_width = max(half_width, float(np.percentile(np.abs(screen[:, 0]), 99.7)))
        low = min(low, float(np.percentile(-screen[:, 1], 0.3)))
        high = max(high, float(np.percentile(-screen[:, 1], 99.7)))
    return half_width, low, high


def frame_band(height: int, margin: int, caption_lines: int, gap: int = 24) -> float:
    """Vertical room for the object, symmetric about the middle of the frame."""
    caption_height = caption_lines * 27 + max(0, caption_lines - 1) * 9
    return float(height - 2 * (margin + caption_height + gap))


def fit_scale(
    points: np.ndarray, width: int, tilt: float, fill: float, band: float
) -> tuple[float, float]:
    half_width, low, high = turn_extent(points, tilt)
    half_height = (high - low) * 0.5
    scale = min(
        fill * width / max(2.0 * half_width, 1e-9),
        fill * band / max(2.0 * half_height, 1e-9),
    )
    return scale, (high + low) * 0.5


# --------------------------------------------------------------------------
# Encoding
# --------------------------------------------------------------------------


def splat_density(screen: np.ndarray, weights: np.ndarray, width: int, height: int) -> np.ndarray:
    colours = np.zeros((len(screen), 3), dtype=np.float32)
    _, density = glow.splat(width, height, screen, colours, weights)
    return density


def pick_cover_yaw(
    points: np.ndarray, tilt: float, scale: float, width: int, height: int, centre_y: float
) -> float:
    """The turn angle whose silhouette fills the frame best, for the thumbnail."""
    sparse = points[:: max(1, len(points) // 40000)]
    weights = np.ones(len(sparse), dtype=np.float32)
    best_yaw, best_cover = 0.0, -1.0
    for degrees in range(0, 360, 10):
        yaw = math.radians(degrees)
        screen, _ = project(sparse, yaw, tilt, scale, width, height, centre_y)
        cover = float((splat_density(screen, weights, width, height) > 0).mean())
        if cover > best_cover:
            best_yaw, best_cover = yaw, cover
    return best_yaw


def find_encoder() -> tuple[str, list[str]]:
    """Pick an ffmpeg that can actually encode H.264.

    Conda environments routinely ship one built without libx264; it advertises
    libopenh264 and then fails at runtime with a version mismatch.
    """
    candidates: list[str] = []
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / "ffmpeg"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            candidates.append(str(candidate))
    candidates.append("/usr/bin/ffmpeg")
    fallback: tuple[str, list[str]] | None = None
    for ffmpeg in dict.fromkeys(candidates):
        try:
            encoders = subprocess.run(
                [ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, check=True
            ).stdout
        except (OSError, subprocess.CalledProcessError):
            continue
        if " libx264 " in encoders:
            return ffmpeg, ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high"]
        if fallback is None and " libopenh264 " in encoders:
            fallback = (ffmpeg, ["-c:v", "libopenh264", "-threads", "1", "-b:v", "12M", "-maxrate", "16M"])
    if fallback is not None:
        return fallback
    raise RuntimeError("No ffmpeg with an H.264 encoder was found.")


def start_encoder(output: Path, width: int, height: int, fps: int) -> subprocess.Popen[bytes]:
    if width % 2 or height % 2:
        # yuv420p subsamples chroma by two; an odd dimension makes libx264 fail
        # with a message that says nothing about the actual cause.
        raise ValueError(f"H.264 needs even dimensions; got {width}x{height}.")
    ffmpeg, codec = find_encoder()
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}", "-r", str(fps), "-i", "-",
        "-an", *codec, "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output),
    ]
    return subprocess.Popen(command, stdin=subprocess.PIPE)


def emit(frames, output: Path, cover: np.ndarray, width: int, height: int, fps: int) -> Path:
    """Write the cover frame first, then the clip, and save the cover as a PNG."""
    encoder = start_encoder(output, width, height, fps)
    assert encoder.stdin is not None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(cover).save(output.with_suffix(".cover.png"))
        encoder.stdin.write(cover.tobytes())
        for frame in frames:
            encoder.stdin.write(frame.tobytes())
    finally:
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError(f"ffmpeg failed while writing {output.name}.")
    return output


# --------------------------------------------------------------------------
# Life recorded as a solid in space and time
# --------------------------------------------------------------------------


def build_spacetime(name: str, spec: dict, rng: np.random.Generator) -> dict[str, np.ndarray]:
    board = spec["board"]
    grid = np.zeros((board, board), dtype=np.uint8)
    if name == "gosper":
        # Set the gun in one corner so its gliders have the whole board to cross;
        # over 600 generations the first one travels 148 cells, which is the
        # board, so the fan reaches the far edge exactly as the run ends.
        for column, row in automata.GOSPER_GUN:
            grid[row + 6, column + 6] = 1
    else:
        # Seeded inside a disc on an open board rather than filling a torus: the
        # silhouette becomes a column instead of a cube, and gliders leaving the
        # crowd get empty space to cross rather than wrapping back into it.
        centre = board / 2.0
        rows, columns = np.mgrid[0:board, 0:board]
        inside = (rows - centre) ** 2 + (columns - centre) ** 2 < spec["seed_radius"] ** 2
        grid[inside & (rng.random((board, board)) < spec["density"])] = 1
    return automata.evolve(grid, (3,), (2, 3), spec["generations"], wrap=spec["wrap"])


def render_spacetime(name: str, spec: dict, args: argparse.Namespace) -> Path:
    width, height = args.width, args.height
    frames = round(args.duration * args.fps)
    tilt = math.radians(spec["tilt"])
    rng = np.random.default_rng(SEED)

    cloud = build_spacetime(name, spec, rng)
    points, age = automata.voxels(cloud, spec["per_cell"], spec["time_scale"], rng)
    points = centre_cloud(points)
    print(
        f"  {name}: {len(cloud['x']):,} live cells over {spec['generations']} generations"
        f"  ->  {len(points):,} samples",
        flush=True,
    )

    # Age spans three orders of magnitude and is heavily skewed towards the
    # transient, so it is read logarithmically; a linear ramp would put every
    # glider and nearly every oscillator in the same colour.
    shade = (np.log1p(age) / math.log1p(float(age.max()))).astype(np.float32)
    palette = glow.build_palette(spec["palette"])
    colours = glow.sample_palette(palette, shade)
    weights = np.ones(len(points), dtype=np.float32)

    band = frame_band(height, args.margin, len(spec["caption"]))
    scale, model_middle = fit_scale(points, width, tilt, spec["fill"], band)
    centre_y = height * 0.5 + model_middle * scale
    caption = glow.make_caption(width, height, spec["title"], spec["caption"], margin=args.margin)
    cover_yaw = pick_cover_yaw(points, tilt, scale, width, height, centre_y)

    references: list[float] = []
    for probe in range(6):
        screen, _ = project(points, 2.0 * math.pi * probe / 6, tilt, scale, width, height, centre_y)
        density = splat_density(screen, weights, width, height)
        positive = density[density > 0]
        if positive.size:
            references.append(float(np.percentile(positive, 92.0)))
    reference = float(np.mean(references))

    def draw(count: int, yaw: float) -> np.ndarray:
        screen, depth = project(points[:count], yaw, tilt, scale, width, height, centre_y)
        near = (1.0 - args.fog) + args.fog * depth
        colour_sum, density = glow.splat(
            width, height, screen, colours[:count] * near[:, None], weights[:count]
        )
        linear = glow.flame_map(colour_sum, density, reference, boost=spec["boost"])
        linear = glow.bloom(linear, threshold=args.bloom_threshold, strength=args.bloom_strength)
        return glow.compose(glow.to_bytes(glow.tone_map(linear, exposure=spec["exposure"])), caption)

    # Samples come out of `evolve` in generation order, so everything computed by
    # a given moment is a prefix and the tower can build itself upward.
    times = points[:, 1]
    order = np.argsort(times, kind="stable")
    assert bool((np.diff(times[order]) >= 0).all())
    top, bottom = float(times.max()), float(times.min())

    def revealed(index: int) -> int:
        elapsed = min(index / max((frames - 1) * args.growth_end, 1e-9), 1.0)
        eased = elapsed ** args.growth_shape
        return max(int(np.searchsorted(times, bottom + (top - bottom) * eased, side="right")), 2)

    def clip():
        for index in range(1, frames):
            turn = (index - 1) / (frames - 1)
            yield draw(revealed(index - 1), 2.0 * math.pi * turn)
            if index % 60 == 0:
                print(f"  {name}: frame {index}/{frames}", flush=True)

    stem = f"{spec['slug']}_{width}x{height}_{args.duration:g}s_{args.fps}fps"
    cover = draw(len(points), cover_yaw)
    if args.preview:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        path = args.output_dir / f"{stem}.preview.png"
        Image.fromarray(cover).save(path)
        return path
    return emit(clip(), args.output_dir / f"{stem}.mp4", cover, width, height, args.fps)


# --------------------------------------------------------------------------
# Life as a continuous field on a colony of cells
# --------------------------------------------------------------------------


def colony_offsets(count: int, per_cell: int, rng: np.random.Generator) -> np.ndarray:
    """Fixed unit-disc offsets for every cell, drawn once for the whole clip.

    Redrawing them each frame puts every cell's dot cloud somewhere new thirty
    times a second. On screen the dish boils; to the encoder it is fresh noise in
    every frame, which cost 61 MB for twelve seconds and is the first thing a
    re-encode destroys. Fixing the pattern and letting only the radius and the
    brightness follow the state keeps the motion in the tissue, where it belongs.
    """
    angle = rng.uniform(0.0, 2.0 * math.pi, (count, per_cell))
    reach = np.sqrt(rng.random((count, per_cell)))
    return np.stack((np.cos(angle) * reach, np.sin(angle) * reach), axis=2)


def colony_samples(
    positions: np.ndarray,
    state: np.ndarray,
    offsets: np.ndarray,
    cell_radius: float,
    ceiling: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Each cell as a small disc of light that swells and brightens with state."""
    per_cell = offsets.shape[1]
    radius = cell_radius * (1.0 + 2.0 * state)
    points = (positions[:, None, :] + offsets * radius[:, None, None]).reshape(-1, 2)
    weight = np.repeat((0.06 + 0.94 * state).astype(np.float32), per_cell)
    # The rule settles well short of 1, so the palette is stretched to the range
    # the tissue actually reaches; read raw, every crest lands mid-ramp and the
    # whole dish comes out one flat violet.
    shade = np.repeat(1.0 - np.clip(state / ceiling, 0.0, 1.0), per_cell)
    return points, shade, weight


def halo_pattern(per_core: int) -> tuple[np.ndarray, ...]:
    """One fixed sunflower of offsets, reused by every core and every frame.

    Golden-angle spacing so a few hundred points cover the disc evenly without
    ever landing on a repeating spoke.
    """
    index = np.arange(per_core)
    angle = index * 2.399963229728653
    band = index % 5
    base = np.where(band < 2, 5.0, 10.0)
    gain = np.where(band < 2, 8.0, np.where(band < 4, 12.0, 20.0))
    spread = np.where(band < 4, 1.0, np.sqrt((index + 0.5) / per_core))
    weight = np.where(band < 2, 0.55, np.where(band < 4, 0.22, 0.10)).astype(np.float32)
    return np.column_stack((np.cos(angle), np.sin(angle))), base, gain, spread, weight


def halo_samples(
    centres: np.ndarray, intensity: np.ndarray, pattern: tuple[np.ndarray, ...], unit: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The bright cores: a tight ring, a wider fainter one, and a soft glow."""
    direction, base, gain, spread, weight = pattern
    if not len(centres):
        return np.zeros((0, 2)), np.zeros(0), np.zeros(0, dtype=np.float32)
    radius = unit * (base[None, :] + gain[None, :] * intensity[:, None]) * spread[None, :]
    points = (centres[:, None, :] + direction[None, :, :] * radius[:, :, None]).reshape(-1, 2)
    return points, np.full(len(points), 0.02), np.tile(weight, len(centres))


def wave_samples(
    rings: list[dict], lifetime: float, sigma: float, count: int, bound: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The propagating fronts, drawn as the circles they are.

    Sampled at fixed angles with a phase derived from the ring's own centre, so a
    front expands smoothly instead of reshuffling its dots every frame. Clipped
    to the colony too: a ring keeps growing for its whole life whether or not
    there is any tissue left out there, and the part that has run off the edge
    hangs loose arcs in the black around the dish.
    """
    positions: list[np.ndarray] = []
    shades: list[np.ndarray] = []
    weights: list[np.ndarray] = []
    slot = 2.0 * math.pi * np.arange(count) / count
    for ring in rings:
        radius = float(ring["radius"])
        alpha = 1.0 - float(ring["age"]) / lifetime
        if radius <= 0.0 or alpha <= 0.0:
            continue
        centre = np.asarray(ring["centre"])
        phase = float((centre[0] * 7.31 + centre[1] * 3.17) % (2.0 * math.pi))
        angle = slot + phase
        offset = radius + sigma * np.cos(angle * 9.0 + phase * 5.0)
        drawn = centre + np.column_stack((np.cos(angle), np.sin(angle))) * offset[:, None]
        drawn = drawn[np.linalg.norm(drawn, axis=1) <= bound]
        if not len(drawn):
            continue
        positions.append(drawn)
        shades.append(np.full(len(drawn), 0.30))
        weights.append(np.full(len(drawn), 0.16 * alpha, dtype=np.float32))
    if not positions:
        return np.zeros((0, 2)), np.zeros(0), np.zeros(0, dtype=np.float32)
    return np.concatenate(positions), np.concatenate(shades), np.concatenate(weights)


def render_colony(name: str, spec: dict, args: argparse.Namespace) -> Path:
    width, height = args.width, args.height
    frames = round(args.duration * args.fps)
    rng = np.random.default_rng(SEED)

    radius = 1.0
    positions = automata.colony_positions(radius, spec["cells"], rng)
    colony = automata.Colony(
        positions, spec["neighbours"], rng, inhibit=spec["inhibit"], recovery=spec["recovery"]
    )
    colony.seed(spec["seeds"], sigma=0.10)
    print(f"  {name}: {len(positions):,} cells, k = {spec['neighbours']}", flush=True)

    band = frame_band(height, args.margin, len(spec["caption"]))
    scale = min(args.fill * width, args.fill * band) * 0.5 / radius
    unit = 1.0 / scale  # one screen pixel, in colony units
    palette = glow.build_palette(spec["palette"])
    caption = glow.make_caption(width, height, spec["title"], spec["caption"], margin=args.margin)

    # Loopable drift: whole-cycle harmonics, so the last frame meets the first.
    direction = rng.uniform(0.0, 2.0 * math.pi, (2, len(positions)))
    drift = np.stack((np.cos(direction), np.sin(direction)), axis=2) * (2.0 * unit)
    phase = rng.uniform(0.0, 2.0 * math.pi, 2)

    step = {
        "dt": args.dt,
        "ring_speed": args.ring_speed,
        "ring_lifetime": args.ring_lifetime,
        "ring_sigma": args.ring_sigma,
        "spawn": args.spawn,
    }
    for _ in range(spec["warmup"]):
        colony.advance(**step)

    def place(turn: float) -> np.ndarray:
        scaled = positions * automata.breath(turn * spec["breaths"])
        scaled = scaled + drift[0] * math.cos(2.0 * math.pi * turn + phase[0])
        return scaled + drift[1] * math.cos(4.0 * math.pi * turn + phase[1])

    offsets = colony_offsets(len(positions), args.cell_samples, rng)
    cores_pattern = halo_pattern(args.core_samples)

    def gather(turn: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        moved = place(turn)
        cells = colony_samples(moved, colony.state, offsets, args.cell_radius * unit, args.state_ceiling)
        cores = colony.local_maxima(args.core_threshold)
        halos = halo_samples(moved[cores], colony.state[cores], cores_pattern, unit)
        waves = wave_samples(colony.rings, args.ring_lifetime, args.ring_sigma, args.wave_samples, radius)
        return tuple(np.concatenate(parts) for parts in zip(cells, halos, waves))

    def compose(sample: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
        world, shade, weight = sample
        screen = np.column_stack((world[:, 0] * scale + width * 0.5, -world[:, 1] * scale + height * 0.5))
        colour_sum, density = glow.splat(
            width, height, screen.astype(np.float32), glow.sample_palette(palette, shade), weight
        )
        linear = glow.flame_map(colour_sum, density, reference, boost=spec["boost"])
        linear = glow.bloom(linear, threshold=args.bloom_threshold, strength=args.bloom_strength)
        return glow.compose(glow.to_bytes(glow.tone_map(linear, exposure=spec["exposure"])), caption)

    probe = gather(0.55 / spec["breaths"])
    density = splat_density(
        np.column_stack((probe[0][:, 0] * scale + width * 0.5, -probe[0][:, 1] * scale + height * 0.5)).astype(np.float32),
        probe[2], width, height,
    )
    positive = density[density > 0]
    reference = float(np.percentile(positive, 92.0))

    cover = compose(probe)
    stem = f"{spec['slug']}_{width}x{height}_{args.duration:g}s_{args.fps}fps"
    if args.preview:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        path = args.output_dir / f"{stem}.preview.png"
        Image.fromarray(cover).save(path)
        return path

    def clip():
        for index in range(1, frames):
            colony.advance(**step)
            yield compose(gather((index - 1) / (frames - 1)))
            if index % 60 == 0:
                print(f"  {name}: frame {index}/{frames}", flush=True)

    return emit(clip(), args.output_dir / f"{stem}.mp4", cover, width, height, args.fps)


def render_edition(name: str, args: argparse.Namespace) -> Path:
    spec = EDITIONS[name]
    if spec["kind"] == "colony":
        return render_colony(name, spec, args)
    return render_spacetime(name, spec, args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", choices=sorted(EDITIONS), action="append")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--preview", action="store_true", help="Save the cover still and stop.")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--duration", type=float, default=12)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--margin", type=int, default=64, help="inset for title and caption")
    parser.add_argument("--fill", type=float, default=0.92)
    parser.add_argument("--fog", type=float, default=0.70)
    parser.add_argument("--growth-end", type=float, default=0.88)
    parser.add_argument("--growth-shape", type=float, default=1.0)
    parser.add_argument("--bloom-threshold", type=float, default=0.30)
    parser.add_argument("--bloom-strength", type=float, default=0.60)
    # Continuous colony
    parser.add_argument("--dt", type=float, default=0.03)
    parser.add_argument("--ring-speed", type=float, default=0.4)
    parser.add_argument("--ring-lifetime", type=float, default=2.5)
    parser.add_argument("--ring-sigma", type=float, default=0.012)
    parser.add_argument("--spawn", type=float, default=0.30)
    parser.add_argument("--state-ceiling", type=float, default=0.65)
    parser.add_argument("--cell-radius", type=float, default=1.1, help="quiet cell radius, in pixels")
    parser.add_argument("--cell-samples", type=int, default=6, help="fixed splats per cell")
    parser.add_argument("--core-threshold", type=float, default=0.72)
    parser.add_argument("--core-samples", type=int, default=120)
    parser.add_argument("--wave-samples", type=int, default=520, help="splats around each front")
    return parser.parse_args()


if __name__ == "__main__":
    options = parse_args()
    for edition_name in options.edition or list(EDITIONS):
        print(f"Rendering {edition_name} ...", flush=True)
        print(f"Saved {render_edition(edition_name, options)}", flush=True)
