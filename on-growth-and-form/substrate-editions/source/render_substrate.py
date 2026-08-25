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
import subprocess
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
    linear = glow.flame_map(colour_sum, density, reference, boost=spec["boost"])
    linear = glow.bloom(linear, threshold=args.bloom_threshold, strength=args.bloom_strength)
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


TIMELINES = {
    "hyphae": hyphae_timeline,
    "cleavage": cleavage_timeline,
    "sandpile": sandpile_timeline,
    "reentry": reentry_timeline,
}


def render_edition(name: str, args: argparse.Namespace) -> Path:
    spec = EDITIONS[name]
    draw, finished = TIMELINES[name](spec, args)

    stem = f"{spec['slug']}_{args.width}x{args.height}_{args.duration:g}s_{args.fps}fps"
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
