#!/usr/bin/env python3
"""The third biomorph: a shoal that appears to agree about something.

The cosine creature was one wave pretending to be a body. The medusa was the
same wave told radially, fourteen delays deep, pretending to swim. This is the
same trick told *socially*, and it is the one that should be uncomfortable:

    body    the animal's own wave, sin(5ξ − 8t + φ), head → tail
    shoal   φ = 3θ₀                                  one delay per fish
    mill    θ(t) = θ₀ + t                            the whole ball turns once

A hundred and twenty fish on the shell of a spindle, each swimming, each a real
animal rather than a streak — `fish.py` holds the anatomy and this file only
places it. Because every fish's phase is a fixed function of *where it started*
— three turns of phase per turn of the ball — the crests line up across
neighbours into rotating bands, and the population reads as one thing doing one
thing. A bait ball. A murmuration. A decision.

There is no interaction term. Fish i is a pure function of i and t and nothing
else; the array is never even indexed by another fish. Nothing in here can
perceive anything, so nothing is following, fleeing, aligning or agreeing — and
the picture is indistinguishable from a population that is. That is the whole
piece: `affinity`, over in the alife edition, is a real interaction and says so;
this one is a fake, says so, and you cannot tell by looking.

Magenta marks the crest of the wave, and it marks it *on the lateral line* —
the organ a real fish senses its neighbours with, the channel a real shoal
synchronises through. Drawn here on animals that sense nothing at all. Same
rule as the two pieces before it: the accent is not decoration, it is the
position of the only moving thing in the equation. Red, then green, then
magenta: the three biomorphs are the three corners.

The ball is hollow and projected orthographically with a tilt, so the near wall
sweeps one way and the far wall sweeps back the other, and depth falls out of
per-point alpha rather than out of a camera move. Nothing turns except the
animals.

Every time term is an integer multiple of t and t runs a full 2π over the clip
— eight beats, one revolution — so the last frame meets the first and the loop
is seamless by construction.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/on-growth-and-form-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/on-growth-and-form-cache")

import matplotlib

matplotlib.use("Agg")

import numpy as np
from PIL import Image

import fish as fishmod
import glow


DEFAULT_OUTPUT = (
    Path(__file__).parents[1]
    / "instagram"
    / "phone-9x16"
    / "growth-form_quorum-shoal_1080x1920_8s_30fps_hook_plex.mp4"
)

TITLE = "Quorum"
CAPTION = (
    "body      lateral ∝ sin(5ξ − 8t + φ)",
    "shoal     φ = 3θ · nothing couples one body to another",
    "magenta   the crest, brightest on the lateral line",
)
HOOK = ("They move as one. None of them knows that.",)

ACCENT = (1.00, 0.169, 0.839)   # #ff2bd6 — the third corner after red and green

MARGIN = 64          # left inset shared by the title and the data block
CAPTION_SIZE = 27    # house size for the data block
HOOK_GAP = 82        # ink to ink, hook down to the data block — the house spacing

FONT_FAMILIES = {
    "dejavu": (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"),
    ),
    "plex": (
        Path(__file__).parents[2] / "fonts" / "IBMPlexMono-Regular.ttf",
        Path(__file__).parents[2] / "fonts" / "IBMPlexMono-Bold.ttf",
    ),
}


class Shoal:
    """Where each fish sits on the ball, and how it is bent onto its latitude.

    Model space is 1 unit = 1 pixel, so every clearance in this file can be read
    straight off the frame without converting anything. The anatomy lives in
    `fish.py`; nothing here knows what a fin is.
    """

    N_FISH = 155
    FISH_LEN = 172.0
    DENSITY = 0.20     # points per fish, as a fraction of the module's full draw
    VARY = 0.7         # spread of proportions between individuals

    R_MAX = 405.0      # widest radius of the ball
    HALF = 468.0       # half its height
    CENTRE_ROW = 882   # where model y = 0 lands. Not the middle of the frame:
                       # the ball's own extremes are asymmetric, and the title
                       # has less room above it than the hook has below.
    TILT = 0.42        # how much depth leaks into y — the far side, without turning
    U_MIN = 0.10       # the ball is open at both ends, so you look down into it
    U_MAX = 0.95       # rather than at a closed blob with two ragged poles

    OMEGA = 8          # beats per loop         (integer → seamless)
    SPIN = 1           # revolutions of the mill (integer → seamless)
    ARMS = 3.0         # turns of phase per turn of the ball — the apparent bands
    CHURN = 24.0       # how far a fish slides up or down the ball over the loop

    def __init__(self) -> None:
        rng = np.random.default_rng(7)

        # Fish on the shell of a spindle. u runs 0 at the crown to 1 at the base;
        # accepted with probability ∝ the radius there, so the ball is evenly
        # covered rather than crowded at its two narrow ends.
        u: list[float] = []
        while len(u) < self.N_FISH:
            trial = self.U_MIN + (self.U_MAX - self.U_MIN) * rng.random(self.N_FISH)
            keep = rng.random(self.N_FISH) < self.profile(trial) / self.R_MAX
            u.extend(trial[keep].tolist())
        self.u = np.array(u[: self.N_FISH])

        self.theta0 = rng.random(self.N_FISH) * 2 * np.pi
        self.r0 = self.profile(self.u) * (1.0 + 0.05 * rng.normal(0, 1, self.N_FISH))

        # The only thing that differs between two fish. A little jitter, or the
        # bands come out machine-ruled and the ball stops reading as animals.
        self.phi = self.ARMS * self.theta0 + 0.06 * rng.normal(0, 1, self.N_FISH)

        # Heading. Without it every fish lies along its latitude and the ball
        # reads as contour lines on a globe; the sin(πu) damping keeps fish at
        # the two narrow ends lying flat, where there is no room to climb.
        self.pitch = 0.15 * rng.normal(0, 1, self.N_FISH) * np.sin(np.pi * self.u)
        self.psi = rng.random(self.N_FISH) * 2 * np.pi

        self.school = [
            fishmod.Fish(
                fishmod.SARDINE,
                length=self.FISH_LEN,
                density=self.DENSITY,
                rng=np.random.default_rng(1000 + i),
                vary=self.VARY,
            )
            for i in range(self.N_FISH)
        ]
        # Every individual carries the same strokes, so one fish's part and
        # weight arrays describe them all and the frame loop can preallocate.
        self.per = len(self.school[0])
        self.weight = np.tile(self.school[0].weight, self.N_FISH)

        # The arc a body is measured against. The cap stops a fish near a narrow
        # end from wrapping the whole way round the ball.
        self.r_arc = np.maximum(self.r0, 150.0)

    @classmethod
    def profile(cls, u: np.ndarray) -> np.ndarray:
        """Radius of the ball at height fraction u — widest a little above centre."""
        return cls.R_MAX * (0.10 + 0.90 * np.sin(np.pi * u ** 0.88) ** 0.75)

    def frame(self, t: float):
        """Every point of every fish at loop phase t ∈ [0, 2π).

        Returns x, y, the crest mask, and how near the viewer each point is.
        """
        n, per = self.N_FISH, self.per
        x = np.empty(n * per)
        y = np.empty(n * per)
        near = np.empty(n * per)      # where on the ball, front to back
        face = np.empty(n * per)      # which flank of its own body, near or far
        glow = np.empty(n * per)

        # One slow contraction travelling down the ball, so the crowd breathes.
        breathe = 1.0 + 0.035 * np.sin(2 * t - 3.0 * self.u)
        base_y = (
            self.HALF * (1.0 - 2.0 * self.u) * breathe
            + self.CHURN * np.sin(t + self.psi)
        )
        head = self.theta0 + self.SPIN * t
        radius = self.r0 * breathe

        for i, animal in enumerate(self.school):
            # The animal in its own frame: snout at the origin, body trailing.
            pose = animal.pose(self.OMEGA * t, phase=self.phi[i])
            c, s = np.cos(self.pitch[i]), np.sin(self.pitch[i])
            rx, ry = c * pose.x - s * pose.y, s * pose.x + c * pose.y

            # Bent onto its latitude: length becomes arc, depth stays vertical,
            # and the animal's own width becomes radius — a fish is thicker than
            # the shell it swims on, so it pokes in and out of it.
            theta = head[i] - rx / self.r_arc[i]
            sin_theta = np.sin(theta)
            r = radius[i] + pose.z
            depth = r * sin_theta

            sl = slice(i * per, (i + 1) * per)
            x[sl] = r * np.cos(theta)
            y[sl] = base_y[i] + ry + self.TILT * depth
            near[sl] = 0.5 * (1.0 + sin_theta)
            # A fish's own thickness is ±20 px against the ball's ±405, so its
            # near and far flanks have to be shaded on their own terms or the
            # animals come out flat inside a round crowd.
            face[sl] = 0.5 * (1.0 + pose.nz * sin_theta)
            glow[sl] = pose.glow

        return x, y, glow, near, face


def draw_hook(overlay: Image.Image, args: argparse.Namespace) -> None:
    """The hook, set in the strip between the ball and the data block.

    Plex, not the data block's DejaVu: there is no Greek in it, so house rule
    5's default applies. Centred on the frame, unlike the left-column title and
    data block, so it reads as a caption over the animal rather than a third
    line in that column.

    Its position is measured from where CAPTION's ink lands, not from the lines
    actually being drawn, so the hook holds still while the title card fades.
    """
    from PIL import ImageDraw, ImageFont

    draw = ImageDraw.Draw(overlay)
    caption_font = ImageFont.truetype(str(args.equation_face), CAPTION_SIZE)
    caption_box = draw.multiline_textbbox(
        (0, 0), "\n".join(CAPTION), font=caption_font, spacing=max(4, CAPTION_SIZE // 3)
    )
    caption_ink_top = overlay.height - args.caption_bottom - caption_box[3] - 4 + caption_box[1]

    font = ImageFont.truetype(str(glow.MONO_FONT), args.hook_size)
    text = "\n".join(HOOK)
    spacing = max(6, args.hook_size // 3)
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align="center")
    draw.multiline_text(
        (overlay.width / 2 - (box[0] + box[2]) / 2, caption_ink_top - HOOK_GAP - box[3]),
        text,
        font=font,
        fill=(255, 255, 255, 244),
        spacing=spacing,
        align="center",
        stroke_width=4,
        stroke_fill=(0, 0, 0, 165),
    )


def build_overlay(
    width: int, height: int, args: argparse.Namespace, equation: tuple[str, ...]
) -> Image.Image:
    """Title, hook and — once the card has cleared — the data block."""
    overlay = glow.make_caption(
        width, height, TITLE, equation,
        equation_size=CAPTION_SIZE, margin=MARGIN, equation_face=args.equation_face,
        top_margin=args.title_top, bottom_margin=args.caption_bottom, scrim=args.scrim,
    )
    draw_hook(overlay, args)
    return overlay


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
            return ffmpeg, ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high"]
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


def build_figure(width: int, height: int, dpi: int):
    """Three scatter layers, drawn back to front, in model units of one pixel.

    The limits put model y = 0 on `Shoal.CENTRE_ROW`, at exactly one model unit
    per pixel, so every clearance can be read straight off the frame.
    """
    import matplotlib.pyplot as plt

    figure = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi)
    figure.patch.set_facecolor("black")
    axes = figure.add_axes((0, 0, 1, 1), facecolor="black")

    axes.set_xlim(-width / 2, width / 2)
    axes.set_ylim(Shoal.CENTRE_ROW - height, Shoal.CENTRE_ROW)
    axes.set_aspect("equal", adjustable="box")
    axes.axis("off")

    scale = width / 960
    layers = {}
    for name, size in (("body", 2.2), ("halo", 34.0)):
        collection = axes.scatter([], [], s=size * scale**2, linewidths=0, edgecolors="none")
        # Per-point alpha carries the depth, so the scalar alpha has to be off
        # or matplotlib multiplies the whole layer down by it instead.
        collection.set_alpha(None)
        layers[name] = (collection, size * scale**2)
    return figure, axes, layers, plt


def set_layer(layers, name, x, y, near, colour, low, span, size_low, size_span,
              weight=1.0) -> None:
    """Offsets, per-point alpha and per-point size for one depth-faded layer.

    `weight` is the stroke's own emphasis, straight out of `fish.py`: an outline
    carries more than the fin rays it encloses, and a thread fades along itself.
    """
    collection, base = layers[name]
    collection.set_offsets(np.c_[x, y])
    rgba = np.empty((x.size, 4), dtype=np.float32)
    rgba[:, 0:3] = colour
    rgba[:, 3] = np.clip((low + span * near) * weight, 0.0, 1.0)
    collection.set_facecolors(rgba)
    collection.set_sizes(base * (size_low + size_span * near) * weight)


def blend(layers, name, x, y, near, glow, weight) -> None:
    """The body layer: white where the wave is not, magenta where it is.

    The accent rides a continuous band rather than a threshold, so the colour is
    a mix rather than a separate layer — `glow` is how far towards magenta a
    point has been carried, and it brightens as well as tints.
    """
    collection, base = layers[name]
    collection.set_offsets(np.c_[x, y])
    lit = np.clip(glow, 0.0, 1.0)
    rgba = np.empty((x.size, 4), dtype=np.float32)
    rgba[:, 0:3] = (1.0 - lit)[:, None] + lit[:, None] * np.asarray(ACCENT, dtype=np.float32)
    rgba[:, 3] = np.clip(weight * (0.045 + 1.05 * near) * (1.0 + 0.85 * lit), 0.0, 1.0)
    collection.set_facecolors(rgba)
    collection.set_sizes(base * (0.34 + 1.25 * near) * weight * (1.0 + 0.35 * lit))


def render(args: argparse.Namespace) -> Path:
    frames = round(args.duration * args.fps)
    shoal = Shoal()
    figure, axes, layers, plt = build_figure(args.width, args.height, args.dpi)
    caption = build_overlay(args.width, args.height, args, CAPTION)
    card = build_overlay(args.width, args.height, args, ()) if args.title_card > 0 else None

    def points_at(index: int) -> np.ndarray:
        t = (index / frames + args.phase) * 2 * np.pi
        x, y, glow, near, face = shoal.frame(t)
        w = shoal.weight * (0.30 + 0.72 * face)
        blend(layers, "body", x, y, near, glow, w)
        lit = glow > 0.62
        set_layer(layers, "halo", x[lit], y[lit], near[lit],
                  ACCENT, 0.004, 0.050, 0.45, 1.00, glow[lit])
        figure.canvas.draw()
        # Straight off the Agg canvas rather than through a temporary PNG, so
        # the caption can be composited before anything is encoded.
        return np.ascontiguousarray(np.asarray(figure.canvas.buffer_rgba())[:, :, :3])

    def draw(index: int, alpha: float = 1.0) -> np.ndarray:
        # The ball keeps turning under the card: one continuous cycle, no
        # finished form to hold on, same as the two before it.
        buffer = points_at(index)
        if card is None:
            return glow.compose(buffer, caption)
        level = args.title_dim + (1.0 - args.title_dim) * alpha
        if level < 1.0:
            buffer = (buffer * level).astype(np.uint8)
        if alpha <= 0.0:
            return glow.compose(buffer, card)
        if alpha >= 1.0:
            return glow.compose(buffer, caption)
        with_card = glow.compose(buffer, card).astype(np.float32)
        without = glow.compose(buffer, caption).astype(np.float32)
        return (with_card * (1.0 - alpha) + without * alpha).astype(np.uint8)

    held = round(args.title_card * args.fps) if card is not None else 0
    fade = round(args.title_fade * args.fps) if card is not None else 0

    def alpha_at(index: int) -> float:
        if index < held:
            return 0.0
        if index < held + fade:
            return (index - held + 1) / fade
        if index >= frames - fade:
            return (frames - 1 - index) / fade
        return 1.0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    cover = draw(0, alpha_at(0))
    Image.fromarray(cover).save(args.output.with_name(args.output.stem + "_cover.png"))
    if args.cover_only:
        plt.close(figure)
        return args.output.with_name(args.output.stem + "_cover.png")

    encoder = start_encoder(args.output, args.width, args.height, args.fps)
    assert encoder.stdin is not None
    try:
        encoder.stdin.write(cover.tobytes())
        for index in range(1, frames):
            encoder.stdin.write(draw(index, alpha_at(index)).tobytes())
            if index % 60 == 0:
                print(f"  frame {index}/{frames}", flush=True)
    finally:
        encoder.stdin.close()
        plt.close(figure)
    if encoder.wait() != 0:
        raise RuntimeError("ffmpeg failed while rendering the shoal.")
    return args.output


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parametric bait ball with the house typography.")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--duration", type=float, default=8.0)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--dpi", type=int, default=120)
    parser.add_argument("--title-top", type=int, default=240)
    parser.add_argument("--caption-bottom", type=int, default=190)
    parser.add_argument("--scrim", type=float, default=0.95)
    parser.add_argument("--font", choices=sorted(FONT_FAMILIES), default="plex")
    parser.add_argument(
        "--equation-font", choices=sorted(FONT_FAMILIES), default="dejavu",
        help="face for the data block alone; DejaVu because Plex has no ξ, φ or ∝",
    )
    parser.add_argument("--title-card", type=float, default=0.0, help="seconds held on the opening card")
    parser.add_argument("--title-fade", type=float, default=0.4)
    parser.add_argument("--title-dim", type=float, default=0.18)
    parser.add_argument("--hook-size", type=int, default=34)
    parser.add_argument(
        "--phase", type=float, default=0.9750,
        help="where in the cycle the clip starts, in turns. The loop closes at any "
             "value, so this only chooses which frame Instagram gets as the grid "
             "thumbnail; 0.9750 is the best-scoring frame of the 240, picked on "
             "visible crest plus near-wall density minus how clumped the crest is.",
    )
    parser.add_argument("--cover-only", action="store_true", help="write the cover PNG and stop")
    args = parser.parse_args(argv)
    if args.width % 2 or args.height % 2:
        parser.error("width and height must be even for H.264")

    regular, bold = FONT_FAMILIES[args.font]
    args.equation_face = FONT_FAMILIES[args.equation_font][0]
    for face in (regular, bold, args.equation_face):
        if not face.exists():
            parser.error(f"missing font file: {face}")
    glow.MONO_FONT, glow.MONO_BOLD_FONT = regular, bold

    if args.output == DEFAULT_OUTPUT and args.title_card > 0:
        args.output = args.output.with_name(
            args.output.stem.replace("_1080x1920", "_titlecard_1080x1920") + ".mp4"
        )
    return args


if __name__ == "__main__":
    print(f"Saved {render(parse_args())}")
