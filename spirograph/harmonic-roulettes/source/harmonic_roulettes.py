#!/usr/bin/env python3
"""Render full-screen 9:16 harmonic roulette editions for Instagram.

A roulette is the path of a pen fixed to a circle that rolls without slipping
along another circle. The ratio of the two radii decides everything: a rational
ratio closes into a finite rosette, an irrational ratio never closes at all.

The three editions are built as one argument. HYPOTROCHOID uses the consecutive
Fibonacci radii 233/144 — the best rational approximation of the golden ratio,
so it closes, but only after 144 turns. GOLDEN ROULETTE uses φ itself and never
closes. EPITROCHOID rolls the circle along the outside instead of the inside.
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "instagram" / "phone-9x16"
DEFAULT_PREVIEW_DIR = PROJECT_DIR / "previews"

SANS_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
MONO_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")

PHI = (1 + 5 ** 0.5) / 2

# Stops run from the outer rim inward, so the last colour lands on the bright
# caustic at the heart of the figure. Every stop stays luminous on purpose: the
# darkness in these frames has to come from thinning strand density, never from
# a dark colour, or the sparse outer weave sinks into the background.
PALETTES = {
    "ultraviolet-bloom": [
        (96, 84, 255), (140, 78, 250), (188, 84, 236), (232, 96, 198),
        (255, 122, 158), (255, 162, 152), (255, 206, 178), (255, 244, 226),
    ],
    "verdigris-tide": [
        (56, 200, 255), (48, 220, 214), (66, 232, 160), (124, 240, 128),
        (182, 246, 132), (222, 250, 168), (242, 253, 214), (252, 255, 246),
    ],
    "molten-brass": [
        (255, 92, 108), (255, 116, 72), (255, 148, 52), (255, 180, 60),
        (255, 208, 92), (255, 230, 140), (255, 244, 196), (255, 253, 238),
    ],
}

PIECES = {
    "hypotrochoid": {
        "title": "HYPOTROCHOID",
        "palette": "ultraviolet-bloom",
        "fixed": 233,
        "rolling": 144,
        "pen": 89,
        "outside": False,
        "equation": (
            "x = (R−r)·cos t + d·cos((R−r)t/r)",
            "y = (R−r)·sin t − d·sin((R−r)t/r)",
            "",
            "R = 233  r = 144  d = 89  (Fibonacci)",
            "R/r ≈ φ → closes after 144 turns",
        ),
    },
    "epitrochoid": {
        "title": "EPITROCHOID",
        "palette": "verdigris-tide",
        "fixed": 199,
        "rolling": 64,
        "pen": 96,
        "outside": True,
        "equation": (
            "x = (R+r)·cos t − d·cos((R+r)t/r)",
            "y = (R+r)·sin t − d·sin((R+r)t/r)",
            "",
            "R = 199   r = 64   d = 96",
            "gcd(R,r) = 1 → closes after 64 turns",
        ),
    },
    "golden-roulette": {
        "title": "GOLDEN ROULETTE",
        "palette": "molten-brass",
        "fixed": 1.0,
        "rolling": 1 / PHI,
        "pen": 1.8 / PHI,
        "outside": False,
        "revolutions": 140,
        "equation": (
            "x = (R−r)·cos t + d·cos((R−r)t/r)",
            "y = (R−r)·sin t − d·sin((R−r)t/r)",
            "",
            "R/r = φ = (1+√5)/2    d = 1.8 r",
            "φ is irrational → the curve never closes",
        ),
    },
}


def build_palette(stops: list[tuple[int, int, int]], size: int = 1024) -> np.ndarray:
    """Interpolate the colour stops into a linear 0–1 lookup table."""
    palette = np.zeros((size, 3), dtype=np.float32)
    for index in range(size):
        position = index / (size - 1)
        segment = min(int(position * (len(stops) - 1)), len(stops) - 2)
        fraction = position * (len(stops) - 1) - segment
        palette[index] = [
            (start + (end - start) * fraction) / 255.0
            for start, end in zip(stops[segment], stops[segment + 1])
        ]
    return palette


def roulette(fixed: float, rolling: float, pen: float, revolutions: float, samples: int, outside: bool) -> np.ndarray:
    """Trace the path of a pen carried by a circle rolling on a fixed circle.

    The parameter t is the turning angle of the rolling circle's centre, so
    equal steps in t are equal steps in time. The pen therefore lingers where it
    moves slowly, and those crowded samples are what burn the bright caustics.
    """
    t = np.linspace(0.0, 2 * math.pi * revolutions, samples)
    if outside:
        span = fixed + rolling
        x = span * np.cos(t) - pen * np.cos(span / rolling * t)
        y = span * np.sin(t) - pen * np.sin(span / rolling * t)
    else:
        span = fixed - rolling
        x = span * np.cos(t) + pen * np.cos(span / rolling * t)
        y = span * np.sin(t) - pen * np.sin(span / rolling * t)
    return np.column_stack((x, y))


def closure_revolutions(fixed: float, rolling: float) -> int:
    """Turns of the rolling circle before a rational roulette closes."""
    return int(rolling // math.gcd(int(fixed), int(rolling)))


def place_on_canvas(points: np.ndarray, width: int, height: int, diameter: float, centre: float) -> np.ndarray:
    minimum, maximum = points.min(0), points.max(0)
    middle = (minimum + maximum) * 0.5
    scale = width * diameter / max((maximum - minimum).max(), 1e-9)
    placed = (points - middle) * scale
    placed[:, 0] += width * 0.5
    placed[:, 1] += height * centre
    return placed


def trace_points(spec: dict, revolutions: float, samples: int, args: argparse.Namespace) -> np.ndarray:
    points = roulette(spec["fixed"], spec["rolling"], spec["pen"], revolutions, samples, spec["outside"])
    return place_on_canvas(
        points,
        args.width * args.supersample,
        args.height * args.supersample,
        args.diameter,
        args.centre,
    )


def resolve_samples(spec: dict, revolutions: float, args: argparse.Namespace) -> np.ndarray:
    """Sample densely enough that no drawn step jumps more than about a pixel."""
    probe = trace_points(spec, revolutions, 120000, args)
    longest = np.abs(np.diff(probe, axis=0)).max()
    samples = int(np.clip(120000 * longest / 1.1, 200000, args.max_samples))
    return trace_points(spec, revolutions, samples, args)


def shade_values(points: np.ndarray, args: argparse.Namespace) -> np.ndarray:
    """Where each sample sits in the palette, as a 0–1 value.

    Colouring by radius is what suits a roulette: every strand crosses the whole
    figure, so colouring by progress along the curve just averages the palette
    into mud. The radius is the coordinate the rolling circle actually modulates,
    so it lays the spectrum down in concentric bands.
    """
    if args.colour_by == "progress":
        return np.linspace(0.0, 1.0, len(points), dtype=np.float32)
    centre = np.array(
        [args.width * args.supersample * 0.5, args.height * args.supersample * args.centre],
        dtype=np.float64,
    )
    radius = np.linalg.norm(points - centre, axis=1)
    lowest, highest = radius.min(), radius.max()
    return (1.0 - (radius - lowest) / max(highest - lowest, 1e-9)).astype(np.float32)


class Accumulator:
    """Two light buffers: how much ink landed, and what shade it was.

    Summing colour channel by channel would let crossing strands add their way
    to a muddy white, which is exactly what ruins the mid-tones. So the shade is
    banked as a density-weighted total and only becomes colour at the end. Hue
    then stays as pure as a single strand no matter how many cross it, and the
    density alone decides how brightly that hue burns.
    """

    def __init__(self, width: int, height: int, supersample: int) -> None:
        shape = (height * supersample, width * supersample)
        self.supersample = supersample
        self.density = np.zeros(shape, dtype=np.float32)
        self.tint = np.zeros(shape, dtype=np.float32)

    def add_segment(self, points: np.ndarray, shade: float, line_width: int) -> None:
        if len(points) < 2:
            return
        pad = line_width + 2
        x0 = max(int(points[:, 0].min()) - pad, 0)
        x1 = min(int(points[:, 0].max()) + pad, self.density.shape[1])
        y0 = max(int(points[:, 1].min()) - pad, 0)
        y1 = min(int(points[:, 1].max()) + pad, self.density.shape[0])
        if x1 <= x0 or y1 <= y0:
            return
        tile = Image.new("L", (x1 - x0, y1 - y0), 0)
        local = [(float(x) - x0, float(y) - y0) for x, y in points]
        ImageDraw.Draw(tile).line(local, fill=255, width=line_width, joint="curve")
        stamp = np.asarray(tile, dtype=np.float32) * (1.0 / 255.0)
        self.density[y0:y1, x0:x1] += stamp
        self.tint[y0:y1, x0:x1] += stamp * shade

    def _box(self, plane: np.ndarray) -> np.ndarray:
        step = self.supersample
        if step == 1:
            return plane
        total = plane[0::step, 0::step].copy()
        for row in range(step):
            for column in range(step):
                if row or column:
                    total += plane[row::step, column::step]
        return total / (step * step)

    def resolve(self) -> tuple[np.ndarray, np.ndarray]:
        density = self._box(self.density)
        tint = self._box(self.tint)
        return density, tint / np.maximum(density, 1e-6)


def shade_to_image(density: np.ndarray, hue: np.ndarray, palette: np.ndarray, args: argparse.Namespace) -> np.ndarray:
    """Turn density and hue into light: pure colour, brightened by how much ink."""
    toned = 1.0 - np.exp(-density * args.exposure)
    luminance = np.power(np.clip(toned, 0, 1), 1.0 / args.gamma)
    index = np.clip(hue * (len(palette) - 1), 0, len(palette) - 1).astype(np.int32)
    colour = palette[index]
    if args.bleach < 1.0:
        # Only the very densest crossings are allowed to burn out to white.
        heat = np.clip((toned - args.bleach) / (1.0 - args.bleach), 0, 1) ** 2
        colour = colour * (1.0 - heat[:, :, None]) + heat[:, :, None]
    image = colour * luminance[:, :, None]
    if args.bloom > 0:
        halo = Image.fromarray((np.clip(luminance - 0.25, 0, 1) * 255).astype(np.uint8))
        halo = halo.filter(ImageFilter.GaussianBlur(20))
        image = image + colour * (np.asarray(halo, dtype=np.float32)[:, :, None] * (args.bloom / 255.0))
    return np.clip(image, 0, 1)


def draw_pen(image: Image.Image, position: np.ndarray, supersample: int) -> None:
    x, y = float(position[0]) / supersample, float(position[1]) / supersample
    glow = Image.new("L", image.size, 0)
    ImageDraw.Draw(glow).ellipse((x - 11, y - 11, x + 11, y + 11), fill=150)
    glow = glow.filter(ImageFilter.GaussianBlur(7))
    image.paste(Image.new("RGB", image.size, (255, 252, 244)), (0, 0), glow)
    ImageDraw.Draw(image).ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 255, 255))


def draw_typography(image: Image.Image, title: str, equation: tuple[str, ...]) -> None:
    """Title top-left with wide tracking, equation block bottom-left."""
    for font_path in (SANS_FONT, MONO_FONT):
        if not font_path.exists():
            raise RuntimeError(f"Font not found: {font_path}")
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.truetype(str(SANS_FONT), 26)
    cursor = 66.0
    for letter in title:
        draw.text((cursor, 71), letter, font=title_font, fill=(255, 255, 255))
        cursor += draw.textlength(letter, font=title_font) + 17

    mono = ImageFont.truetype(str(MONO_FONT), 27)
    text = "\n".join(equation)
    box = draw.multiline_textbbox((0, 0), text, font=mono, spacing=5)
    draw.multiline_text(
        (62, image.height - 42 - (box[3] - box[1])),
        text,
        font=mono,
        fill=(228, 233, 240),
        spacing=5,
    )


def compose(accumulator: Accumulator, spec: dict, palette: np.ndarray, args: argparse.Namespace, pen: np.ndarray | None) -> Image.Image:
    density, hue = accumulator.resolve()
    frame = shade_to_image(density, hue, palette, args)
    image = Image.fromarray((frame * 255).astype(np.uint8), "RGB")
    if pen is not None:
        draw_pen(image, pen, accumulator.supersample)
    draw_typography(image, spec["title"], spec["equation"])
    return image


def write_all(stream: object, data: bytes) -> None:
    remaining = memoryview(data)
    while remaining:
        written = stream.write(remaining)  # type: ignore[attr-defined]
        if written is not None:
            remaining = remaining[written:]


def start_encoder(output: Path, args: argparse.Namespace) -> subprocess.Popen[bytes]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to export MP4 files.")
    encoders = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, check=True).stdout
    if " libx264 " in encoders:
        codec = ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high"]
    elif " libopenh264 " in encoders:
        codec = ["-c:v", "libopenh264", "-threads", "1", "-b:v", "12M", "-maxrate", "16M"]
    else:
        raise RuntimeError("No H.264 encoder is available in ffmpeg.")
    output.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen(
        [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{args.width}x{args.height}", "-r", str(args.animation_fps), "-i", "-",
            "-an", *codec, "-r", str(args.fps),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
        ],
        stdin=subprocess.PIPE,
    )


def reveal_fraction(progress: float, hold: float) -> float:
    position = min(progress / hold, 1.0)
    eased = 0.35 * position + 0.65 * position * position * (3 - 2 * position)
    return 0.004 + 0.996 * eased


def prepare(name: str, args: argparse.Namespace) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray, float]:
    spec = PIECES[name]
    revolutions = spec.get("revolutions") or closure_revolutions(spec["fixed"], spec["rolling"])
    points = resolve_samples(spec, revolutions, args)
    shade = shade_values(points, args)
    palette = build_palette(PALETTES[spec["palette"]])
    return spec, points, shade, palette, revolutions


def paint(accumulator: Accumulator, points: np.ndarray, shade: np.ndarray, start: int, end: int, args: argparse.Namespace) -> None:
    """Lay down the strand between two indices, one shade per short run."""
    for begin in range(start, end, args.colour_chunk):
        stop = min(begin + args.colour_chunk, end)
        accumulator.add_segment(
            points[max(begin - 1, 0) : stop + 1],
            float(shade[begin:stop].mean()),
            args.line_width,
        )


def render_preview(name: str, args: argparse.Namespace) -> Path:
    spec, points, shade, palette, revolutions = prepare(name, args)
    accumulator = Accumulator(args.width, args.height, args.supersample)
    paint(accumulator, points, shade, 0, len(points), args)
    image = compose(accumulator, spec, palette, args, None)
    args.preview_dir.mkdir(parents=True, exist_ok=True)
    output = args.preview_dir / f"{name}_{spec['palette']}_{args.width}x{args.height}.png"
    image.save(output)
    print(f"Saved {output}  ({revolutions} turns, {len(points)} samples)")
    return output


def render_video(name: str, args: argparse.Namespace) -> Path:
    spec, points, shade, palette, revolutions = prepare(name, args)
    accumulator = Accumulator(args.width, args.height, args.supersample)
    output = args.output_dir / f"{name}_{spec['palette']}_roulette_{args.width}x{args.height}_{args.duration:g}s_{args.fps}fps.mp4"
    encoder = start_encoder(output, args)
    drawn = 0
    try:
        for frame_index in range(args.animation_frames):
            progress = frame_index / max(args.animation_frames - 1, 1)
            target = max(2, int(reveal_fraction(progress, args.hold) * (len(points) - 1)))
            paint(accumulator, points, shade, drawn, target, args)
            drawn = target
            image = compose(accumulator, spec, palette, args, points[drawn - 1] if progress < args.hold else None)
            assert encoder.stdin is not None
            write_all(encoder.stdin, np.asarray(image, dtype=np.uint8).tobytes())
    finally:
        assert encoder.stdin is not None
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError(f"ffmpeg failed while rendering {name}.")
    print(f"Saved {output}  ({revolutions} turns, {len(points)} samples)")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--piece", choices=sorted(PIECES), default="hypotrochoid")
    parser.add_argument("--all-pieces", action="store_true")
    parser.add_argument("--preview", action="store_true", help="Save a still PNG instead of an MP4.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--preview-dir", type=Path, default=DEFAULT_PREVIEW_DIR)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--duration", type=float, default=12)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--animation-fps", type=int, default=15)
    parser.add_argument("--supersample", type=int, default=2)
    parser.add_argument("--line-width", type=int, default=1)
    parser.add_argument("--colour-by", choices=("radius", "progress"), default="radius")
    parser.add_argument("--colour-chunk", type=int, default=240)
    parser.add_argument("--max-samples", type=int, default=1400000)
    parser.add_argument("--diameter", type=float, default=0.92, help="Figure width as a fraction of the frame.")
    parser.add_argument("--centre", type=float, default=0.47, help="Figure centre as a fraction of the height.")
    parser.add_argument("--exposure", type=float, default=3.4)
    parser.add_argument("--gamma", type=float, default=1.8)
    parser.add_argument("--bleach", type=float, default=0.86, help="Tone above which colour burns out to white.")
    parser.add_argument("--bloom", type=float, default=0.30)
    parser.add_argument("--hold", type=float, default=0.90, help="Progress at which the figure completes.")
    args = parser.parse_args()
    args.animation_frames = round(args.duration * args.animation_fps)
    return args


if __name__ == "__main__":
    options = parse_args()
    for piece_name in (sorted(PIECES) if options.all_pieces else [options.piece]):
        if options.preview:
            render_preview(piece_name, options)
        else:
            render_video(piece_name, options)
