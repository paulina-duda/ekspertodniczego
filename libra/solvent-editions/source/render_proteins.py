#!/usr/bin/env python3
"""Protein assemblies breathing in solvent, in the luminous house style.

Three deposited structures, drawn as glowing backbone traces on black and set
moving. The visual language is carried over unchanged from the attractor pieces:
one 360 degree turn, additive splatting into a float buffer, multi-scale bloom,
log-density tone mapping, colour from a physical scalar, and a cover frame of
the finished structure for the Instagram grid.

What the colour means changes with the subject. For an attractor it was speed.
Here it is how far each residue moves -- its amplitude in the low-frequency
modes of an elastic network over the fold. That is the same kind of quantity:
intrinsic to the object, unchanged by where the camera is.

The motion is not molecular dynamics and does not pretend to be. It is those
same normal modes, driven as standing waves, plus a thermal rattle on the
solvent-exposed residues. See `structures.py` for what that buys and what it
costs.
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
import structures


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "instagram" / "phone-9x16"

# The luminous palettes, unchanged, so the proteomics posts rhyme with the
# mathematics ones rather than merely coexisting with them.
EMBER = [(255, 0, 90), (255, 90, 0), (255, 205, 40), (60, 255, 170), (0, 190, 255), (120, 80, 255)]
CITRUS = [(0, 255, 190), (140, 255, 40), (255, 230, 0), (255, 120, 0), (255, 40, 110), (170, 60, 255)]
ORCHID = [(255, 200, 60), (255, 110, 40), (255, 40, 140), (200, 40, 255), (90, 90, 255), (0, 220, 235)]

EDITIONS: dict[str, dict] = {
    "clathrin": {
        "source": "1xi4-assembly1",
        "title": "Clathrin",
        "palette": ORCHID,
        "slug": "clathrin_1xi4_orchid-gold",
        "orient": "principal",
        "tilt": 16.0,
        "fill": 0.7128,
        "amplitude": 3.2,
        "caption": (
            "PDB 1XI4  ·  clathrin coat",
            "cryo-EM  ·  D6 barrel assembly",
            "216 chains  ·  183,600 residues",
        ),
    },
    "chaperonin": {
        "source": "4b2t",
        "title": "Chaperonin",
        "palette": EMBER,
        "slug": "chaperonin_4b2t_ember-spectrum",
        "orient": "symmetry",
        # Down the symmetry axis. The picker maximises lit area, which for a
        # barrel favours the side view; but the ring is what this molecule is,
        # so the thumbnail is pinned to it.
        "cover_yaw": 0.0,
        "tilt": 16.0,
        "fill": 0.8096,
        "amplitude": 3.6,
        "caption": (
            "PDB 4B2T  ·  TRiC / CCT",
            "X-ray  5.50 Å  ·  R-free 0.399",
            "16 chains  ·  6,842 residues",
        ),
    },
    "synthase": {
        "source": "6vq6",
        "title": "ATP synthase",
        "palette": CITRUS,
        "slug": "atp-synthase_6vq6_electric-citrus",
        "orient": "principal",
        "tilt": 14.0,
        "fill": 0.6358,
        "amplitude": 4.0,
        "caption": (
            "PDB 6VQ6  ·  F₁F₀ ATP synthase",
            "cryo-EM  ·  rotary motor",
            "34 chains  ·  8,454 residues",
        ),
    },
}


def orient(coordinates: np.ndarray, chain: np.ndarray, mode: str) -> np.ndarray:
    """Put the structure's own axis up the screen.

    Rotationally symmetric assemblies get the axis their chains are arranged
    around, recovered as the normal of the plane the chain centroids sit in --
    for the chaperonin those centroids fall on a ring 56 Å across to within
    2 Å, so the axis is unambiguous. Everything else falls back to the thinnest
    principal direction, which for a cage or a stalked machine is the one worth
    turning around.

    Centring is on the median rather than the mean: a deposition with a long
    appendage would otherwise drag the centre off the body of the structure.
    """
    centred = coordinates - np.median(coordinates, axis=0)
    if mode == "symmetry":
        centroids = np.array([
            centred[chain == index].mean(axis=0)
            for index in range(int(chain.max()) + 1)
            if int((chain == index).sum()) > 50
        ])
        axis = np.linalg.svd(centroids - centroids.mean(axis=0))[2][2]
    else:
        axis = np.linalg.svd(centred[::11])[2][2]

    reference = np.array([1.0, 0.0, 0.0])
    if abs(float(axis @ reference)) > 0.9:
        reference = np.array([0.0, 1.0, 0.0])
    first = np.cross(axis, reference)
    first /= np.linalg.norm(first)
    second = np.cross(axis, first)

    along_first, along_second = centred @ first, centred @ second
    if np.ptp(along_first) > np.ptp(along_second):
        vertical, horizontal = along_first, along_second
    else:
        vertical, horizontal = along_second, along_first
    return np.column_stack((horizontal, vertical, centred @ axis)).astype(np.float32)


def frame_band(height: int, margin: int, caption_lines: int, gap: int = 24) -> float:
    """Vertical room for the structure, symmetric about the middle of the frame.

    The layout is the attractor editions' layout: a standard inset for the title
    and caption, and the structure centred on the frame with a modest band of
    black around it. Reserving space for the Reel player's chrome instead was
    tried and abandoned -- it pushed the title down a fifth of the frame and left
    so much empty black that it wrecked the composition, which matters more than
    keeping the caption clear of an overlay that is only there while the clip is
    playing in the app.

    The allowance is symmetric so the structure sits on the frame's centre line
    rather than the centre of some off-centre band, and it is sized off the
    deeper of the two insets -- the caption -- so the structure never runs into
    its own text.
    """
    caption_height = caption_lines * 27 + max(0, caption_lines - 1) * 9
    reserve = margin + caption_height + gap
    return float(height - 2 * reserve)


def vertical_extent(points: np.ndarray, tilt: float, samples: int = 24) -> tuple[float, float]:
    """Where the silhouette actually starts and stops, over the whole turn.

    Measuring the true top and bottom rather than assuming the structure is
    symmetric about its centre. It usually is not: the ATP synthase carries its
    F₁ head at one end and its membrane ring at the other, and runs from −150 Å
    to +89 Å about the median. Taking the larger side and mirroring it, as a
    `percentile(|y|)` does, both drops the structure below the middle of the
    frame and shrinks it to fit a margin that is only needed on one side.
    """
    cos_tilt, sin_tilt = math.cos(tilt), math.sin(tilt)
    low, high = math.inf, -math.inf
    for index in range(samples):
        yaw = 2.0 * math.pi * index / samples
        rotated = -points[:, 0] * math.sin(yaw) + points[:, 2] * math.cos(yaw)
        screen_y = points[:, 1] * cos_tilt + rotated * sin_tilt
        low = min(low, float(np.percentile(screen_y, 0.5)))
        high = max(high, float(np.percentile(screen_y, 99.5)))
    return low, high


def fit_scale(
    points: np.ndarray, width: int, tilt: float, fill: float, band: float
) -> tuple[float, float]:
    """Projection scale for the whole turn, and the model height to centre on.

    The 99th percentile rather than the maximum: a single flexible tail would
    otherwise shrink the whole assembly to leave room for it.
    """
    horizontal = float(np.percentile(np.hypot(points[:, 0], points[:, 2]), 99.0))
    low, high = vertical_extent(points, tilt)
    half_height = (high - low) * 0.5
    scale = min(
        fill * width / max(2.0 * horizontal, 1e-9),
        fill * band / max(2.0 * half_height, 1e-9),
    )
    return scale, (high + low) * 0.5


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
    y = points[:, 1]
    cos_tilt, sin_tilt = math.cos(tilt), math.sin(tilt)
    screen_y = y * cos_tilt + z * sin_tilt
    depth = -y * sin_tilt + z * cos_tilt
    middle = height * 0.5 if centre_y is None else centre_y
    screen = np.column_stack((x * scale + width * 0.5, -screen_y * scale + middle))
    span = max(float(np.ptp(depth)), 1e-9)
    return screen.astype(np.float32), ((depth - depth.min()) / span).astype(np.float32)


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


def render_edition(name: str, args: argparse.Namespace) -> Path:
    spec = EDITIONS[name]
    width, height = args.width, args.height
    frames = round(args.duration * args.fps)
    tilt = math.radians(spec["tilt"])

    source = spec["source"]
    path = structures.CIF_DIR / f"{source}.cif"
    if not path.exists():
        path = structures.fetch_cif(source)
    backbone = structures.load_backbone(path)
    rest = orient(backbone["coordinates"].astype(np.float64), backbone["chain"], spec["orient"])
    print(f"  {name}: {len(rest):,} backbone atoms, {len(backbone['chain_names'])} chains", flush=True)

    nodes, modes, values = structures.network_modes(
        rest, node_limit=args.nodes, mode_count=args.modes
    )
    shapes = structures.interpolate_modes(rest, nodes, modes)
    # Equipartition: a softer mode is excited further. Normalised so the softest
    # mode carries unit amplitude and `amplitude` sets its swing in angstroms.
    strength = 1.0 / np.sqrt(np.maximum(values, 1e-12))
    strength /= strength[0]
    shapes *= (strength[:, None, None] / np.abs(shapes[0]).max()) * spec["amplitude"]

    mobility = np.sqrt((shapes**2).sum(axis=2).sum(axis=0))
    # Ranked rather than scaled: mobility is strongly skewed -- most of a fold
    # is rigid -- and a linear ramp leaves all but the few floppiest residues
    # crowded into one end of the palette.
    shade = (np.argsort(np.argsort(mobility)) / max(len(mobility) - 1, 1)).astype(np.float32)

    band = frame_band(height, args.margin, len(spec["caption"]))
    scale, model_middle = fit_scale(rest, width, tilt, spec["fill"], band)
    # Offset so the silhouette's own midpoint lands on the frame's centre line.
    centre_y = height * 0.5 + model_middle * scale
    control, fraction = structures.trace_topology(
        rest, backbone["chain"], target_length=args.trace_pixels / scale
    )
    weights = structures.spline_weights(fraction)
    trace_shade = np.einsum("ks,ks->s", weights, shade[control]).astype(np.float32)
    print(f"  {name}: {control.shape[1]:,} trace samples", flush=True)

    # Thermal rattle on whatever the solvent can reach. Two harmonics with
    # random directions per atom, both whole-cycle periodic so they cannot break
    # the seam of the turn.
    generator = np.random.default_rng(20260803)
    surface = structures.exposure(rest)[:, None]
    rattle = generator.standard_normal((2, len(rest), 3)).astype(np.float32) * surface * args.rattle
    phase = generator.uniform(0.0, 2.0 * math.pi, 2).astype(np.float32)

    palette = glow.build_palette(spec["palette"])
    colours = glow.sample_palette(palette, trace_shade)
    caption = glow.make_caption(width, height, spec["title"], spec["caption"], margin=args.margin)

    def posed(turn: float) -> np.ndarray:
        """Structure displaced along its modes at a given point in the cycle."""
        # Integer frequencies: the pose at turn 1 is the pose at turn 0.
        beat = np.sin(
            2.0 * math.pi * (np.arange(len(shapes)) // 2 + 1) * turn
            + np.linspace(0.0, math.pi, len(shapes))
        ).astype(np.float32)
        moved = rest + np.einsum("m,mac->ac", beat, shapes)
        moved += rattle[0] * math.cos(2.0 * math.pi * turn + float(phase[0]))
        moved += rattle[1] * math.cos(4.0 * math.pi * turn + float(phase[1]))
        return moved

    reference_pose = posed(0.0)
    if spec.get("cover_yaw") is None:
        cover_yaw = pick_cover_yaw(reference_pose, tilt, scale, width, height, centre_y)
    else:
        cover_yaw = math.radians(spec["cover_yaw"])

    references: list[float] = []
    probe_points = structures.draw_traces(reference_pose, control, weights)
    ones = np.ones(probe_points.shape[0], dtype=np.float32)
    for probe in range(6):
        screen, _ = project(
            probe_points, 2.0 * math.pi * probe / 6, tilt, scale, width, height, centre_y
        )
        density = splat_density(screen, ones, width, height)
        positive = density[density > 0]
        if positive.size:
            references.append(float(np.percentile(positive, 92.0)))
    reference = float(np.mean(references))

    def draw(turn: float, yaw: float) -> np.ndarray:
        points = structures.draw_traces(posed(turn), control, weights)
        screen, depth = project(points, yaw, tilt, scale, width, height, centre_y)
        # Depth cueing does most of the work of making a dense assembly read as
        # a solid object rather than a tangle of wire.
        near = (1.0 - args.fog) + args.fog * depth
        colour_sum, density = glow.splat(
            width, height, screen, colours * near[:, None], (1.0 - 0.7 * args.fog) + 0.7 * args.fog * depth
        )
        linear = glow.flame_map(colour_sum, density, reference, boost=args.boost)
        linear = glow.bloom(linear, threshold=args.bloom_threshold, strength=args.bloom_strength)
        return glow.compose(glow.to_bytes(glow.tone_map(linear, exposure=args.exposure)), caption)

    stem = f"{spec['slug']}_{width}x{height}_{args.duration:g}s_{args.fps}fps"
    output = args.output_dir / f"{stem}.mp4"
    encoder = start_encoder(output, width, height, args.fps)
    assert encoder.stdin is not None
    try:
        cover = draw(0.0, cover_yaw)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        Image.fromarray(cover).save(args.output_dir / f"{stem}.cover.png")
        encoder.stdin.write(cover.tobytes())
        for index in range(1, frames):
            turn = (index - 1) / (frames - 1)
            encoder.stdin.write(draw(turn, 2.0 * math.pi * turn).tobytes())
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
    parser.add_argument("--duration", type=float, default=8)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--nodes", type=int, default=900)
    parser.add_argument("--modes", type=int, default=8)
    parser.add_argument("--rattle", type=float, default=0.55, help="thermal jitter in angstroms")
    parser.add_argument("--trace-pixels", type=float, default=0.7)
    parser.add_argument("--margin", type=int, default=64, help="inset for title and caption")
    parser.add_argument("--fog", type=float, default=0.78)
    parser.add_argument("--boost", type=float, default=1.25)
    parser.add_argument("--exposure", type=float, default=1.20)
    parser.add_argument("--bloom-threshold", type=float, default=0.30)
    parser.add_argument("--bloom-strength", type=float, default=0.60)
    return parser.parse_args()


if __name__ == "__main__":
    options = parse_args()
    for edition_name in options.edition or list(EDITIONS):
        print(f"Rendering {edition_name} ...", flush=True)
        print(f"Saved {render_edition(edition_name, options)}", flush=True)
