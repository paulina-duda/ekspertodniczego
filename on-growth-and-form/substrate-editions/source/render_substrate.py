#!/usr/bin/env python3
"""Four biomorphs, three of them alive, in the luminous house style.

The companion set in `../source/` runs two mathematical processes against one
biological one. This set inverts that: HYPHAE, CLEAVAGE and REENTRY are
processes a microscope can be pointed at, and SANDPILE is a rule about integers
that has no business producing an organism and produces one anyway.

Everything structural is inherited -- black field, additive accumulation into a
float buffer, log-density tone mapping, multi-scale bloom, spaced title,
monospace caption, a cover frame for the grid. Two things are not.

**Eight seconds, and the clip is a loop.** It opens on the finished organism,
cuts to a single seed, and grows back to exactly the frame it opened on. The
first thing anyone sees is the payoff, which is what buys the second of
attention; the cut is what turns that into a question; and because the last
frame is the first frame, the loop closes without a seam and the answer plays
again before anyone notices it has.

**Growth is paced by measurement, not by the clock.** Every one of these
processes accelerates or stalls on its own schedule -- a mycelium creeps and
then floods, an embryo doubles, a sandpile's edge slows as the square root of
its grain count. Left on a linear timeline each one crawls and then bolts. So
each model reports a scalar for how far along it is, and frames are placed at
equal intervals of *that*, which is what keeps the growth hypnotic rather than
merely present. REENTRY is the exception that proves the rule: a wave in an
excitable medium travels at a fixed speed, so equal steps of the clock already
are equal steps of the process, and it is banked one state per frame.
"""

from __future__ import annotations

import argparse
import math
import os
import pickle
import subprocess
import time
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import glow
import growths


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "instagram" / "phone-9x16"

# Distinct from the sibling set's violet-magenta-cyan, so the two editions do
# not compete on the grid: one warm and fungal, one cold and clinical, one that
# posterises into four flat bands because the process only has four states.
MYCELIUM = [(8, 2, 0), (78, 20, 0), (200, 70, 0), (255, 150, 20), (255, 220, 110), (255, 250, 220)]
EPITHELIUM = [(2, 6, 18), (0, 60, 100), (0, 160, 215), (70, 225, 255), (185, 248, 255), (240, 255, 255)]
# Exactly four stops, because the process has exactly four states. A longer ramp
# samples this one at 0, 1/3, 2/3 and 1 and lands three of those between stops,
# which muddies the only thing the picture has to say: how many grains are here.
LATTICE = [(30, 0, 90), (120, 0, 255), (255, 0, 140), (120, 255, 0)]
# Phosphor. The wake is the piece -- almost every lit pixel is tissue that has
# already fired -- so the ramp spends most of its length in the dark greens and
# only reaches white in the couple of cells that are firing right now.
PHOSPHOR = [(2, 10, 7), (0, 62, 44), (0, 150, 96), (60, 226, 150), (175, 250, 206), (240, 255, 246)]
# Rose, because the other four substrate palettes have taken amber, cyan, acid
# and green, and colour here is age: the oldest droplets sit at the dark end and
# the ones that grew last come out nearly white.
CYTOSOL = [(8, 2, 14), (58, 6, 52), (140, 14, 88), (222, 52, 96), (255, 138, 122), (255, 232, 214)]
# Load, not orientation, and the reason is worth keeping. Orientation is cyclic,
# so its ramp has to return to its first stop; holding luminance level all the
# way round -- which is what stops one arbitrary direction reading as a lighting
# fault -- costs the dark low end, and with it house rule one. The first cut came
# out an evenly lit pastel mosaic in which nothing was brighter for being denser
# and the cells standing up did not separate at all. Load has a true zero, so the
# ramp can start at black and mean it. Blue only in the dark end, as an accent.
STRESS = [(4, 2, 18), (36, 10, 88), (104, 22, 196), (186, 74, 255), (236, 168, 255), (255, 246, 255)]
# The cells that have left the plane, deliberately off the ramp and warm against
# it: they are the one thing in the frame that is no longer being measured.
UPRIGHT = (255, 214, 122)
# The orientation ramp, kept for the `_orientation` variant. Cyclic, and held at
# roughly level luminance all the way round so that no one direction reads as a
# lighting fault. The cost is the dark low end -- see STRESS above -- so this is
# a look, not the default, and it is paired with a paler upright.
NEMATIC = [(255, 62, 148), (255, 150, 48), (206, 250, 92), (58, 224, 186), (255, 62, 148)]
NEMATIC_UPRIGHT = (255, 252, 240)
# The lawn, by how far through lysis it is. No stop is dark: brightness here has
# to come from how much lawn is on the pixel, and a cleared plaque is black
# because nothing is left in it, not because the ramp said so. A dark low end
# would have made the healthy lawn -- most of the plate, most of the clip --
# read as empty.
AGAR = [(84, 118, 44), (128, 168, 56), (176, 214, 78), (216, 240, 128), (245, 252, 210), (255, 255, 248)]
# The mutants, off the ramp because they are not on the same axis as the lawn:
# they are a different lineage, and the piece is about the difference.
MUTANT = (255, 122, 96)
# Colour in `defect` is how recently a tear went past, and almost all of the
# drop has had no tear through it lately -- so, like AGAR, **no stop is dark**.
# Brightness here comes from how fast the film is moving, not from the ramp; a
# dark low end would black out the quiet film, which is most of every frame.
# Steel for the film, ember for a fresh tear: the low end is cold and
# desaturated so it reads as grey rather than as a blue piece.
FILAMENT = [(44, 66, 86), (72, 104, 128), (134, 140, 140), (206, 160, 108), (252, 186, 96), (255, 246, 224)]
# The same ramp with a petrol film instead of a steel one, kept as the
# alternative rather than as a variant: more saturated, and closer to the green
# PHOSPHOR and the cyan EPITHELIUM already on the grid, which is why it is not
# the default. Same rule -- no dark stop.
TEAR = [(30, 70, 72), (54, 108, 106), (118, 150, 138), (206, 160, 108), (252, 186, 96), (255, 246, 224)]

EDITIONS: dict[str, dict] = {
    "hyphae": {
        "kind": "points",
        "title": "Hyphae",
        "slug": "hyphae_mycelial-network_substrate",
        "palette": MYCELIUM,
        "exposure": 1.22,
        "boost": 1.26,
        "caption": (
            "fungal mycelium",
            "extend · branch · anastomose",
            "fusion makes a network, not a tree",
        ),
        "hook": ("A tree branches. A fungus branches back.",),
    },
    "cleavage": {
        "kind": "field",
        "title": "Cleavage",
        "slug": "cleavage_embryonic-packing_substrate",
        "palette": EPITHELIUM,
        "exposure": 1.18,
        "boost": 1.24,
        "caption": (
            "embryonic cleavage",
            "divide · relax · repack",
            "fixed volume, halving cells",
        ),
        "hook": ("The only kind of growth that does not grow",),
    },
    "sandpile": {
        "kind": "field",
        "title": "Sandpile",
        "slug": "sandpile_abelian-lattice_substrate",
        "palette": LATTICE,
        "exposure": 1.00,
        "boost": 0.80,
        "caption": (
            "abelian sandpile",
            "four grains on a cell, one to each side",
            "150,000 grains dropped on one square",
        ),
        "hook": ("One rule about integers. No biology at all.",),
    },
    "condensate": {
        "kind": "field",
        "title": "Condensate",
        "slug": "condensate_phase-separation_substrate",
        "palette": CYTOSOL,
        "exposure": 1.12,
        "boost": 1.18,
        "caption": (
            "liquid-liquid phase separation",
            "demix · round up · coalesce",
            "nucleolus · stress granule · P granule",
        ),
        "hook": ("Nothing was built. It only stopped mixing.",),
    },
    "packing": {
        "kind": "points",
        "title": "Packing",
        "slug": "packing_monolayer-verticalisation_substrate",
        "palette": STRESS,
        "exposure": 1.10,
        "boost": 1.16,
        "caption": (
            "bacterial monolayer · verticalisation (Beroz 2018)",
            "elongate · divide · shove · stand up",
            "2 cells to 5,496 · 56% no longer lying down",
        ),
        "hook": ("Room runs out. Growth does not.",),
    },
    "plaque": {
        "kind": "points",
        "title": "Plaque",
        "slug": "plaque_luria-delbruck_substrate",
        "palette": AGAR,
        # `sharp`. A plaque is an edge -- the whole subject is where the lawn
        # stops -- and the default halo smears every one of them into smoke.
        "exposure": 1.00,
        "boost": 1.05,
        "bloom_threshold": 0.55,
        "bloom_strength": 0.25,
        "look": "sharp",
        "caption": (
            "phage on a bacterial lawn · Luria & Delbrück 1943",
            "adsorb · burst · diffuse · clear",
            "200 resistant cells, present before the phage landed",
        ),
        "hook": ("Nothing here learned to survive.",),
    },
    "defect": {
        "kind": "points",
        "title": "Defect",
        "slug": "defect_active-nematic_substrate",
        "palette": FILAMENT,
        "exposure": 1.12,
        "boost": 1.15,
        "caption": (
            "active nematic · kinesin on microtubules (Sanchez 2012)",
            "align · slide · bend · tear",
            "0 defects to 528 · each one born with its opposite",
        ),
        "hook": ("Nothing here is alive. It still cannot rest.",),
    },
    "reentry": {
        "kind": "field",
        "title": "Reentry",
        "slug": "reentry_excitable-medium_substrate",
        "palette": PHOSPHOR,
        "exposure": 1.15,
        "boost": 1.20,
        "caption": (
            "excitable medium · Barkley model",
            "fire · refract · recover",
            "one beat too early and it never stops",
        ),
        "hook": ("Nothing in the rule says spiral.",),
    },
}


# --------------------------------------------------------------------------
# Encoding
# --------------------------------------------------------------------------


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


# --------------------------------------------------------------------------
# Shared pieces
# --------------------------------------------------------------------------


def build_overlay(width: int, height: int, spec: dict, args) -> Image.Image:
    """Title, hook and data block — one text layer, drawn once, held all clip.

    The hook sits in the strip between the form and the data block, centred,
    a few points above the block so it reads as the louder of the two and no
    louder than that: every pixel it takes is a pixel the organism gives up.
    Plex regular throughout, per house rule 5.
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
        scrim=args.scrim,
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


def even_schedule(metric: np.ndarray, frames: int) -> np.ndarray:
    """State indices placed at equal intervals of progress, not of time.

    The metric is forced upward before inverting: a couple of these processes
    can dip -- cells drift during relaxation, hyphal tips fuse and stop -- and a
    non-monotonic curve inverts into a schedule that runs backwards for a frame.
    """
    curve = np.maximum.accumulate(np.asarray(metric, dtype=np.float64))
    curve -= curve[0]
    curve /= max(curve[-1], 1e-9)
    return np.searchsorted(curve, np.linspace(0.0, 1.0, frames)).clip(0, len(curve) - 1)


def place_square(field: np.ndarray, height: int, width: int, factor: int) -> np.ndarray:
    """Block-upsample a square simulation and centre it in the frame."""
    grown = np.repeat(np.repeat(field, factor, axis=0), factor, axis=1)
    canvas = np.zeros((height, width), dtype=np.float32)
    for axis, (target, source) in enumerate(zip((height, width), grown.shape)):
        if source > target:
            start = (source - target) // 2
            grown = np.take(grown, np.arange(start, start + target), axis=axis)
    offset_y = (height - grown.shape[0]) // 2
    offset_x = (width - grown.shape[1]) // 2
    canvas[offset_y : offset_y + grown.shape[0], offset_x : offset_x + grown.shape[1]] = grown
    return canvas


def tone(colour_sum: np.ndarray, density: np.ndarray, reference: float, spec: dict, args) -> np.ndarray:
    """`venation` shipped on `sharp` and its filename never said so, so a
    re-render silently changed the cut. A piece that is not on the default look
    pins it here instead of relying on the flags being remembered."""
    linear = glow.flame_map(colour_sum, density, reference, boost=spec["boost"])
    linear = glow.bloom(
        linear,
        threshold=spec.get("bloom_threshold", args.bloom_threshold),
        strength=spec.get("bloom_strength", args.bloom_strength),
    )
    return glow.to_bytes(glow.tone_map(linear, exposure=spec["exposure"]))


# --------------------------------------------------------------------------
# Timelines: each returns draw(u) for u in 0..1, and the finished frame at u = 1
# --------------------------------------------------------------------------


def hyphae_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    height, width = args.height, args.width
    model = growths.Hyphae(height, width)
    progress = [model.metric()]
    while len(model.x) and model.step_index < args.hyphae_steps:
        model.step(1)
        progress.append(model.metric())
    points, ages = model.samples()
    print(f"  hyphae: {model.step_index} steps, {len(points):,} samples, {model.metric()/(height*width):.0%} lit", flush=True)

    schedule = even_schedule(np.asarray(progress), args.duration_frames)
    palette = glow.build_palette(spec["palette"])
    caption = build_overlay(width, height, spec, args)
    span = max(float(ages[-1]), 1.0)
    colours = glow.sample_palette(palette, (ages / span).astype(np.float32))

    def weights_for(count: int, now: float) -> np.ndarray:
        # The advancing front is the only part of the picture that is doing
        # anything; lighting it is what gives the eye something to follow.
        recent = np.exp(-(now - ages[:count]) / args.tip_decay)
        return (1.0 + args.tip_boost * recent).astype(np.float32)

    reference = 1.0

    def draw(u: float) -> np.ndarray:
        step = float(schedule[min(int(u * (len(schedule) - 1)), len(schedule) - 1)])
        count = max(int(np.searchsorted(ages, step, side="right")), 2)
        weight = weights_for(count, step)
        colour_sum, density = glow.splat(width, height, points[:count], colours[:count], weight)
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    ones = np.ones(len(points), dtype=np.float32)
    _, probe = glow.splat(width, height, points, np.zeros((len(points), 3), dtype=np.float32), ones)
    reference = float(np.percentile(probe[probe > 0], 92.0))
    return draw, draw(1.0)


def cleavage_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    height, width = args.height, args.width
    simulation_height, simulation_width = height // 2, width // 2
    model = growths.Cleavage(
        simulation_height, simulation_width, radius=simulation_width * 0.44, divide_rate=args.divide_rate
    )
    states: list[tuple[np.ndarray, np.ndarray]] = []
    progress: list[float] = []
    for _ in range(args.cleavage_steps):
        model.step(1)
        states.append((model.centres.copy(), model.generation.copy()))
        # Wall length rises with the square root of the cell count at fixed
        # area, and wall length is what the frame actually shows.
        progress.append(math.sqrt(model.metric()))
    print(f"  cleavage: {args.cleavage_steps} steps, {len(model.centres):,} cells", flush=True)

    schedule = even_schedule(np.asarray(progress), args.duration_frames)
    palette = glow.build_palette(spec["palette"])
    caption = build_overlay(width, height, spec, args)
    reference = 1.0

    def fields_at(index: int) -> tuple[np.ndarray, np.ndarray]:
        model.centres, model.generation = states[index]
        density, shade = model.fields()
        return place_square_pair(density, shade, height, width)

    def place_square_pair(density, shade, height, width):
        return (
            np.repeat(np.repeat(density, 2, axis=0), 2, axis=1)[:height, :width],
            np.repeat(np.repeat(shade, 2, axis=0), 2, axis=1)[:height, :width],
        )

    def draw(u: float) -> np.ndarray:
        density, shade = fields_at(int(schedule[min(int(u * (len(schedule) - 1)), len(schedule) - 1)]))
        colour_sum = glow.sample_palette(palette, shade) * density[:, :, None]
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    final_density, _ = fields_at(len(states) - 1)
    reference = float(np.percentile(final_density[final_density > 0], 92.0))
    return draw, draw(1.0)


def sandpile_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    height, width = args.height, args.width
    pile = growths.Sandpile(args.pile_size)
    states = pile.record(args.duration_frames, args.grains)
    print(f"  sandpile: {pile.grains:,} grains, radius {math.sqrt(pile.metric()/math.pi):.0f} lattice cells", flush=True)

    palette = glow.build_palette(spec["palette"])
    caption = build_overlay(width, height, spec, args)
    reference = 1.0

    # The frame each cell first held a grain. A cell that has toppled itself
    # empty is still part of the pile, so "inside" cannot be read off the
    # current grid; and walking the whole history per frame to find out is both
    # slow and, if subsampled to make it fast, wrong.
    first_lit = np.full(states[0].shape, len(states), dtype=np.int32)
    for index, state in enumerate(states):
        np.minimum(first_lit, np.where(state > 0, index, len(states)), out=first_lit)

    def fields_at(index: int) -> tuple[np.ndarray, np.ndarray]:
        grid = states[index].astype(np.float32)
        earlier = states[max(index - 1, 0)].astype(np.float32)
        touched = first_lit <= index
        shade = grid / 3.0
        density = np.where(touched, 0.45 + 0.55 * shade, 0.0)
        density = density + args.front_boost * (grid != earlier)
        return (
            place_square(density.astype(np.float32), height, width, args.pile_factor),
            place_square(shade.astype(np.float32), height, width, args.pile_factor),
        )

    def draw(u: float) -> np.ndarray:
        density, shade = fields_at(min(int(u * (len(states) - 1)), len(states) - 1))
        colour_sum = glow.sample_palette(palette, shade) * density[:, :, None]
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    final_density, _ = fields_at(len(states) - 1)
    reference = float(np.percentile(final_density[final_density > 0], 92.0))
    return draw, draw(1.0)


def reentry_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    height, width = args.height, args.width
    model = growths.Excitable(
        height // 2,
        width // 2,
        epsilon=args.epsilon,
        roughness=args.roughness,
        dt=args.reentry_dt,
        afterglow=args.afterglow,
    )
    states = model.record(args.duration_frames, args.reentry_steps, tuple(args.stimulus))
    print(
        f"  reentry: {args.duration_frames * args.reentry_steps:,} steps, "
        f"{len(args.stimulus)} premature beats, {model.metric()/model.dish.sum():.0%} of the dish fired",
        flush=True,
    )

    palette = glow.build_palette(spec["palette"])
    caption = build_overlay(width, height, spec, args)
    reference = 1.0

    def fields_at(index: int) -> tuple[np.ndarray, np.ndarray]:
        density, shade = growths.Excitable.fields(states[index])
        return (
            np.repeat(np.repeat(density, 2, axis=0), 2, axis=1)[:height, :width],
            np.repeat(np.repeat(shade, 2, axis=0), 2, axis=1)[:height, :width],
        )

    def draw(u: float) -> np.ndarray:
        density, shade = fields_at(min(int(u * (len(states) - 1)), len(states) - 1))
        colour_sum = glow.sample_palette(palette, shade) * density[:, :, None]
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    final_density, _ = fields_at(len(states) - 1)
    reference = float(np.percentile(final_density[final_density > 0], 92.0))
    return draw, draw(1.0)


def condensate_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    height, width = args.height, args.width
    # A quarter of the frame, upsampled fourfold. Coarsening is a t^(1/3) law, so
    # doubling the grid costs eight times the steps to reach the same droplet
    # size relative to the dish -- and the droplets are smooth blobs, which
    # survive being enlarged far better than anything with a filament in it.
    model = growths.Condensate(
        height // 4,
        width // 4,
        epsilon=args.epsilon_ch,
        dt=args.condensate_dt,
        mixture=args.mixture,
        reference_radius=args.droplet_reference,
    )

    # Banked as bytes, one state per frame, then scheduled by coarsening rather
    # than by the clock. Droplet growth is a power law: half the visible change
    # happens in the first few hundred steps and the rest takes tens of
    # thousands, so equal steps of time would spend most of the clip on a still.
    # Nothing is visible until the mixture actually separates: starting off
    # centre at -0.35, every cell is on the same side of zero and there is no
    # interface at all until the noise has been amplified past it. Banking from
    # step zero would spend the opening frames on a blank dish and hand the
    # scheduler a metric of zero to divide by.
    model.step(args.condensate_settle)

    # Banked on a cube-root schedule, not at equal step intervals, and this is
    # the whole difference between a clip that moves and one that stutters.
    # Coarsening is a t^(1/3) law: sampled evenly in *time*, the droplet scale
    # leaps in the first few states and then crawls, so the metric scheduler --
    # which picks states at equal increments of that scale -- finds nothing to
    # pick between and holds one state for twenty-odd frames. Spacing the states
    # so that t^(1/3) is linear makes the increments equal instead, and the
    # scheduler then advances about one state per frame.
    #
    # Measured on the version that shipped first: 117 of 239 frame transitions
    # were identical to the frame before, the longest freeze ran 0.70 s, and it
    # sat in the opening two seconds.
    start = float(args.condensate_settle)
    end = start + float(args.condensate_total)
    marks = np.linspace(start ** (1 / 3), end ** (1 / 3), args.condensate_states + 1) ** 3

    states: list[tuple[np.ndarray, np.ndarray]] = []
    progress: list[float] = []
    reached = start
    for target in marks[1:]:
        model.step(max(int(round(target - reached)), 1))
        reached = target
        density, shade = model.fields()
        states.append(
            ((density * 255.0).astype(np.uint8), (shade * 255.0).astype(np.uint8))
        )
        progress.append(model.metric())
    print(
        f"  condensate: {int(reached):,} steps, "
        f"droplets fattened from {progress[0]:.1f} to {progress[-1]:.1f} cells of area per cell of surface",
        flush=True,
    )

    # Played straight through: 240 banked states into 229 frames, in order.
    #
    # Not for want of trying a scheduler. Any of them can only do two things --
    # repeat a state or skip one -- and repeating is exactly the stutter being
    # avoided. Pacing by the droplet scale froze 117 of 239 transitions, because
    # coarsening is a t^(1/3) law and the scale spends most of its range in the
    # first few states. Pacing by measured picture-change was worse where it
    # counted: "equal change per frame" wants to insert frames where the change
    # is large, and with no intermediate states to insert it repeats the state
    # instead, so it dwelt precisely on the fastest-moving part.
    #
    # The pacing belongs in how the states were banked, which the cube-root
    # spacing above already does: change per banked state falls from 0.82 to
    # 0.19, a gentle deceleration that suits a process winding down. Straight
    # playback then leaves only what the physics does -- measured at 1% of
    # consecutive states below the stutter threshold, against a house norm of 4%.
    palette = glow.build_palette(spec["palette"])
    caption = build_overlay(width, height, spec, args)
    reference = 1.0

    def fields_at(index: int) -> tuple[np.ndarray, np.ndarray]:
        density, shade = states[index]
        return (
            np.repeat(np.repeat(density.astype(np.float32) / 255.0, 4, axis=0), 4, axis=1)[:height, :width],
            np.repeat(np.repeat(shade.astype(np.float32) / 255.0, 4, axis=0), 4, axis=1)[:height, :width],
        )

    def draw(u: float) -> np.ndarray:
        density, shade = fields_at(min(int(u * (len(states) - 1)), len(states) - 1))
        colour_sum = glow.sample_palette(palette, shade) * density[:, :, None]
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    final_density, _ = fields_at(len(states) - 1)
    reference = float(np.percentile(final_density[final_density > 0], 92.0))
    return draw, draw(1.0)


def packing_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    height, width = args.height, args.width
    model = growths.Packing(
        dish=args.packing_dish,
        adhesion=args.packing_adhesion,
        iterations=args.packing_iterations,
    )
    states: list[tuple] = []
    progress: list[float] = []

    def bank() -> None:
        head, tail, length, vertical, pressure, threshold = model.state()
        states.append((head.astype(np.float32), tail.astype(np.float32),
                       length.astype(np.float32), vertical,
                       pressure.astype(np.float32), threshold.astype(np.float32)))
        progress.append(model.metric())

    # Simulated once and banked, for the same reason the sandpile is: the run is
    # minutes long and every look decision -- palette, ramp, bloom -- wants to be
    # judged on the same colony rather than on a fresh one.
    cache = args.packing_cache
    if cache is not None and cache.exists():
        with cache.open("rb") as handle:
            states, progress, summary = pickle.load(handle)
        print(f"  packing: {summary} [from {cache.name}]", flush=True)
    else:
        while not model.full() and model.steps < args.packing_max_steps:
            model.step(1)
            bank()
        wall = len(states)
        for _ in range(args.packing_past):
            model.step(1)
            bank()

        report = model.overlap()
        summary = (
            f"{model.steps} steps, {report['cells']:,} cells, "
            f"{model.upright():.0%} standing up, dish full at step {wall}, "
            f"density {report['density']:.2f}, contact overlap {report['mean']:.1%} mean "
            f"/ {report['max']:.0%} max"
        )
        print(f"  packing: {summary}", flush=True)
        if cache is not None:
            cache.parent.mkdir(parents=True, exist_ok=True)
            with cache.open("wb") as handle:
                pickle.dump((states, progress, summary), handle, protocol=4)

    # Progress is derived from the banked states rather than read back from the
    # model, so the pacing can be re-tuned against a run that is already on disk
    # instead of costing another eight minutes of simulation.
    #
    # Cell count is the wrong scalar to pace on, and the failure is at the very
    # front of the clip: the two founder cells take about a hundred and twenty
    # steps to reach dividing length, so the count sits flat at 2 while the only
    # thing happening is elongation. Every frame the schedule spends in there
    # lands on a state that differs from its neighbour by half a percent of a
    # cell, and the motion check reads them as frozen -- 5.7% of transitions
    # after the hold, all of them inside the first second, which is the worst
    # second in the clip to lose.
    #
    # Area has no such plateau: it rises smoothly from the first step, because
    # the cells are always elongating whether or not they are dividing. What
    # area cannot do is pace the second half, where the dish is full and the
    # picture develops by cells leaving the plane rather than by covering more
    # of it. So the schedule advances on both -- area while the colony is free,
    # the standing-up count once it is not.
    radius = model.radius
    covered = np.array(
        [float((state[2] * 2.0 * radius + math.pi * radius**2).sum()) for state in states]
    )
    standing = np.array([float(state[3].sum()) for state in states])
    progress = covered / max(covered.max(), 1e-9) + args.packing_upright_weight * (
        standing / max(standing.max(), 1.0)
    )
    schedule = even_schedule(progress, args.duration_frames)
    orientation = args.packing_colour == "orientation"
    palette = glow.build_palette(NEMATIC if orientation else spec["palette"])
    standing_colour = NEMATIC_UPRIGHT if orientation else UPRIGHT
    caption = build_overlay(width, height, spec, args)
    scale = (min(width, height) * 0.44) / args.packing_dish
    centre = (width * 0.5, height * 0.5)
    reference = 1.0

    def parts(index: int):
        model.head, model.tail, model.length = (
            states[index][0].astype(np.float64),
            states[index][1].astype(np.float64),
            states[index][2].astype(np.float64),
        )
        model.vertical, model.pressure, model.threshold = (
            states[index][3], states[index][4].astype(np.float64),
            states[index][5].astype(np.float64),
        )
        return model.samples(scale, centre, mode=args.packing_colour)

    def buffers(index: int) -> tuple[np.ndarray, np.ndarray]:
        points, phase, upright = parts(index)
        colours = glow.sample_palette(palette, phase)
        colour_sum, density = glow.splat(
            width, height, points, colours, np.ones(len(points), dtype=np.float32)
        )
        if len(upright):
            # A cell seen end-on is a bright disc under a microscope, and it is
            # off the orientation ramp on purpose: it no longer has one.
            pale = np.tile(np.float32(standing_colour) / 255.0, (len(upright), 1))
            extra_colour, extra_density = glow.splat(
                width, height, upright, pale,
                np.full(len(upright), args.upright_boost, dtype=np.float32),
            )
            colour_sum = colour_sum + extra_colour
            density = density + extra_density
        return colour_sum, density

    def draw(u: float) -> np.ndarray:
        index = int(schedule[min(int(u * (len(schedule) - 1)), len(schedule) - 1)])
        colour_sum, density = buffers(index)
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    _, final_density = buffers(len(states) - 1)
    reference = float(np.percentile(final_density[final_density > 0], 92.0))
    return draw, draw(1.0)


def plaque_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    height, width = args.height, args.width
    model = growths.Plaque(
        args.plaque_size,
        args.plaque_size * 0.469,
        founders=args.founders,
        landings=args.landings,
        decay=args.phage_decay,
        resistant_rate=args.resistant_rate,
        adsorption=args.adsorption,
        lawn_start=args.lawn_start,
        landing_span=args.landing_span,
        latent=args.latent,
        landing_delay=args.landing_delay,
    )
    states: list[tuple] = []
    progress: list[float] = []
    for _ in range(args.plaque_steps):
        model.step(1)
        states.append(model.state() + (model.lysed.copy(),))
        progress.append(model.metric())
        report = model.report()
        if report["colonies"] > args.plaque_until:
            break
    print(
        f"  plaque: {model.steps} steps, {report['cleared']:.0%} of the plate cleared, "
        f"{report['lawn']:.0%} lawn left, {report['colonies']:.0%} resistant colonies",
        flush=True,
    )

    # The two processes have very different ranges -- half the plate is cleared,
    # the colonies reach five percent -- so paced on their sum the colonies get
    # a ninth of the clip and all of it at the end. Normalised separately and
    # weighted, the plaques still open across the whole clip and the colonies
    # get frames while they are small enough to read as colonies.
    area = max(float(model.dish.sum()), 1.0)
    # Biomass, not the count of pixels over a threshold. The thresholded version
    # saturates about thirty steps in -- the lawn crosses 0.10 everywhere almost
    # at once -- so the schedule handed a quarter of the clip to thirty states
    # and repeated each of them twice. The clip measured 25 frozen transitions
    # in second zero on that version, which is the worst second to lose.
    filled = np.maximum.accumulate(
        np.array([float((s0 + i0).sum()) / area for s0, i0, _, _ in states])
    )
    opened = np.array([float(l0.sum()) / area for _, _, _, l0 in states])
    grown = np.array([float((r0 > 0.10).sum()) / area for _, _, r0, _ in states])
    progress = (
        args.fill_weight * filled / max(filled.max(), 1e-9)
        + args.plaque_weight * opened / max(opened.max(), 1e-9)
        + args.colony_weight * grown / max(grown.max(), 1e-9)
    )
    schedule = even_schedule(progress, args.duration_frames)
    palette = glow.build_palette(spec["palette"])
    caption = build_overlay(width, height, spec, args)
    reference = 1.0

    # The lawn is plated once, as individual cells, and never moves. Carrying it
    # as a field instead would put smooth blobs on the frame -- which is the
    # register `condensate` was rejected for -- and worse, a lawn at carrying
    # capacity is flat, so the tone mapping and the bloom would have nothing to
    # work on across most of the plate. Plated as cells, brightness is once again
    # how many of them are on the pixel, and a plaque is black because it is
    # empty.
    generator = np.random.default_rng(4)
    angle = generator.uniform(0.0, 2.0 * math.pi, args.plated)
    reach = model.radius * np.sqrt(generator.uniform(0.0, 1.0, args.plated))
    rows = model.size * 0.5 + reach * np.sin(angle)
    columns = model.size * 0.5 + reach * np.cos(angle)
    sample_row = np.clip(rows.astype(np.int64), 0, model.size - 1)
    sample_column = np.clip(columns.astype(np.int64), 0, model.size - 1)
    scale = (min(width, height) * 0.44) / model.radius
    screen = np.column_stack([
        (columns - model.size * 0.5) * scale + width * 0.5,
        (rows - model.size * 0.5) * scale + height * 0.5,
    ]).astype(np.float32)
    # Cells are not all the same brightness; a real lawn is grainy.
    grain = (0.55 + 0.9 * generator.random(args.plated)).astype(np.float32)

    def buffers(index: int) -> tuple[np.ndarray, np.ndarray]:
        susceptible, infected, resistant, _ = states[index]
        here_s = susceptible[sample_row, sample_column]
        here_i = infected[sample_row, sample_column]
        here_r = resistant[sample_row, sample_column]

        # The ring of cells currently bursting is the only part of the plate
        # doing anything, and it is two cells wide. Lit at the same weight as the
        # lawn it disappears, and the clip measures 78.7% frozen -- the same
        # arithmetic that sank `cohort`. `hyphae` solved this by lighting its
        # advancing tips; this is the same fix on a different front.
        lawn_weight = (here_s + here_i * (1.0 + args.plaque_front_boost)) * grain
        lysing = np.clip(here_i / np.maximum(here_s + here_i, 1e-6), 0.0, 1.0)
        colour_sum, density = glow.splat(
            width, height, screen, glow.sample_palette(palette, lysing.astype(np.float32)), lawn_weight
        )
        mutant = np.tile(np.float32(MUTANT) / 255.0, (args.plated, 1))
        extra_colour, extra_density = glow.splat(
            width, height, screen, mutant, (here_r * grain * args.mutant_boost).astype(np.float32)
        )
        return colour_sum + extra_colour, density + extra_density

    def draw(u: float) -> np.ndarray:
        index = int(schedule[min(int(u * (len(schedule) - 1)), len(schedule) - 1)])
        colour_sum, density = buffers(index)
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    _, final_density = buffers(len(states) - 1)
    reference = float(np.percentile(final_density[final_density > 0], 92.0))
    return draw, draw(1.0)


def defect_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    height, width = args.height, args.width
    model = growths.Nematic(
        args.defect_size,
        activity=args.defect_activity,
        dt=args.defect_dt,
        afterglow=args.defect_afterglow,
    )
    # Two passes, and the reason is the one `condensate` wrote down: a scheduler
    # can only repeat a state or skip one. Pass one measures the progress curve;
    # pass two re-runs the same deterministic simulation and banks a state at
    # exactly the step each frame wants. The frames are then played straight
    # through, so there is nothing left for a scheduler to stutter over. Two
    # passes cost forty seconds against one banked run's twenty, and they also
    # cut the memory: 229 states instead of 701.
    def survey() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        probe = growths.Nematic(
            args.defect_size, activity=args.defect_activity,
            dt=args.defect_dt, afterglow=args.defect_afterglow,
        )
        order, counts, speed = [], [], []
        for step in range(args.defect_steps + 1):
            if step % args.defect_stride == 0:
                order.append(probe.order())
                plus, minus = probe.defects()
                counts.append(plus + minus)
                speed.append(float(probe.arrays()[2][probe.dish].mean()))
            probe.step(1)
        return (np.asarray(order, dtype=np.float64),
                np.asarray(counts, dtype=np.float64),
                np.asarray(speed, dtype=np.float64))

    started = time.time()
    order, counts, speed = survey()

    # No single scalar paces this, and it takes three of them.
    #
    # For the first six thousand steps the film is whole: there are no defects
    # at all to count, and the only thing happening is the alignment buckling,
    # which only the order parameter sees. After it breaks, the order parameter
    # is pinned near zero for the rest of the clip and the tearing is all that
    # is left developing.
    #
    # The defect count alone will not pace that second half either, and this is
    # what the first cut got wrong: it is an integer, so it is a step function.
    # 54.6% of consecutive banked states hold the same count and the longest
    # identical run is 124 states -- 3,720 simulation steps of a curve that does
    # not move. Paced on it the clip measured **15.4% frozen after the hold**
    # against a house norm of 4%. The third term is the cumulative mean flow
    # speed: how far the film has slid in total, which is continuous, never
    # flat, and still a measurement of the process rather than of the clock.
    total = np.cumsum(speed)
    total -= total[0]
    progress = (
        (1.0 - order / max(float(order[0]), 1e-9))
        + args.defect_weight * (counts / max(float(counts.max()), 1.0))
        + args.defect_travel_weight * (total / max(float(total.max()), 1e-9))
    )
    curve = np.maximum.accumulate(progress)
    curve -= curve[0]
    curve /= max(float(curve[-1]), 1e-9)
    wanted = np.interp(
        np.linspace(0.0, 1.0, args.duration_frames),
        curve, np.arange(len(curve), dtype=np.float64) * args.defect_stride,
    )
    wanted = np.round(wanted).astype(np.int64)
    # Strictly increasing: two frames on one simulation step would be the very
    # stutter the two passes are here to remove.
    for index in range(1, len(wanted)):
        wanted[index] = max(wanted[index], wanted[index - 1] + 1)
    wanted = np.minimum(wanted, args.defect_steps)

    model = growths.Nematic(
        args.defect_size, activity=args.defect_activity,
        dt=args.defect_dt, afterglow=args.defect_afterglow,
    )
    states: list[tuple] = []
    cursor = 0
    for step in range(args.defect_steps + 1):
        while cursor < len(wanted) and wanted[cursor] == step:
            states.append(model.state())
            cursor += 1
        model.step(1)
    while len(states) < len(wanted):
        states.append(model.state())

    plus, minus = model.defects()
    print(
        f"  defect: {args.defect_steps:,} steps twice on {model.device} in {time.time()-started:.0f}s, "
        f"{len(states)} states banked one per frame, drop radius {model.radius:.1f} of "
        f"{args.defect_size}, {plus + minus} defects (+{plus}/-{minus}), "
        f"order {order[0]:.3f} to {order[-1]:.4f}, film breaks at frame "
        f"{int(np.argmax(np.interp(wanted, np.arange(len(counts)) * args.defect_stride, counts) > 10))}"
        f" of {args.duration_frames}",
        flush=True,
    )
    schedule = np.arange(len(states))

    palette = glow.build_palette(TEAR if args.defect_palette == "tear" else FILAMENT)
    caption = build_overlay(width, height, spec, args)
    scale = (min(width, height) * 0.44) / model.radius
    centre = (width * 0.5, height * 0.5)

    # Brightness is how fast this patch of film is moving, against one fixed
    # reference for the whole clip -- so "brighter" means the same thing in
    # every frame. Ranked per frame it would say nothing, because the contrast
    # between the fast and slow parts barely changes; what changes is the
    # overall speed, and that is the measurement worth keeping.
    sampled = np.concatenate([
        states[index][2][model.dish].astype(np.float32)
        for index in range(0, len(states), max(len(states) // 24, 1))
    ])
    speed_reference = float(np.percentile(sampled, args.defect_speed_percentile))
    print(f"  defect: speed reference {speed_reference:.4f} "
          f"(p{args.defect_speed_percentile:g} over the banked run)", flush=True)
    reference = 1.0

    def buffers(index: int) -> tuple[np.ndarray, np.ndarray]:
        # The same seed every frame, deliberately. Re-scattering the seeds each
        # time makes the strokes crawl, and the crawl is louder than the film.
        points, values, weights = model.samples(
            states[index], scale, centre,
            seeds=args.defect_seeds, walk=args.defect_walk,
            generator=np.random.default_rng(args.defect_seed),
        )
        shade = np.clip(weights / speed_reference, 0.0, 1.0)
        colours = glow.sample_palette(palette, np.clip(values, 0.0, 1.0))
        # The floor is the film itself. An aligned nematic generates no flow at
        # all -- no bend, no force, no motion -- so speed alone draws the first
        # state of the clip as an empty frame, and the clip would open on black
        # and fade the drop in. A microscope would see the filaments whether or
        # not they were moving; the floor is that, and the speed on top of it is
        # what the activity adds.
        weight = args.defect_floor + (1.0 - args.defect_floor) * shade ** args.defect_gamma
        return glow.splat(width, height, points, colours, weight.astype(np.float32))

    def draw(u: float) -> np.ndarray:
        index = int(schedule[min(int(u * (len(schedule) - 1)), len(schedule) - 1)])
        colour_sum, density = buffers(index)
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    _, final_density = buffers(len(states) - 1)
    reference = float(np.percentile(final_density[final_density > 0], 92.0))
    return draw, draw(1.0)


TIMELINES = {
    "hyphae": hyphae_timeline,
    "cleavage": cleavage_timeline,
    "sandpile": sandpile_timeline,
    "reentry": reentry_timeline,
    "condensate": condensate_timeline,
    "packing": packing_timeline,
    "plaque": plaque_timeline,
    "defect": defect_timeline,
}


def render_edition(name: str, args: argparse.Namespace) -> Path:
    spec = EDITIONS[name]
    draw, finished = TIMELINES[name](spec, args)

    stem = f"{spec['slug']}_{args.width}x{args.height}_{args.duration:g}s_{args.fps}fps"
    if args.tag:
        stem += f"_{args.tag}"
    if args.hook and spec.get("hook"):
        # Same suffix the cleavage re-render carries, so the hooked Plex cut and
        # the older DejaVu one sit side by side in the folder without ambiguity.
        stem += "_hook_plex"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(finished).save(args.output_dir / f"{stem}.cover.png")
    if args.preview:
        return args.output_dir / f"{stem}.cover.png"

    output = args.output_dir / f"{stem}.mp4"
    encoder = start_encoder(output, args.width, args.height, args.fps)
    assert encoder.stdin is not None
    try:
        payload = finished.tobytes()
        for _ in range(args.hold):
            encoder.stdin.write(payload)
        growing = args.duration_frames - args.hold
        for index in range(growing):
            # Ends on u = 1, which is the frame the clip opened on, so the loop
            # has no seam in it.
            encoder.stdin.write(draw((index + 1) / growing).tobytes())
            if (index + 1) % 60 == 0:
                print(f"  {name}: frame {index + 1}/{growing}", flush=True)
    finally:
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError(f"ffmpeg failed while rendering {name}.")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", choices=sorted(EDITIONS), action="append")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--preview", action="store_true", help="Save the cover still and stop.")
    parser.add_argument("--tag", type=str, default=None, help="suffix, so a variant lands beside the original")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--duration", type=float, default=8)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--hold", type=int, default=11, help="frames held on the finished form")
    parser.add_argument("--margin", type=int, default=64, help="left inset, shared by all three text layers")
    # Not symmetric and not negotiable: the Reel player lays its header over the
    # top of the frame and the account row over the bottom, and the bottom needs
    # the most clearance of the two.
    parser.add_argument("--title-top", type=int, default=240)
    parser.add_argument("--caption-bottom", type=int, default=190)
    parser.add_argument("--caption-size", type=int, default=27)
    parser.add_argument("--scrim", type=float, default=0.95)
    parser.add_argument("--no-hook", dest="hook", action="store_false", help="drop the hook line")
    parser.add_argument("--hook-size", type=int, default=34)
    parser.add_argument("--hook-gap", type=int, default=82, help="hook ink down to the data block's ink")
    parser.add_argument("--bloom-threshold", type=float, default=0.30)
    parser.add_argument("--bloom-strength", type=float, default=0.60)
    parser.add_argument("--hyphae-steps", type=int, default=1400)
    parser.add_argument("--tip-boost", type=float, default=2.2)
    parser.add_argument("--tip-decay", type=float, default=26.0)
    parser.add_argument("--cleavage-steps", type=int, default=300)
    parser.add_argument("--divide-rate", type=float, default=0.035)
    parser.add_argument("--pile-size", type=int, default=379)
    parser.add_argument("--pile-factor", type=int, default=3)
    parser.add_argument("--grains", type=int, default=150_000)
    parser.add_argument("--front-boost", type=float, default=0.55)
    parser.add_argument("--reentry-steps", type=int, default=16, help="simulation steps per frame")
    parser.add_argument("--reentry-dt", type=float, default=0.10)
    parser.add_argument("--epsilon", type=float, default=0.05, help="how brief the excited state is")
    parser.add_argument("--roughness", type=float, default=0.016, help="spread of the excitability field")
    parser.add_argument("--afterglow", type=float, default=45.0, help="half-life of the phosphor, in steps")
    parser.add_argument("--packing-dish", type=float, default=54.0, help="dish radius in cell widths")
    # Nothing tips over below this: measured contact load during free growth
    # tops out near 0.33, so a threshold of 0.45 keeps the monolayer intact
    # until the dish is full and there is nowhere left to put a new cell.
    parser.add_argument("--packing-adhesion", type=float, default=0.45, help="contact load a cell holds before it stands up")
    parser.add_argument("--packing-iterations", type=int, default=24)
    parser.add_argument("--packing-past", type=int, default=400, help="steps run on after the dish is full")
    parser.add_argument("--packing-max-steps", type=int, default=4000)
    # How much of the clip the breakup gets. At 0 the schedule is paced on area
    # alone and the dish fills at frame 157 of 229, leaving 72 for the part that
    # develops; at 0.8 it fills at 83 and the breakup gets 146. 0.8 also gives
    # the most even frame-to-frame change of the values tried -- the smallest
    # step is 0.69 of the mean, against 0.26 at 0 and 0.47 at 1.4.
    parser.add_argument("--packing-upright-weight", type=float, default=0.8, help="weight on the standing-up count in the pacing")
    parser.add_argument("--packing-colour", choices=("load", "orientation"), default="load")
    parser.add_argument("--plaque-size", type=int, default=384)
    parser.add_argument("--plaque-steps", type=int, default=6000)
    # Stopped while a colony is still a dot inside its plaque. Left to 5% they
    # fill the clearing they grew in and the picture becomes blobs again.
    parser.add_argument("--plaque-until", type=float, default=0.035, help="stop once colonies cover this much")
    parser.add_argument("--founders", type=int, default=200, help="resistant cells present before the phage")
    parser.add_argument("--landings", type=int, default=130)
    parser.add_argument("--landing-span", type=int, default=560, help="steps over which phage arrive")
    # The latent period sets how wide the bursting ring is, and the ring is
    # the only thing on the plate that moves. At 1.2 it is two cells across
    # and the clip measured 32.6% frozen.
    parser.add_argument("--latent", type=float, default=1.2)
    parser.add_argument("--phage-decay", type=float, default=0.04)
    parser.add_argument("--resistant-rate", type=float, default=0.30)
    parser.add_argument("--adsorption", type=float, default=9.0)
    parser.add_argument("--lawn-start", type=float, default=0.10)
    parser.add_argument("--colony-weight", type=float, default=0.70)
    parser.add_argument("--plaque-weight", type=float, default=2.20)
    parser.add_argument("--fill-weight", type=float, default=0.60)
    parser.add_argument("--landing-delay", type=int, default=170, help="steps before the first phage lands")
    parser.add_argument("--plated", type=int, default=700_000, help="individual cells drawn on the plate")
    parser.add_argument("--plaque-front-boost", type=float, default=7.0, help="extra weight on the bursting ring")
    parser.add_argument("--mutant-boost", type=float, default=1.35)
    # `defect`. The drop is 0.44 of the grid, so the simulation square maps one
    # for one onto the frame width and the dish lands where the reel skill puts
    # it without any cropping.
    parser.add_argument("--defect-size", type=int, default=320)
    # Measured in the dish, at 0.86 ms a step on the GPU: 0 / 2 / 158 / 358 / 528
    # defects across 21,000 steps. Longer is denser and the last quarter gets
    # thinner -- 16% at 26,000 against 32% here.
    parser.add_argument("--defect-steps", type=int, default=21_000)
    parser.add_argument("--defect-stride", type=int, default=30, help="steps between banked states")
    parser.add_argument("--defect-activity", type=float, default=0.030, help="extensile active stress")
    parser.add_argument("--defect-dt", type=float, default=0.05)
    parser.add_argument("--defect-afterglow", type=float, default=400.0, help="half-life of the tear phosphor, in steps")
    parser.add_argument("--defect-seeds", type=int, default=320_000, help="streamlines drawn per frame")
    parser.add_argument("--defect-walk", type=int, default=9, help="samples along each streamline")
    parser.add_argument("--defect-seed", type=int, default=4, help="held fixed across frames on purpose")
    # 1.5 leaves the drop a flat milky wash: the log-density map compresses what
    # is already a narrow range and nothing in the film separates. 2.6 puts the
    # slow channels back into the dark, which is where the tearing shows.
    parser.add_argument("--defect-gamma", type=float, default=2.6, help="how hard speed is turned into brightness")
    parser.add_argument("--defect-speed-percentile", type=float, default=97.0)
    # Small on purpose. The floor buys the ordered film at the head of the clip;
    # paid past about 0.06 it also buys back the contrast the tearing is made of,
    # because the log-density map has only so much range. At 0.03 the still film
    # reads as a flat grey disc and the turbulence keeps its dark channels.
    parser.add_argument("--defect-floor", type=float, default=0.03, help="what the film is worth when it is not moving")
    # The film is whole for the first ~6,000 steps of 21,000. At 2.0 that phase
    # gets about a third of the clip, which is what it needs to read as a fabric
    # before it is a wreck.
    parser.add_argument("--defect-weight", type=float, default=2.0, help="weight on the defect count in the pacing")
    # The continuous term. Without it the pacing rides an integer step
    # function and the cut measured 15.4% frozen after the hold.
    parser.add_argument("--defect-travel-weight", type=float, default=1.0, help="weight on how far the film has slid in total")
    parser.add_argument("--defect-palette", choices=("filament", "tear"), default="filament")
    parser.add_argument("--packing-cache", type=Path, default=None, help="bank the run here and reuse it")
    parser.add_argument("--upright-boost", type=float, default=1.5)
    parser.add_argument("--condensate-states", type=int, default=240)
    # Ripening is slow by nature: 199 droplets at 20k steps, 22 at 1.2M. Stopping
    # early is what made the first cut look like almost nothing was happening.
    parser.add_argument("--condensate-total", type=int, default=1_200_000, help="steps after the settle")
    parser.add_argument("--condensate-settle", type=int, default=4000, help="steps before the first banked state")
    parser.add_argument("--condensate-dt", type=float, default=0.01)
    parser.add_argument("--epsilon-ch", type=float, default=1.0, help="interface width, and the stability limit")
    parser.add_argument("--mixture", type=float, default=-0.35, help="negative makes the dense phase a minority")
    parser.add_argument("--droplet-reference", type=float, default=20.0, help="radius, in cells, that reads as white")
    parser.add_argument(
        "--stimulus", type=float, action="append", default=None,
        help="fractions of the clip at which a premature beat is delivered",
    )
    parser.add_argument("--exposure", type=float, help="override the edition's exposure")
    parser.add_argument("--boost", type=float, help="override the edition's boost")
    args = parser.parse_args()
    args.duration_frames = round(args.duration * args.fps)
    if args.stimulus is None:
        # The first beat goes out into clear tissue; these land in the wake of
        # the one before, which is the only place a wave can be broken.
        args.stimulus = [0.16, 0.34, 0.52, 0.70]
    return args


if __name__ == "__main__":
    options = parse_args()
    for edition_name in options.edition or list(EDITIONS):
        for key in ("exposure", "boost"):
            if getattr(options, key) is not None:
                EDITIONS[edition_name][key] = getattr(options, key)
        print(f"Rendering {edition_name} ...", flush=True)
        print(f"Saved {render_edition(edition_name, options)}", flush=True)
