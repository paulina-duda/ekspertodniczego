#!/usr/bin/env python3
"""The third biomorph: an ammonite, the equiangular spiral worn as a shell.

The cosine creature was a formula read along an axis; the medusa was one wave
read radially. This one is the coordinate system D'Arcy Thompson kept for the
last chapter: the logarithmic spiral,

    r = R · K^(−p)        K = 2.3^(1/16), one whorl grows 2.3×
    θ = θ₀ − (2π/16) p    p = how many ribs behind the lip

which is the only curve that is the same shape at every size — which is why a
mollusc can live in one its whole life, only ever adding to the edge.

That is also the whole animation. The animal sits still at the aperture and
lays down one rib per loop; everything it has already built recedes down the
coil, shrinking by exactly K per rib. Because the spiral is self-similar, the
frame after one rib is indistinguishable from the frame before it: the loop is
seamless *because* r = e^(bθ), not despite it.

Magenta is not decoration: it is the living tissue — the tentacles, the mantle
lip, and the one rib being written right now (it materialises dot by dot as it
slides out of the lip). Everything white is shell: dead the moment it was
finished. The animal is the small pink thing; the rest is its log file.

Every time term is an integer multiple of t and the rib conveyor shares one
dot pattern across all ribs (scaled by the local tube width), so rib j at the
end of the loop lands exactly on rib j+1 at its start — no seam, verified by
construction.
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
    / "growth-form_ammonite-logspiral_1080x1920_8s_30fps.mp4"
)

TITLE = "Ammonite"
CAPTION = (
    "shell    r ∝ e^(0.13 θ)",
    "one rib laid down per loop",
    "magenta where alive · the rest is shell",
)
HOOK = (
    "The shell is a log file.",
    "Only the edge is alive.",
)

ACCENT = "#ff3bd4"

MARGIN = 64          # left inset shared by the title, the hook and the data block
CAPTION_SIZE = 27    # house size for the data block
HOOK_GAP = 82        # ink to ink, hook down to the data block -- the house
                     # spacing for this layout, same as medusa and hyphae

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


class Ammonite:
    """Static geometry built once; every frame is a pure function of t."""

    M = 16                      # ribs per whorl
    TURNS = 4.25
    U = int(M * TURNS)          # ribs drawn before they vanish into the core
    K = 2.3 ** (1.0 / 16)       # growth per rib; 2.3 per whorl
    C = 2 * np.pi / 16
    R_AP = 215.0                # radius at the aperture
    TH_AP = np.deg2rad(200.0)
    WFRAC = 0.20                # tube half-width as a fraction of r
    CX, CY = 55.0, 5.0          # coil centre, in the un-mirrored model frame

    def spiral(self, p):
        return self.R_AP * self.K ** (-p), self.TH_AP - self.C * p

    def __init__(self) -> None:
        rng = np.random.default_rng(5)

        # Tube edges: two dotted rails. The envelope is self-similar, so the
        # rails are static truth; only the material (the ribs) drifts.
        n_rail = 3400
        self.p_rail = np.tile(np.linspace(0.0, self.U - 0.001, n_rail // 2), 2)
        self.side = np.repeat([1.0, -1.0], n_rail // 2)
        self.rail_jit = rng.normal(0, 0.9, n_rail)

        # Ribs: every rib shares one transverse dot pattern, scaled by the
        # local width — this is what makes the conveyor seamless.
        self.pts_rib = 34
        self.v_rib = np.tile(np.linspace(-1.0, 1.0, self.pts_rib), self.U)
        self.jid = np.repeat(np.arange(self.U), self.pts_rib)
        self.rib_jit = np.tile(rng.normal(0, 0.035, self.pts_rib), self.U)

        # Tentacles: rooted across the mouth, each starting already fanned and
        # turning at its own rate towards its own hanging direction, so the
        # curtain never pinches into a ponytail.
        self.n_t, self.pts_t = 9, 300
        self.hang = np.deg2rad(np.linspace(-150, -78, self.n_t))
        self.root_v = np.linspace(0.8, -0.8, self.n_t)
        self.phi_t = np.arange(self.n_t) * 2.399
        self.LT = np.array([300, 360, 280, 400, 330, 380, 300, 350, 260], dtype=float)
        self.ell = np.tile(np.linspace(0.0, 1.0, self.pts_t), self.n_t)
        self.tid = np.repeat(np.arange(self.n_t), self.pts_t)
        self.t_jit = rng.normal(0, 0.9, self.n_t * self.pts_t)

        # Mantle lip: a thin band of living dust across the mouth.
        n_lip = 320
        self.v_lip = rng.uniform(-1, 1, n_lip)
        self.d_lip = rng.random(n_lip) ** 2

    def width(self, p, t):
        """Tube half-width, breathing with a wave that runs down the coil."""
        return (
            self.WFRAC * self.R_AP * self.K ** (-p)
            * (1.0 + 0.05 * np.sin(2 * t - 0.4 * p))
        )

    def frame(self, t: float):
        """Everything at loop phase t ∈ [0, 2π).

        Returns (rail_x, rail_y), (rib_x, rib_y, rib_size, newest_mask),
        (pink_x, pink_y) for the living dust. x is already mirrored so the
        mouth sits lower-right and the core upper-left.
        """
        tau = t / (2 * np.pi)

        r, th = self.spiral(self.p_rail)
        w = self.width(self.p_rail, t)
        rail_x = self.CX + (r + self.side * w) * np.cos(th) + self.rail_jit
        rail_y = self.CY + (r + self.side * w) * np.sin(th) + self.rail_jit * 0.5

        # Ribs: age p = j + tau behind the lip. Born at the lip (size ramps in
        # over its first loop), dies fading into the core, drifts in between.
        p_r = self.jid + tau
        rr, tth = self.spiral(p_r)
        ww = self.width(p_r, t)
        bow = 0.35 * ww * (1.0 - self.v_rib**2)
        rmid = rr + self.v_rib * ww
        rib_x = self.CX + rmid * np.cos(tth) - bow * np.sin(tth) + self.rib_jit * ww
        rib_y = self.CY + rmid * np.sin(tth) + bow * np.cos(tth) + self.rib_jit * ww * 0.5
        fade = np.clip(p_r, 0, 1) * np.clip((self.U - p_r) / 6.0, 0, 1)
        rib_size = fade * (0.55 + 0.032 * ww)   # outer ribs get bigger dots
        rib_new = p_r < 1.0

        r_ap, th_ap = self.spiral(0.0)
        w_ap = self.width(0.0, t)
        mx = self.CX + r_ap * np.cos(th_ap)
        my = self.CY + r_ap * np.sin(th_ap)
        ang = th_ap + np.pi / 2 + np.arctan(np.log(self.K) * self.M / (2 * np.pi))
        ang = float(np.angle(np.exp(1j * ang)))  # wrap, or the heading blend loops the long way
        rux, ruy = np.cos(th_ap), np.sin(th_ap)

        lip_x = mx + self.v_lip * w_ap * rux + self.d_lip * 6.0 * np.cos(ang)
        lip_y = my + self.v_lip * w_ap * ruy + self.d_lip * 6.0 * np.sin(ang)

        ell, tid = self.ell, self.tid
        a0 = ang + np.deg2rad(np.linspace(-30, 26, self.n_t))[tid]
        blend = ell ** np.linspace(0.65, 1.55, self.n_t)[tid]
        a = a0 * (1.0 - blend) + self.hang[tid] * blend
        step = self.LT[tid] / self.pts_t
        dx = (np.cos(a) * step).reshape(self.n_t, self.pts_t).cumsum(axis=1).ravel()
        dy = (np.sin(a) * step).reshape(self.n_t, self.pts_t).cumsum(axis=1).ravel()
        ph = 5.0 * ell - 2 * t + self.phi_t[tid]
        sway = (16.0 * ell**1.3) * np.sin(ph) + 26.0 * np.sin(np.pi * ell) * np.linspace(
            -1, 1, self.n_t
        )[tid]
        tent_x = (
            mx + self.root_v[tid] * w_ap * rux + dx - np.sin(a) * sway
            + self.t_jit * (1 + 1.4 * ell)
        )
        tent_y = (
            my + self.root_v[tid] * w_ap * ruy + dy + np.cos(a) * sway
            + self.t_jit * (1 + 1.4 * ell) * 0.4
        )

        pink_x = np.concatenate([lip_x, tent_x])
        pink_y = np.concatenate([lip_y, tent_y])
        return (
            (-rail_x, rail_y),
            (-rib_x, rib_y, rib_size, rib_new),
            (-pink_x, pink_y),
        )


def draw_hook(overlay: Image.Image, args: argparse.Namespace) -> None:
    """The hook, set in the strip under the tentacle curtain.

    Plex, not the data block's DejaVu: no Greek in it, so house rule 5's
    default applies. Centered on the frame, unlike the left-column title and
    data block, so it reads as a caption over the animal. Its position is
    measured from where CAPTION's ink lands, not from the lines actually being
    drawn, so the hook holds still while the title card fades.
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
    """Title, hook and -- once the card has cleared -- the data block."""
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

    # Coil upper-left, mouth lower-right, tentacle curtain across the bottom;
    # the lower-left stays black for the data block. Same stage width as the
    # medusa; y chosen so the coil's crown sits ~30 px under the title ink and
    # the longest tentacle stays well clear of the hook's first line.
    x_min, x_max = -336.0, 336.0
    y_mid = -199.0
    y_span = (x_max - x_min) * height / width
    axes.set_xlim(x_min, x_max)
    axes.set_ylim(y_mid - y_span / 2, y_mid + y_span / 2)
    axes.set_aspect("equal", adjustable="box")
    axes.axis("off")

    scale = width / 960
    rails = axes.scatter([], [], s=0.8 * scale**2, c="white", alpha=0.5, linewidths=0)
    ribs = axes.scatter([], [], s=0.8 * scale**2, c="white", alpha=0.55, linewidths=0)
    pink = axes.scatter([], [], s=2.2 * scale**2, c=ACCENT, alpha=0.65, linewidths=0)
    fresh = axes.scatter([], [], s=8 * scale**2, c=ACCENT, alpha=0.95, linewidths=0)
    return figure, axes, rails, ribs, pink, fresh, scale, plt


def render(args: argparse.Namespace) -> Path:
    frames = round(args.duration * args.fps)
    ammonite = Ammonite()
    figure, axes, rails, ribs, pink, fresh, scale, plt = build_figure(
        args.width, args.height, args.dpi
    )
    caption = build_overlay(args.width, args.height, args, CAPTION)
    card = build_overlay(args.width, args.height, args, ()) if args.title_card > 0 else None

    def points_at(index: int) -> np.ndarray:
        t = index / frames * 2 * np.pi
        (rx, ry), (bx, by, bsize, bnew), (px, py) = ammonite.frame(t)
        rails.set_offsets(np.c_[rx, ry])
        old = ~bnew
        ribs.set_offsets(np.c_[bx[old], by[old]])
        ribs.set_sizes(0.8 * scale**2 * bsize[old])
        pink.set_offsets(np.c_[px, py])
        fresh.set_offsets(np.c_[bx[bnew], by[bnew]])
        fresh.set_sizes(8 * scale**2 * bsize[bnew])
        figure.canvas.draw()
        return np.ascontiguousarray(np.asarray(figure.canvas.buffer_rgba())[:, :, :3])

    def draw(index: int, alpha: float = 1.0) -> np.ndarray:
        # The animal keeps writing its shell under the card: one continuous
        # cycle, no finished form to hold on, same as its two siblings.
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
        raise RuntimeError("ffmpeg failed while rendering the ammonite.")
    return args.output


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Log-spiral ammonite with the house typography.")
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
        help="face for the data block alone; DejaVu because Plex has no θ or ∝",
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
