#!/usr/bin/env python3
"""Generate a 9:16 Instagram MP4 of Hopfield memory attractors.

What the animation represents
------------------------------
Each point is a binary Hopfield-network state:

    s_i ∈ {-1, +1}

The network stores several memory patterns. Noisy versions of those
patterns evolve under asynchronous Hopfield updates and converge to
stable attractors.

Visual axes:
    x, y = first two PCA coordinates of neural-state space
    z    = Hopfield energy E(s)

Hopfield energy:
    E(s) = -1/2 * s^T W s

The 3D plot is therefore an embedding of the high-dimensional network
state plus its actual energy. The trajectories descend toward stored
memory attractors.

Dependencies:
    pip install numpy pillow

System dependency:
    ffmpeg
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parents[0]


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


def interpolate_color(
    stops: list[tuple[int, int, int]],
    t: float,
) -> tuple[int, int, int]:
    """Interpolate smoothly through a palette."""

    t = float(np.clip(t, 0.0, 1.0))
    position = t * (len(stops) - 1)

    index = min(int(position), len(stops) - 2)
    local_t = position - index

    start = stops[index]
    end = stops[index + 1]

    return tuple(
        int(start[channel] + (end[channel] - start[channel]) * local_t)
        for channel in range(3)
    )


def attractor_colors(
    palette_name: str,
    n_memories: int,
) -> list[tuple[int, int, int]]:
    """Pick separated colors from the chosen palette.

    Color labels a basin of attraction, not a biological variable.
    """

    stops = FINAL_PALETTE_STOPS[palette_name]

    if n_memories == 1:
        positions = [0.70]
    else:
        positions = np.linspace(0.10, 0.86, n_memories)

    return [
        interpolate_color(stops, float(position))
        for position in positions
    ]


def hopfield_weights(memories: np.ndarray) -> np.ndarray:
    """Build Hebbian Hopfield weights.

    Parameters
    ----------
    memories:
        Matrix with shape:
            (n_memories, n_neurons)

        Each entry must be either -1 or +1.

    Returns
    -------
    W:
        Symmetric weight matrix with zero diagonal.
    """

    n_neurons = memories.shape[1]

    weights = memories.T @ memories
    weights = weights.astype(np.float64) / n_neurons

    np.fill_diagonal(weights, 0.0)

    return weights


def hopfield_energy(
    state: np.ndarray,
    weights: np.ndarray,
) -> float:
    """Classical binary Hopfield energy.

    For asynchronous updates and symmetric W with zero diagonal,
    energy cannot increase.
    """

    return float(-0.5 * state @ weights @ state)


def update_neuron(
    state: np.ndarray,
    weights: np.ndarray,
    neuron_index: int,
) -> bool:
    """Update one neuron asynchronously.

    Returns True when the neuron changed state.
    Ties retain the existing state.
    """

    local_field = float(weights[neuron_index] @ state)

    if local_field > 1e-12:
        new_value = 1.0
    elif local_field < -1e-12:
        new_value = -1.0
    else:
        new_value = state[neuron_index]

    changed = new_value != state[neuron_index]
    state[neuron_index] = new_value

    return changed


def is_fixed_point(
    state: np.ndarray,
    weights: np.ndarray,
) -> bool:
    """Check whether a state is stable under Hopfield updates."""

    for neuron_index in range(len(state)):
        local_field = float(weights[neuron_index] @ state)

        if local_field > 1e-12:
            proposed = 1.0
        elif local_field < -1e-12:
            proposed = -1.0
        else:
            proposed = state[neuron_index]

        if proposed != state[neuron_index]:
            return False

    return True


def make_memories(
    n_neurons: int,
    n_memories: int,
    max_abs_overlap: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate mutually separated stable memory patterns.

    The overlap rule prevents memories from being too similar.
    """

    for _ in range(3000):
        memories = rng.choice(
            np.array([-1.0, 1.0]),
            size=(n_memories, n_neurons),
        )

        overlaps = (memories @ memories.T) / n_neurons
        off_diagonal = overlaps - np.eye(n_memories)

        if np.max(np.abs(off_diagonal)) > max_abs_overlap:
            continue

        weights = hopfield_weights(memories)

        if all(is_fixed_point(memory, weights) for memory in memories):
            return memories, weights

    raise RuntimeError(
        "Nie udało się wygenerować stabilnych wzorców pamięci. "
        "Zwiększ --neurons albo zmniejsz --memories."
    )


def corrupt_memory(
    memory: np.ndarray,
    noise_min: float,
    noise_max: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Flip a random fraction of binary neurons."""

    n_neurons = len(memory)

    min_flips = max(1, math.ceil(noise_min * n_neurons))
    max_flips = max(min_flips, math.floor(noise_max * n_neurons))

    n_flips = int(rng.integers(min_flips, max_flips + 1))

    corrupted = memory.copy()
    flip_indices = rng.choice(
        n_neurons,
        size=n_flips,
        replace=False,
    )

    corrupted[flip_indices] *= -1.0

    return corrupted


def simulate_recall(
    initial_state: np.ndarray,
    weights: np.ndarray,
    max_sweeps: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Run asynchronous Hopfield recall until convergence.

    A trajectory is recorded every time a neuron flips. This makes the
    path reflect genuine discrete state transitions, not a fake smooth
    oscillator pretending to be AI.
    """

    state = initial_state.astype(np.float64).copy()

    states = [state.copy()]
    energies = [hopfield_energy(state, weights)]

    n_neurons = len(state)

    for _ in range(max_sweeps):
        changed_this_sweep = False

        update_order = rng.permutation(n_neurons)

        for neuron_index in update_order:
            changed = update_neuron(
                state,
                weights,
                int(neuron_index),
            )

            if changed:
                changed_this_sweep = True
                states.append(state.copy())
                energies.append(hopfield_energy(state, weights))

        if not changed_this_sweep:
            break
    else:
        raise RuntimeError(
            "Sieć nie osiągnęła stabilnego stanu. "
            "Zwiększ --max-sweeps."
        )

    return (
        np.asarray(states, dtype=np.float64),
        np.asarray(energies, dtype=np.float64),
    )


def build_recall_trajectories(
    memories: np.ndarray,
    weights: np.ndarray,
    traces_per_memory: int,
    noise_min: float,
    noise_max: float,
    max_sweeps: int,
    rng: np.random.Generator,
) -> tuple[list[np.ndarray], list[np.ndarray], list[int]]:
    """Create noisy recall runs that end in their intended memories."""

    trajectories: list[np.ndarray] = []
    energies: list[np.ndarray] = []
    target_indices: list[int] = []

    for target_index, target_memory in enumerate(memories):
        accepted = 0
        attempts = 0

        while accepted < traces_per_memory:
            attempts += 1

            if attempts > 3000:
                raise RuntimeError(
                    "Za dużo prób odzyskania wzorca. "
                    "Zmniejsz poziom szumu albo liczbę pamięci."
                )

            cue = corrupt_memory(
                target_memory,
                noise_min,
                noise_max,
                rng,
            )

            states, state_energies = simulate_recall(
                cue,
                weights,
                max_sweeps,
                rng,
            )

            final_state = states[-1]

            if np.array_equal(final_state, target_memory):
                trajectories.append(states)
                energies.append(state_energies)
                target_indices.append(target_index)
                accepted += 1

    return trajectories, energies, target_indices


def pca_embedding(
    trajectories: list[np.ndarray],
    trajectory_energies: list[np.ndarray],
    memories: np.ndarray,
    weights: np.ndarray,
) -> tuple[list[np.ndarray], np.ndarray]:
    """Embed trajectories in (PC1, PC2, energy) coordinates.

    PC1 and PC2 preserve as much geometry of neural-state space as a
    two-dimensional projection can preserve. The vertical coordinate is
    actual Hopfield energy.

    This is not a literal 3D landscape of all possible states.
    A 24-neuron Hopfield network has 2^24 possible binary states,
    because apparently mathematics was not content with merely making
    people suffer in linear algebra.
    """

    all_states = np.vstack(
        [*trajectories, memories]
    )

    mean_state = np.mean(all_states, axis=0)
    centered = all_states - mean_state

    _, _, right_vectors = np.linalg.svd(
        centered,
        full_matrices=False,
    )

    pca_basis = right_vectors[:2].T

    all_xy = centered @ pca_basis

    xy_min = np.min(all_xy, axis=0)
    xy_max = np.max(all_xy, axis=0)
    xy_center = 0.5 * (xy_min + xy_max)

    xy_span = max(
        float(np.ptp(all_xy[:, 0])),
        float(np.ptp(all_xy[:, 1])),
        1e-9,
    )

    all_energies = np.concatenate(
        [
            *trajectory_energies,
            np.array(
                [
                    hopfield_energy(memory, weights)
                    for memory in memories
                ]
            ),
        ]
    )

    energy_min = float(np.min(all_energies))
    energy_max = float(np.max(all_energies))
    energy_span = max(energy_max - energy_min, 1e-9)

    def embed(
        states: np.ndarray,
        energies: np.ndarray,
    ) -> np.ndarray:
        xy = (states - mean_state) @ pca_basis
        xy = (xy - xy_center) / xy_span * 2.15

        z = (energies - energy_min) / energy_span * 1.45

        return np.column_stack(
            [
                xy[:, 0],
                xy[:, 1],
                z,
            ]
        )

    embedded_trajectories = [
        embed(states, state_energies)
        for states, state_energies in zip(
            trajectories,
            trajectory_energies,
        )
    ]

    memory_energies = np.array(
        [
            hopfield_energy(memory, weights)
            for memory in memories
        ]
    )

    embedded_memories = embed(
        memories,
        memory_energies,
    )

    return embedded_trajectories, embedded_memories


def resample_polyline(
    points: np.ndarray,
    n_samples: int,
) -> np.ndarray:
    """Resample a trajectory at equal visual distances.

    Hopfield updates are discrete jumps. Interpolation is used only to
    make the drawn line visually continuous between genuine network
    states. It does not change the underlying dynamics.
    """

    if len(points) == 1:
        return np.repeat(points, n_samples, axis=0)

    segment_lengths = np.linalg.norm(
        np.diff(points, axis=0),
        axis=1,
    )

    cumulative = np.concatenate(
        [
            [0.0],
            np.cumsum(segment_lengths),
        ]
    )

    total_length = float(cumulative[-1])

    if total_length < 1e-12:
        return np.repeat(points[:1], n_samples, axis=0)

    targets = np.linspace(
        0.0,
        total_length,
        n_samples,
    )

    resampled = np.empty(
        (n_samples, points.shape[1]),
        dtype=np.float64,
    )

    for dimension in range(points.shape[1]):
        resampled[:, dimension] = np.interp(
            targets,
            cumulative,
            points[:, dimension],
        )

    return resampled


def project_points(
    points: np.ndarray,
    width: int,
    height: int,
    yaw_degrees: float,
    pitch_degrees: float,
    view_scale: float,
    perspective_strength: float,
) -> np.ndarray:
    """Project 3D embedding coordinates to the 2D video frame."""

    yaw = math.radians(yaw_degrees)
    pitch = math.radians(pitch_degrees)

    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2] - 0.55

    cos_yaw = math.cos(yaw)
    sin_yaw = math.sin(yaw)

    x_rot = cos_yaw * x - sin_yaw * y
    y_rot = sin_yaw * x + cos_yaw * y

    cos_pitch = math.cos(pitch)
    sin_pitch = math.sin(pitch)

    # Positive energy rises visually in the rendered composition.
    y_tilt = cos_pitch * y_rot + sin_pitch * z
    z_tilt = -sin_pitch * y_rot + cos_pitch * z

    depth = 1.0 / np.clip(
        1.0 + perspective_strength * z_tilt,
        0.25,
        None,
    )

    scale_pixels = view_scale * min(width, height)

    screen_x = width * 0.50 + x_rot * depth * scale_pixels
    screen_y = height * 0.54 - y_tilt * depth * scale_pixels

    return np.column_stack(
        [
            screen_x,
            screen_y,
        ]
    )


def to_draw_points(points: np.ndarray) -> list[tuple[int, int]]:
    """Convert floating projected coordinates into PIL-ready points."""

    return [
        (int(round(x)), int(round(y)))
        for x, y in points
    ]


def draw_node(
    draw: ImageDraw.ImageDraw,
    position: np.ndarray,
    color: tuple[int, int, int],
    radius: int,
    pulse: float,
) -> None:
    """Draw a stable Hopfield-memory attractor."""

    x = int(round(position[0]))
    y = int(round(position[1]))

    halo_radius = int(radius * (2.4 + 0.35 * pulse))
    outer_radius = int(radius * (1.35 + 0.10 * pulse))

    draw.ellipse(
        (
            x - halo_radius,
            y - halo_radius,
            x + halo_radius,
            y + halo_radius,
        ),
        fill=(*color, 38),
    )

    draw.ellipse(
        (
            x - outer_radius,
            y - outer_radius,
            x + outer_radius,
            y + outer_radius,
        ),
        fill=(*color, 190),
    )

    draw.ellipse(
        (
            x - radius,
            y - radius,
            x + radius,
            y + radius,
        ),
        fill=(255, 255, 255, 245),
    )


def make_base_frame(
    width: int,
    height: int,
    background: tuple[int, int, int],
    projected_trajectories: list[np.ndarray],
    projected_memories: np.ndarray,
    trajectory_targets: list[int],
    colors: list[tuple[int, int, int]],
    line_width: int,
    node_radius: int,
) -> Image.Image:
    """Build a static faint map of possible recall trajectories."""

    base = Image.new(
        "RGBA",
        (width, height),
        (*background, 255),
    )

    draw = ImageDraw.Draw(base, "RGBA")

    for trajectory, target_index in zip(
        projected_trajectories,
        trajectory_targets,
    ):
        color = colors[target_index]

        draw.line(
            to_draw_points(trajectory),
            fill=(*color, 30),
            width=max(1, line_width),
            joint="curve",
        )

    for memory_index, position in enumerate(projected_memories):
        draw_node(
            draw,
            position,
            colors[memory_index],
            node_radius,
            pulse=0.0,
        )

    return base


def render_frame(
    base_frame: Image.Image,
    projected_trajectories: list[np.ndarray],
    projected_memories: np.ndarray,
    trajectory_targets: list[int],
    colors: list[tuple[int, int, int]],
    frame_index: int,
    n_frames: int,
    line_width: int,
    node_radius: int,
    stagger_fraction: float,
    motion_fraction: float,
) -> Image.Image:
    """Draw the currently visible descent of every noisy cue."""

    frame = base_frame.copy()
    draw = ImageDraw.Draw(frame, "RGBA")

    global_progress = (
        frame_index / max(n_frames - 1, 1)
    )

    n_trajectories = len(projected_trajectories)

    for trajectory_index, (
        trajectory,
        target_index,
    ) in enumerate(
        zip(
            projected_trajectories,
            trajectory_targets,
        )
    ):
        if n_trajectories == 1:
            start_offset = 0.0
        else:
            start_offset = (
                trajectory_index
                / (n_trajectories - 1)
                * stagger_fraction
            )

        local_progress = (
            global_progress - start_offset
        ) / max(motion_fraction, 1e-9)

        local_progress = float(
            np.clip(local_progress, 0.0, 1.0)
        )

        visible_count = max(
            1,
            int(
                round(
                    1
                    + local_progress
                    * (len(trajectory) - 1)
                )
            ),
        )

        visible = trajectory[:visible_count]
        color = colors[target_index]

        if len(visible) >= 2:
            points = to_draw_points(visible)

            draw.line(
                points,
                fill=(*color, 62),
                width=max(2, line_width * 4),
                joint="curve",
            )

            draw.line(
                points,
                fill=(*color, 235),
                width=max(1, line_width),
                joint="curve",
            )

        head = visible[-1]

        head_x = int(round(head[0]))
        head_y = int(round(head[1]))

        head_radius = max(3, int(node_radius * 0.70))

        draw.ellipse(
            (
                head_x - head_radius * 2,
                head_y - head_radius * 2,
                head_x + head_radius * 2,
                head_y + head_radius * 2,
            ),
            fill=(*color, 55),
        )

        draw.ellipse(
            (
                head_x - head_radius,
                head_y - head_radius,
                head_x + head_radius,
                head_y + head_radius,
            ),
            fill=(255, 255, 255, 245),
        )

    pulse = 0.5 + 0.5 * math.sin(
        frame_index / max(n_frames - 1, 1) * 2.0 * math.pi
    )

    for memory_index, position in enumerate(projected_memories):
        draw_node(
            draw,
            position,
            colors[memory_index],
            node_radius,
            pulse,
        )

    return frame


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
        "Nie znaleziono enkodera H.264: "
        "libx264 ani libopenh264."
    )


def write_mp4(
    output: Path,
    base_frame: Image.Image,
    projected_trajectories: list[np.ndarray],
    projected_memories: np.ndarray,
    trajectory_targets: list[int],
    colors: list[tuple[int, int, int]],
    args: argparse.Namespace,
) -> None:
    """Render all frames and pipe RGB video directly into ffmpeg."""

    ffmpeg = shutil.which("ffmpeg")

    if ffmpeg is None:
        raise RuntimeError("Nie znaleziono ffmpeg.")

    output.parent.mkdir(parents=True, exist_ok=True)

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

    assert process.stdin is not None

    try:
        for frame_index in range(args.frames):
            frame = render_frame(
                base_frame=base_frame,
                projected_trajectories=projected_trajectories,
                projected_memories=projected_memories,
                trajectory_targets=trajectory_targets,
                colors=colors,
                frame_index=frame_index,
                n_frames=args.frames,
                line_width=args.line_width_pixels,
                node_radius=args.node_radius_pixels,
                stagger_fraction=args.stagger_fraction,
                motion_fraction=args.motion_fraction,
            )

            process.stdin.write(
                frame.convert("RGB").tobytes()
            )
    finally:
        process.stdin.close()

    return_code = process.wait()

    if return_code != 0:
        raise subprocess.CalledProcessError(
            return_code,
            command,
        )


def save_trajectories(
    output_dir: Path,
    trajectories: list[np.ndarray],
    trajectory_energies: list[np.ndarray],
    trajectory_targets: list[int],
    memories: np.ndarray,
    weights: np.ndarray,
) -> None:
    """Save exact states and energies used in the animation."""

    output_dir.mkdir(parents=True, exist_ok=True)

    np.save(
        output_dir / "hopfield_memories.npy",
        memories,
    )

    np.save(
        output_dir / "hopfield_weights.npy",
        weights,
    )

    for index, (
        states,
        energies,
        target_index,
    ) in enumerate(
        zip(
            trajectories,
            trajectory_energies,
            trajectory_targets,
        )
    ):
        matrix = np.column_stack(
            [
                np.arange(len(states)),
                energies,
                states,
            ]
        )

        header = (
            "step,energy,"
            + ",".join(
                f"neuron_{i + 1}"
                for i in range(states.shape[1])
            )
            + f"\nTarget memory index: {target_index}"
        )

        np.savetxt(
            output_dir / f"trajectory_{index:02d}.csv",
            matrix,
            delimiter=",",
            header=header,
            comments="",
            fmt="%.8f",
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
            "Create a 9:16 MP4 showing Hopfield-memory attractors "
            "and noisy recall trajectories."
        )
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "final4",
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
        "--save-trajectories",
        action="store_true",
        help=(
            "Zapisz stany neuronów i energię "
            "dla każdej trajektorii jako CSV."
        ),
    )

    parser.add_argument("--width", type=int, default=2160)
    parser.add_argument("--height", type=int, default=3840)
    parser.add_argument("--duration", type=float, default=16.0)
    parser.add_argument("--fps", type=int, default=30)

    parser.add_argument(
        "--neurons",
        type=int,
        default=24,
        help="Liczba neuronów binarnych w sieci.",
    )

    parser.add_argument(
        "--memories",
        type=int,
        default=3,
        help="Liczba zapamiętanych wzorców i atraktorów.",
    )

    parser.add_argument(
        "--traces-per-memory",
        type=int,
        default=4,
        help="Liczba zaszumionych trajektorii dla jednego atraktora.",
    )

    parser.add_argument(
        "--max-abs-overlap",
        type=float,
        default=0.25,
        help=(
            "Maksymalna bezwzględna korelacja między pamięciami. "
            "Mniej = bardziej odseparowane atraktory."
        ),
    )

    parser.add_argument(
        "--noise-min",
        type=float,
        default=0.20,
        help="Minimalna frakcja odwróconych neuronów w cue.",
    )

    parser.add_argument(
        "--noise-max",
        type=float,
        default=0.35,
        help="Maksymalna frakcja odwróconych neuronów w cue.",
    )

    parser.add_argument(
        "--max-sweeps",
        type=int,
        default=40,
        help="Maksymalna liczba pełnych rund aktualizacji neuronów.",
    )

    parser.add_argument(
        "--visual-samples",
        type=int,
        default=180,
        help=(
            "Liczba punktów renderowanych na trajektorię. "
            "To wygładza wyłącznie obraz, nie dynamikę."
        ),
    )

    parser.add_argument(
        "--yaw-degrees",
        type=float,
        default=-34.0,
    )

    parser.add_argument(
        "--pitch-degrees",
        type=float,
        default=56.0,
    )

    parser.add_argument(
        "--view-scale",
        type=float,
        default=0.37,
    )

    parser.add_argument(
        "--perspective-strength",
        type=float,
        default=0.18,
    )

    parser.add_argument(
        "--line-thickness",
        type=int,
        default=3,
        help="Grubość linii dla finalnego 2160 px width.",
    )

    parser.add_argument(
        "--node-radius",
        type=int,
        default=10,
        help="Promień markera atraktora dla finalnego 2160 px width.",
    )

    parser.add_argument(
        "--stagger-fraction",
        type=float,
        default=0.18,
        help="Jak bardzo kolejne trajektorie startują z przesunięciem.",
    )

    parser.add_argument(
        "--motion-fraction",
        type=float,
        default=0.74,
        help=(
            "Część filmu przeznaczona na dojście do atraktora. "
            "Reszta utrzymuje stabilne minima."
        ),
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=20260703,
        help="Seed zapewniający powtarzalną kompozycję.",
    )

    parser.add_argument("--bitrate", default="28M")
    parser.add_argument("--maxrate", default="36M")

    args = parser.parse_args()

    args.frames = max(
        1,
        round(args.duration * args.fps),
    )

    render_scale = args.width / 2160.0

    args.line_width_pixels = max(
        1,
        round(args.line_thickness * render_scale),
    )

    args.node_radius_pixels = max(
        3,
        round(args.node_radius * render_scale),
    )

    if args.memories < 1:
        parser.error("--memories musi być co najmniej 1.")

    if args.neurons < 6:
        parser.error(
            "--neurons powinno mieć co najmniej 6."
        )

    if args.noise_min <= 0:
        parser.error("--noise-min musi być większe od 0.")

    if args.noise_max < args.noise_min:
        parser.error(
            "--noise-max musi być większe lub równe --noise-min."
        )

    return args


def main() -> None:
    args = parse_args()

    if args.list_colors:
        print_palettes()
        return

    rng = np.random.default_rng(args.seed)

    memories, weights = make_memories(
        n_neurons=args.neurons,
        n_memories=args.memories,
        max_abs_overlap=args.max_abs_overlap,
        rng=rng,
    )

    trajectories, trajectory_energies, trajectory_targets = (
        build_recall_trajectories(
            memories=memories,
            weights=weights,
            traces_per_memory=args.traces_per_memory,
            noise_min=args.noise_min,
            noise_max=args.noise_max,
            max_sweeps=args.max_sweeps,
            rng=rng,
        )
    )

    embedded_trajectories, embedded_memories = pca_embedding(
        trajectories=trajectories,
        trajectory_energies=trajectory_energies,
        memories=memories,
        weights=weights,
    )

    visual_trajectories = [
        resample_polyline(
            trajectory,
            args.visual_samples,
        )
        for trajectory in embedded_trajectories
    ]

    projected_trajectories = [
        project_points(
            trajectory,
            width=args.width,
            height=args.height,
            yaw_degrees=args.yaw_degrees,
            pitch_degrees=args.pitch_degrees,
            view_scale=args.view_scale,
            perspective_strength=args.perspective_strength,
        )
        for trajectory in visual_trajectories
    ]

    projected_memories = project_points(
        embedded_memories,
        width=args.width,
        height=args.height,
        yaw_degrees=args.yaw_degrees,
        pitch_degrees=args.pitch_degrees,
        view_scale=args.view_scale,
        perspective_strength=args.perspective_strength,
    )

    presets = (
        FINAL_PRESETS
        if args.all_presets
        else [(args.palette, args.background)]
    )

    for palette_name, background_name in presets:
        colors = attractor_colors(
            palette_name,
            args.memories,
        )

        base_frame = make_base_frame(
            width=args.width,
            height=args.height,
            background=FINAL_BACKGROUNDS[background_name],
            projected_trajectories=projected_trajectories,
            projected_memories=projected_memories,
            trajectory_targets=trajectory_targets,
            colors=colors,
            line_width=args.line_width_pixels,
            node_radius=args.node_radius_pixels,
        )

        stem = (
            f"hopfield_attractors_"
            f"n{args.neurons}_"
            f"m{args.memories}_"
            f"seed{args.seed}_"
            f"{palette_name}_"
            f"{background_name}_"
            f"{args.width}x{args.height}_"
            f"{args.duration:.0f}s_"
            f"{args.fps}fps"
        )

        output_mp4 = args.output_dir / f"{stem}.mp4"

        write_mp4(
            output=output_mp4,
            base_frame=base_frame,
            projected_trajectories=projected_trajectories,
            projected_memories=projected_memories,
            trajectory_targets=trajectory_targets,
            colors=colors,
            args=args,
        )

        print(f"Zapisano MP4: {output_mp4}")

        if args.save_trajectories:
            data_dir = args.output_dir / f"{stem}_data"

            save_trajectories(
                output_dir=data_dir,
                trajectories=trajectories,
                trajectory_energies=trajectory_energies,
                trajectory_targets=trajectory_targets,
                memories=memories,
                weights=weights,
            )

            print(f"Zapisano dane modelu: {data_dir}")


if __name__ == "__main__":
    main()
