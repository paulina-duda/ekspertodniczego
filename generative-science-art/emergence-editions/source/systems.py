#!/usr/bin/env python3
"""Attractor sampling and camera projection, with a sample age for each point.

This is the flow sampler from `luminous-editions`, with one addition: every
sample carries the integration step it came from. That is what lets the
renderer show the attractor being drawn rather than already finished.

Because the samples are stored step-major and every filter below preserves that
order, the returned age array is non-decreasing. The renderer relies on it: a
binary search gives the prefix of samples that exist at a given moment, so no
per-frame mask over four million points is needed.
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


def _thomas(state: np.ndarray, b: float = 0.208186) -> np.ndarray:
    x, y, z = state[:, 0], state[:, 1], state[:, 2]
    return np.column_stack((
        np.sin(y) - b * x,
        np.sin(z) - b * y,
        np.sin(x) - b * z,
    ))


FLOWS = {"lorenz": _lorenz, "halvorsen": _halvorsen, "aizawa": _aizawa, "thomas": _thomas}

SEEDS = {
    "lorenz": (0.1, 0.0, 0.0),
    "halvorsen": (1.0, 0.0, 0.0),
    "aizawa": (0.1, 0.0, 0.0),
    "thomas": (0.1, 0.0, 0.0),
}

# Thomas drifts far more slowly than the others, so it needs a much larger step
# to cover comparable ground in a comparable number of samples.
STEP_SIZES = {"lorenz": 0.0035, "halvorsen": 0.0035, "aizawa": 0.006, "thomas": 0.045}

# The sampling the luminous editions use. Colour comes from speed, and speed is
# normalised against the sample population, so a run with different parameters
# maps the same physical speed onto a different part of the palette. Measured on
# Lorenz: the emergence run's missing warm-up lets the launch transient stretch
# the 98th percentile from 182 to 241, which slides the whole attractor towards
# the warm end and hands the violet to the transient. Taking the bounds from a
# reference run in this configuration is what keeps the two editions matching.
LUMINOUS_SAMPLING = {"trajectories": 1200, "steps": 3800, "warmup": 1400, "spread": 0.55}

# Which model axis should point up the screen. Lorenz and Aizawa are far taller
# in z than they are wide, so standing them on that axis fills a 9:16 frame
# instead of leaving a wide form stranded in a tall crop.
UP_AXIS = {
    "lorenz": (0, 2, 1),
    "halvorsen": (0, 2, 1),
    "aizawa": (0, 2, 1),
    "thomas": (0, 1, 2),
}

# Radius of a thin cylinder around the vertical axis whose samples are thrown
# away. Aizawa needs one: besides the orbits that park on its invariant z-axis,
# a slow near-axis orbit piles roughly half a percent of all samples onto a
# single radius, which draws a hairline straight down the middle of the frame.
AXIS_CUT = {"aizawa": 0.035}


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
    """Speed bounds as the luminous editions would compute them.

    Deliberately runs the full luminous configuration rather than a cheap
    approximation. A short run does not converge for Lorenz: with the
    trajectories still clustered, its heavy speed tail is under-sampled and the
    98th percentile comes out at 52 instead of 182, which would recolour the
    whole piece. It costs about a second.
    """
    _, speeds = _integrate(name, seed=seed, **LUMINOUS_SAMPLING)
    low, high = np.percentile(speeds.reshape(-1), (2, 98))
    return float(low), float(high)


def sample_flow(
    name: str,
    trajectories: int = 520,
    steps: int = 2600,
    warmup: int = 1400,
    spread: float = 0.55,
    seed: int = 20260731,
    speed_range: tuple[float, float] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Integrate a cloud of neighbouring trajectories with vectorised RK4.

    Returns the sampled points, each sample's normalised speed, and each
    sample's normalised age.

    With a small `spread` and no `warmup` the trajectories all start from
    essentially the same state, so early on they trace a single curve and only
    separate as chaos pulls them apart. That divergence is the growth: one
    thread becomes the whole butterfly.

    Pass `speed_range` to normalise colour against fixed bounds instead of this
    run's own percentiles -- see `reference_speed_range`.
    """
    points, speeds = _integrate(name, trajectories, steps, warmup, spread, seed)

    ages = np.repeat(
        np.linspace(0.0, 1.0, steps, dtype=np.float32)[:, None], trajectories, axis=1
    )

    # Drop trajectories that fell off the attractor into a fixed point. Aizawa's
    # z-axis is invariant -- x = y = 0 gives dx/dt = dy/dt = 0 -- and the axial
    # dynamics dz/dt = c + a z - z^3/3 have a stable root below the body, so any
    # orbit that drifts onto the axis parks there. A handful doing that deposits
    # millions of samples on one spot, which renders as a hairline and a hot
    # blob hanging under the sculpture.
    travel = np.linalg.norm(np.ptp(points, axis=0), axis=1)
    alive = travel > 0.05 * np.median(travel)
    points, speeds, ages = points[:, alive], speeds[:, alive], ages[:, alive]

    points = points.reshape(-1, 3)
    speeds = speeds.reshape(-1)
    ages = ages.reshape(-1)
    finite = np.isfinite(points).all(axis=1) & np.isfinite(speeds)
    points, speeds, ages = points[finite], speeds[finite], ages[finite]

    points = points[:, UP_AXIS[name]]
    cut = AXIS_CUT.get(name, 0.0)
    if cut:
        kept = np.hypot(points[:, 0], points[:, 2]) >= cut
        points, speeds, ages = points[kept], speeds[kept], ages[kept]

    low, high = speed_range if speed_range is not None else np.percentile(speeds, (2, 98))
    speeds = np.clip((speeds - low) / max(high - low, 1e-9), 0.0, 1.0)
    return _centre(points), speeds, ages


def roll(points: np.ndarray, degrees: float) -> np.ndarray:
    """Spin the cloud in its own xy-plane before projection."""
    if not degrees:
        return points
    angle = math.radians(degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    rotated = points.copy()
    rotated[:, 0] = points[:, 0] * cosine - points[:, 1] * sine
    rotated[:, 1] = points[:, 0] * sine + points[:, 1] * cosine
    return rotated


def _centre(points: np.ndarray) -> np.ndarray:
    """Centre on the bulk of the cloud, ignoring rare excursions."""
    low = np.percentile(points, 0.3, axis=0)
    high = np.percentile(points, 99.7, axis=0)
    return (points - (low + high) * 0.5).astype(np.float32)


def fit_scale(points: np.ndarray, width: int, height: int, tilt: float, fill: float) -> float:
    """Pick one projection scale that fits every yaw of the turn.

    Deriving the scale from the worst-case silhouette rather than per frame is
    what stops the sculpture from breathing in and out as it rotates -- and here
    it must come from the finished attractor, not from whatever has been drawn
    so far, or the growing form would be rescaled on every frame.
    """
    # A percentile rather than the maximum: chaotic flows throw occasional
    # far-flung samples, and fitting to those shrinks the whole sculpture to
    # leave room for a handful of stray pixels.
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
