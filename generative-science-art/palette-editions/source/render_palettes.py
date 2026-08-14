#!/usr/bin/env python3
"""The three attractors forming, finishing on exactly the luminous colours.

Same cut as `emergence-editions/`: a cover frame of the finished attractor, then
the formation over one 360 degree turn.

The difference is the point cloud. `emergence-editions` starts every trajectory
from the same state so the growth reads as a single thread, but that run reaches
further into the attractor's fast outer excursions than the luminous editions
do, and since colour follows speed those excursions arrive violet -- which is
why its Lorenz has a lavender fringe where the luminous one has a magenta one.

Here the sampling is the luminous sampling, unchanged. The last frame is
therefore pixel-identical to the corresponding luminous edition, verified rather
than assumed. The trade is the growth: with the trajectories already spread
across the attractor it blooms from many threads at once instead of one.

Lorenz keeps the luminous palette exactly. The other two carry alternative
palettes in the same family, selectable with `--variant`.
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

# The sampling the luminous editions use. Reproducing their colours means
# reproducing their cloud, so none of these may drift.
LUMINOUS_SAMPLING = {"trajectories": 1200, "steps": 3800, "warmup": 1400, "spread": 0.55}

# Locked: this is the luminous Lorenz palette, byte for byte.
EMBER = [(255, 0, 90), (255, 90, 0), (255, 205, 40), (60, 255, 170), (0, 190, 255), (120, 80, 255)]

# Alternatives, all built the same way as the originals -- a full neon spectrum
# on black -- but entering it at a different point, so the fast outer shells and
# the slow cores land on different hues.
PALETTES: dict[str, list[tuple[int, int, int]]] = {
    "ember": EMBER,
    # Cool entry, warm tail: cores go blue-violet, the outer shells warm to rose.
    "aurora": [(70, 0, 235), (0, 130, 255), (0, 235, 225), (130, 255, 150), (250, 240, 120), (255, 120, 190)],
    # Everything hot: a furnace ramp that only breaks to white at the very top.
    "magma": [(90, 0, 140), (215, 0, 130), (255, 40, 40), (255, 130, 0), (255, 210, 60), (255, 250, 220)],
    # Tropical: teal cores through gold to a magenta rim.
    "reef": [(0, 190, 180), (0, 240, 210), (150, 255, 90), (255, 215, 40), (255, 110, 90), (255, 40, 165)],
    # Cold and jewelled: magenta cores falling away through blue to pale mint.
    "glacier": [(255, 40, 160), (185, 60, 255), (70, 110, 255), (0, 200, 245), (140, 255, 215), (235, 255, 245)],
    # Warm-led like ember, but resolving into gold rather than violet.
    "iris": [(40, 60, 220), (150, 50, 235), (255, 60, 150), (255, 120, 110), (255, 185, 90), (255, 240, 170)],
}

EDITIONS: dict[str, dict] = {
    "lorenz": {
        "title": "Lorenz",
        "system": "lorenz",
        "slug": "lorenz",
        "tilt": 14.0,
        "fill": 0.97,
        "exposure": 1.20,
        "boost": 1.25,
        "variants": ["ember"],
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
        "system": "aizawa",
        "slug": "aizawa",
        "tilt": 18.0,
        "fill": 0.94,
        "exposure": 1.22,
        "boost": 1.30,
        "variants": ["glacier", "iris", "magma"],
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
        "system": "halvorsen",
        "slug": "halvorsen",
        "tilt": 20.0,
        "fill": 0.94,
        "exposure": 1.20,
        "boost": 1.25,
        "variants": ["aurora", "reef", "magma"],
        "equation": (
            "dx/dt = -a x - 4y - 4z - y^2",
            "dy/dt = -a y - 4z - 4x - z^2",
            "dz/dt = -a z - 4x - 4y - x^2",
            "",
            "a = 1.4",
        ),
    },
}


def splat_density(screen: np.ndarray, weights: np.ndarray, width: int, height: int) -> np.ndarray:
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

    Samples do not contribute evenly, so revealing them at a steady rate gives a
    crawl followed by a bang. Splatting them in age order into a running density
    buffer and recording the mean log density -- one full splat, not one per
    probe -- gives a curve that can be inverted into an even schedule. The metric
    is log density rather than covered area because the tone mapper is
    logarithmic, and late samples thicken what is already lit rather than
    lighting anything new.
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
    """Choose the turn angle whose silhouette fills the frame best.

    This frame is the grid thumbnail, so it should be the fullest view rather
    than wherever the turn happens to start. Ranked on every 24th sample.
    """
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

    Conda environments routinely ship an ffmpeg built without libx264; it
    advertises libopenh264 and then fails at runtime with a version mismatch.
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
        # with a generic message that says nothing about the actual cause.
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


class Piece:
    """A prepared edition: cloud, camera and exposure, ready to draw frames from."""

    def __init__(self, name: str, variant: str, width: int, height: int) -> None:
        spec = EDITIONS[name]
        self.name, self.variant, self.spec = name, variant, spec
        self.width, self.height = width, height
        self.base_tilt = math.radians(spec["tilt"])

        # Colour normalisation is left to the run's own percentiles, exactly as
        # the luminous editions do it. Since the sampling matches theirs, the
        # bounds match too, and so does every hue.
        self.points, self.shade, self.ages = systems.sample_flow(name, **LUMINOUS_SAMPLING)
        self.palette = glow.build_palette(PALETTES[variant])
        self.weights = np.ones(len(self.points), dtype=np.float32)
        self.scale = systems.fit_scale(self.points, width, height, self.base_tilt, spec["fill"])
        self.caption = glow.make_caption(width, height, spec["title"], spec["equation"])

    def calibrate(self, frames: int) -> None:
        base_screen, _ = systems.project(
            self.points, 0.0, self.base_tilt, self.scale, self.width, self.height
        )
        self.growth, self.growth_age = coverage_curve(
            base_screen, self.weights, self.ages, self.width, self.height
        )
        del base_screen
        self.cover_yaw = pick_cover_yaw(
            self.points, self.base_tilt, self.scale, self.width, self.height
        )
        references: list[float] = []
        for probe in range(6):
            yaw, tilt = self.camera(round(probe * frames / 6), frames)
            screen, _ = systems.project(
                self.points, yaw, tilt, self.scale, self.width, self.height
            )
            density = splat_density(screen, self.weights, self.width, self.height)
            positive = density[density > 0]
            if positive.size:
                references.append(float(np.percentile(positive, 92.0)))
        self.reference = float(np.mean(references))

    def camera(self, index: int, frames: int) -> tuple[float, float]:
        turn = index / max(frames - 1, 1)
        return (
            2.0 * math.pi * turn,
            self.base_tilt + math.radians(3.0) * math.sin(2.0 * math.pi * turn),
        )

    def draw(self, count: int, yaw: float, tilt: float, args: argparse.Namespace) -> np.ndarray:
        screen, depth = systems.project(
            self.points[:count], yaw, tilt, self.scale, self.width, self.height
        )
        colours = glow.sample_palette(self.palette, self.shade[:count])
        colours = colours * (0.60 + 0.40 * depth)[:, None]
        colour_sum, density = glow.splat(
            self.width, self.height, screen, colours, self.weights[:count]
        )
        linear = glow.flame_map(colour_sum, density, self.reference, boost=self.spec["boost"])
        linear = glow.bloom(linear, threshold=args.bloom_threshold, strength=args.bloom_strength)
        frame = glow.to_bytes(glow.tone_map(linear, exposure=self.spec["exposure"]))
        return glow.compose(frame, self.caption)


def render_edition(name: str, variant: str, args: argparse.Namespace) -> Path:
    frames = round(args.duration * args.fps)
    piece = Piece(name, variant, args.width, args.height)
    piece.calibrate(frames)

    def revealed(index: int) -> float:
        elapsed = min(index / max((frames - 1) * args.growth_end, 1e-9), 1.0)
        target = elapsed ** args.growth_shape
        return max(float(np.interp(target, piece.growth, piece.growth_age)), args.seed_fraction)

    stem = f"{piece.spec['slug']}_{variant}_emergence_{args.width}x{args.height}_{args.duration:g}s_{args.fps}fps"
    output = args.output_dir / f"{stem}.mp4"
    encoder = start_encoder(output, args.width, args.height, args.fps)
    assert encoder.stdin is not None
    try:
        cover = piece.draw(len(piece.points), piece.cover_yaw, piece.base_tilt, args)
        Image.fromarray(cover).save(args.output_dir / f"{stem}.cover.png")
        encoder.stdin.write(cover.tobytes())
        for index in range(1, frames):
            yaw, tilt = piece.camera(index - 1, frames)
            count = max(int(np.searchsorted(piece.ages, revealed(index - 1), side="right")), 2)
            encoder.stdin.write(piece.draw(count, yaw, tilt, args).tobytes())
            if index % 60 == 0:
                print(f"  {name}/{variant}: frame {index}/{frames}", flush=True)
    finally:
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError(f"ffmpeg failed while rendering {name}/{variant}.")
    return output


def render_variant_sheet(name: str, args: argparse.Namespace) -> Path:
    """Cover stills for each of an edition's palettes, side by side."""
    spec = EDITIONS[name]
    tiles = []
    for variant in spec["variants"]:
        piece = Piece(name, variant, args.width, args.height)
        piece.calibrate(round(args.duration * args.fps))
        cover = piece.draw(len(piece.points), piece.cover_yaw, piece.base_tilt, args)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        Image.fromarray(cover).save(args.output_dir / f"{spec['slug']}_{variant}.cover.png")
        tiles.append(np.asarray(Image.fromarray(cover).resize((args.width // 3, args.height // 3))))
        print(f"  {name}: {variant}", flush=True)
    sheet = args.output_dir / f"{spec['slug']}_variants.png"
    Image.fromarray(np.concatenate(tiles, axis=1)).save(sheet)
    return sheet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", choices=sorted(EDITIONS), action="append")
    parser.add_argument("--variant", help="palette to render; defaults to the edition's first")
    parser.add_argument("--variant-sheet", action="store_true", help="cover stills of every palette")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--duration", type=float, default=12)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--seed-fraction", type=float, default=0.004)
    parser.add_argument("--growth-end", type=float, default=0.82)
    parser.add_argument("--growth-shape", type=float, default=1.5)
    parser.add_argument("--bloom-threshold", type=float, default=0.30)
    parser.add_argument("--bloom-strength", type=float, default=0.60)
    return parser.parse_args()


if __name__ == "__main__":
    options = parse_args()
    for edition_name in options.edition or list(EDITIONS):
        if options.variant_sheet:
            print(f"Variant sheet for {edition_name} ...", flush=True)
            print(f"Saved {render_variant_sheet(edition_name, options)}", flush=True)
            continue
        chosen = options.variant or EDITIONS[edition_name]["variants"][0]
        print(f"Rendering {edition_name} / {chosen} ...", flush=True)
        print(f"Saved {render_edition(edition_name, chosen, options)}", flush=True)
