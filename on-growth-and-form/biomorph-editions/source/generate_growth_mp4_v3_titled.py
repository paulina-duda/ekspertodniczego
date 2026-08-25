#!/usr/bin/env python3
"""The v3 pointillist biomorph, with the house title and caption over it.

The animal is left exactly as it was. Same expression, same point count, same
two scatter layers, same frame — this only lays the account's typography on top
so the piece sits with the other editions instead of beside them.

Geometry, unchanged from `generate_growth_mp4_v3.py`:

    k = 4 cos(x/21)          the fast frequency, which makes the ribs
    e = x/1880 − 20          the slow one, which makes the body axis
    d = √(k² + e²)
    q = 3 sin 2k + 0.3/k + k sin(x/4465) (9 + 2 sin(14e − 3d + 2t))

    screen x = q + 50 cos(d − t) + 200
    screen y = 875 − q sin(d − t) − 39 d

The phase term `d − t` depends on position, which is why the ribs sweep as a
wave rather than all moving together, and why the thing reads as alive. Points
where `k² ≥ 15` — the extremes of the fast oscillation, the tips of the ribs —
are drawn in red.

Because `t` runs a full 2π over the clip, the last frame meets the first: the
loop is seamless and always was.
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

import glow


DEFAULT_OUTPUT = (
    Path(__file__).parents[1]
    / "instagram"
    / "phone-9x16"
    / "growth-form_cosine-creature_1080x1920_8s_30fps.mp4"
)

TITLE = "Cosine Creature"
CAPTION = (
    "k = 4 cos(x/21)      ribs",
    "e = x/1880 − 20      axis",
    "red where k² ≥ 15 · rib tips",
)
HOOK = (
    "Not biology.",
    "Just two cosine waves",
    "and a phase delay.",
)

# Vendored in the repo rather than installed system-wide, so a clone renders
# identically without anyone having to add a font to their machine.
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


def make_title_card(width: int, height: int, args) -> Image.Image:
    """Opening overlay: the spaced title, and one line worth stopping for.

    No data block. The card carries a single claim, and the equations would
    only compete with it for the second of attention that decides whether
    anyone watches the rest.
    """
    from PIL import ImageDraw, ImageFont

    overlay = glow.make_caption(
        width, height, TITLE, (),
        top_margin=args.title_top, bottom_margin=args.caption_bottom, scrim=args.scrim,
    )
    draw = ImageDraw.Draw(overlay)
    # The regular weight, matching the data block rather than the title: the
    # bold face reads as a heading, the plain one keeps the typewriter voice.
    font = ImageFont.truetype(str(glow.MONO_FONT), args.hook_size)
    text = "\n".join(HOOK)
    spacing = max(6, args.hook_size // 3)
    # Centred on the frame, measured from the ink box so the block sits on the
    # middle rather than starting there.
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align="center")
    draw.multiline_text(
        ((width - (box[2] - box[0])) / 2 - box[0], (height - (box[3] - box[1])) / 2 - box[1]),
        text,
        font=font,
        fill=(255, 255, 255, 244),
        spacing=spacing,
        align="center",
        stroke_width=5,
        stroke_fill=(0, 0, 0, 175),
    )
    return overlay


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
            return ffmpeg, ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high"]
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


def build_figure(points_count: int, width: int, height: int, dpi: int):
    """The original figure and its two scatter layers, untouched."""
    import matplotlib.pyplot as plt

    x = np.arange(points_count)
    k = 4 * np.cos(x / 21)
    e = x / 1880 - 20
    d = np.sqrt(k**2 + e**2)
    highlighted = k**2 >= 15

    figure = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi)
    figure.patch.set_facecolor("black")
    axes = figure.add_axes((0, 0, 1, 1), facecolor="black")

    # The geometry of the original 8:10 GIF, with only its black canvas extended
    # to a true 9:16 phone frame so nothing is stretched.
    x_min, x_max = 100.0, 300.0
    y_mid = (75.0 + 320.0) / 2
    y_span = (x_max - x_min) * height / width
    axes.set_xlim(x_min, x_max)
    axes.set_ylim(y_mid - y_span / 2, y_mid + y_span / 2)
    axes.set_aspect("equal", adjustable="box")
    axes.axis("off")

    scale = width / 960
    white = axes.scatter([], [], s=0.8 * scale**2, c="white", alpha=0.55, linewidths=0)
    red = axes.scatter([], [], s=8 * scale**2, c="#ff2020", alpha=0.9, linewidths=0)
    return figure, axes, white, red, (x, k, e, d, highlighted), plt


def frame_points(state, t: float):
    x, k, e, d, highlighted = state
    with np.errstate(divide="ignore", invalid="ignore"):
        q = 3 * np.sin(2 * k) + 0.3 / k + k * np.sin(x / 4465) * (
            9 + 2 * np.sin(14 * e - 3 * d + 2 * t)
        )
    rendered_x = q + 50 * np.cos(d - t) + 200
    rendered_y = 875 - q * np.sin(d - t) - 39 * d
    finite = np.isfinite(rendered_x) & np.isfinite(rendered_y)
    return rendered_x, rendered_y, finite, highlighted


def render(args: argparse.Namespace) -> Path:
    frames = round(args.duration * args.fps)
    figure, axes, white, red, state, plt = build_figure(
        args.points, args.width, args.height, args.dpi
    )
    caption = glow.make_caption(
        args.width, args.height, TITLE, CAPTION,
        top_margin=args.title_top, bottom_margin=args.caption_bottom, scrim=args.scrim,
    )
    card = make_title_card(args.width, args.height, args) if args.title_card > 0 else None

    def points_at(index: int) -> np.ndarray:
        t = index / frames * 2 * np.pi
        rendered_x, rendered_y, finite, highlighted = frame_points(state, t)
        white.set_offsets(
            np.c_[rendered_x[finite & ~highlighted], rendered_y[finite & ~highlighted]]
        )
        red.set_offsets(np.c_[rendered_x[finite & highlighted], rendered_y[finite & highlighted]])
        figure.canvas.draw()
        # Straight off the Agg canvas rather than through a temporary PNG, so
        # the caption can be composited before anything is encoded.
        return np.ascontiguousarray(np.asarray(figure.canvas.buffer_rgba())[:, :, :3])

    def draw(index: int, alpha: float = 1.0) -> np.ndarray:
        """One frame. `alpha` runs 0 at the title card to 1 at the plain frame.

        The creature keeps moving underneath the card rather than freezing on
        it. This piece has no finished form to hold on -- it is one continuous
        cycle -- and a second of stillness at the top of every loop would read
        as a stall rather than as an opening.
        """
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
        # The card returns over the last stretch, so the clip meets its own
        # first frame and the loop keeps its seam closed.
        if index >= frames - fade:
            return (frames - 1 - index) / fade
        return 1.0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    cover = draw(0, alpha_at(0))
    Image.fromarray(cover).save(args.output.with_name(args.output.stem + "_cover.png"))

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
        raise RuntimeError("ffmpeg failed while rendering the titled biomorph.")
    return args.output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="v3 biomorph with the house typography.")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--duration", type=float, default=8.0)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--points", type=int, default=10_000)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--dpi", type=int, default=120)
    parser.add_argument("--title-top", type=int, default=240)
    parser.add_argument("--caption-bottom", type=int, default=190)
    parser.add_argument("--scrim", type=float, default=0.95)
    parser.add_argument("--font", choices=sorted(FONT_FAMILIES), default="dejavu")
    parser.add_argument("--title-card", type=float, default=0.0, help="seconds held on the opening card")
    parser.add_argument("--title-fade", type=float, default=0.4)
    parser.add_argument("--title-dim", type=float, default=0.18)
    parser.add_argument("--hook-size", type=int, default=52)
    args = parser.parse_args()
    if args.width % 2 or args.height % 2:
        parser.error("width and height must be even for H.264")

    # Set before any caption is built: every text layer in the frame has to come
    # from one family or the card stops reading as a single object.
    regular, bold = FONT_FAMILIES[args.font]
    for face in (regular, bold):
        if not face.exists():
            parser.error(f"missing font file: {face}")
    glow.MONO_FONT, glow.MONO_BOLD_FONT = regular, bold

    if args.output == DEFAULT_OUTPUT:
        suffix = "_titlecard" if args.title_card > 0 else ""
        suffix += "" if args.font == "dejavu" else f"_{args.font}"
        if suffix:
            args.output = args.output.with_name(
                args.output.stem.replace("_1080x1920", f"{suffix}_1080x1920") + ".mp4"
            )
    return args


if __name__ == "__main__":
    print(f"Saved {render(parse_args())}")
