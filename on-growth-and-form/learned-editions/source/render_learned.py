#!/usr/bin/env python3
"""A rule nobody wrote, filmed growing an animal and then rebuilding it.

Everything else in this project runs a rule somebody chose. Gray-Scott is two
diffusion constants; Lenia is a kernel and a growth curve; the sandpile is one
sentence about integers. This edition films the other kind: a cellular automaton
whose update is a small network, fitted by gradient descent until a grid of
identical cells reliably assembles one particular animal out of one lit cell
(Mordvintsev et al., *Growing Neural Cellular Automata*, Distill 2020).

The training asks for exactly one thing -- **after some number of steps, look
like this picture** -- and the piece is what happens when you then do something
to the organism that the training never did.

**The clip is the experiment, in order.** It opens on the animal healed, cuts to
a single cell, grows the whole body, holds; then the head is amputated, and the
fragment builds a new one, eyes included, and arrives back at exactly the frame
the clip opened on. The loop closes on the healed organism, which is also the
grid thumbnail.

**Colour is when a cell was built**, which is `hyphae`'s scheme and is the only
one that survives the cut. Anything measuring current activity -- the phosphor
`reentry` uses, say -- fades as the organism settles, and the last frame of this
piece is a settled organism: the new head would cool to the same violet as the
body it is attached to and the picture would lose its whole subject. Age does
not fade. The body stays at the dark end of the ramp because it was built first,
the head runs bright because it was built second, and the scar is permanent.

**How far the process gets and how long the clip runs are separate knobs**, as
in `soliton`, and here that is not a luxury. This automaton *converges*: it was
fitted to stop, and it does. Growth is finished at about 220 steps and the
regrowth at about 220 more, so a clip that keeps stepping past that is a still
photograph of a finished animal -- measured on the first cut, at two steps a
frame, 78% of the transitions were frozen and the longest still run was 142
frames, four and a half seconds of nothing at the end.

So the run is 440 steps and the frame count only decides how fast it is played.
There is still no scheduler: the automaton does the same work per step from
beginning to end, so equal steps of the clock are equal steps of the process.
What was wrong was not the pacing but the length -- which is also why the clip
is 8 s and not 10. A longer cut does not show more process, it shows the same
440 steps more slowly, and every extra frame lands on the settled animal.

**The cut is placed where growth finishes**, not at a round fraction of the
clip, which is the same thing said from the other side.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
from typing import Callable

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageDraw, ImageFont

import glow
import neuralca


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "instagram" / "phone-9x16"
DEFAULT_WEIGHTS = PROJECT_DIR / "weights" / "regrowth-planarian.npz"

# Violet, because the other editions have taken amber, cyan, acid, phosphor
# green, rose and magenta, and because colour here is how recently a cell was
# still working: the dark end has to be a colour a *finished* body can be drawn
# in rather than a near-black, or the payoff frame is a glowing head attached to
# nothing. So the ramp starts at a definite indigo, spends its middle in violet,
# and only reaches white in the cells that are changing right now.
NEURITE = [(26, 8, 58), (62, 16, 122), (118, 34, 210), (186, 88, 255), (234, 164, 255), (255, 248, 252)]

EDITIONS: dict[str, dict] = {
    "regrowth": {
        "title": "Regrowth",
        "slug": "regrowth_neural-ca_learned",
        "palette": NEURITE,
        "exposure": 1.12,
        "boost": 1.18,
        "caption": (
            "neural cellular automaton (Mordvintsev 2020)",
            "sense · update · fire at random",
            "8,320 fitted numbers, one rule, every cell",
        ),
        # Precise about what the fitting did and did not supply. Damaged states
        # go in -- three of every eight -- but the only thing ever compared
        # against anything is the finished picture: no intermediate target, no
        # wound response, nothing anywhere that describes repair.
        "hook": ("It was shown the wound, never the repair.",),
    },
}


# --------------------------------------------------------------------------
# Encoding
# --------------------------------------------------------------------------


def find_encoder() -> tuple[str, list[str]]:
    """Pick an ffmpeg that can actually encode H.264 (conda builds cannot)."""
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
# Shared pieces — the house layout, identical to the substrate and alife sets
# --------------------------------------------------------------------------


def hook_box(spec: dict, args) -> tuple[int, int] | None:
    """Where the hook's ink starts and ends, or None if there is no hook.

    Wanted twice: once to draw it, and once to work out how much frame is left
    for the organism between the title and it.
    """
    lines = spec.get("hook") if args.hook else None
    if not lines:
        return None
    ink_top = glow.caption_ink_top(args.height, spec["caption"], args.caption_size, args.caption_bottom)
    font = ImageFont.truetype(str(glow.MONO_FONT), args.hook_size)
    draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    box = draw.multiline_textbbox(
        (0, 0), "\n".join(lines), font=font, spacing=max(6, args.hook_size // 3)
    )
    origin = ink_top - args.hook_gap - box[3]
    return origin + box[1], ink_top


def build_overlay(width: int, height: int, spec: dict, args) -> Image.Image:
    """Title, hook and data block: Plex, 240 px down, 190 px up, hook centred."""
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


def tone(colour_sum: np.ndarray, density: np.ndarray, reference: float, spec: dict, args) -> np.ndarray:
    linear = glow.flame_map(colour_sum, density, reference, boost=spec["boost"])
    linear = glow.bloom(linear, threshold=args.bloom_threshold, strength=args.bloom_strength)
    return glow.to_bytes(glow.tone_map(linear, exposure=spec["exposure"]))


def place(field: np.ndarray, height: int, width: int, top: int, left: int) -> np.ndarray:
    canvas = np.zeros((height, width), dtype=np.float32)
    canvas[top : top + field.shape[0], left : left + field.shape[1]] = field
    return canvas


# --------------------------------------------------------------------------
# The timeline
# --------------------------------------------------------------------------


def regrowth_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    height, width = args.height, args.width
    device = neuralca.device_for(args.device)
    rule = neuralca.Rule.load(args.weights, device)
    target = neuralca.planarian(args.grid_width, args.grid_height)
    grid_height, grid_width = target.shape

    # Three animals, not one, and this is the decision the piece turns on.
    #
    # A single organism leaves 92% of the frame black and the body itself is a
    # flat paddle -- the alpha this rule settles on is very nearly binary, so
    # there is no density gradient anywhere, and the whole house pipeline
    # (additive splatting, log-density, bloom) has nothing to work with. It is
    # also the wrong picture of what is being claimed: one specimen healing is an
    # anecdote.
    #
    # Three run in parallel in their own grids, seeded identically and cut in the
    # same frame, and they come out different -- because cells fire with
    # probability 1/2 and nothing else. That divergence is the only thing in the
    # piece that shows the rule is stochastic rather than a recording, and it
    # costs nothing: they batch.
    #
    # Each keeps its *own* 124x168 grid rather than sharing a wider one. The rule
    # was fitted with that boundary and against zero padding, and three animals
    # in one grid would be three animals in a world none of them was fitted in.
    box = hook_box(spec, args)
    ceiling = args.title_top + args.title_clear
    floor = (box[0] if box else height - args.caption_bottom) - args.form_clear

    # Only the middle of each grid is drawn. Nothing is being cropped away: the
    # organism never reaches beyond column 36 or 88 of 124, so the discarded
    # margin is empty by measurement, and dropping it is what buys the scale that
    # makes the eyespots survive a phone.
    window = min(args.columns, grid_width)
    first_column = (grid_width - window) // 2
    usable = width - 2 * args.side_margin - (args.specimens - 1) * args.gap
    scale = min(usable / (args.specimens * window), (floor - ceiling) / grid_height)
    tile_width, tile_height = int(round(window * scale)), int(round(grid_height * scale))
    span = args.specimens * tile_width + (args.specimens - 1) * args.gap
    top = int(round((ceiling + floor) / 2 - tile_height / 2))
    lefts = [(width - span) // 2 + index * (tile_width + args.gap) for index in range(args.specimens)]
    if top < ceiling or top + tile_height > floor:
        raise ValueError(
            f"the forms ({tile_height} px) do not fit between {ceiling} and {floor}"
        )

    # How far the process gets and how long the clip runs are separate knobs, as
    # in `soliton`. Here that separation is not a luxury, it is the whole
    # difference between a clip and a slideshow: this automaton *converges*.
    # Growth is done at about 220 steps and the regrowth at about 220 more, and
    # a clip that runs 578 spends its last five seconds on a still photograph of
    # a finished animal. Measured on the first cut at two steps a frame: 78% of
    # transitions frozen, the longest run 142 frames.
    #
    # So the run length is set to what the process actually needs, and the frame
    # count only decides how fast it is played -- 440 steps over 229 frames, a
    # shade under two per frame, with the cut placed where growth finishes
    # rather than at a round fraction of the clip.
    frames = args.duration_frames - args.hold
    total_steps = args.grow_steps + args.regrow_steps
    rate = total_steps / frames
    cut_frame = int(round(frames * args.grow_steps / total_steps))
    cut_row = int(
        round(neuralca.body_top(target) + args.cut_at * neuralca.body_length(target))
    )

    seed_row, seed_column = neuralca.seed_cell(target)
    torch.manual_seed(args.model_seed)
    state = neuralca.seeded(
        args.specimens, rule.channels, grid_height, grid_width, seed_row, seed_column, device
    )
    # When each cell was last built: the frame its alpha first passed the same
    # 0.1 the rule itself uses to decide a cell is alive. The only thing that
    # resets it is the amputation, because the amputation is the only thing that
    # actually removes tissue. Letting a cell be forgotten whenever its alpha
    # dips instead -- which was the first version -- hands the newest colour in
    # the ramp to every cell that flickers across the threshold, and paints a
    # rim of white speckle around the organism that is a fact about the
    # threshold rather than about the animal.
    birth = torch.full((args.specimens, grid_height, grid_width), -1.0, device=device)

    alphas: list[np.ndarray] = []
    ages: list[np.ndarray] = []
    advanced = 0
    with torch.no_grad():
        for frame in range(frames):
            if frame == cut_frame:
                # All three in the same frame. Staggering the cuts would read as
                # three separate events and lose the only thing three buys, which
                # is that the same injury at the same instant comes out different.
                state = neuralca.amputate(state, cut_row, keep="below")
                birth[:, :cut_row] = -1.0
                advanced = args.grow_steps
            reach = args.grow_steps if frame < cut_frame else total_steps
            while advanced < min(int(round(rate * (frame + 1))), reach):
                state = rule(state)
                advanced += 1
            alpha = state[:, 0].clamp(0.0, 1.0)
            birth = torch.where((birth < 0) & (alpha > args.alive), float(frame), birth)
            alphas.append(alpha.cpu().numpy())
            ages.append(birth.clamp(min=0.0).cpu().numpy())

    # Reach is measured over every specimen at once: the clearance has to hold
    # for the worst of the three, not for the average.
    body = np.stack(alphas).reshape(-1, grid_height, grid_width) > args.alive
    rows = np.any(body, axis=2)
    columns = np.any(body, axis=1)
    # flatnonzero, not argmax: argmax on an all-false row returns 0, so a grid
    # edge the organism never touched reports as touched, and the clearance the
    # whole "nothing is confined" argument rests on comes out of the check
    # looking worse than it is.
    lit_rows = np.flatnonzero(rows.any(axis=0))
    lit_columns = np.flatnonzero(columns.any(axis=0))
    if not len(lit_rows):
        raise RuntimeError("no cell was ever alive: the rule did not grow at all")
    reach_top, reach_bottom = int(lit_rows[0]), int(lit_rows[-1])
    reach_left, reach_right = int(lit_columns[0]), int(lit_columns[-1])
    worst_frame = int(np.argmax(rows[:, reach_top] | rows[:, reach_bottom]))
    # Reaching a wall and being visible against it are different questions. A
    # cell whose alpha is a hair over the aliveness threshold draws nothing once
    # the floor has been taken off it, so what matters is the brightest the very
    # edge of the grid ever gets, not whether anything was ever counted there.
    edge_peak = float(max(a[:, 0].max() for a in alphas) - args.floor)
    errors = ((alphas[-1] - target[None]) ** 2).mean(axis=(1, 2))
    print(
        f"  regrowth: {args.specimens} specimens, "
        f"{total_steps} steps over {frames} frames ({rate:.2f} per frame), "
        f"cut at frame {cut_frame} on row {cut_row} of {grid_height}, "
        f"final error {' '.join(f'{e:.5f}' for e in errors)}",
        flush=True,
    )
    # The organism has to keep clear of the grid's own edge as well as of the
    # typography: it is not confined by anything, so a rule that overgrew would
    # be cropped by the wall and the frame would show a straight line the rule
    # never drew.
    print(
        f"  reach: rows {reach_top}-{reach_bottom} of {grid_height} "
        f"(furthest at frame {worst_frame}, "
        f"peak alpha on the edge rows {edge_peak:.3f}), "
        f"columns {reach_left}-{reach_right} of {grid_width} "
        f"(window is {first_column}-{first_column + window}) "
        f"-> frame rows {top + int(reach_top * scale)}-{top + int((reach_bottom + 1) * scale)}, "
        f"clear of the title by {top + int(reach_top * scale) - ceiling} px "
        f"and of the hook by {floor + args.form_clear - (top + int((reach_bottom + 1) * scale))} px",
        flush=True,
    )
    if reach_left < first_column or reach_right >= first_column + window:
        raise ValueError(
            f"an organism reached columns {reach_left}-{reach_right}, outside the drawn "
            f"window {first_column}-{first_column + window}: raise --columns"
        )

    # One fixed scale for the whole clip -- the clip's own length -- so that the
    # colour of a cell means the same thing in every frame. Ranking per frame,
    # which is the usual answer to a skewed scalar, would be exactly wrong here:
    # it would rescale every frame to use the whole ramp and destroy the one
    # thing the colour has to say, which is that the head is younger than the
    # body it is attached to.
    shades = [age / max(frames - 1, 1) for age in ages]
    # Below the alive threshold there is a fuzz of very low alpha around the
    # organism that the log-density map lifts into a visible violet mist. The
    # rule does not count those cells as alive; neither does the picture.
    alphas = [np.clip((a - args.floor) / (1.0 - args.floor), 0.0, 1.0) for a in alphas]
    print(
        f"  age: body born by frame {int(np.percentile(ages[-1][alphas[-1] > 0], 50)):d}, "
        f"newest tissue at frame {int(ages[-1].max()):d} of {frames}",
        flush=True,
    )
    # How far the three actually diverge, which is the piece's whole reason for
    # showing three. Nothing differs between them except which cells fired.
    spread = float(np.abs(alphas[-1][:, None] - alphas[-1][None, :]).max())
    print(
        f"  divergence: worst pairwise difference between the three finished "
        f"animals {spread:.2f}, final errors spread {errors.max() - errors.min():.5f}",
        flush=True,
    )

    palette = glow.build_palette(spec["palette"])
    caption = build_overlay(width, height, spec, args)
    reference = 1.0

    def fields_at(index: int) -> tuple[np.ndarray, np.ndarray]:
        # Bilinear, not block-repeat. At this magnification a nearest-neighbour
        # upsample lays a visible grid over the whole organism, and the bloom then
        # gives every one of those squares its own halo.
        cut = slice(first_column, first_column + window)
        pair = torch.tensor(
            np.stack([alphas[index][:, :, cut], shades[index][:, :, cut]], axis=1),
            dtype=torch.float32,
        )
        grown = F.interpolate(
            pair, size=(tile_height, tile_width), mode="bilinear", align_corners=False
        ).numpy()
        density = np.zeros((height, width), dtype=np.float32)
        shade = np.zeros((height, width), dtype=np.float32)
        for specimen, left in enumerate(lefts):
            density[top : top + tile_height, left : left + tile_width] = grown[specimen, 0]
            shade[top : top + tile_height, left : left + tile_width] = grown[specimen, 1]
        return density, shade

    def draw(u: float) -> np.ndarray:
        density, shade = fields_at(min(int(u * (len(alphas) - 1)), len(alphas) - 1))
        colour_sum = glow.sample_palette(palette, shade) * density[:, :, None]
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    final_density, _ = fields_at(len(alphas) - 1)
    if not (final_density > 0).any():
        # A rule that has died leaves an empty frame and an empty percentile,
        # which otherwise fails several lines later with an index error about
        # axis 0 and nothing about the automaton.
        raise RuntimeError(
            "nothing is alive in the last frame: the rule did not regrow after the cut"
        )
    reference = float(np.percentile(final_density[final_density > 0], 92.0))
    return draw, draw(1.0)


TIMELINES = {"regrowth": regrowth_timeline}


def render_edition(name: str, args: argparse.Namespace) -> Path:
    spec = EDITIONS[name]
    draw, finished = TIMELINES[name](spec, args)

    stem = f"{spec['slug']}_{args.width}x{args.height}_{args.duration:g}s_{args.fps}fps"
    if args.hook and spec.get("hook"):
        stem += "_hook_plex"
    if args.tag:
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
            # Ends on u = 1, the frame the clip opened on: no seam in the loop.
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
    parser.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    parser.add_argument("--device", default=None)
    parser.add_argument("--preview", action="store_true", help="Save the cover still and stop.")
    parser.add_argument("--tag", help="suffix for a variant cut, e.g. sharp")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    # Eight, and the ten-second cut was tried first and is worse. The run is a
    # fixed 440 steps either way, so a longer clip does not show more process --
    # it shows the same process more slowly, and this one converges, so the extra
    # two seconds land entirely on the settled animal at the end. Measured inside
    # the organism: 18% of frames still at 8 s against 28% at 10 s, longest run
    # 21 frames against 49.
    parser.add_argument("--duration", type=float, default=8)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--hold", type=int, default=11, help="frames held on the finished form")
    parser.add_argument("--margin", type=int, default=64)
    parser.add_argument("--title-top", type=int, default=240)
    parser.add_argument("--caption-bottom", type=int, default=190)
    parser.add_argument("--caption-size", type=int, default=27)
    parser.add_argument("--scrim", type=float, default=0.95)
    parser.add_argument("--no-hook", dest="hook", action="store_false")
    parser.add_argument("--hook-size", type=int, default=34)
    parser.add_argument("--hook-gap", type=int, default=82)
    parser.add_argument("--bloom-threshold", type=float, default=0.30)
    parser.add_argument("--bloom-strength", type=float, default=0.60)
    parser.add_argument("--title-clear", type=int, default=30, help="title ink below --title-top")
    parser.add_argument("--form-clear", type=int, default=40, help="gap kept above the hook's ink")
    parser.add_argument("--grid-width", type=int, default=124)
    parser.add_argument("--grid-height", type=int, default=168)
    # Three, because one leaves 92% of the frame black and because one specimen
    # healing is an anecdote. They batch, so the cost is nothing.
    parser.add_argument("--specimens", type=int, default=3)
    # Cells of each grid actually drawn, centred. The organism never reaches past
    # column 36 or 88 of 124, so this discards measured-empty margin and buys the
    # magnification the eyespots need. The renderer refuses to run if any
    # specimen ever reaches outside it.
    parser.add_argument("--columns", type=int, default=60)
    parser.add_argument("--gap", type=int, default=24, help="black between specimens")
    parser.add_argument("--side-margin", type=int, default=40)
    parser.add_argument("--model-seed", type=int, default=20260827)
    # Measured, not chosen: the error against the target stops improving at
    # about 220 steps in each phase, and everything past that is a still.
    parser.add_argument("--grow-steps", type=int, default=220, help="steps from the seed to the cut")
    parser.add_argument("--regrow-steps", type=int, default=220, help="steps from the cut to the end")
    parser.add_argument(
        "--cut-at", type=float, default=0.22,
        help="fraction of the body length removed, measured from the head",
    )
    parser.add_argument("--alive", type=float, default=0.1, help="the rule's own aliveness threshold")
    # Higher than the rule's own 0.1, and the reason is the eyespots. The fitted
    # rule holds them at about 0.2 rather than at 0 -- close enough for the loss,
    # not close enough to read as holes once the bloom has been over them. At
    # 0.28 the two eyes are the darkest thing in the head, which is what the
    # piece's sharpest evidence needs in order to survive H.264 and a phone.
    parser.add_argument("--floor", type=float, default=0.28, help="alpha subtracted before drawing")
    parser.add_argument("--exposure", type=float)
    parser.add_argument("--boost", type=float)
    args = parser.parse_args()
    args.duration_frames = round(args.duration * args.fps)
    return args


if __name__ == "__main__":
    options = parse_args()
    for edition_name in options.edition or list(EDITIONS):
        for key in ("exposure", "boost"):
            if getattr(options, key) is not None:
                EDITIONS[edition_name][key] = getattr(options, key)
        print(f"Rendering {edition_name} ...", flush=True)
        print(f"Saved {render_edition(edition_name, options)}", flush=True)
