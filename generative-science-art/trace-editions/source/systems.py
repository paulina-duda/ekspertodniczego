#!/usr/bin/env python3
"""Attractor integration that produces continuous traces, not sample clouds.

The earlier emergence project splats one point per integration step. Measured at
the shipped framing, consecutive steps land 3 to 4 pixels apart on Lorenz and up
to 20 in the fast outer excursions, so every individual trajectory is drawn as a
dotted trail. The picture only looks continuous because twelve hundred of them
overlap -- which is why it reads as accumulating density rather than as lines
being drawn.

Here each segment is subdivided until successive splats land about a pixel
apart, so a trajectory is a genuine unbroken filament. That costs samples, so
far fewer trajectories are integrated; the point is to see individual strands
and the bands they braid into, not to bury them.
"""

from __future__ import annotations

import math

import numpy as np


def _lorenz(state: np.ndarray) -> np.ndarray:
    x, y, z = state[:, 0], state[:, 1], state[:, 2]
    return np.column_stack((10.0 * (y - x), x * (28.0 - z) - y, x * y - (8.0 / 3.0) * z))


def _halvorsen(state: np.ndarray, alpha: float = 1.4) -> np.ndarray:
    x, y, z = state[:, 0], state[:, 1], state[:, 2]
    return np.column_stack((
        -alpha * x - 4.0 * y - 4.0 * z - y * y,
        -alpha * y - 4.0 * z - 4.0 * x - z * z,
        -alpha * z - 4.0 * x - 4.0 * y - x * x,
    ))


def _aizawa(state: np.ndarray) -> np.ndarray:
    x, y, z = state[:, 0], state[:, 1], state[:, 2]
    a, b, c, d, e, f = 0.95, 0.7, 0.6, 3.5, 0.25, 0.1
    return np.column_stack((
        (z - b) * x - d * y,
        d * x + (z - b) * y,
        c + a * z - z**3 / 3.0 - (x * x + y * y) * (1.0 + e * z) + f * z * x**3,
    ))


FLOWS = {"lorenz": _lorenz, "halvorsen": _halvorsen, "aizawa": _aizawa}

SEEDS = {"lorenz": (0.1, 0.0, 0.0), "halvorsen": (1.0, 0.0, 0.0), "aizawa": (0.1, 0.0, 0.0)}

STEP_SIZES = {"lorenz": 0.0035, "halvorsen": 0.0035, "aizawa": 0.006}

# Which model axis points up the screen. Lorenz and Aizawa are far taller in z
# than they are wide, so standing them on that axis fills a 9:16 frame.
UP_AXIS = {"lorenz": (0, 2, 1), "halvorsen": (0, 2, 1), "aizawa": (0, 2, 1)}

# Radius of a thin cylinder around the vertical axis whose samples are discarded.
# Aizawa's z-axis is invariant -- x = y = 0 gives dx/dt = dy/dt = 0 -- and a slow
# near-axis orbit otherwise piles half a percent of all samples onto one radius,
# drawing a hairline straight down the middle of the frame.
AXIS_CUT = {"aizawa": 0.035}

# The sampling the luminous editions use, kept only as the reference for colour.
LUMINOUS_SAMPLING = {"trajectories": 1200, "steps": 3800, "warmup": 1400, "spread": 0.55}


def _integrate(
    name: str, trajectories: int, steps: int, warmup: int, spread: float, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    """Vectorised RK4 over a cloud of trajectories; returns positions and speeds."""
    derivative = FLOWS[name]
    step = STEP_SIZES[name]
    generator = np.random.default_rng(seed)
    state = np.asarray(SEEDS[name], dtype=np.float64)[None, :] + spread * generator.standard_normal(
        (trajectories, 3)
    )

    def advance(current: np.ndarray) -> np.ndarray:
        k1 = derivative(current)
        k2 = derivative(current + 0.5 * step * k1)
        k3 = derivative(current + 0.5 * step * k2)
        k4 = derivative(current + step * k3)
        return current + (step / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

    for _ in range(warmup):
        state = advance(state)

    points = np.empty((steps, trajectories, 3), dtype=np.float32)
    speeds = np.empty((steps, trajectories), dtype=np.float32)
    for index in range(steps):
        speeds[index] = np.linalg.norm(derivative(state), axis=1)
        points[index] = state
        state = advance(state)
    return points, speeds


def reference_speed_range(name: str, seed: int = 20260731) -> tuple[float, float]:
    """Speed bounds as the luminous editions compute them.

    Colour follows speed, and speed is normalised against the sample population,
    so a run with different parameters maps the same physical speed onto a
    different part of the palette. Borrowing these bounds is what keeps the
    traces the same colour as the editions they belong to.

    Deliberately the full luminous configuration rather than a cheap
    approximation: a short run does not converge for Lorenz, whose heavy speed
    tail comes out at 52 instead of 182 while the trajectories are still
    clustered.
    """
    _, speeds = _integrate(name, seed=seed, **LUMINOUS_SAMPLING)
    low, high = np.percentile(speeds.reshape(-1), (2, 98))
    return float(low), float(high)


def _subdivide(
    points: np.ndarray,
    speeds: np.ndarray,
    ages: np.ndarray,
    target_length: float,
    limit: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Split each step into enough pieces that successive splats nearly touch.

    Counts vary per segment -- a slow stretch needs one piece, a fast excursion
    twenty -- so the result cannot keep the step-major grid. It is sorted by age
    afterwards instead, which the renderer needs anyway: with ages ascending, the
    samples drawn by a given moment are a prefix, findable by binary search.
    """
    delta = points[1:] - points[:-1]
    lengths = np.linalg.norm(delta, axis=2)
    counts = np.clip(np.ceil(lengths / max(target_length, 1e-9)), 1, limit).astype(np.int64)

    flat_counts = counts.reshape(-1)
    total = int(flat_counts.sum())
    segment = np.repeat(np.arange(flat_counts.size, dtype=np.int64), flat_counts)

    starts = np.zeros(flat_counts.size + 1, dtype=np.int64)
    np.cumsum(flat_counts, out=starts[1:])
    within = np.arange(total, dtype=np.int64) - starts[segment]
    fraction = (within / flat_counts[segment]).astype(np.float32)

    head_points = points[:-1].reshape(-1, 3)
    sub_points = head_points[segment] + fraction[:, None] * delta.reshape(-1, 3)[segment]

    def interpolate(values: np.ndarray) -> np.ndarray:
        head = values[:-1].reshape(-1)[segment]
        tail = values[1:].reshape(-1)[segment]
        return head + fraction * (tail - head)

    sub_speeds = interpolate(speeds)
    sub_ages = interpolate(ages)

    order = np.argsort(sub_ages, kind="stable")
    return sub_points[order], sub_speeds[order], sub_ages[order]


def sample_traces(
    name: str,
    trajectories: int = 300,
    steps: int = 9000,
    warmup: int = 1400,
    spread: float = 0.02,
    seed: int = 20260731,
    pixels_per_radius: float = 520.0,
    subdivision_limit: int = 24,
    speed_range: tuple[float, float] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Integrate trajectories and return them as continuous, age-ordered traces.

    With a small `spread` and a warm-up the trajectories start together and
    already on the attractor, so the opening seconds show one strand and the
    growth is chaos pulling them apart. Starting off the attractor instead sends
    a very fast transient across the frame, and since colour follows speed that
    transient arrives violet.
    """
    points, speeds = _integrate(name, trajectories, steps, warmup, spread, seed)
    ages = np.repeat(
        np.linspace(0.0, 1.0, steps, dtype=np.float32)[:, None], trajectories, axis=1
    )

    # Drop whole trajectories that went non-finite or parked on a fixed point.
    # Filtering by column keeps the grid that subdivision needs; a NaN fails the
    # comparison and is dropped with them.
    travel = np.linalg.norm(np.ptp(points, axis=0), axis=1)
    alive = travel > 0.05 * np.median(travel[np.isfinite(travel)])
    points, speeds, ages = points[:, alive], speeds[:, alive], ages[:, alive]

    points = points[:, :, UP_AXIS[name]]

    # Subdivide towards one pixel. The scale is derived from the cloud itself --
    # its radius maps to `pixels_per_radius` on screen -- so this stays correct
    # without the renderer having to hand back its projection scale.
    centred = points - np.percentile(points.reshape(-1, 3), 50.0, axis=0)
    radius = float(np.percentile(np.linalg.norm(centred.reshape(-1, 3)[:, ::2], axis=1), 99.7))
    points, speeds, ages = _subdivide(
        points, speeds, ages, radius / max(pixels_per_radius, 1.0), subdivision_limit
    )

    finite = np.isfinite(points).all(axis=1) & np.isfinite(speeds)
    points, speeds, ages = points[finite], speeds[finite], ages[finite]

    cut = AXIS_CUT.get(name, 0.0)
    if cut:
        kept = np.hypot(points[:, 0], points[:, 2]) >= cut
        points, speeds, ages = points[kept], speeds[kept], ages[kept]

    low, high = speed_range if speed_range is not None else np.percentile(speeds, (2, 98))
    speeds = np.clip((speeds - low) / max(high - low, 1e-9), 0.0, 1.0)
    return _centre(points), speeds, ages


def _centre(points: np.ndarray) -> np.ndarray:
    """Centre on the bulk of the cloud, ignoring rare excursions."""
    low = np.percentile(points, 0.3, axis=0)
    high = np.percentile(points, 99.7, axis=0)
    return (points - (low + high) * 0.5).astype(np.float32)


def fit_scale(points: np.ndarray, width: int, height: int, tilt: float, fill: float) -> float:
    """One projection scale that fits every yaw of the turn.

    Taken from the worst-case silhouette rather than per frame, so the sculpture
    does not breathe in and out as it rotates -- and from the finished attractor,
    so the growing trace is never rescaled.
    """
    horizontal_radius = float(np.percentile(np.sqrt(points[:, 0] ** 2 + points[:, 2] ** 2), 99.7))
    vertical_radius = float(np.percentile(np.abs(points[:, 1]), 99.7))
    screen_half_height = vertical_radius * math.cos(tilt) + horizontal_radius * math.sin(tilt)
    return min(
        fill * width / max(2.0 * horizontal_radius, 1e-9),
        fill * height / max(2.0 * screen_half_height, 1e-9),
    )


def project(
    points: np.ndarray,
    yaw: float,
    tilt: float,
    scale: float,
    width: int,
    height: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Rotate about the vertical axis, tilt, and project to screen coordinates."""
    cos_yaw, sin_yaw = math.cos(yaw), math.sin(yaw)
    x = points[:, 0] * cos_yaw + points[:, 2] * sin_yaw
    z = -points[:, 0] * sin_yaw + points[:, 2] * cos_yaw
    y = points[:, 1]

    cos_tilt, sin_tilt = math.cos(tilt), math.sin(tilt)
    screen_y = y * cos_tilt + z * sin_tilt
    depth = -y * sin_tilt + z * cos_tilt

    screen = np.column_stack((x * scale + width * 0.5, -screen_y * scale + height * 0.5))
    span = max(float(np.ptp(depth)), 1e-9)
    normalised_depth = (depth - depth.min()) / span
    return screen.astype(np.float32), normalised_depth.astype(np.float32)
