#!/usr/bin/env python3
"""Render attractors forming, in the luminous house style, as Instagram posts.

Each clip opens on a single cover frame of the finished attractor -- Instagram
takes the first frame as the grid thumbnail -- and then plays the formation from
almost nothing to the complete sculpture.

Everything about the look is inherited from `luminous-editions`: the same single
360 degree turn and tilt sway, the same palettes, the same additive glow, bloom
and log-density tone mapping. Only the growth is new.

The growth is physical rather than a wipe. Every trajectory starts from
essentially the same state on the attractor, so the opening seconds show one
thread; chaos pulls them apart and the sculpture is what that divergence leaves
behind.
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

# Unchanged from the luminous editions, so the set reads as one family.
EMBER = [(255, 0, 90), (255, 90, 0), (255, 205, 40), (60, 255, 170), (0, 190, 255), (120, 80, 255)]
CITRUS = [(0, 255, 190), (140, 255, 40), (255, 230, 0), (255, 120, 0), (255, 40, 110), (170, 60, 255)]
ORCHID = [(255, 200, 60), (255, 110, 40), (255, 40, 140), (200, 40, 255), (90, 90, 255), (0, 220, 235)]

EDITIONS: dict[str, dict] = {
    "lorenz": {
        "title": "Lorenz",
        "palette": EMBER,
        "slug": "lorenz_ember-spectrum_emergence",
        "tilt": 14.0,
        "fill": 0.97,
        "exposure": 1.20,
        "boost": 1.25,
        "equation": (
            "dx/dt = s (y - x)",
            "dy/dt = x (r - z) - y",
            "dz/dt = x y - b z",
            "",
            "s = 10   r = 28   b = 8/3",
        ),
    },
    "aizawa": {
        "title": "Aizawa",
        "palette": ORCHID,
        "slug": "aizawa_orchid-gold_emergence",
        "tilt": 18.0,
        "fill": 0.94,
        "exposure": 1.22,
        "boost": 1.30,
        "equation": (
            "dx/dt = (z-b)x - d y",
            "dy/dt = d x + (z-b)y",
            "dz/dt = c + a z - z^3/3",
            "        - (x^2+y^2)(1+e z) + f z x^3",
            "",
            "a=0.95  b=0.7   c=0.6",
            "d=3.5   e=0.25  f=0.1",
        ),
    },
    "halvorsen": {
        "title": "Halvorsen",
        "palette": CITRUS,
        "slug": "halvorsen_electric-citrus_emergence",
        "tilt": 20.0,
        "fill": 0.94,
        "exposure": 1.20,
        "boost": 1.25,
        "equation": (
            "dx/dt = -a x - 4y - 4z - y^2",
            "dy/dt = -a y - 4z - 4x - z^2",
            "dz/dt = -a z - 4x - 4y - x^2",
            "",
            "a = 1.4",
        ),
    },
}


def smoothstep(value: float) -> float:
    position = min(max(value, 0.0), 1.0)
    return position * position * (3.0 - 2.0 * position)


def splat_density(
    screen: np.ndarray, weights: np.ndarray, width: int, height: int
) -> np.ndarray:
    colours = np.zeros((len(screen), 3), dtype=np.float32)
    _, density = glow.splat(width, height, screen, colours, weights)
    return density


def coverage_curve(
    screen: np.ndarray,
    weights: np.ndarray,
    ages: np.ndarray,
    width: int,
    height: int,
    chunks: int = 64,
) -> tuple[np.ndarray, np.ndarray]:
    """Measure how much the image grows as samples accumulate by age.

    Revealing samples at a steady rate makes a terrible animation, because they
    do not contribute evenly. Measured on the finished Lorenz run: the first
    half of the samples paint about a seventh of the final coverage -- they are
    all retracing one curve -- then a seventh of them paint four fifths of it as
    the trajectories come apart, and the last third lights no new pixels at all.
    Played back linearly that is a crawl, a bang, and a freeze.

    So instead of guessing a curve, measure this one and invert it. Samples are
    splatted in age order into a running density buffer, which costs one full
    splat rather than one per probe.

    The metric is mean log density, not covered area, because the tone mapper is
    logarithmic. Plain coverage would write off the last third of the samples as
    worthless and dump them in at once as a visible pop, when they are in fact
    what thickens the wings.
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
    # np.interp needs a strictly increasing x; the curve plateaus at the end.
    grown_array = np.maximum.accumulate(grown_array + np.arange(len(grown_array)) * 1e-9)
    return grown_array, np.asarray(age_at, dtype=np.float64)


def pick_cover_yaw(
    points: np.ndarray,
    tilt: float,
    scale: float,
    width: int,
    height: int,
    stride: int = 24,
) -> float:
    """Choose the turn angle whose silhouette fills the frame best.

    This frame is the grid thumbnail, so it should be the fullest view of the
    attractor rather than whichever angle the turn happens to start on. Ranking
    is done on every 24th sample -- enough to compare silhouettes, and cheap.
    """
    sparse = points[::stride]
    weights = np.ones(len(sparse), dtype=np.float32)
    best_yaw, best_cover = 0.0, -1.0
    for degrees in range(0, 360, 10):
        yaw = math.radians(degrees)
        screen, _ = systems.project(sparse, yaw, tilt, scale, width, height)
        density = splat_density(screen, weights, width, height)
        cover = float((density > 0).mean())
        if cover > best_cover:
            best_yaw, best_cover = yaw, cover
    return best_yaw


def find_encoder() -> tuple[str, list[str]]:
    """Pick an ffmpeg that can actually encode H.264.

    Conda environments routinely ship an ffmpeg built without libx264; it
    advertises libopenh264 instead and then fails at runtime with a library
    version mismatch. So probe each ffmpeg on PATH plus the usual system
    location and take the first one offering a working encoder.
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
        # yuv420p subsamples chroma by two, so an odd dimension makes libx264
        # fail with a generic "error while opening encoder" that says nothing
        # about the actual cause.
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

    # Colour comes from speed normalised against the sample population, so a run
    # with different parameters maps the same physical speed onto a different
    # part of the palette. Borrowing the luminous editions' bounds is what keeps
    # this set matching them.
    speed_range = systems.reference_speed_range(name)
    points, shade, ages = systems.sample_flow(
        name,
        trajectories=args.trajectories,
        steps=args.steps,
        warmup=args.warmup,
        spread=args.spread,
        speed_range=speed_range,
    )

    palette = glow.build_palette(spec["palette"])
    weights = np.ones(len(points), dtype=np.float32)
    # Framed on the finished attractor, so the growing form is never rescaled.
    scale = systems.fit_scale(points, width, height, base_tilt, spec["fill"])
    caption = glow.make_caption(width, height, spec["title"], spec["equation"])

    base_screen, _ = systems.project(points, 0.0, base_tilt, scale, width, height)
    growth, growth_age = coverage_curve(base_screen, weights, ages, width, height)
    del base_screen

    cover_yaw = pick_cover_yaw(points, base_tilt, scale, width, height)

    def frame_camera(index: int) -> tuple[float, float]:
        turn = index / max(frames - 1, 1)
        return 2.0 * math.pi * turn, base_tilt + math.radians(3.0) * math.sin(2.0 * math.pi * turn)

    def revealed(index: int) -> float:
        """Age threshold to draw up to, chosen for steady visual growth."""
        elapsed = min(index / max((frames - 1) * args.growth_end, 1e-9), 1.0)
        target = elapsed ** args.growth_shape
        return max(float(np.interp(target, growth, growth_age)), args.seed_fraction)

    # Exposure is calibrated on the finished attractor, so the piece genuinely
    # brightens as it fills in rather than being levelled out frame by frame.
    references: list[float] = []
    for probe in range(6):
        yaw, tilt = frame_camera(round(probe * frames / 6))
        screen, _ = systems.project(points, yaw, tilt, scale, width, height)
        density = splat_density(screen, weights, width, height)
        positive = density[density > 0]
        if positive.size:
            references.append(float(np.percentile(positive, 92.0)))
    reference = float(np.mean(references))

    def compose_frame(count: int, yaw: float, tilt: float) -> np.ndarray:
        screen, depth = systems.project(points[:count], yaw, tilt, scale, width, height)
        colours = glow.sample_palette(palette, shade[:count]) * (0.60 + 0.40 * depth)[:, None]
        colour_sum, density = glow.splat(width, height, screen, colours, weights[:count])
        linear = glow.flame_map(colour_sum, density, reference, boost=spec["boost"])
        linear = glow.bloom(linear, threshold=args.bloom_threshold, strength=args.bloom_strength)
        frame = glow.to_bytes(glow.tone_map(linear, exposure=spec["exposure"]))
        return glow.compose(frame, caption)

    output = args.output_dir / f"{spec['slug']}_{width}x{height}_{args.duration:g}s_{args.fps}fps.mp4"
    encoder = start_encoder(output, width, height, args.fps)
    assert encoder.stdin is not None
    try:
        # Frame one: the finished attractor, for the grid thumbnail. Saved
        # alongside as a PNG too, in case it is easier to set as a custom cover.
        cover = compose_frame(len(points), cover_yaw, base_tilt)
        Image.fromarray(cover).save(output.with_suffix("").with_suffix(".cover.png"))
        encoder.stdin.write(cover.tobytes())

        # Then the formation, from almost nothing to complete.
        for index in range(1, frames):
            yaw, tilt = frame_camera(index - 1)
            count = max(int(np.searchsorted(ages, revealed(index - 1), side="right")), 2)
            encoder.stdin.write(compose_frame(count, yaw, tilt).tobytes())
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
    parser.add_argument("--trajectories", type=int, default=1200)
    # Roughly twice the luminous editions' run. Starting the trajectories on top
    # of each other means the early samples all retrace one curve and add no
    # coverage, so the same step count would finish on a visibly thinner
    # attractor. This lands on the same density for all three systems.
    parser.add_argument("--steps", type=int, default=9000)
    # The trajectories start together but already on the attractor. Launching
    # them from off it instead sends a very fast transient sweeping across the
    # frame, and since colour follows speed that transient arrives violet --
    # which is exactly what made the first Lorenz emergence read cold next to
    # its luminous counterpart.
    parser.add_argument("--warmup", type=int, default=1400)
    parser.add_argument("--spread", type=float, default=0.02)
    parser.add_argument("--seed-fraction", type=float, default=0.004)
    parser.add_argument("--growth-end", type=float, default=0.82)
    parser.add_argument("--growth-shape", type=float, default=1.5)
    parser.add_argument("--bloom-threshold", type=float, default=0.30)
    parser.add_argument("--bloom-strength", type=float, default=0.60)
    return parser.parse_args()


if __name__ == "__main__":
    options = parse_args()
    for edition_name in options.edition or list(EDITIONS):
        print(f"Rendering {edition_name} ...", flush=True)
        print(f"Saved {render_edition(edition_name, options)}", flush=True)
