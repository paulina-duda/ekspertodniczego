#!/usr/bin/env python3
"""Generate a 9:16 Instagram MP4 of a glycolytic limit cycle.

Model:
    Selkov glycolytic oscillator

    dS/dt = -S + a*P + S^2*P
    dP/dt =  b - a*P - S^2*P

S and P are dimensionless reduced variables representing a substrate
and a product/regulator in a simplified glycolytic feedback model.

For a=0.08 and b=0.60, the model converges to a stable limit cycle.
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parents[0]

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Reuse your existing Lorenz rendering pipeline.
from lorenz_gif_basic import normalize_points
from lorenz_palette_gifs import render_frame


FINAL_PALETTE_STOPS = {
    "ember_garden": [
        (71, 255, 48),
        (172, 255, 38),
        (255, 239, 45),
        (255, 172, 26),
        (255, 83, 34),
        (255, 34, 96),
        (255, 236, 192),
        (255, 255, 255),
    ],
    "ruby_lime": [
        (116, 255, 18),
        (214, 255, 26),
        (255, 205, 20),
        (255, 111, 32),
        (255, 35, 67),
        (255, 41, 143),
        (255, 220, 170),
        (255, 255, 255),
    ],
    "orchid_gold": [
        (246, 255, 72),
        (255, 210, 50),
        (255, 143, 35),
        (255, 72, 64),
        (255, 38, 137),
        (214, 58, 196),
        (255, 208, 135),
        (255, 255, 255),
    ],
}

FINAL_BACKGROUNDS = {
    "black": (0, 0, 0),
    "warm_graphite": (24, 16, 14),
}

FINAL_PRESETS = [
    ("ember_garden", "black"),
    ("ember_garden", "warm_graphite"),
    ("ruby_lime", "black"),
    ("ruby_lime", "warm_graphite"),
    ("orchid_gold", "black"),
    ("orchid_gold", "warm_graphite"),
]


def build_palette(
    palette_name: str,
    background_name: str,
) -> list[tuple[int, int, int]]:
    """Create a 256-color palette compatible with render_frame()."""

    palette = [FINAL_BACKGROUNDS[background_name]]
    stops = FINAL_PALETTE_STOPS[palette_name]

    for i in range(255):
        t = i / 254.0
        segment = min(int(t * (len(stops) - 1)), len(stops) - 2)
        local_t = t * (len(stops) - 1) - segment

        start = stops[segment]
        end = stops[segment + 1]

        palette.append(
            tuple(
                int(
                    start[channel]
                    + (end[channel] - start[channel]) * local_t
                )
                for channel in range(3)
            )
        )

    return palette


def selkov_derivatives(
    state: np.ndarray,
    a: float,
    b: float,
) -> np.ndarray:
    """Return derivatives for the Selkov glycolytic oscillator.

    Equations:
        dS/dt = -S + aP + S²P
        dP/dt =  b - aP - S²P

    Parameters
    ----------
    S:
        Reduced substrate concentration.
    P:
        Reduced product/regulator concentration.
    a, b:
        Dimensionless Selkov parameters.
    """

    substrate, product = state

    d_substrate = -substrate + a * product + substrate**2 * product
    d_product = b - a * product - substrate**2 * product

    return np.array([d_substrate, d_product], dtype=np.float64)


def integrate_selkov(
    steps: int,
    dt: float,
    a: float,
    b: float,
    initial_substrate: float,
    initial_product: float,
) -> np.ndarray:
    """Integrate the Selkov model with classical fourth-order RK4."""

    points = np.empty((steps, 2), dtype=np.float64)
    state = np.array(
        [initial_substrate, initial_product],
        dtype=np.float64,
    )

    for index in range(steps):
        points[index] = state

        k1 = selkov_derivatives(state, a, b)
        k2 = selkov_derivatives(state + 0.5 * dt * k1, a, b)
        k3 = selkov_derivatives(state + 0.5 * dt * k2, a, b)
        k4 = selkov_derivatives(state + dt * k3, a, b)

        state = state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)

        if not np.all(np.isfinite(state)):
            raise RuntimeError(
                "Model Selkova stał się numerycznie niestabilny. "
                "Zmniejsz dt albo zmień parametry a i b."
            )

    return points


def make_3d_phase_portrait(points_2d: np.ndarray) -> np.ndarray:
    """Convert the 2D limit cycle into a shallow 3D ribbon.

    Biologically meaningful coordinates remain:
        x = substrate S
        y = product/regulator P

    The z coordinate is only a small visual lift for your existing
    3D camera renderer. It is not a third metabolite.
    """

    substrate = points_2d[:, 0]
    product = points_2d[:, 1]

    substrate_centered = substrate - np.mean(substrate)
    product_centered = product - np.mean(product)

    scale = max(
        np.ptp(substrate_centered),
        np.ptp(product_centered),
        1e-12,
    )

    x = substrate_centered / scale
    y = product_centered / scale

    # Phase around the centre of the cycle.
    phase = np.unwrap(np.arctan2(y, x))

    # Small visual depth only. Keeps it recognisably a closed phase-space loop.
    z = 0.16 * np.sin(phase)

    return np.column_stack([x, y, z])


def available_encoders(ffmpeg: str) -> str:
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-encoders"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def choose_h264_encoder(
    ffmpeg: str,
    bitrate: str,
    maxrate: str,
) -> list[str]:
    encoders = available_encoders(ffmpeg)

    if " libx264 " in encoders:
        return [
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "16",
            "-profile:v",
            "high",
        ]

    if " libopenh264 " in encoders:
        return [
            "-c:v",
            "libopenh264",
            "-b:v",
            bitrate,
            "-maxrate",
            maxrate,
        ]

    raise RuntimeError(
        "Nie znaleziono enkodera H.264: libx264 ani libopenh264."
    )


def stream_frames(
    process: subprocess.Popen[bytes],
    points: np.ndarray,
    palette_array: np.ndarray,
    args: argparse.Namespace,
) -> None:
    start_angle = math.radians(args.angle_degrees)
    rotation_angle = math.radians(args.rotation_degrees)
    tilt = math.radians(args.tilt_degrees)
    phone_roll = math.radians(args.phone_roll_degrees)

    assert process.stdin is not None

    try:
        for index in range(args.frames):
            frame = render_frame(
                points,
                index,
                args.frames,
                args.width,
                args.height,
                args.line_thickness,
                args.focus_tail,
                start_angle,
                rotation_angle,
                tilt,
                phone_roll,
            )

            process.stdin.write(palette_array[frame].tobytes())

    finally:
        process.stdin.close()


def write_mp4(
    output: Path,
    points: np.ndarray,
    palette: list[tuple[int, int, int]],
    args: argparse.Namespace,
) -> None:
    ffmpeg = shutil.which("ffmpeg")

    if ffmpeg is None:
        raise RuntimeError("Nie znaleziono ffmpeg.")

    output.parent.mkdir(parents=True, exist_ok=True)

    palette_array = np.array(palette, dtype=np.uint8)
    frame_size = f"{args.width}x{args.height}"

    encoder_args = choose_h264_encoder(
        ffmpeg,
        args.bitrate,
        args.maxrate,
    )

    command = [
        ffmpeg,
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        frame_size,
        "-r",
        str(args.fps),
        "-i",
        "-",
        "-an",
        *encoder_args,
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]

    process = subprocess.Popen(command, stdin=subprocess.PIPE)

    stream_frames(
        process,
        points,
        palette_array,
        args,
    )

    return_code = process.wait()

    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)


def print_palettes() -> None:
    print("Final palettes:")

    for name, stops in FINAL_PALETTE_STOPS.items():
        colors = ["#%02X%02X%02X" % color for color in stops]
        print(f"- {name}: {', '.join(colors)}")

    print("\nFinal backgrounds:")

    for name, color in FINAL_BACKGROUNDS.items():
        print("- %s: #%02X%02X%02X" % (name, *color))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a 9:16 glycolytic limit-cycle MP4."
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "final2",
    )

    parser.add_argument(
        "--palette",
        choices=sorted(FINAL_PALETTE_STOPS),
        default="orchid_gold",
    )

    parser.add_argument(
        "--background",
        choices=sorted(FINAL_BACKGROUNDS),
        default="black",
    )

    parser.add_argument("--all-presets", action="store_true")
    parser.add_argument("--list-colors", action="store_true")

    parser.add_argument("--width", type=int, default=2160)
    parser.add_argument("--height", type=int, default=3840)
    parser.add_argument("--duration", type=float, default=16.0)
    parser.add_argument("--fps", type=int, default=30)

    # Numerical integration
    parser.add_argument("--steps", type=int, default=11000)
    parser.add_argument("--warmup-steps", type=int, default=30000)
    parser.add_argument("--dt", type=float, default=0.006)

    # Selkov oscillator parameters.
    # a=0.08 and b=0.60 produce a clear stable limit cycle.
    parser.add_argument("--selkov-a", type=float, default=0.08)
    parser.add_argument("--selkov-b", type=float, default=0.60)

    parser.add_argument("--initial-substrate", type=float, default=0.10)
    parser.add_argument("--initial-product", type=float, default=0.10)

    # Camera/render settings. Kept close to your Lorenz visual language.
    parser.add_argument("--angle-degrees", type=float, default=180.0)
    parser.add_argument("--rotation-degrees", type=float, default=180.0)
    parser.add_argument("--tilt-degrees", type=float, default=52.0)
    parser.add_argument("--phone-roll-degrees", type=float, default=-90.0)

    parser.add_argument("--line-thickness", type=int, default=2)

    # More than Lorenz, because a closed loop needs enough visible history
    # to read as an orbit rather than as a lone moving worm.
    parser.add_argument("--focus-tail", type=int, default=2400)

    parser.add_argument("--bitrate", default="28M")
    parser.add_argument("--maxrate", default="36M")

    args = parser.parse_args()
    args.frames = max(1, round(args.duration * args.fps))

    return args


def main() -> None:
    args = parse_args()

    if args.list_colors:
        print_palettes()
        return

    raw_points = integrate_selkov(
        steps=args.steps + args.warmup_steps,
        dt=args.dt,
        a=args.selkov_a,
        b=args.selkov_b,
        initial_substrate=args.initial_substrate,
        initial_product=args.initial_product,
    )

    cycle_2d = raw_points[args.warmup_steps :]

    amplitude_substrate = np.ptp(cycle_2d[:, 0])
    amplitude_product = np.ptp(cycle_2d[:, 1])

    if amplitude_substrate < 1e-4 or amplitude_product < 1e-4:
        raise RuntimeError(
            "Trajektoria nie utworzyła wyraźnego cyklu granicznego. "
            "Spróbuj parametrów --selkov-a 0.08 --selkov-b 0.60."
        )

    points_3d = make_3d_phase_portrait(cycle_2d)
    points = normalize_points(points_3d)

    presets = (
        FINAL_PRESETS
        if args.all_presets
        else [(args.palette, args.background)]
    )

    for palette_name, background_name in presets:
        output = args.output_dir / (
            f"glycolytic_limit_cycle_selkov_"
            f"a{args.selkov_a:.2f}_b{args.selkov_b:.2f}_"
            f"{palette_name}_{background_name}_"
            f"{args.width}x{args.height}_"
            f"{args.duration:.0f}s_{args.fps}fps.mp4"
        )

        write_mp4(
            output,
            points,
            build_palette(palette_name, background_name),
            args,
        )

        print(f"Zapisano MP4: {output}")


if __name__ == "__main__":
    main()
