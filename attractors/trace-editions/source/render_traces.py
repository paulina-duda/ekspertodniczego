#!/usr/bin/env python3
"""Attractors drawn as continuous traces, in the luminous house style.

The earlier emergence project splats one point per integration step, and at the
shipped framing consecutive steps land three to twenty pixels apart, so every
trajectory is a dotted trail. The image only looks continuous because twelve
hundred of them overlap, which is why it reads as accumulating density rather
than as lines being drawn.

Here each step is subdivided until successive splats nearly touch, so a
trajectory is a genuine unbroken filament, and far fewer are integrated so the
individual strands and the bands they braid into stay legible.

A bright head on each strand's leading edge was tried and removed. With this
many strands a head spanning few enough steps to read as a point contributes
too few samples to survive the bloom, and one wide enough to survive is a long
bright arc rather than a pen tip: at a gain of 25 it moved 2% of the frame's
pixels without ever looking like the place the drawing was happening.

Everything else is inherited: one 360 degree turn with a tilt sway, the luminous
palettes and speed bounds, additive glow, bloom, log-density tone mapping, and a
cover frame of the finished attractor for the Instagram grid.
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
import systems


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "instagram" / "phone-9x16"

EMBER = [(255, 0, 90), (255, 90, 0), (255, 205, 40), (60, 255, 170), (0, 190, 255), (120, 80, 255)]
CITRUS = [(0, 255, 190), (140, 255, 40), (255, 230, 0), (255, 120, 0), (255, 40, 110), (170, 60, 255)]
ORCHID = [(255, 200, 60), (255, 110, 40), (255, 40, 140), (200, 40, 255), (90, 90, 255), (0, 220, 235)]

# Greek where the literature is Greek. Aizawa's a..f really are Latin in the
# standard formulation, so they stay as they are.
EDITIONS: dict[str, dict] = {
    "lorenz": {
        "title": "Lorenz",
        "palette": EMBER,
        "slug": "lorenz_ember-spectrum_trace",
        "tilt": 14.0,
        "fill": 0.97,
        "exposure": 1.20,
        "boost": 1.25,
        "equation": (
            "dx/dt = σ (y - x)",
            "dy/dt = x (ρ - z) - y",
            "dz/dt = x y - β z",
            "",
            "σ = 10   ρ = 28   β = 8/3",
        ),
    },
    "aizawa": {
        "title": "Aizawa",
        "palette": ORCHID,
        "slug": "aizawa_orchid-gold_trace",
        "tilt": 18.0,
        "fill": 0.94,
        "exposure": 1.22,
        "boost": 1.30,
        "equation": (
            "dx/dt = (z-b)x - d y",
            "dy/dt = d x + (z-b)y",
            "dz/dt = c + a z - z³/3",
            "        - (x²+y²)(1+e z) + f z x³",
            "",
            "a=0.95  b=0.7   c=0.6",
            "d=3.5   e=0.25  f=0.1",
        ),
    },
    "halvorsen": {
        "title": "Halvorsen",
        "palette": CITRUS,
        "slug": "halvorsen_electric-citrus_trace",
        "tilt": 20.0,
        "fill": 0.94,
        "exposure": 1.20,
        "boost": 1.25,
        "equation": (
            "dx/dt = -α x - 4y - 4z - y²",
            "dy/dt = -α y - 4z - 4x - z²",
            "dz/dt = -α z - 4x - 4y - x²",
            "",
            "α = 1.4",
        ),
    },
}


def splat_density(screen: np.ndarray, weights: np.ndarray, width: int, height: int) -> np.ndarray:
    colours = np.zeros((len(screen), 3), dtype=np.float32)
    _, density = glow.splat(width, height, screen, colours, weights)
    return density


def growth_curve(
    screen: np.ndarray,
    weights: np.ndarray,
    ages: np.ndarray,
    width: int,
    height: int,
    chunks: int = 64,
) -> tuple[np.ndarray, np.ndarray]:
    """Measure how much the image grows as the traces extend.

    Samples do not contribute evenly, so drawing them at a steady rate gives a
    crawl and then a bang: while the trajectories are still bunched they retrace
    one curve and add nothing, and once they separate a small slice of the run
    paints most of the picture. Splatting in age order into a running density
    buffer -- one full splat, not one per probe -- gives a curve that inverts
    into an even schedule.

    The metric is mean log density rather than covered area because the tone
    mapper is logarithmic, and late samples thicken what is already lit instead
    of lighting anything new.
    """
    density = np.zeros((height, width), dtype=np.float32)
    edges = np.linspace(0, len(screen), chunks + 1).astype(int)
    grown: list[float] = [0.0]
    age_at: list[float] = [0.0]
    for start, stop in zip(edges[:-1], edges[1:]):
        if stop <= start:
            continue
        density += splat_density(screen[start:stop], weights[start:stop], width, height)
        grown.append(float(np.log1p(density).mean()))
        age_at.append(float(ages[stop - 1]))
    grown_array = np.asarray(grown, dtype=np.float64)
    grown_array /= max(grown_array[-1], 1e-12)
    grown_array = np.maximum.accumulate(grown_array + np.arange(len(grown_array)) * 1e-9)
    return grown_array, np.asarray(age_at, dtype=np.float64)


def pick_cover_yaw(
    points: np.ndarray, tilt: float, scale: float, width: int, height: int, stride: int = 24
) -> float:
    """The turn angle whose silhouette fills the frame best, for the thumbnail."""
    sparse = points[::stride]
    weights = np.ones(len(sparse), dtype=np.float32)
    best_yaw, best_cover = 0.0, -1.0
    for degrees in range(0, 360, 10):
        yaw = math.radians(degrees)
        screen, _ = systems.project(sparse, yaw, tilt, scale, width, height)
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


def render_edition(name: str, args: argparse.Namespace) -> Path:
    spec = EDITIONS[name]
    width, height = args.width, args.height
    frames = round(args.duration * args.fps)
    base_tilt = math.radians(spec["tilt"])

    speed_range = systems.reference_speed_range(name)
    points, shade, ages = systems.sample_traces(
        name,
        trajectories=args.trajectories,
        steps=args.steps,
        warmup=args.warmup,
        spread=args.spread,
        pixels_per_radius=spec["fill"] * width / 2.0,
        speed_range=speed_range,
    )
    print(f"  {name}: {len(points):,} trace samples", flush=True)

    palette = glow.build_palette(spec["palette"])
    colours = glow.sample_palette(palette, shade)
    weights = np.ones(len(points), dtype=np.float32)
    scale = systems.fit_scale(points, width, height, base_tilt, spec["fill"])
    caption = glow.make_caption(width, height, spec["title"], spec["equation"])

    base_screen, _ = systems.project(points, 0.0, base_tilt, scale, width, height)
    growth, growth_age = growth_curve(base_screen, weights, ages, width, height)
    del base_screen
    cover_yaw = pick_cover_yaw(points, base_tilt, scale, width, height)

    def camera(index: int) -> tuple[float, float]:
        turn = index / max(frames - 1, 1)
        return (
            2.0 * math.pi * turn,
            base_tilt + math.radians(3.0) * math.sin(2.0 * math.pi * turn),
        )

    def revealed(index: int) -> float:
        elapsed = min(index / max((frames - 1) * args.growth_end, 1e-9), 1.0)
        return max(
            float(np.interp(elapsed ** args.growth_shape, growth, growth_age)), args.seed_fraction
        )

    references: list[float] = []
    for probe in range(6):
        yaw, tilt = camera(round(probe * frames / 6))
        screen, _ = systems.project(points, yaw, tilt, scale, width, height)
        density = splat_density(screen, weights, width, height)
        positive = density[density > 0]
        if positive.size:
            references.append(float(np.percentile(positive, 92.0)))
    reference = float(np.mean(references))

    def draw(count: int, yaw: float, tilt: float) -> np.ndarray:
        screen, depth = systems.project(points[:count], yaw, tilt, scale, width, height)
        shaded = colours[:count] * (0.60 + 0.40 * depth)[:, None]
        colour_sum, density = glow.splat(width, height, screen, shaded, weights[:count])
        linear = glow.flame_map(colour_sum, density, reference, boost=spec["boost"])
        linear = glow.bloom(linear, threshold=args.bloom_threshold, strength=args.bloom_strength)
        return glow.compose(glow.to_bytes(glow.tone_map(linear, exposure=spec["exposure"])), caption)

    stem = f"{spec['slug']}_{width}x{height}_{args.duration:g}s_{args.fps}fps"
    output = args.output_dir / f"{stem}.mp4"
    encoder = start_encoder(output, width, height, args.fps)
    assert encoder.stdin is not None
    try:
        # Frame one: the finished attractor, for the grid thumbnail.
        cover = draw(len(points), cover_yaw, base_tilt)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        Image.fromarray(cover).save(args.output_dir / f"{stem}.cover.png")
        encoder.stdin.write(cover.tobytes())

        for index in range(1, frames):
            yaw, tilt = camera(index - 1)
            count = max(int(np.searchsorted(ages, revealed(index - 1), side="right")), 2)
            encoder.stdin.write(draw(count, yaw, tilt).tobytes())
            if index % 60 == 0:
                print(f"  {name}: frame {index}/{frames}  drawn {count/len(points):.1%}", flush=True)
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
    # Few strands on purpose: subdivision makes each one continuous, so the
    # attractor fills in without needing a crowd, and the individual bands stay
    # readable. The finished frame is within a point of the same coverage at
    # forty strands as at three hundred.
    parser.add_argument("--trajectories", type=int, default=72)
    parser.add_argument("--steps", type=int, default=9000)
    # Started together but already on the attractor: off it, the launch
    # transient crosses the frame at high speed, and colour follows speed, so it
    # arrives violet.
    parser.add_argument("--warmup", type=int, default=1400)
    parser.add_argument("--spread", type=float, default=0.02)
    parser.add_argument("--seed-fraction", type=float, default=0.002)
    parser.add_argument("--growth-end", type=float, default=0.86)
    parser.add_argument("--growth-shape", type=float, default=1.5)
    parser.add_argument("--bloom-threshold", type=float, default=0.30)
    parser.add_argument("--bloom-strength", type=float, default=0.60)
    return parser.parse_args()


if __name__ == "__main__":
    options = parse_args()
    for edition_name in options.edition or list(EDITIONS):
        print(f"Rendering {edition_name} ...", flush=True)
        print(f"Saved {render_edition(edition_name, options)}", flush=True)
