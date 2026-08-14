#!/usr/bin/env python3
"""Attractor sampling and camera projection.

Everything is vectorised across trajectories rather than stepped one point at a
time. A single trajectory traced with a visible line only ever shows a curve;
integrating several hundred neighbouring trajectories at once resolves the
attractor as a surface, which is what makes the density -- and therefore the
glow -- carry the image.
"""

from __future__ import annotations

import math

import numpy as np


CLIFFORD_PRESETS = {
    "classic-butterfly": (-1.4, 1.6, 1.0, 0.7),
    "ring": (-1.7, 1.8, -1.9, -0.4),
    "shell": (1.7, 1.7, 0.6, 1.2),
}


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

SEEDS = {
    "lorenz": (0.1, 0.0, 0.0),
    "halvorsen": (1.0, 0.0, 0.0),
    "aizawa": (0.1, 0.0, 0.0),
}

STEP_SIZES = {"lorenz": 0.0035, "halvorsen": 0.0035, "aizawa": 0.006}

# Which model axis should point up the screen. Lorenz and Aizawa are far taller
# in z than they are wide, so standing them on that axis fills a 9:16 frame
# instead of leaving a wide form stranded in a tall crop.
UP_AXIS = {"lorenz": (0, 2, 1), "halvorsen": (0, 2, 1), "aizawa": (0, 2, 1)}

# Radius of a thin cylinder around the vertical axis whose samples are thrown
# away. Aizawa needs one: besides the orbits that park on its invariant z-axis,
# a slow near-axis orbit piles roughly half a percent of all samples onto a
# single radius, which draws a hairline straight down the middle of the frame.
AXIS_CUT = {"aizawa": 0.035}


def sample_flow(
    name: str,
    trajectories: int = 520,
    steps: int = 2600,
    warmup: int = 1400,
    spread: float = 0.55,
    seed: int = 20260731,
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate a cloud of neighbouring trajectories with vectorised RK4.

    Returns the sampled points and each sample's normalised speed, which is an
    intrinsic property of the flow -- unlike camera depth it stays fixed as the
    view rotates, so the structure keeps a stable identity through the turn.
    """
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

    # Drop trajectories that fell off the attractor into a fixed point. Aizawa's
    # z-axis is invariant -- x = y = 0 gives dx/dt = dy/dt = 0 -- and the axial
    # dynamics dz/dt = c + a z - z^3/3 have a stable root below the body, so any
    # orbit that drifts onto the axis parks there. A handful doing that deposits
    # millions of samples on one spot, which renders as a hairline and a hot
    # blob hanging under the sculpture.
    travel = np.linalg.norm(np.ptp(points, axis=0), axis=1)
    alive = travel > 0.05 * np.median(travel)
    points, speeds = points[:, alive], speeds[:, alive]

    points = points.reshape(-1, 3)
    speeds = speeds.reshape(-1)
    finite = np.isfinite(points).all(axis=1) & np.isfinite(speeds)
    points, speeds = points[finite], speeds[finite]

    points = points[:, UP_AXIS[name]]
    cut = AXIS_CUT.get(name, 0.0)
    if cut:
        kept = np.hypot(points[:, 0], points[:, 2]) >= cut
        points, speeds = points[kept], speeds[kept]

    low, high = np.percentile(speeds, (2, 98))
    speeds = np.clip((speeds - low) / max(high - low, 1e-9), 0.0, 1.0)
    return _centre(points), speeds


def sample_clifford(
    preset: str,
    seeds: int = 26000,
    steps: int = 90,
    warmup: int = 40,
    seed: int = 20260731,
) -> tuple[np.ndarray, np.ndarray]:
    """Iterate the Clifford map from many seeds at once, then give it depth.

    The map is elementwise, so thousands of orbits advance in one vectorised
    step. Depth is a smooth function of the planar position, which turns the
    flat attractor into a coherent shell rather than a rotating card.
    """
    a, b, c, d = CLIFFORD_PRESETS[preset]
    generator = np.random.default_rng(seed)
    x = generator.uniform(-1.8, 1.8, seeds)
    y = generator.uniform(-1.8, 1.8, seeds)
    for _ in range(warmup):
        x, y = np.sin(a * y) + c * np.cos(a * x), np.sin(b * x) + d * np.cos(b * y)

    collected_x = np.empty((steps, seeds), dtype=np.float32)
    collected_y = np.empty((steps, seeds), dtype=np.float32)
    for index in range(steps):
        x, y = np.sin(a * y) + c * np.cos(a * x), np.sin(b * x) + d * np.cos(b * y)
        collected_x[index] = x
        collected_y[index] = y

    planar = np.column_stack((collected_x.reshape(-1), collected_y.reshape(-1)))
    planar = planar[np.isfinite(planar).all(axis=1)]

    centre = (planar.min(axis=0) + planar.max(axis=0)) * 0.5
    span = max(np.ptp(planar[:, 0]), np.ptp(planar[:, 1]))
    planar = (planar - centre) / max(span * 0.5, 1e-9)

    radius = np.clip(np.linalg.norm(planar, axis=1) / 1.45, 0.0, 1.0)
    half_depth = 0.30 + 0.20 * (1.0 - radius)
    ripple = np.sin(6.0 * planar[:, 0]) * np.cos(5.0 * planar[:, 1])
    depth = half_depth * ripple + 0.06 * np.sin(11.0 * planar[:, 0] - 7.0 * planar[:, 1])
    points = np.column_stack((planar, depth)).astype(np.float32)

    angle = np.arctan2(planar[:, 1], planar[:, 0])
    phase = np.mod(angle / (2.0 * math.pi) + 0.5 * radius, 1.0).astype(np.float32)
    return _centre(points), phase


def roll(points: np.ndarray, degrees: float) -> np.ndarray:
    """Spin the cloud in its own xy-plane before projection.

    Some attractors are wide and squat. Scaling one up to fill a 9:16 frame
    just runs it off the sides, because it is already width-limited; standing
    its long axis upright is what actually uses the height.
    """
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
    what stops the sculpture from breathing in and out as it rotates.
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
