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
from PIL import Image, ImageDraw, ImageFont

import glow
import morphogens


PROJECT_DIR = Path(__file__).resolve().parents[1]
# These three are the wetware edition, and its cuts live with it. The source
# sits one level up because `wetware-editions/source/` was never filled in --
# worth remembering before looking for this file where the outputs are.
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "wetware-editions" / "instagram" / "phone-9x16"

# Cyberpunk rather than the attractors' spectrum ramps: these stay inside the
# violet-magenta-cyan band that reads as circuitry, and only reach white where
# the process is densest.
SYNAPSE = [(6, 0, 28), (86, 0, 150), (208, 0, 160), (255, 60, 190), (0, 225, 255), (200, 255, 255)]
CULTURE = [(0, 14, 10), (0, 110, 70), (86, 235, 70), (200, 255, 110), (240, 255, 220)]
FILAMENT_A = [(0, 8, 24), (0, 78, 140), (0, 190, 245), (170, 250, 255)]
FILAMENT_B = [(26, 0, 20), (128, 0, 92), (245, 0, 140), (255, 175, 220)]
# Cyclic, because what it carries is a phase: it has to arrive back where it
# started or the wrap shows up as a seam the process never made. Luminance
# rides round with the hue, which is honest here -- a clock reporter really is
# dark for half of every turn, and it is what makes the bands read as bands.
PULSE = [
    (6, 0, 22), (86, 0, 158), (214, 0, 150), (255, 120, 200),
    (196, 238, 255), (0, 214, 226), (34, 58, 140), (6, 0, 22),
]

# Two systems in one section, so two palettes that sum where they cross. The
# split is not decorative: an element is in one or the other depending on
# whether it is being pulled or pushed, which is exactly how an anatomist
# separates the trabecular groups. Warm for compression, cool for tension.
STRUT_C = [(26, 0, 14), (150, 0, 70), (255, 44, 130), (255, 170, 80), (255, 246, 220)]
STRUT_T = [(4, 0, 30), (74, 0, 190), (0, 172, 245), (176, 250, 255)]

# Violet through magenta into a warm white. Deliberately not `CULTURE`, which
# is the green the other growing piece already owns, and not `SYNAPSE`, which
# ends cold -- an apex is the warm end of this account, not the cold one.
MERISTEM = [(8, 0, 26), (72, 0, 140), (190, 0, 170), (255, 70, 150), (255, 170, 120), (255, 240, 210)]

# Violet through magenta into gold. The account has a green growing piece and
# a cold one already; this is the warm one, and the gold end is where the tips
# are, which is the only part of a leaf that is actually still growing.
# The top stop is gold rather than white on purpose. The growing margin is
# both the densest thing in the frame and the brightest end of the ramp, and
# when it sweeps up through the hook it took the background behind that line to
# 151 -- brighter than anything else in the account. Pulling the ramp short of
# white costs nothing structural and is the only thing that fixed it.
LAMINA = [(16, 0, 22), (110, 0, 92), (222, 20, 96), (250, 104, 36), (255, 186, 92), (255, 222, 160)]

# Hot core, cold tail. The head is where the actin was made a moment ago and
# the far end is about to stop existing, so the ramp runs from near-black
# indigo up to white and the contrast does the work of making a streak read as
# a streak.
ACTIN = [(8, 0, 24), (78, 0, 120), (198, 0, 132), (255, 72, 116), (255, 176, 150), (255, 246, 235)]

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
        "hook": ("No brain. One cell. Still finds a way.",),
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
    "trabecula": {
        "kind": "bone",
        "title": "Trabecula",
        "slug": "trabecula_bone-remodelling_strut",
        "palette": STRUT_C,
        "palette_b": STRUT_T,
        "exposure": 1.14,
        "boost": 1.22,
        "steps_per_frame": 1,
        "settle": 0,
        # Its text sits on black either way -- the section is nowhere near the
        # margins -- and the full veil costs the head, which is the thumbnail.
        "scrim": 0.55,
        "caption": (
            "bone remodelling  ·  Frost's mechanostat",
            "sense strain · deposit · resorb",
            "three stances of one leg  ·  weighted 6:2:2",
            "nothing fixes the total; the mass is an outcome",
        ),
        "hook": ("No one drew this. The load did.",),
    },
    "comet": {
        "kind": "comet",
        "title": "Comet",
        "slug": "comet_actin-tail_cytoplasm",
        "palette": ACTIN,
        "exposure": 1.16,
        "boost": 1.24,
        "steps_per_frame": 3,
        "settle": 0,
        # Weight falls with the age of the actin as well as hue, so a tail
        # thins towards its far end instead of ending on a flat stub. It is
        # also what depolymerisation looks like.
        "taper": 2.0,
        "head": 3.4,
        "head_samples": 30,
        "head_weight": 2.6,
        "caption": (
            "Listeria monocytogenes  ·  actin comet tail",
            "nucleate · push · outrun · depolymerise",
            "the same actin your own cells crawl on",
            "ten bacteria become 160 in eight seconds",
        ),
        "hook": ("No motor. It is pushed by what it builds.",),
    },
    "venation": {
        "kind": "vein",
        "title": "Venation",
        "slug": "venation_canalisation_lamina",
        "palette": LAMINA,
        "exposure": 1.10,
        "boost": 1.20,
        "steps_per_frame": 3,
        "settle": 0,
        "caption": (
            "leaf venation  ·  canalisation (Sachs 1981)",
            "pull · advance · drain",
            "10,164 sources of auxin  ·  19,637 vein tips",
            "space colonisation, Runions & Prusinkiewicz",
        ),
        "hook": ("The vein is not a route. It is a leftover.",),
    },
    "phyllotaxis": {
        "kind": "spiral",
        "title": "Phyllotaxis",
        "slug": "phyllotaxis_primordia_meristem",
        "palette": MERISTEM,
        "exposure": 1.16,
        "boost": 1.24,
        "steps_per_frame": 5,
        "settle": 0,
        "cell_radius": 9.0,
        "cell_samples": 48,
        "caption": (
            "shoot apical meristem  ·  Douady & Couder 1992",
            "grow · inhibit · place the next one",
            "spiral counts 8, 13, 21 out to 21, 34, 55",
            "divergence 137.4°  ·  no angle is in the rule",
        ),
        "hook": ("The plant is not counting. You are.",),
    },
    "somite": {
        "kind": "cells",
        "title": "Somite",
        "slug": "somite_clock-and-wavefront_pulse",
        "palette": PULSE,
        "exposure": 1.16,
        "boost": 1.24,
        "steps_per_frame": 3,
        "settle": 0,
        "scrim": 0.55,
        "caption": (
            "vertebrate segmentation clock",
            "oscillate · slow · arrest · condense",
            "human clock · one segment every five hours",
            "clock and wavefront, Cooke & Zeeman 1976",
        ),
        "hook": ("Your spine was counted, not measured.",),
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


def build_overlay(width: int, height: int, spec: dict, args) -> Image.Image:
    """Title, hook and data block -- the layout the substrate set settled on.

    Plex throughout, spaced bold title 240 px down, data block 190 px up, hook
    centred at 34 px with its lowest ink 82 px clear of the block, soft scrim at
    both edges. Reused rather than re-derived: the numbers were measured off the
    `cleavage` cut pixel by pixel and there is no reason for a second opinion.
    """
    overlay = glow.make_caption(
        width,
        height,
        spec["title"],
        spec["caption"],
        equation_size=args.caption_size,
        margin=args.margin,
        top_margin=args.title_top,
        bottom_margin=args.caption_bottom,
        # A piece whose text already sits on black does not need the full
        # veil, and `somite` pays for it: the column runs to the top edge, so
        # a scrim strong enough to protect a title over texture also swallows
        # the oldest segments in the piece.
        scrim=spec.get("scrim", args.scrim),
    )
    lines = spec.get("hook") if args.hook else None
    if not lines:
        return overlay

    ink_top = glow.caption_ink_top(height, spec["caption"], args.caption_size, args.caption_bottom)
    font = ImageFont.truetype(str(glow.MONO_FONT), args.hook_size)
    draw = ImageDraw.Draw(overlay)
    text = "\n".join(lines)
    spacing = max(6, args.hook_size // 3)
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing)
    draw.multiline_text(
        ((width - (box[2] - box[0])) // 2, ink_top - args.hook_gap - box[3]),
        text,
        font=font,
        fill=(255, 255, 255, 244),
        spacing=spacing,
        align="center",
        stroke_width=4,
        stroke_fill=(0, 0, 0, 165),
    )
    return overlay


def field_channels(model, spec, palette, palette_b, height, width, reference):
    """Build the (density, shade, palette) channels for a field edition."""
    if spec["kind"] in ("physarum", "bone"):
        # Two populations, or the two trabecular groups: same problem, same
        # answer. Each carries its own density and its own palette, and the sum
        # is what lets a crossing read as a crossing instead of one of them
        # painting over the other. Shade has to come from the channel's own
        # density -- taking it from the total sends both palettes to their white
        # ends at once and throws the hue away.
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


# A cell is a few square microns of tissue, not a point, so it is splatted as
# a small blob. The offsets are drawn once and indexed by cell, so a cell keeps
# the same speckle from frame to frame -- redrawing them every frame makes the
# whole sheet boil.
DISC = np.column_stack((lambda a, r: (r * np.cos(a), r * np.sin(a)))(
    np.random.default_rng(7).uniform(0.0, 2.0 * math.pi, 8192),
    np.random.default_rng(11).random(8192) ** 0.62,
)).astype(np.float32)


def cell_samples(model, args, spec=None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Expand one cell per row into a blob of samples carrying its phase.

    A somite cell is a few square microns and a floret is an organ, so the two
    want blobs an order of magnitude apart; the edition may say so.
    """
    spec = spec or {}
    points, shade = model.cells()
    radius = spec.get("cell_radius", args.cell_radius)
    count, per_cell = len(points), spec.get("cell_samples", args.cell_samples)
    index = (np.arange(count, dtype=np.int64)[:, None] * per_cell
             + np.arange(per_cell, dtype=np.int64)[None, :]) % len(DISC)
    samples = (points[:, None, :] + DISC[index] * radius).reshape(-1, 2)
    weights = np.full(count * per_cell, 1.0 / per_cell, dtype=np.float32)
    return samples, np.repeat(shade, per_cell), weights


def tree_samples(start: np.ndarray, end: np.ndarray, target: float = 0.6) -> tuple[np.ndarray, np.ndarray]:
    """Sample every vein segment along its own length.

    By length, not a fixed count per segment: a fixed count turns the long
    segments into dotted rules across the frame, and it reads as a layout bug
    rather than a sampling one. It cost real time in `descent`.
    """
    delta = end - start
    length = np.linalg.norm(delta, axis=1)
    counts = np.clip(np.ceil(length / target), 1, 32).astype(np.int64)
    total = int(counts.sum())
    segment = np.repeat(np.arange(counts.size, dtype=np.int64), counts)
    starts = np.zeros(counts.size + 1, dtype=np.int64)
    np.cumsum(counts, out=starts[1:])
    fraction = ((np.arange(total, dtype=np.int64) - starts[segment]) / counts[segment]).astype(np.float32)
    return (start[segment] + fraction[:, None] * delta[segment]).astype(np.float32), segment


def with_heads(state, samples, shade, weights, spec):
    """Add the moving object at the front of each trail.

    A blob rather than a point, and heavier than any tail sample, so the
    thing travelling is the brightest thing in the frame and the trail reads
    as belonging to it.
    """
    heads = state.heads()
    radius, per_head = spec["head"], spec.get("head_samples", 26)
    offsets = DISC[:per_head] * radius
    blobs = (heads[:, None, :] + offsets[None, :, :]).reshape(-1, 2).astype(np.float32)
    return (
        np.concatenate((samples, blobs)),
        np.concatenate((shade, np.ones(len(blobs), dtype=np.float32))),
        np.concatenate((weights, np.full(len(blobs), spec.get("head_weight", 2.4), dtype=np.float32))),
    )


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
    if spec["kind"] == "cells":
        # The run length is fixed to the clip, not to the clock: the tail has
        # to arrive at the bottom of the frame on the last frame whatever the
        # duration, and the speed it needs to do that is what sets the segment
        # length. Asking for a longer cut plays the same process more slowly.
        frames = round(args.duration * args.fps)
        return morphogens.SegmentationClock(
            args.height,
            args.width,
            steps=spec["steps_per_frame"] * (frames - 1),
            somite=args.somite_length,
            tail_start=args.tail_start,
            tail_end=args.tail_end,
            densify=args.densify,
        )
    if spec["kind"] == "physarum":
        band = (args.band_top, args.band_bottom) if args.band_top < args.band_bottom else None
        return morphogens.Physarum(args.height, args.width, agents=args.agents, band=band)
    if spec["kind"] == "comet":
        return morphogens.Comet(args.height, args.width, speed=args.comet_speed)
    if spec["kind"] == "vein":
        # Stride and blade schedule are set together, and what they buy is
        # pacing: the veins reach the top of the frame around frame 155 and
        # spend the last third filling in reticulation everywhere at once.
        # Slower than that and the top two thirds of the frame are empty black
        # for the first third of the clip, which is the part anyone watches.
        return morphogens.Venation(args.height, args.width, stride=args.vein_stride)
    if spec["kind"] == "spiral":
        # One organ per plastochrone, five per frame, so the clip is the whole
        # ontogeny of the head rather than a window onto part of it. The head
        # is exactly full on the last step, which is what fixes the spacing.
        frames = round(args.duration * args.fps)
        return morphogens.Phyllotaxis(
            args.height, args.width, radius=args.head_radius,
            primordia=spec["steps_per_frame"] * (frames - 1) + 1,
        )
    if spec["kind"] == "bone":
        # One turn of the rule per frame, so the clip is the run rather than a
        # sampling of it. The grid is a third of the frame and gets
        # interpolated up: struts come out about a dozen pixels wide, which is
        # a trabecula at this magnification and survives the bloom.
        return morphogens.Trabecula(
            args.height, args.width, divisor=args.bone_divisor,
            sensing=args.bone_sensing, setpoint=args.bone_setpoint,
        )
    return morphogens.DifferentialGrowth(
        (args.width * 0.5, args.height * 0.5), 55.0, nodes=200, spacing=2.5, repulsion_radius=11.0
    )


def render_edition(name: str, args: argparse.Namespace) -> Path:
    spec = EDITIONS[name]
    width, height = args.width, args.height
    frames = round(args.duration * args.fps)
    caption = build_overlay(width, height, spec, args)
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
    elif spec["kind"] in ("vein", "comet"):

        def draw_veins(state) -> np.ndarray:
            start, end, shade = state.segments()
            samples, segment = tree_samples(start, end)
            carried = shade[segment]
            taper = spec.get("taper", 0.0)
            weights = (carried ** taper if taper else np.ones(len(samples))).astype(np.float32)
            if spec.get("head"):
                samples, carried, weights = with_heads(state, samples, carried, weights, spec)
            colours = glow.sample_palette(palette, carried)
            colour_sum, density = glow.splat(width, height, samples, colours, weights)
            linear = glow.flame_map(colour_sum, density, reference, boost=spec["boost"])
            linear = glow.bloom(linear, threshold=args.bloom_threshold, strength=args.bloom_strength)
            return glow.compose(glow.to_bytes(glow.tone_map(linear, exposure=spec["exposure"])), caption)

        start, end, shade = model.segments()
        samples, segment = tree_samples(start, end)
        taper = spec.get("taper", 0.0)
        probe_weights = (shade[segment] ** taper if taper else np.ones(len(samples))).astype(np.float32)
        if spec.get("head"):
            samples, _, probe_weights = with_heads(model, samples, shade[segment], probe_weights, spec)
        _, probe = glow.splat(
            width, height, samples, np.zeros((len(samples), 3), dtype=np.float32), probe_weights
        )
        reference = float(np.percentile(probe[probe > 0], 92.0))
        if spec["kind"] == "comet":
            print(f"  {name}: {model.count:,} bacteria, {len(samples):,} samples", flush=True)
        else:
            print(f"  {name}: {model.count:,} tips, {len(model.sources):,} sources left", flush=True)
        cover = draw_veins(model)
    elif spec["kind"] in ("cells", "spiral"):

        def draw_cells(state) -> np.ndarray:
            samples, shade, weights = cell_samples(state, args, spec)
            colours = glow.sample_palette(palette, shade)
            colour_sum, density = glow.splat(width, height, samples, colours, weights)
            linear = glow.flame_map(colour_sum, density, reference, boost=spec["boost"])
            linear = glow.bloom(linear, threshold=args.bloom_threshold, strength=args.bloom_strength)
            return glow.compose(glow.to_bytes(glow.tone_map(linear, exposure=spec["exposure"])), caption)

        samples, _, weights = cell_samples(model, args, spec)
        _, probe = glow.splat(
            width, height, samples, np.zeros((len(samples), 3), dtype=np.float32), weights
        )
        reference = float(np.percentile(probe[probe > 0], args.cell_reference))
        if hasattr(model, "closed"):
            print(f"  {name}: {model.count:,} cells, {len(model.closed)} segments formed", flush=True)
        else:
            print(f"  {name}: {model.count:,} organs, outer radius {model.radii()[0]:.0f} px", flush=True)
        cover = draw_cells(model)
    else:
        channels = field_channels(model, spec, palette, palette_b, height, width, None)
        stacked = sum(channel[0] for channel in channels)
        reference = float(np.percentile(stacked[stacked > 0], 99.0))
        channels = field_channels(model, spec, palette, palette_b, height, width, reference)
        cover = compose_field(channels, reference, spec, args, caption)

    stem = f"{spec['slug']}_{width}x{height}_{args.duration:g}s_{args.fps}fps"
    if args.hook and spec.get("hook"):
        stem += "_hook_plex"
    if args.tag:
        # A variant cut written alongside the original rather than over it.
        stem += f"_{args.tag}"
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
            elif spec["kind"] in ("vein", "comet"):
                frame = draw_veins(model)
            elif spec["kind"] in ("cells", "spiral"):
                frame = draw_cells(model)
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
    # The head's outer edge on the last frame. Sets the spacing too, because
    # the organ count is fixed by the clip length.
    parser.add_argument("--comet-speed", type=float, default=6.4)
    parser.add_argument("--vein-stride", type=float, default=4.0)
    parser.add_argument("--head-radius", type=float, default=500.0)
    parser.add_argument("--bone-divisor", type=int, default=3)
    # How far an osteocyte is taken to feel, in grid cells. It is the only
    # length in the rule and it sets trabecular thickness and spacing.
    parser.add_argument("--bone-sensing", type=float, default=2.6)
    # The fraction of the tissue that starts above its set point.
    parser.add_argument("--bone-setpoint", type=float, default=0.5)
    parser.add_argument("--bloom-threshold", type=float, default=0.30)
    parser.add_argument("--bloom-strength", type=float, default=0.60)
    parser.add_argument("--tag", help="suffix for a variant cut")
    # The house layout, same numbers as the substrate and alife sets. The older
    # wetware cuts predate it and used a symmetric 64 px inset with no scrim
    # and no hook, which is why they need re-rendering rather than patching.
    parser.add_argument("--margin", type=int, default=64)
    parser.add_argument("--title-top", type=int, default=240)
    parser.add_argument("--caption-bottom", type=int, default=190)
    parser.add_argument("--caption-size", type=int, default=27)
    parser.add_argument("--scrim", type=float, default=0.95)
    parser.add_argument("--no-hook", dest="hook", action="store_false")
    parser.add_argument("--hook-size", type=int, default=34)
    parser.add_argument("--hook-gap", type=int, default=82)
    # Physarum only: the band the agents are held in, so the title and the hook
    # have black to sit on. Set band-top >= band-bottom to switch it off.
    # Somite only. The tail has to end clear of the hook, and the segment
    # length is the one number that trades the size of a block against how many
    # of them get stamped out inside the clip.
    parser.add_argument("--somite-length", type=float, default=135.0)
    parser.add_argument("--tail-start", type=float, default=520.0)
    parser.add_argument("--tail-end", type=float, default=1400.0)
    parser.add_argument("--densify", type=float, default=1.60)
    parser.add_argument("--cell-samples", type=int, default=10)
    parser.add_argument("--cell-radius", type=float, default=3.1)
    parser.add_argument("--cell-reference", type=float, default=92.0)
    parser.add_argument("--band-top", type=float, default=330.0)
    parser.add_argument("--band-bottom", type=float, default=1400.0)
    return parser.parse_args()


if __name__ == "__main__":
    options = parse_args()
    for edition_name in options.edition or list(EDITIONS):
        print(f"Rendering {edition_name} ...", flush=True)
        print(f"Saved {render_edition(edition_name, options)}", flush=True)
