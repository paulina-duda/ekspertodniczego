#!/usr/bin/env python3
"""Render the six luminous editions as seamlessly looping 9:16 MP4 files.

Three things drive the design, all of them reactions to how the first editions
actually behave in a feed:

* Every clip opens on the finished sculpture. The originals fade up from an
  empty black frame, which spends the one second you get to stop a scroll.
* The camera completes exactly one 360 degree turn, so the last frame meets the
  first and Instagram's auto-repeat is invisible.
* Density is tone mapped logarithmically and bloomed, so the structure reads as
  emitted light rather than as coloured hairlines.
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
from pathlib import Path

import numpy as np

import glow
import systems


ART_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ART_DIR / "instagram" / "phone-9x16"

EMBER = [(255, 0, 90), (255, 90, 0), (255, 205, 40), (60, 255, 170), (0, 190, 255), (120, 80, 255)]
CITRUS = [(0, 255, 190), (140, 255, 40), (255, 230, 0), (255, 120, 0), (255, 40, 110), (170, 60, 255)]
ORCHID = [(255, 200, 60), (255, 110, 40), (255, 40, 140), (200, 40, 255), (90, 90, 255), (0, 220, 235)]
RAINBOW = [
    (255, 0, 92), (255, 58, 0), (255, 225, 0), (54, 255, 0), (0, 255, 148),
    (0, 218, 255), (34, 76, 255), (153, 0, 255), (255, 0, 205), (255, 0, 92),
]

EDITIONS: dict[str, dict] = {
    "lorenz": {
        "kind": "flow",
        "system": "lorenz",
        "title": "Lorenz",
        "palette": EMBER,
        "slug": "lorenz_ember-spectrum_luminous",
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
    "halvorsen": {
        "kind": "flow",
        "system": "halvorsen",
        "title": "Halvorsen",
        "palette": CITRUS,
        "slug": "halvorsen_electric-citrus_luminous",
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
    "aizawa": {
        "kind": "flow",
        "system": "aizawa",
        "title": "Aizawa",
        "palette": ORCHID,
        "slug": "aizawa_orchid-gold_luminous",
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
    "classic-butterfly": {
        "kind": "clifford",
        "system": "classic-butterfly",
        "title": "Clifford",
        "palette": RAINBOW,
        "slug": "clifford_classic-butterfly_rainbow_luminous",
        "tilt": 26.0,
        "fill": 0.95,
        "exposure": 1.25,
        "boost": 1.15,
    },
    "ring": {
        "kind": "clifford",
        "system": "ring",
        "title": "Clifford",
        "palette": RAINBOW,
        "slug": "clifford_ring_rainbow_luminous",
        "tilt": 26.0,
        # This preset is wide and squat -- upright it uses more than twice the
        # frame height, and only then is there room to scale it up at all.
        "roll": 90.0,
        "fill": 1.05,
        "exposure": 1.25,
        "boost": 1.15,
    },
    "shell": {
        "kind": "clifford",
        "system": "shell",
        "title": "Clifford",
        "palette": RAINBOW,
        "slug": "clifford_shell_rainbow_luminous",
        "tilt": 26.0,
        "fill": 0.95,
        "exposure": 1.25,
        "boost": 1.15,
    },
}


def clifford_equation(preset: str) -> tuple[str, ...]:
    a, b, c, d = systems.CLIFFORD_PRESETS[preset]
    return (
        "x[n+1] = sin(a y[n]) + c cos(a x[n])",
        "y[n+1] = sin(b x[n]) + d cos(b y[n])",
        "",
        f"a = {a:<6g} b = {b:<6g}",
        f"c = {c:<6g} d = {d:<6g}",
    )


def find_encoder() -> tuple[str, list[str]]:
    """Pick an ffmpeg that can actually encode H.264.

    Conda environments routinely ship an ffmpeg built without libx264; it
    advertises libopenh264 instead and then fails at runtime with a library
    version mismatch. So probe each ffmpeg on PATH plus the usual system
    location and take the first one offering a working encoder, rather than
    trusting whichever binary happens to come first.
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

    if spec["kind"] == "flow":
        points, shade = systems.sample_flow(
            spec["system"],
            trajectories=args.trajectories,
            steps=args.steps,
            warmup=args.warmup,
        )
        equation = spec["equation"]
    else:
        points, shade = systems.sample_clifford(
            spec["system"], seeds=args.clifford_seeds, steps=args.clifford_steps
        )
        equation = clifford_equation(spec["system"])
    points = systems.roll(points, spec.get("roll", 0.0))

    palette = glow.build_palette(spec["palette"])
    weights = np.ones(len(points), dtype=np.float32)
    scale = systems.fit_scale(points, width, height, base_tilt, spec["fill"])
    caption = glow.make_caption(width, height, spec["title"], equation)

    def frame_camera(index: int) -> tuple[float, float, float]:
        turn = index / frames
        yaw = 2.0 * math.pi * turn
        # Both extra motions are whole-cycle periodic, so they cannot break the
        # seam: a small tilt sway for the flows, a full hue revolution for the
        # Clifford clouds, which reads as light travelling around the shell.
        tilt = base_tilt + math.radians(3.0) * math.sin(2.0 * math.pi * turn)
        hue_shift = turn if spec["kind"] == "clifford" else 0.0
        return yaw, tilt, hue_shift

    # One exposure reference for the whole clip. Recomputing it per frame would
    # track the silhouette as it turns and pump the brightness up and down.
    references: list[float] = []
    for probe in range(6):
        yaw, tilt, _ = frame_camera(round(probe * frames / 6))
        screen, _ = systems.project(points, yaw, tilt, scale, width, height)
        _, density = glow.splat(
            width, height, screen, np.zeros((len(points), 3), dtype=np.float32), weights
        )
        positive = density[density > 0]
        if positive.size:
            references.append(float(np.percentile(positive, 92.0)))
    reference = float(np.mean(references))

    output = args.output_dir / f"{spec['slug']}_{width}x{height}_{args.duration:g}s_{args.fps}fps.mp4"
    encoder = start_encoder(output, width, height, args.fps)
    assert encoder.stdin is not None
    try:
        for index in range(frames):
            yaw, tilt, hue_shift = frame_camera(index)
            screen, depth = systems.project(points, yaw, tilt, scale, width, height)
            colours = glow.sample_palette(palette, np.mod(shade + hue_shift, 1.0))
            colours = colours * (0.60 + 0.40 * depth)[:, None]
            colour_sum, density = glow.splat(width, height, screen, colours, weights)
            linear = glow.flame_map(colour_sum, density, reference, boost=spec["boost"])
            linear = glow.bloom(linear, threshold=args.bloom_threshold, strength=args.bloom_strength)
            frame = glow.to_bytes(glow.tone_map(linear, exposure=spec["exposure"]))
            encoder.stdin.write(glow.compose(frame, caption).tobytes())
            if index % 30 == 0:
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
    parser.add_argument("--duration", type=float, default=10)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--trajectories", type=int, default=1200)
    parser.add_argument("--steps", type=int, default=3800)
    parser.add_argument("--warmup", type=int, default=1400)
    parser.add_argument("--clifford-seeds", type=int, default=42000)
    parser.add_argument("--clifford-steps", type=int, default=110)
    parser.add_argument("--bloom-threshold", type=float, default=0.30)
    parser.add_argument("--bloom-strength", type=float, default=0.60)
    return parser.parse_args()


if __name__ == "__main__":
    options = parse_args()
    names = options.edition or list(EDITIONS)
    for edition_name in names:
        print(f"Rendering {edition_name} ...", flush=True)
        print(f"Saved {render_edition(edition_name, options)}", flush=True)
