#!/usr/bin/env python3
"""Shared typography helpers for unobtrusive equation captions."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")


def make_equation_overlay(
    width: int,
    height: int,
    lines: tuple[str, ...],
    font_size: int = 22,
    right_margin: int = 38,
    bottom_margin: int = 42,
) -> Image.Image:
    """Create a transparent, bottom-right, monospace equation layer."""
    if not FONT_PATH.exists():
        raise RuntimeError(f"Monospace font not found: {FONT_PATH}")
    font = ImageFont.truetype(str(FONT_PATH), font_size)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    text = "\n".join(lines)
    spacing = max(3, font_size // 4)
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing)
    text_width, text_height = box[2] - box[0], box[3] - box[1]
    position = (width - right_margin - text_width, height - bottom_margin - text_height)
    draw.multiline_text(
        position,
        text,
        font=font,
        fill=(242, 245, 250, 215),
        spacing=spacing,
        align="left",
        stroke_width=1,
        stroke_fill=(0, 0, 0, 180),
    )
    return overlay


def apply_equation_overlay(frame: np.ndarray, overlay: Image.Image) -> np.ndarray:
    image = Image.fromarray(frame).convert("RGBA")
    image.alpha_composite(overlay)
    return np.asarray(image.convert("RGB"))
