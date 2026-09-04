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
import copy
import math
import os
import subprocess
from pathlib import Path
from typing import Callable

import numpy as np
from scipy import ndimage
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

# HYPHAE 2.0. Colour here is not age and not an amount -- it is which spore the
# strand grew from, so the ramp has exactly one stop per spore and a segment
# lands on its own. No in-between colours means nothing to go muddy, and it is
# the same argument as LATTICE's four stops for four states. Brightness is
# carried by density instead, as in LINEAGE: a colony is not less of anything
# for being the first stop, which is why the frame is still black where nothing
# has grown. Six hues at full chroma, the reading a fluorescence microscope
# gives when strains are imaged on separate channels and the channels are
# summed. Retuned for `sharp` rather than ported from MYCELIUM -- with the halo
# down, amber cores come out pastel.
FLUORO = [(255, 0, 150), (0, 225, 255), (170, 255, 0), (255, 120, 0), (150, 60, 255), (0, 255, 160)]

# Hue is a lineage here, not an amount, so this ramp is the one in the set that
# does *not* darken towards its low end: a wedge landing on the first stop is
# not less of anything, and dimming it would say it was. Brightness is carried
# by the density channel instead, which is why the plate is still black where
# nothing has grown. The arc runs violet to gold and deliberately never reaches
# cyan or green -- CLEAVAGE owns the cold end of this edition.
LINEAGE = [(120, 20, 255), (200, 0, 230), (255, 0, 130), (255, 24, 40), (255, 100, 0), (255, 200, 20)]

# Colour here is what fired the cell -- how much synaptic input it was holding
# when it crossed threshold, ranked across the population -- so the ramp is an
# ordering in time, not an identity and not an amount. Five stops for the five
# fifths a rank divides the population into, the same argument as LATTICE's four
# stops for four states. It runs warm to cold because that is the order the
# reading goes in: a cell that got there on its own leak, through the shove of a
# small local wave, to one carried over by a front that had already recruited
# half the frame. Held at roughly one luminance across all five, unlike
# CYTOSOL's ramp: brightness in this piece is how recently a cell fired, and a
# palette that darkens at one end would fight that for the same pixels. Indigo
# is one fifth of the frame and the only cold stop, which is house rule 6's
# accent rather than a blue piece.
IGNITION = [(255, 246, 214), (255, 168, 78), (255, 84, 148), (198, 74, 255), (110, 96, 255)]

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
    # HYPHAE 2.0, and it changes four things rather than the two the rule asks
    # for: the look (bloom -> sharp), the scale of the mesh (sensor 7 -> 20,
    # branch_rate 0.030 -> 0.009), the shape (dish -> field), and what the colour
    # means (age -> which spore). It lands alongside the original, never on top
    # of it: --tag v2.
    "syncytium": {
        "kind": "points",
        "title": "Syncytium",
        "slug": "syncytium_hyphal-fusion_substrate",
        "palette": FLUORO,
        "look": "sharp",
        # sharp at a lifted exposure, which is `venation`'s setting rather than
        # `sector`'s: a frame 8% covered by one-pixel filaments has a fraction of
        # the density a solid colony has, and at the nominal 1.00/1.05 the mesh
        # came out bone-white and lost most of its colour to the grid downscale.
        "exposure": 1.10,
        "boost": 1.20,
        "bloom_threshold": 0.55,
        "bloom_strength": 0.25,
        "model": {
            # A wide avoidance radius and a third of the branching open the mesh
            # from 1.4 px between filaments to 14. That number is what retires
            # the objection recorded in the edition README -- the mycelium was
            # given a dish because unbounded it filled the frame, blew out to
            # white and put the caption on a bright field, and all three of those
            # are consequences of 72% coverage, not of the missing rim. At 8%
            # the frame keeps its black and `bound="frame"` is safe.
            "sensor": 20.0,
            "branch_rate": 0.009,
            "max_tips": 1750,
            "bound": "frame",
            # Six spores rather than one, because a single inoculum is a disc for
            # the first half of the clip whatever shape it is bounded to -- and
            # because fusion between two colonies is a stronger event than a
            # colony fusing with itself. One spore per palette stop.
            "seeds": 6,
            "tips": 5,
        },
        "colour": "founder",
        "caption": (
            "fungal mycelium · anastomosis",
            "extend · branch · fuse · stop",
            "six spores · 407 fusions joined two of them",
        ),
        "hook": ("A tree only branches apart.", "These branched into each other."),
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
    "culture": {
        "kind": "points",
        "title": "Culture",
        "slug": "culture_cortical-network_substrate",
        "palette": IGNITION,
        "colour": "recency",
        "exposure": 1.15,
        "boost": 1.20,
        "caption": (
            "dissociated cortical culture · Wagenaar et al. 2006",
            "charge · fire · deplete · recover",
            "colour is how long ago a cell fired · gold is now",
            "12,000 neurons · 570,560 synapses, none of them chosen",
        ),
        "hook": ("Every connection was cut.", "It is firing again."),
    },
    "sector": {
        "kind": "field",
        "title": "Sector",
        "slug": "sector_range-expansion_substrate",
        "palette": LINEAGE,
        # The sharp look, and named here rather than left to the command line.
        # The default bloom turned a solid plate into a pastel disc inside a
        # mid-tone veil: every wedge bleached towards white and the halo lifted
        # the black the whole account is composed on. venation shipped on sharp
        # without recording it anywhere and re-rendering changed the cut; this
        # does not repeat that.
        "look": "sharp",
        "exposure": 1.00,
        "boost": 1.05,
        "bloom_threshold": 0.55,
        "bloom_strength": 0.25,
        "caption": (
            "microbial range expansion · Hallatschek & Nelson 2007",
            "divide at the edge · drift · mutate · sweep",
            "colour is descent · hue drifts with each mutation",
            "48 founders · 8 of them still on the rim",
        ),
        "hook": ("Not one cell moved. Every border did.",),
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

    `--no-text` returns an empty layer. That is what a T4 legibility still is
    rendered with: a title names the subject, and a still captioned with its own
    name asks "is this a good drawing of X" rather than "what is this".
    """
    if not args.text:
        return Image.new("RGBA", (width, height), (0, 0, 0, 0))
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


def text_keepout(width: int, height: int, spec: dict, args) -> np.ndarray:
    """Ground the colony is not allowed onto: a ragged margin, and a halo of
    clear substrate around every glyph.

    The halo is taken from the text layer's own alpha, not from hand-measured
    boxes, so it follows the actual letterforms and stays correct if the copy or
    the type size changes. The scrim is switched off while measuring it -- it is
    a soft wash over most of the frame, and dilating that would forbid half the
    picture.

    **Both edges are perturbed by one smooth noise field, and that is not
    decoration.** A straight inset reads as a UI panel with the mycelium poured
    into it: the colony stops dead on a horizontal line, which no colony does.
    Letting the boundary wander by roughly its own depth costs nothing and the
    edge goes back to looking like the limit of a substrate.

    Cropping the render would slice filaments mid-stride. Forbidding the ground
    means the black is black because nothing was ever allowed to grow there, and
    because `Hyphae` senses the mask, tips turn away from it rather than dying
    on it.
    """
    ink_only = copy.copy(args)
    ink_only.scrim = 0.0
    alpha = np.asarray(build_overlay(width, height, spec, ink_only).split()[-1])
    options = spec["keepout"]

    generator = np.random.default_rng(options.get("seed", 20260902))
    noise = ndimage.gaussian_filter(
        generator.normal(size=(height, width)).astype(np.float32), sigma=options.get("sigma", 90.0)
    )
    noise = noise / max(float(np.abs(noise).max()), 1e-9)

    # The bottom margin is not a number anyone chose -- it is measured off the
    # copy block itself, so the hook and the data block always sit on black and
    # stay there if the copy changes length. Everything above is a halo around
    # the title only, which reads as the word stamped into the mat.
    lower_ink = np.flatnonzero((alpha[height // 2 :] > 8).any(axis=1))
    copy_top = height // 2 + int(lower_ink[0]) if len(lower_ink) else height
    bottom = height - copy_top + options.get("copy_clearance", 34.0)

    rows, columns = np.indices((height, width))
    rough = options.get("roughness", 0.0) * noise
    forbidden = (
        (rows < options["top"] + rough)
        | (height - 1 - rows < bottom + rough)
        | (np.minimum(columns, width - 1 - columns) < options["side"] + rough)
        | (ndimage.distance_transform_edt(alpha <= 8)
           < options["clearance"] + options.get("halo_roughness", 0.0) * noise)
    )

    # Open the growable region by a disc, then drop what is left over as small
    # islands. Without this the mask leaves slivers -- between a halo and the
    # margin, or along the bottom edge where the noise thins it -- and a sliver
    # narrower than the sensor is a trap: tips inside it cannot smell a way out,
    # mill around, and pile density into a strip that tone-maps to solid white
    # directly under the data block. Measured on the first cut of this variant.
    # Two distance transforms rather than binary_opening with a 61 x 61
    # structure, which is the same result and far cheaper.
    reach = options.get("throat", 30.0)
    allowed = ~forbidden
    eroded = ndimage.distance_transform_edt(allowed) >= reach
    allowed = ndimage.distance_transform_edt(~eroded) <= reach
    labels, found = ndimage.label(allowed)
    if found:
        areas = ndimage.sum(allowed, labels, range(1, found + 1))
        survivors = 1 + np.flatnonzero(areas >= options.get("min_patch", 40_000))
        allowed = np.isin(labels, survivors)
    return ~allowed


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
    model_options = dict(spec.get("model", {}))
    if spec.get("keepout"):
        forbidden = text_keepout(width, height, spec, args)
        model_options["keepout"] = forbidden
        print(f"  keepout: {1.0 - forbidden.mean():.1%} of the frame is growable", flush=True)
    model = growths.Hyphae(height, width, **model_options)
    progress = [model.metric()]
    while len(model.x) and model.step_index < args.hyphae_steps:
        model.step(1)
        progress.append(model.metric())
    points, ages = model.samples()
    print(f"  {spec['title'].lower()}: {model.step_index} steps, {len(points):,} samples, {model.metric()/(height*width):.0%} lit", flush=True)

    # `pace` bends how the frames are distributed over the run. 1.0 is equal
    # newly-lit pixels per frame, which is right when the colony has open black
    # to fill. Once it is growing into ground that is already bright, a newly
    # lit pixel changes the tone-mapped picture less, so equal pixels per frame
    # stops being equal change per frame and the last two seconds go still.
    # Below 1.0 the schedule advances further per frame late and less early.
    # Measured on the inset cut: 14.5% frozen frames at 1.0, 6.1% at 0.80,
    # 5.3% at 0.65 -- but 0.65 pushes six of them into the opening second,
    # which is the one place a freeze is unrecoverable, and 0.50 puts 29 there.
    schedule = even_schedule(np.asarray(progress) ** spec.get("pace", 1.0), args.duration_frames)
    palette = glow.build_palette(spec["palette"])
    caption = build_overlay(width, height, spec, args)

    if spec.get("colour", "age") == "fate":
        # Colour is what happened to the segment's tip, and it arrives when it
        # happens: a filament is slate while its tip is still running, and warms
        # to ember over `--fuse-warm` steps at the moment that tip fuses into an
        # older hypha. A segment whose tip reached the wall instead never warms,
        # so the finished frame separates the network from its dead ends.
        # Colouring by the *final* fate from the first frame would be a spoiler
        # and, worse, would throw away the only discrete event the piece has.
        fused_at = model.fusion_steps()[model.segments()].astype(np.float32)
        fused_at[fused_at < 0.0] = np.inf
        cold, hot = float(spec.get("unfused", 0.28)), float(spec.get("fused", 0.96))
        segments = len(model.fusion_steps())
        fused_segments = int((model.fusion_steps() >= 0).sum())
        print(
            f"    {segments:,} segments · {fused_segments:,} fused into the network "
            f"· {segments - fused_segments:,} ran to the wall",
            flush=True,
        )

        def colours_for(count: int, now: float) -> np.ndarray:
            warm = np.clip((now - fused_at[:count]) / args.fuse_warm, 0.0, 1.0)
            return glow.sample_palette(palette, (cold + (hot - cold) * warm).astype(np.float32))
    elif spec.get("colour") == "founder":
        # Hue is an identity, not an amount, so the palette has one stop per
        # spore and a segment lands exactly on its own -- no ramp, no in-between
        # colours to go muddy. Brightness is carried by density, as in LINEAGE:
        # a colony is not less of anything for being the first stop.
        per_sample = model.founders_of()[model.segments()]
        stops = len(spec["palette"])
        value = (per_sample % stops) / max(stops - 1, 1)
        by_founder = glow.sample_palette(palette, value.astype(np.float32))
        grafts = len(model.grafts)
        print(
            f"    {model.founders} spores · {len(model.fusion_steps()):,} segments · "
            f"{int((model.fusion_steps() >= 0).sum()):,} fused · {grafts:,} of those joined two spores",
            flush=True,
        )

        def colours_for(count: int, now: float) -> np.ndarray:
            return by_founder[:count]
    else:
        span = max(float(ages[-1]), 1.0)
        by_age = glow.sample_palette(palette, (ages / span).astype(np.float32))

        def colours_for(count: int, now: float) -> np.ndarray:
            return by_age[:count]

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
        colour_sum, density = glow.splat(width, height, points[:count], colours_for(count, step), weight)
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


def sector_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    height, width = args.height, args.width
    # Simulated at half the frame and block-upsampled twofold. The lattice is
    # the model -- one cell is one cell -- so this is the one edition where the
    # simulation size is not a speed compromise but the answer to how coarse the
    # colony should look. At 474 px of radius the dish lands on the house
    # figure, 0.44 of the short side.
    model = growths.Sector(
        args.sector_size,
        radius=args.sector_size * 0.494,
        founders=args.founders,
        mutation=args.mutation,
        beneficial=args.beneficial,
        advantage=args.advantage,
        hue_step=args.hue_step,
        inoculum=args.inoculum,
        pacing=args.pacing,
    )
    progress = [model.metric()]
    fronts = [model.front_lineages()]
    while model.step_index < args.sector_steps:
        before = int((model.label > 0).sum())
        model.step(1)
        if int((model.label > 0).sum()) == before:
            break
        progress.append(model.metric())
        fronts.append(model.front_lineages())
    print(
        f"  sector: {model.step_index} steps, {int((model.label > 0).sum()):,} cells, "
        f"radius {math.sqrt(int((model.label > 0).sum()) / math.pi):.0f} lattice cells, "
        f"{model.count} lineages founded, "
        f"{max(fronts[len(fronts)//4:])} holding the front at the quarter mark",
        flush=True,
    )

    schedule = even_schedule(np.asarray(progress), args.duration_frames)
    palette = glow.build_palette(spec["palette"])
    caption = build_overlay(width, height, spec, args)
    reference = 1.0

    def fields_at(index: int) -> tuple[np.ndarray, np.ndarray]:
        density, shade = model.fields(int(index), tip_boost=args.tip_boost_front, tip_decay=args.tip_decay_front)
        return (
            place_square(density, height, width, args.sector_factor),
            place_square(shade, height, width, args.sector_factor),
        )

    def draw(u: float) -> np.ndarray:
        density, shade = fields_at(schedule[min(int(u * (len(schedule) - 1)), len(schedule) - 1)])
        colour_sum = glow.sample_palette(palette, shade) * density[:, :, None]
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    final_density, _ = fields_at(schedule[-1])
    reference = float(np.percentile(final_density[final_density > 0], 92.0))
    return draw, draw(1.0)


def culture_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    height, width = args.height, args.width
    model = growths.Culture(
        height,
        width,
        neurons=args.neurons,
        reach=args.culture_reach,
        growth=args.culture_growth,
        weight=args.culture_weight,
        drive=args.culture_drive,
        depression=args.culture_depression,
        recovery=args.culture_recovery,
        afterglow=args.culture_afterglow,
        trace=args.culture_trace,
        maturity=args.culture_maturity,
        seed=args.culture_seed,
    )
    # Banked one state per frame and played straight through. Every other
    # process here is paced by `even_schedule` because it creeps and then
    # floods; this one carries a beat, and equal steps of the clock are the
    # only schedule that leaves a beat where the model put it.
    states = model.record(args.duration_frames, args.culture_steps)
    print(
        f"  culture: {model.neurons:,} neurons, {len(model.source):,} synapses "
        f"({model.live:,} grown by the end), {model.spikes:,} spikes",
        flush=True,
    )

    # A neuron is one point and a point is one pixel, which is the mistake that
    # sank `aggregation` and `nematic`: at this density the mean spacing is
    # 7.7 px, so cells drawn a pixel wide stay separate specks at any size and
    # come out as grey speckle in the grid thumbnail. Splatting each cell as a
    # small disc of samples lets neighbours fuse into mass where the tissue is
    # active, which is the only reason the additive pipeline has anything to
    # work on.
    rng = np.random.default_rng(args.culture_seed + 1)
    count = args.cell_samples
    angle = rng.random((model.neurons, count)) * (2.0 * math.pi)
    radius = np.sqrt(rng.random((model.neurons, count))) * args.cell_radius
    points = np.empty((model.neurons * count, 2), dtype=np.float64)
    points[:, 0] = (model.positions[:, 0:1] + np.cos(angle) * radius).ravel()
    points[:, 1] = (model.positions[:, 1:2] + np.sin(angle) * radius).ravel()
    owner = np.repeat(np.arange(model.neurons), count)

    # Ranked once, over every spike in the clip rather than frame by frame, so
    # that a frame early on genuinely sits at the low end of the ramp. Ranked at
    # all because the raw quantity is badly skewed -- a long thin tail of cells
    # go over on almost nothing -- and a linear map puts four spikes in five on
    # one stop, which is house rule 2's case for ranking a skewed scalar.
    pool = np.concatenate([state[2] for state in states[::4]])
    pool = np.sort(pool[pool > 0.0])
    print(f"    push at the last spike: {pool[0]:.4f} .. {pool[-1]:.4f} thresholds "
          f"over {len(pool):,} sampled spikes", flush=True)

    def ranked(push: np.ndarray) -> np.ndarray:
        return (np.searchsorted(pool, push).astype(np.float32) / max(len(pool), 1))

    palette = glow.build_palette(spec["palette"])
    caption = build_overlay(width, height, spec, args)
    share = np.float32(1.0 / count)
    reference = 1.0

    def draw(u: float) -> np.ndarray:
        spike, trace, push = states[min(int(u * (len(states) - 1)), len(states) - 1)]
        lit = spike + args.cell_trace * trace
        shade = ranked(push) if spec.get("colour", "push") == "push" else 1.0 - spike
        # `lit` already carries the spike and the slow trace behind it. There is
        # no floor under the cells that have never fired: a flat floor over all
        # 12,000 of them covers three quarters of the frame in dust, which is
        # what the first cut did, and it buried the structure it was meant to
        # sit under.
        weight = (lit * share)[owner]
        colours = glow.sample_palette(palette, shade)[owner]
        colour_sum, density = glow.splat(width, height, points, colours, weight)
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    _, probe = glow.splat(
        width, height, points,
        np.zeros((len(points), 3), dtype=np.float32),
        ((states[-1][0] + args.cell_trace * states[-1][1]) * share)[owner],
    )
    reference = float(np.percentile(probe[probe > 0], 92.0))
    return draw, draw(1.0)


TIMELINES = {
    "hyphae": hyphae_timeline,
    "syncytium": hyphae_timeline,
    "cleavage": cleavage_timeline,
    "sandpile": sandpile_timeline,
    "reentry": reentry_timeline,
    "condensate": condensate_timeline,
    "sector": sector_timeline,
    "culture": culture_timeline,
}


def render_edition(name: str, args: argparse.Namespace) -> Path:
    spec = EDITIONS[name]
    draw, finished = TIMELINES[name](spec, args)

    stem = f"{spec['slug']}_{args.width}x{args.height}_{args.duration:g}s_{args.fps}fps"
    if spec.get("look"):
        stem += f"_{spec['look']}"
    if args.hook and spec.get("hook"):
        # Same suffix the cleavage re-render carries, so the hooked Plex cut and
        # the older DejaVu one sit side by side in the folder without ambiguity.
        stem += "_hook_plex"
    if args.tag:
        # How a 2.0 lands alongside the cut it descends from instead of on top
        # of it. Same mechanism as the biomorph renderer, which is how `gyrus`
        # was written out next to `folding`.
        stem += f"_{args.tag}"
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
    parser.add_argument("--tag", help="suffix appended to the filename, e.g. v2")
    parser.add_argument("--no-text", dest="text", action="store_false",
                        help="render the form with no title, hook or data block — a T4 legibility still")
    parser.add_argument("--hyphae-steps", type=int, default=1400)
    parser.add_argument("--fuse-warm", type=float, default=22.0,
                        help="steps a segment takes to warm from slate to ember once its tip fuses")
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
    parser.add_argument("--neurons", type=int, default=12_000)
    parser.add_argument("--culture-reach", type=float, default=62.0,
                        help="how far a neurite reaches by the end of the clip, in pixels")
    parser.add_argument("--culture-growth", type=float, default=0.35,
                        help="exponent on neurite outgrowth; below 1 puts most of it early")
    parser.add_argument("--culture-weight", type=float, default=0.030, help="one synapse, in thresholds")
    parser.add_argument("--culture-drive", type=float, default=4e-4, help="spontaneous charging per step")
    parser.add_argument("--culture-depression", type=float, default=0.45, help="what a spike leaves behind")
    parser.add_argument("--culture-recovery", type=float, default=0.010, help="how fast that comes back")
    parser.add_argument("--culture-afterglow", type=float, default=8.0, help="half-life of a spike, in steps")
    parser.add_argument("--culture-trace", type=float, default=150.0,
                        help="half-life of the tissue behind it, in steps")
    parser.add_argument("--culture-maturity", type=float, default=0.60,
                        help="how far into the outgrowth the last frame lands")
    parser.add_argument("--culture-steps", type=int, default=5, help="simulation steps per frame")
    parser.add_argument("--culture-seed", type=int, default=7)
    parser.add_argument("--cell-samples", type=int, default=48, help="splat samples per neuron")
    parser.add_argument("--cell-radius", type=float, default=6.5, help="radius of one neuron, in pixels")
    # Zero, and pinned here rather than left on the command line: the cut that
    # was judged was rendered with the trace off. At 0.20 and above the slow
    # layer lights every cell that has fired in the last second, which by the
    # end of the clip is all of them, and the frame fills with an even carpet
    # that buries the structure the layer was meant to sit under. `venation`
    # shipped a look it did not record and re-rendering changed the cut; this
    # does not repeat that.
    parser.add_argument("--cell-trace", type=float, default=0.0,
                        help="how bright tissue stays after the spike has gone")
    parser.add_argument("--sector-size", type=int, default=480)
    parser.add_argument("--sector-factor", type=int, default=2)
    parser.add_argument("--sector-steps", type=int, default=900, help="cap; the colony stops at the dish wall")
    parser.add_argument("--founders", type=int, default=48, help="labelled strains in the inoculum")
    parser.add_argument("--mutation", type=float, default=0.0022, help="chance a division founds a lineage")
    parser.add_argument("--beneficial", type=float, default=0.16, help="fraction of those that divide faster")
    parser.add_argument("--advantage", type=float, default=0.10, help="how much faster")
    # Area, not radius, and this was decided by measurement rather than taste.
    # Paced by radius the front advances at a steady speed and the change
    # profile comes out comet-shaped -- 9.5% of the growth in the first quarter
    # and 40.4% in the last -- but the colony spends the opening two seconds as
    # a dot, and a dot advancing one cell of radius per frame changes almost no
    # pixels. That cut measured 22.6% frozen frames with 52 of the 54 inside the
    # first two seconds, which is the worst place a freeze can land. Equal area
    # per frame is equal newly-lit pixels per frame, which is the thing the
    # frozen-frame test actually measures: 5.4%, and 1.3% once the cover hold is
    # discounted. The intermediate, area^0.75, splits the difference at 7.9%.
    parser.add_argument("--pacing", type=float, default=1.0, help="0.5 paces by radius, 1.0 by area")
    parser.add_argument("--inoculum", type=float, default=22.0, help="radius of the drop, in lattice cells")
    parser.add_argument("--hue-step", type=float, default=0.26, help="how far a mutation moves along the ramp")
    parser.add_argument("--tip-boost-front", type=float, default=1.35)
    parser.add_argument("--tip-decay-front", type=float, default=26.0)
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
