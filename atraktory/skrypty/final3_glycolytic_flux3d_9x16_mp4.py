#!/usr/bin/env python3
"""Generate a 9:16 MP4 of a glycolytic Selkov limit cycle.

The trajectory is shown in a biologically meaningful 3D embedding:

    x = S                  reduced substrate concentration
    y = P                  reduced product/regulator concentration
    z = v(S, P)            metabolic reaction flux

Selkov model:
    dS/dt = -S + a*P + S^2*P
    dP/dt =  b - a*P - S^2*P

Reaction flux:
    v(S, P) = a*P + S^2*P

The animation deliberately DOES NOT remove the transient. It starts
outside the final orbit, then converges toward the stable limit cycle.
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

# Reuse your existing 3D camera/path renderer.
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
    """Build the same 256-color palette structure as your Lorenz script."""

    palette = [FINAL_BACKGROUNDS[background_name]]
    stops = FINAL_PALETTE_STOPS[palette_name]

    for i in range(255):
        t = i / 254.0

        segment = min(
            int(t * (len(stops) - 1)),
            len(stops) - 2,
        )

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


def reaction_flux(
    substrate: np.ndarray | float,
    product: np.ndarray | float,
    a: float,
) -> np.ndarray | float:
    """Selkov metabolic flux.

    v(S, P) = aP + S²P

    This is the rate that converts the current state of the system
    into metabolic flow through the simplified reaction.
    """

    return a * product + substrate**2 * product


def selkov_derivatives(
    state: np.ndarray,
    a: float,
    b: float,
) -> np.ndarray:
    """Compute the Selkov glycolytic oscillator derivatives."""

    substrate, product = state

    flux = reaction_flux(substrate, product, a)

    d_substrate = -substrate + flux
    d_product = b - flux

    return np.array(
        [d_substrate, d_product],
        dtype=np.float64,
    )


def integrate_selkov(
    steps: int,
    dt: float,
    a: float,
    b: float,
    initial_substrate: float,
    initial_product: float,
) -> np.ndarray:
    """Integrate the Selkov system using 4th-order Runge-Kutta."""

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

        state = state + (dt / 6.0) * (
            k1 + 2.0 * k2 + 2.0 * k3 + k4
        )

        if not np.all(np.isfinite(state)):
            raise RuntimeError(
                "Integracja numeryczna stała się niestabilna. "
                "Spróbuj zmniejszyć --dt."
            )

        if np.any(state < -1e-10):
            raise RuntimeError(
                "Model osiągnął ujemne stężenie. "
                "Spróbuj innych warunków początkowych albo parametrów."
            )

    return points


def make_flux_3d_trajectory(
    points_2d: np.ndarray,
    a: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Create a real 3D phase-space trajectory.

    Coordinates before display normalization:
        x = substrate
        y = product
        z = flux

    z is not decorative depth. It is the actual reaction flux derived
    from the same Selkov equations used for the trajectory.
    """

    substrate = points_2d[:, 0]
    product = points_2d[:, 1]

    flux = reaction_flux(substrate, product, a)

    points_3d = np.column_stack(
        [
            substrate,
            product,
            flux,
        ]
    )

    return points_3d, flux


def save_trajectory_csv(
    output: Path,
    points_2d: np.ndarray,
    flux: np.ndarray,
    dt: float,
) -> None:
    """Save the actual biological trajectory used in the MP4."""

    time = np.arange(len(points_2d), dtype=np.float64) * dt

    data = np.column_stack(
        [
            time,
            points_2d[:, 0],
            points_2d[:, 1],
            flux,
        ]
    )

    np.savetxt(
        output,
        data,
        delimiter=",",
        header="time,reduced_substrate_S,reduced_product_P,metabolic_flux_v",
        comments="",
        fmt="%.10f",
    )


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
    """Render all frames and stream them directly to ffmpeg."""

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

            process.stdin.write(
                palette_array[frame].tobytes()
            )

    finally:
        process.stdin.close()


def write_mp4(
    output: Path,
    points: np.ndarray,
    palette: list[tuple[int, int, int]],
    args: argparse.Namespace,
) -> None:
    """Encode rendered raw RGB frames to Instagram-compatible H.264 MP4."""

    ffmpeg = shutil.which("ffmpeg")

    if ffmpeg is None:
        raise RuntimeError("Nie znaleziono ffmpeg.")

    output.parent.mkdir(parents=True, exist_ok=True)

    palette_array = np.array(
        palette,
        dtype=np.uint8,
    )

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
        f"{args.width}x{args.height}",
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

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
    )

    stream_frames(
        process,
        points,
        palette_array,
        args,
    )

    return_code = process.wait()

    if return_code != 0:
        raise subprocess.CalledProcessError(
            return_code,
            command,
        )


def print_palettes() -> None:
    print("Palety:")

    for name, stops in FINAL_PALETTE_STOPS.items():
        colors = [
            "#%02X%02X%02X" % color
            for color in stops
        ]
        print(f"- {name}: {', '.join(colors)}")

    print("\nTła:")

    for name, color in FINAL_BACKGROUNDS.items():
        print(
            "- %s: #%02X%02X%02X"
            % (name, *color)
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a 9:16 MP4 of a Selkov glycolytic limit cycle "
            "embedded in (S, P, flux) phase space."
        )
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "final3",
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

    parser.add_argument(
        "--all-presets",
        action="store_true",
    )

    parser.add_argument(
        "--list-colors",
        action="store_true",
    )

    parser.add_argument(
        "--save-trajectory",
        action="store_true",
        help="Save time, S, P and flux as CSV next to the MP4.",
    )

    parser.add_argument("--width", type=int, default=2160)
    parser.add_argument("--height", type=int, default=3840)
    parser.add_argument("--duration", type=float, default=16.0)
    parser.add_argument("--fps", type=int, default=30)

    # Numerical integration.
    # The transient is intentionally retained.
    parser.add_argument("--steps", type=int, default=14000)
    parser.add_argument("--dt", type=float, default=0.005)

    # Selkov parameters. This pair gives a clear stable oscillatory regime.
    parser.add_argument("--selkov-a", type=float, default=0.08)
    parser.add_argument("--selkov-b", type=float, default=0.60)

    # Start clearly away from the final limit cycle.
    parser.add_argument(
        "--initial-substrate",
        type=float,
        default=0.10,
    )

    parser.add_argument(
        "--initial-product",
        type=float,
        default=0.10,
    )

    # Kept close to your Lorenz visual language, but with a slightly
    # lower tilt so the flux dimension can actually be seen.
    parser.add_argument(
        "--angle-degrees",
        type=float,
        default=180.0,
    )

    parser.add_argument(
        "--rotation-degrees",
        type=float,
        default=180.0,
    )

    parser.add_argument(
        "--tilt-degrees",
        type=float,
        default=46.0,
    )

    parser.add_argument(
        "--phone-roll-degrees",
        type=float,
        default=-90.0,
    )

    parser.add_argument(
        "--line-thickness",
        type=int,
        default=2,
    )

    # 0 means retain the whole path, including the approach to the cycle.
    parser.add_argument(
        "--focus-tail",
        type=int,
        default=0,
    )

    parser.add_argument("--bitrate", default="28M")
    parser.add_argument("--maxrate", default="36M")

    args = parser.parse_args()

    args.frames = max(
        1,
        round(args.duration * args.fps),
    )

    if args.focus_tail <= 0:
        args.focus_tail = args.steps

    return args


def main() -> None:
    args = parse_args()

    if args.list_colors:
        print_palettes()
        return

    # No warm-up removal here. The beginning of the animation is the
    # transient that visibly approaches the final stable orbit.
    raw_points_2d = integrate_selkov(
        steps=args.steps,
        dt=args.dt,
        a=args.selkov_a,
        b=args.selkov_b,
        initial_substrate=args.initial_substrate,
        initial_product=args.initial_product,
    )

    points_3d_raw, flux = make_flux_3d_trajectory(
        raw_points_2d,
        args.selkov_a,
    )

    # Simple guards against accidentally rendering a near-static model.
    if np.ptp(raw_points_2d[:, 0]) < 1e-4:
        raise RuntimeError(
            "Substrat prawie się nie zmienia. "
            "Model nie utworzył widocznej dynamiki."
        )

    if np.ptp(raw_points_2d[:, 1]) < 1e-4:
        raise RuntimeError(
            "Produkt prawie się nie zmienia. "
            "Model nie utworzył widocznej dynamiki."
        )

    if np.ptp(flux) < 1e-4:
        raise RuntimeError(
            "Flux prawie się nie zmienia. "
            "Sprawdź parametry modelu."
        )

    # This only rescales coordinates for the renderer.
    # It does not alter which biological quantity defines each axis.
    points_for_render = normalize_points(points_3d_raw)

    presets = (
        FINAL_PRESETS
        if args.all_presets
        else [(args.palette, args.background)]
    )

    for palette_name, background_name in presets:
        stem = (
            f"glycolytic_selkov_flux3d_"
            f"a{args.selkov_a:.2f}_"
            f"b{args.selkov_b:.2f}_"
            f"{palette_name}_"
            f"{background_name}_"
            f"{args.width}x{args.height}_"
            f"{args.duration:.0f}s_"
            f"{args.fps}fps"
        )

        output_mp4 = args.output_dir / f"{stem}.mp4"

        write_mp4(
            output_mp4,
            points_for_render,
            build_palette(
                palette_name,
                background_name,
            ),
            args,
        )

        print(f"Zapisano MP4: {output_mp4}")

        if args.save_trajectory:
            output_csv = args.output_dir / f"{stem}.csv"

            save_trajectory_csv(
                output_csv,
                raw_points_2d,
                flux,
                args.dt,
            )

            print(f"Zapisano trajektorię: {output_csv}")


if __name__ == "__main__":
    main()
