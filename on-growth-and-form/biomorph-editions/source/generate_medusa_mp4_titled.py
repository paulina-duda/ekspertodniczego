#!/usr/bin/env python3
"""The second biomorph: a medusa swum by a single travelling wave.

The cosine creature was two frequencies and a phase delay pretending to be an
animal. This one is the same trick told radially. There is exactly one wave in
the whole body — phase = (integer · t) − (rate · how far along) — and every
part of the animal is that wave read at a different place:

    bell        s = ψ/ψmax, apex → margin
                r ∝ 1 + 0.09 sin(2t − 4s + 0.35 sin 2λ)
                the contraction runs down the bell, slightly helical so the
                crest sweeps rather than dropping as a flat band
    tentacles   phase = 6.5ξ − 2t + φ, each tentacle offset by the golden
                angle, so neighbours never beat together: the metachronal wave
    oral arms   the same phase, slower (4ξ), plus a fine frill an octave up

Green marks where sin(phase) > 0.96 — the crest of the wave, *right now*. The
colour is not decoration: it is the position of the only moving thing in the
piece. Everything else is the wave seen at some other delay.

The bell is a 3D dome drawn as dotted meridians — the same pointillist
language as the cosine creature's ribs — projected orthographically with a
small tilt, so it has a far side without ever turning.

`t` runs a full 2π over the clip and every time term is an integer multiple of
`t`, so the last frame meets the first: the loop is seamless by construction.
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
    / "growth-form_medusa-metachronal_1080x1920_8s_30fps.mp4"
)

TITLE = "Medusa"
CAPTION = (
    "bell       r ∝ 1 + 0.09 sin(2t − 4s)",
    "tentacles  phase = 6.5ξ − 2t + φ",
    "green where sin > 0.96 · the crest",
)
HOOK = (
    "Nothing here swims.",
    "One sine wave, fourteen phase delays.",
)

ACCENT = "#2bff88"

MARGIN = 64          # left inset shared by the title, the hook and the data block
CAPTION_SIZE = 27    # house size for the data block
HOOK_GAP = 82        # ink to ink, hook down to the data block — matches the
                     # substrate-editions hyphae hook (render_substrate.py's
                     # default --hook-gap), the house spacing for this layout

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


class Medusa:
    """Static geometry built once; every frame is a pure function of t."""

    R, H = 185.0, 155.0
    PSI_MAX = 2.05   # polar angle at the margin; past π/2, so it curls under
    TILT = 0.16      # how much depth leaks into y — the far side, without turning
    CREST = 0.96     # sin(phase) above this is the crest, drawn in green

    def __init__(self) -> None:
        rng = np.random.default_rng(11)

        # Bell: dotted meridians, denser at the limb exactly where a real
        # sphere of dust would be — the projection does the shading.
        n_mer, pts_mer = 56, 120
        lam = np.linspace(0.0, 2 * np.pi, n_mer, endpoint=False) + 0.05
        psi = np.tile(np.linspace(0.02, self.PSI_MAX, pts_mer), n_mer)
        lam_m = np.repeat(lam, pts_mer)

        # Two faint latitude rings: enough hoop to read as a built thing,
        # not enough to read as a lampshade.
        pts_ring = 220
        psi_r = np.array([0.75, 1.4])
        lam_r = np.tile(np.linspace(0, 2 * np.pi, pts_ring, endpoint=False), len(psi_r))
        psi_ring = np.repeat(psi_r, pts_ring)

        self.psi = np.concatenate([psi, psi_ring])
        self.lam = np.concatenate([lam_m, lam_r])
        self.s_bell = self.psi / self.PSI_MAX
        self.bell_jitter = rng.normal(0, 0.8, (2, self.psi.size))

        # Tentacles: one per phase slot around the margin ring, offset by the
        # golden angle so neighbours never beat together.
        self.n_tent, pts_tent = 14, 430
        self.lam_t = np.linspace(0, 2 * np.pi, self.n_tent, endpoint=False) + 0.19
        self.phi = np.arange(self.n_tent) * 2.399
        self.L = 470.0 * (0.60 + 0.40 * rng.random(self.n_tent))
        self.ell = np.tile(np.linspace(0.0, 1.0, pts_tent), self.n_tent)
        self.tid = np.repeat(np.arange(self.n_tent), pts_tent)
        self.t_jit = rng.normal(0, 0.55, self.n_tent * pts_tent)

        # Oral arms: three ribbons, the same wave slower, frilled an octave up.
        pts_arm = 1100
        self.ua = np.array([-0.30, 0.02, 0.32])
        self.phia = np.array([0.9, 2.6, 4.3])
        self.La = np.array([300.0, 355.0, 325.0])
        self.ell_a = np.tile(np.linspace(0.0, 1.0, pts_arm), 3)
        self.aid = np.repeat(np.arange(3), pts_arm)
        self.ribbon = rng.normal(0, 1.0, 3 * pts_arm)

    def frame(self, t: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """All points at loop phase t ∈ [0, 2π); returns x, y, crest mask."""
        # Bell: contraction wave apex → margin, slightly helical in λ so the
        # crest sweeps around the dome instead of dropping as a flat band.
        ph_b = 2 * t - 4.0 * self.s_bell + 0.35 * np.sin(2 * self.lam + self.s_bell)
        f = 1.0 + 0.09 * np.sin(ph_b) * (0.15 + 0.85 * self.s_bell)
        r = self.R * np.sin(self.psi) * f
        z = r * np.sin(self.lam)
        bx = r * np.cos(self.lam) + self.bell_jitter[0]
        by = (
            self.H * np.cos(self.psi) * (1.0 + 0.04 * np.sin(ph_b))
            + self.TILT * z
            + self.bell_jitter[1]
        )
        bell_hot = (np.sin(ph_b) > self.CREST) & (self.s_bell > 0.15)

        # The whole underside breathes with the margin's phase.
        bob = 9.0 * np.sin(2 * t - 4.0)

        # Tentacle roots ride the pulsing margin ring.
        f_root = 1.0 + 0.09 * np.sin(2 * t - 4.0)
        r_root = self.R * np.sin(self.PSI_MAX) * f_root
        x0 = r_root * np.cos(self.lam_t[self.tid])
        z0 = r_root * np.sin(self.lam_t[self.tid])
        y0 = self.H * np.cos(self.PSI_MAX) + self.TILT * z0 + bob * 0.6

        ell, tid = self.ell, self.tid
        ph_t = 6.5 * ell - 2 * t + self.phi[tid]
        sway = np.sin(t + self.phi[tid] * 0.31) * 16.0
        tx = (
            x0 * (1.0 + 0.20 * ell)
            + 30.0 * ell**1.3 * np.sin(ph_t)
            + sway * ell**1.5
            + self.t_jit * (1 + 1.2 * ell)
        )
        ty = y0 - self.L[tid] * ell * (1.0 - 0.05 * np.cos(ph_t)) + 5.0 * ell * np.cos(ph_t)
        tent_hot = np.sin(ph_t) > self.CREST

        ell_a, aid = self.ell_a, self.aid
        ph_a = 4.0 * ell_a - 2 * t + self.phia[aid]
        frill = (11.0 + 8.0 * ell_a) * np.sin(19.0 * ell_a - 2 * t + self.phia[aid] * 3.1)
        ax = (
            self.ua[aid] * self.R * (1.0 + 0.1 * ell_a)
            + 46.0 * ell_a**1.15 * np.sin(ph_a)
            + frill * ell_a**0.5
            + self.ribbon * (2.0 + 5.0 * ell_a)
        )
        ay = (
            bob * 0.8
            - 30.0
            - self.La[aid] * ell_a
            + 8.0 * ell_a * np.cos(ph_a)
            + np.abs(self.ribbon) * 2.0
        )
        arm_hot = np.sin(ph_a) > self.CREST

        x = np.concatenate([bx, tx, ax])
        y = np.concatenate([by, ty, ay])
        hot = np.concatenate([bell_hot, tent_hot, arm_hot])
        return x, y, hot


def draw_hook(overlay: Image.Image, args: argparse.Namespace) -> None:
    """The hook, set in the strip between the tentacle tips and the data block.

    Plex, not the data block's DejaVu: there is no Greek in it, so house rule
    5's default applies. A few points above the data block so it reads as the
    louder of the two, and no more than that — every pixel it takes is a pixel
    the medusa gives up. Centered on the frame, unlike the left-column title
    and data block, so it reads as a caption over the animal rather than a
    third line in that column.

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
    import matplotlib.pyplot as plt

    figure = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi)
    figure.patch.set_facecolor("black")
    axes = figure.add_axes((0, 0, 1, 1), facecolor="black")

    # The medusa's model space, framed for 9:16: bell at the top, tentacles
    # trailing to just short of the hook. The hook costs the animal about a
    # fifth of its height — these numbers put the bell's crown ~30 px under the
    # title and the longest tentacle ~30 px above the hook's first line, which
    # is as much room as there is between the two margins.
    x_min, x_max = -336.0, 336.0
    y_mid = -239.5
    y_span = (x_max - x_min) * height / width
    axes.set_xlim(x_min, x_max)
    axes.set_ylim(y_mid - y_span / 2, y_mid + y_span / 2)
    axes.set_aspect("equal", adjustable="box")
    axes.axis("off")

    scale = width / 960
    white = axes.scatter([], [], s=0.8 * scale**2, c="white", alpha=0.5, linewidths=0)
    green = axes.scatter([], [], s=8 * scale**2, c=ACCENT, alpha=0.9, linewidths=0)
    return figure, axes, white, green, plt


def render(args: argparse.Namespace) -> Path:
    frames = round(args.duration * args.fps)
    medusa = Medusa()
    figure, axes, white, green, plt = build_figure(args.width, args.height, args.dpi)
    caption = build_overlay(args.width, args.height, args, CAPTION)
    card = build_overlay(args.width, args.height, args, ()) if args.title_card > 0 else None

    def points_at(index: int) -> np.ndarray:
        t = index / frames * 2 * np.pi
        x, y, hot = medusa.frame(t)
        white.set_offsets(np.c_[x[~hot], y[~hot]])
        green.set_offsets(np.c_[x[hot], y[hot]])
        figure.canvas.draw()
        return np.ascontiguousarray(np.asarray(figure.canvas.buffer_rgba())[:, :, :3])

    def draw(index: int, alpha: float = 1.0) -> np.ndarray:
        # The medusa keeps pulsing under the card: one continuous cycle, no
        # finished form to hold on, same as the cosine creature.
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
        raise RuntimeError("ffmpeg failed while rendering the medusa.")
    return args.output


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Metachronal medusa with the house typography.")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--duration", type=float, default=8.0)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--dpi", type=int, default=120)
    parser.add_argument("--title-top", type=int, default=240)
    parser.add_argument("--caption-bottom", type=int, default=190)
    parser.add_argument("--scrim", type=float, default=0.95)
    parser.add_argument("--font", choices=sorted(FONT_FAMILIES), default="dejavu")
    parser.add_argument(
        "--equation-font", choices=sorted(FONT_FAMILIES), default="dejavu",
        help="face for the data block alone; DejaVu because Plex has no ξ, φ or ∝",
    )
    parser.add_argument("--title-card", type=float, default=0.0, help="seconds held on the opening card")
    parser.add_argument("--title-fade", type=float, default=0.4)
    parser.add_argument("--title-dim", type=float, default=0.18)
    parser.add_argument("--hook-size", type=int, default=34)
    args = parser.parse_args(argv)
    if args.width % 2 or args.height % 2:
        parser.error("width and height must be even for H.264")

    regular, bold = FONT_FAMILIES[args.font]
    args.equation_face = FONT_FAMILIES[args.equation_font][0]
    for face in (regular, bold, args.equation_face):
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
