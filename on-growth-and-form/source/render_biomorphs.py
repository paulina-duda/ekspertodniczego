#!/usr/bin/env python3
"""Three morphogenesis algorithms, rendered as wetware.

Same house style as the attractor and protein pieces -- black field, additive
accumulation, multi-scale bloom, log-density tone mapping, spaced title,
monospace caption, a cover frame of the finished form for the grid -- but the
palettes move to the cyan-and-magenta end, and what the pieces are *of* is a
process rather than an object.

Each clip opens on the finished form and then plays its growth from the first
step. Growth is the only motion: these are plane processes, and turning them
would be a camera move pasted onto something that does not have a far side.
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

import glow
import morphogens


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "instagram" / "phone-9x16"

# Cyberpunk rather than the attractors' spectrum ramps: these stay inside the
# violet-magenta-cyan band that reads as circuitry, and only reach white where
# the process is densest.
SYNAPSE = [(6, 0, 28), (86, 0, 150), (208, 0, 160), (255, 60, 190), (0, 225, 255), (200, 255, 255)]
CULTURE = [(0, 14, 10), (0, 110, 70), (86, 235, 70), (200, 255, 110), (240, 255, 220)]
FILAMENT_A = [(0, 8, 24), (0, 78, 140), (0, 190, 245), (170, 250, 255)]
FILAMENT_B = [(26, 0, 20), (128, 0, 92), (245, 0, 140), (255, 175, 220)]

EDITIONS: dict[str, dict] = {
    "turing": {
        "kind": "field",
        "title": "Turing",
        "slug": "turing_gray-scott_synapse",
        "palette": SYNAPSE,
        "exposure": 1.18,
        "boost": 1.30,
        "steps_per_frame": 140,
        "settle": 1200,
        "caption": (
            "Gray-Scott reaction-diffusion",
            "∂u/∂t = Dᵤ∇²u - uv² + F(1-u)",
            "∂v/∂t = Dᵥ∇²v + uv² - (F+k)v",
            "F 0.0300  ·  k 0.0620",
        ),
    },
    "physarum": {
        "kind": "physarum",
        "title": "Physarum",
        "slug": "physarum_transport-network_filament",
        "palette": FILAMENT_A,
        "palette_b": FILAMENT_B,
        "exposure": 1.24,
        "boost": 1.20,
        "steps_per_frame": 3,
        "settle": 0,
        "caption": (
            "slime mould transport network",
            "sense · turn · move · deposit",
            "600,000 agents  ·  two species",
            "sensor 28°  ·  turn 34°",
        ),
    },
    "folding": {
        "kind": "curve",
        "title": "Folding",
        "slug": "folding_differential-growth_culture",
        "palette": CULTURE,
        "exposure": 1.20,
        "boost": 1.25,
        "steps_per_frame": 4,
        "settle": 0,
        "caption": (
            "differential growth",
            "attract · repel · subdivide",
            "a closed curve that must lengthen",
            "and may not touch itself",
        ),
    },
}


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


def upsample(field: np.ndarray, height: int, width: int) -> np.ndarray:
    """Nearest-neighbour block upsample for fields simulated below frame size."""
    if field.shape == (height, width):
        return field
    rows = height // field.shape[0]
    columns = width // field.shape[1]
    return np.repeat(np.repeat(field, rows, axis=0), columns, axis=1)[:height, :width]


def compose_field(
    channels: list[tuple[np.ndarray, np.ndarray, np.ndarray]],
    reference: float,
    spec: dict,
    args: argparse.Namespace,
    caption: Image.Image,
) -> np.ndarray:
    """Tone map one or more scalar fields through their palettes.

    Each channel is a (density, shade, palette) triple. Keeping density and
    shade separate is the point: brightness should follow how much process is
    there, while hue can follow something else entirely -- for Turing it follows
    when each cell first lit, which turns the colony into growth rings.

    The pipeline is otherwise the attractors' pipeline with the splat step
    removed: a field is already an accumulation buffer, so it goes straight into
    the same log-density map. Summing the channels is what lets the two Physarum
    populations blend where they overlap instead of one painting over the other.
    """
    colour_sum = None
    density = None
    for field, shade, palette in channels:
        colour = glow.sample_palette(palette, np.clip(shade, 0.0, 1.0).astype(np.float32))
        weighted = colour * field[:, :, None]
        colour_sum = weighted if colour_sum is None else colour_sum + weighted
        density = field if density is None else density + field
    linear = glow.flame_map(colour_sum, density, reference, boost=spec["boost"])
    linear = glow.bloom(linear, threshold=args.bloom_threshold, strength=args.bloom_strength)
    frame = glow.to_bytes(glow.tone_map(linear, exposure=spec["exposure"]))
    return glow.compose(frame, caption)


def field_channels(model, spec, palette, palette_b, height, width, reference):
    """Build the (density, shade, palette) channels for a field edition."""
    if spec["kind"] == "physarum":
        a, b = model.field()
        a, b = upsample(a, height, width), upsample(b, height, width)
        scale = 1.0 / max(reference or 1.0, 1e-9)
        return [(a, a * scale, palette), (b, b * scale, palette_b)]
    field = upsample(model.field(), height, width)
    return [(field, upsample(model.growth_rings(), height, width), palette)]


def curve_samples(points: np.ndarray, target: float = 0.6) -> np.ndarray:
    """Subdivide a closed polyline so successive samples nearly touch.

    Without this the curve is drawn as a string of dots wherever it runs fast
    across the frame -- the same problem the attractor traces had, and the same
    fix.
    """
    following = np.roll(points, -1, axis=0)
    delta = following - points
    length = np.linalg.norm(delta, axis=1)
    counts = np.clip(np.ceil(length / target), 1, 32).astype(np.int64)
    total = int(counts.sum())
    segment = np.repeat(np.arange(counts.size, dtype=np.int64), counts)
    starts = np.zeros(counts.size + 1, dtype=np.int64)
    np.cumsum(counts, out=starts[1:])
    fraction = ((np.arange(total, dtype=np.int64) - starts[segment]) / counts[segment]).astype(np.float32)
    return (points[segment] + fraction[:, None] * delta[segment]).astype(np.float32), segment


def build(name: str, args: argparse.Namespace):
    """Create a fresh model for an edition, deterministically."""
    spec = EDITIONS[name]
    if spec["kind"] == "field":
        # Solitons: spots that divide and colonise outwards from one seed,
        # which both tells the growth story and leaves black around the colony.
        # The maze-forming regimes fill the frame edge to edge and bury the
        # caption under texture.
        return morphogens.GrayScott(
            args.height // args.field_divisor,
            args.width // args.field_divisor,
            feed=0.0300,
            kill=0.0620,
            seeds=3,
        )
    if spec["kind"] == "physarum":
        return morphogens.Physarum(args.height, args.width, agents=args.agents)
    return morphogens.DifferentialGrowth(
        (args.width * 0.5, args.height * 0.5), 55.0, nodes=200, spacing=2.5, repulsion_radius=11.0
    )


def render_edition(name: str, args: argparse.Namespace) -> Path:
    spec = EDITIONS[name]
    width, height = args.width, args.height
    frames = round(args.duration * args.fps)
    caption = glow.make_caption(width, height, spec["title"], spec["caption"])
    palette = glow.build_palette(spec["palette"])
    palette_b = glow.build_palette(spec["palette_b"]) if "palette_b" in spec else None

    # First pass: run the process to completion. The finished form is both the
    # cover frame and what the exposure is calibrated on, so that the clip
    # brightens into its final state instead of being levelled frame by frame.
    print(f"  {name}: settling", flush=True)
    model = build(name, args)
    model.step(spec["settle"] + spec["steps_per_frame"] * (frames - 1))

    if spec["kind"] == "curve":
        final_points = model.points.copy()
        span = final_points.max(axis=0) - final_points.min(axis=0)
        centre = (final_points.max(axis=0) + final_points.min(axis=0)) * 0.5
        scale = min(args.fill * width / span[0], args.fill * height / span[1])
        print(f"  {name}: {len(final_points):,} nodes, {scale:.2f} px/unit", flush=True)

        def draw(points: np.ndarray, age: np.ndarray) -> np.ndarray:
            samples, segment = curve_samples((points - centre) * scale + np.array([width * 0.5, height * 0.5]))
            # Ranked age, so the palette spreads evenly over the growth history
            # instead of bunching wherever the node count happened to explode.
            rank = (np.argsort(np.argsort(age)) / max(len(age) - 1, 1)).astype(np.float32)
            shade = rank[segment]
            colours = glow.sample_palette(palette, shade)
            colour_sum, density = glow.splat(
                width, height, samples, colours, np.ones(len(samples), dtype=np.float32)
            )
            linear = glow.flame_map(colour_sum, density, reference, boost=spec["boost"])
            linear = glow.bloom(linear, threshold=args.bloom_threshold, strength=args.bloom_strength)
            return glow.compose(glow.to_bytes(glow.tone_map(linear, exposure=spec["exposure"])), caption)

        samples, _ = curve_samples((final_points - centre) * scale + np.array([width * 0.5, height * 0.5]))
        _, probe = glow.splat(
            width, height, samples, np.zeros((len(samples), 3), dtype=np.float32),
            np.ones(len(samples), dtype=np.float32),
        )
        reference = float(np.percentile(probe[probe > 0], 92.0))
        cover = draw(final_points, model.age)
    else:
        channels = field_channels(model, spec, palette, palette_b, height, width, None)
        stacked = sum(channel[0] for channel in channels)
        reference = float(np.percentile(stacked[stacked > 0], 99.0))
        channels = field_channels(model, spec, palette, palette_b, height, width, reference)
        cover = compose_field(channels, reference, spec, args, caption)

    stem = f"{spec['slug']}_{width}x{height}_{args.duration:g}s_{args.fps}fps"
    output = args.output_dir / f"{stem}.mp4"
    encoder = start_encoder(output, width, height, args.fps)
    assert encoder.stdin is not None
    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        Image.fromarray(cover).save(args.output_dir / f"{stem}.cover.png")
        encoder.stdin.write(cover.tobytes())

        # Second pass, from the same seed, emitting a frame as it goes.
        model = build(name, args)
        if spec["settle"]:
            model.step(spec["settle"])
        for index in range(1, frames):
            if index > 1:
                model.step(spec["steps_per_frame"])
            if spec["kind"] == "curve":
                frame = draw(model.points, model.age)
            else:
                frame = compose_field(
                    field_channels(model, spec, palette, palette_b, height, width, reference),
                    reference, spec, args, caption,
                )
            encoder.stdin.write(frame.tobytes())
            if index % 60 == 0:
                print(f"  {name}: frame {index}/{frames}", flush=True)
    finally:
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError(f"ffmpeg failed while rendering {name}.")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", choices=sorted(EDITIONS), action="append")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--duration", type=float, default=12)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--agents", type=int, default=600_000)
    # Reaction-diffusion is smooth on the scale of a pixel, so simulating it at
    # half the frame and upsampling costs nothing visible and quarters the work.
    parser.add_argument("--field-divisor", type=int, default=2)
    parser.add_argument("--fill", type=float, default=0.88)
    parser.add_argument("--bloom-threshold", type=float, default=0.30)
    parser.add_argument("--bloom-strength", type=float, default=0.60)
    return parser.parse_args()


if __name__ == "__main__":
    options = parse_args()
    for edition_name in options.edition or list(EDITIONS):
        print(f"Rendering {edition_name} ...", flush=True)
        print(f"Saved {render_edition(edition_name, options)}", flush=True)
