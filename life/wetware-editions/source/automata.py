#!/usr/bin/env python3
"""Cellular automata kernels: a continuous colony, and Life in spacetime.

Two families live here because the three editions ask two different questions of
the same idea. `Colony` is Life relaxed into a continuous field on an irregular
graph of cells -- what Life looks like as tissue. `evolve` is Conway's rule
exactly as stated, run on a grid and recorded as a solid in (x, y, t) -- what
Life looks like as a machine, and as a history.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.spatial import cKDTree


# Bill Gosper's glider gun, 1970: the first pattern shown to grow without bound,
# and the reason Life is Turing complete. Thirty-six cells, period thirty, and
# it emits a glider forever. Coordinates are (column, row) in its own 36x9 box.
GOSPER_GUN = (
    (0, 4), (0, 5), (1, 4), (1, 5),
    (10, 4), (10, 5), (10, 6),
    (11, 3), (11, 7),
    (12, 2), (12, 8),
    (13, 2), (13, 8),
    (14, 5),
    (15, 3), (15, 7),
    (16, 4), (16, 5), (16, 6),
    (17, 5),
    (20, 2), (20, 3), (20, 4),
    (21, 2), (21, 3), (21, 4),
    (22, 1), (22, 5),
    (24, 0), (24, 1), (24, 5), (24, 6),
    (34, 2), (34, 3),
    (35, 2), (35, 3),
)


# --------------------------------------------------------------------------
# Conway's Life, and its spacetime
# --------------------------------------------------------------------------


def rule_tables(born: tuple[int, ...], survive: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray]:
    """Nine-entry lookup tables, so a step is two gathers rather than two isin scans."""
    born_table = np.zeros(9, dtype=bool)
    survive_table = np.zeros(9, dtype=bool)
    born_table[list(born)] = True
    survive_table[list(survive)] = True
    return born_table, survive_table


def neighbour_count(grid: np.ndarray, wrap: bool) -> np.ndarray:
    """Live neighbours of every cell, on a torus or on a bounded board."""
    if wrap:
        total = np.zeros(grid.shape, dtype=np.int8)
        for shift_y in (-1, 0, 1):
            for shift_x in (-1, 0, 1):
                if shift_y or shift_x:
                    total += np.roll(grid, (shift_y, shift_x), axis=(0, 1))
        return total
    padded = np.pad(grid, 1)
    height, width = grid.shape
    total = np.zeros(grid.shape, dtype=np.int8)
    for offset_y in (0, 1, 2):
        for offset_x in (0, 1, 2):
            if offset_y == 1 and offset_x == 1:
                continue
            total += padded[offset_y : offset_y + height, offset_x : offset_x + width]
    return total


def step(grid: np.ndarray, born: np.ndarray, survive: np.ndarray, wrap: bool) -> np.ndarray:
    counts = neighbour_count(grid, wrap)
    alive = grid.astype(bool)
    return (np.where(alive, survive[counts], born[counts])).astype(np.uint8)


def evolve(
    grid: np.ndarray,
    born: tuple[int, ...],
    survive: tuple[int, ...],
    generations: int,
    wrap: bool = True,
    record_from: int = 0,
) -> dict[str, np.ndarray]:
    """Run the rule and record every live cell as a point in (x, y, t).

    Also returns each point's *age*: how many consecutive generations that cell
    has been alive at that moment. Age is what separates the permanent from the
    passing -- a still life climbs to the full run length, a glider's cells never
    get past four -- and unlike the position it does not depend on where the
    camera ends up, which is what the house style wants driving colour.
    """
    born_table, survive_table = rule_tables(born, survive)
    age = np.zeros(grid.shape, dtype=np.int32)
    columns: list[np.ndarray] = []
    rows: list[np.ndarray] = []
    times: list[np.ndarray] = []
    ages: list[np.ndarray] = []
    populations: list[int] = []

    for generation in range(generations):
        age = (age + 1) * grid
        populations.append(int(grid.sum()))
        if generation >= record_from:
            row_index, column_index = np.nonzero(grid)
            columns.append(column_index.astype(np.float32))
            rows.append(row_index.astype(np.float32))
            times.append(np.full(len(row_index), generation, dtype=np.float32))
            ages.append(age[row_index, column_index].astype(np.float32))
        grid = step(grid, born_table, survive_table, wrap)

    return {
        "x": np.concatenate(columns),
        "y": np.concatenate(rows),
        "t": np.concatenate(times),
        "age": np.concatenate(ages),
        "population": np.asarray(populations, dtype=np.int32),
    }


def voxels(
    cloud: dict[str, np.ndarray],
    per_cell: int,
    time_scale: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Scatter samples through each live cell's unit box in (x, y, t).

    A live cell is a unit volume of spacetime, not a point. Splatting its centre
    alone leaves the solid stippled at any framing where a cell spans more than a
    pixel, and no amount of bloom turns a lattice of dots back into matter. The
    lesson is the one the trace editions learned: put the samples where the
    object actually is, then far fewer of them are needed.
    """
    count = len(cloud["x"])
    jitter = rng.random((count * per_cell, 3), dtype=np.float32) - 0.5
    centres = np.repeat(
        np.column_stack((cloud["x"], cloud["t"] * time_scale, cloud["y"])), per_cell, axis=0
    )
    jitter[:, 1] *= time_scale
    return (centres + jitter).astype(np.float32), np.repeat(cloud["age"], per_cell)


# --------------------------------------------------------------------------
# Life as a continuous field on an irregular colony
# --------------------------------------------------------------------------


def poisson_disc(radius: float, spacing: float, rng: np.random.Generator, attempts: int = 30) -> np.ndarray:
    """Bridson blue-noise sampling inside a disc.

    A square lattice would beat visibly against the propagating rings, and pure
    uniform random leaves clumps and holes that read as flaws rather than as
    texture. Blue noise is the arrangement a confluent cell sheet actually
    reaches: an even spacing that is nowhere exactly repeated.
    """
    cell = spacing / math.sqrt(2.0)
    span = int(math.ceil(2.0 * radius / cell)) + 1
    lookup = np.full((span, span), -1, dtype=np.int64)
    points: list[tuple[float, float]] = []
    active: list[int] = []

    def insert(point: tuple[float, float]) -> None:
        column = int((point[0] + radius) / cell)
        row = int((point[1] + radius) / cell)
        lookup[row, column] = len(points)
        active.append(len(points))
        points.append(point)

    def free(point: tuple[float, float]) -> bool:
        column = int((point[0] + radius) / cell)
        row = int((point[1] + radius) / cell)
        for near_row in range(max(row - 2, 0), min(row + 3, span)):
            for near_column in range(max(column - 2, 0), min(column + 3, span)):
                index = lookup[near_row, near_column]
                if index >= 0:
                    other = points[index]
                    if (other[0] - point[0]) ** 2 + (other[1] - point[1]) ** 2 < spacing * spacing:
                        return False
        return True

    insert((0.0, 0.0))
    while active:
        slot = int(rng.integers(len(active)))
        origin = points[active[slot]]
        for _ in range(attempts):
            angle = float(rng.uniform(0.0, 2.0 * math.pi))
            distance = spacing * math.sqrt(float(rng.uniform(1.0, 4.0)))
            candidate = (origin[0] + distance * math.cos(angle), origin[1] + distance * math.sin(angle))
            if candidate[0] ** 2 + candidate[1] ** 2 > radius * radius:
                continue
            if free(candidate):
                insert(candidate)
                break
        else:
            active.pop(slot)
    return np.asarray(points, dtype=np.float64)


def colony_positions(radius: float, count: int, rng: np.random.Generator) -> np.ndarray:
    """Blue-noise disc sized to land near a target population."""
    # The constant is measured, not derived: Bridson's dart throwing packs a disc
    # to about this fraction of the hexagonal ideal at these sizes.
    spacing = math.sqrt(math.pi * radius * radius / (1.60 * max(count, 1)))
    return poisson_disc(radius, spacing, rng)


class Colony:
    """Life with the discreteness taken out.

    Conway's rule is a threshold on a count of eight neighbours. Relax the state
    to a real number, replace the count by a distance-weighted average over the
    k nearest cells, and keep the part that actually matters -- that there is a
    *window* of neighbourhood activity in which a cell grows, and outside it, in
    loneliness or in crowding, it fades. That window is the whole of Life. What
    it buys is that the same rule now runs on any graph, needs no lattice, and
    produces fronts that travel instead of edges that step.

    The window on its own is bistable, not excitable, and that is not enough to
    animate. Fronts leave the seeds, sweep the colony in about a hundred steps,
    and then everything sits saturated forever: a filled disc, with nowhere left
    to propagate into. So each cell also carries a slow fatigue that chases its
    own activity and subtracts from it. A cell fires, tires, and cannot fire
    again until it has rested. Behind a front the tissue is spent, so the front
    cannot turn back on itself and has to keep moving outward -- which is what
    makes rings expand, collide, annihilate and wind into spirals. It is the
    second variable every excitable medium needs, and it is the difference
    between a wave and a stain.
    """

    def __init__(
        self,
        positions: np.ndarray,
        neighbours: int,
        rng: np.random.Generator,
        activation_low: float = 0.20,
        activation_high: float = 0.45,
        growth: float = 0.08,
        wither: float = 0.04,
        diffusion: float = 0.15,
        decay: float = 0.01,
        noise: float = 0.005,
        inhibit: float = 0.45,
        recovery: float = 0.035,
    ) -> None:
        self.positions = positions.astype(np.float64)
        self.rng = rng
        self.activation_low = activation_low
        self.activation_high = activation_high
        self.growth = growth
        self.wither = wither
        self.diffusion = diffusion
        self.decay = decay
        self.noise = noise
        self.inhibit = inhibit
        self.recovery = recovery

        tree = cKDTree(self.positions)
        distance, index = tree.query(self.positions, k=neighbours + 1)
        # Column zero is the cell itself.
        self.index = index[:, 1:].astype(np.int32)
        gap = distance[:, 1:]
        interaction = float(np.median(gap[:, 0])) * 2.2
        self.weight = np.exp(-((gap / interaction) ** 2)).astype(np.float32)
        self.weight_sum = self.weight.sum(axis=1)

        self.state = rng.uniform(0.0, 0.05, len(positions)).astype(np.float32)
        self.fatigue = np.zeros(len(positions), dtype=np.float32)
        self.rings: list[dict[str, float | np.ndarray]] = []

    def seed(self, colonies: int, sigma: float) -> None:
        for _ in range(colonies):
            self.ignite(int(self.rng.integers(len(self.positions))), sigma)

    def ignite(self, cell: int, sigma: float) -> None:
        centre = self.positions[cell]
        gap = np.linalg.norm(self.positions - centre, axis=1)
        self.state = np.maximum(self.state, np.exp(-((gap / sigma) ** 2))).astype(np.float32)
        self.rings.append({"centre": centre.copy(), "radius": 0.0, "age": 0.0})

    def neighbour_signal(self) -> np.ndarray:
        return (self.state[self.index] * self.weight).sum(axis=1) / self.weight_sum

    def local_maxima(self, threshold: float) -> np.ndarray:
        """Cells brighter than every neighbour: the centres of the active colonies."""
        hot = self.state > threshold
        return np.flatnonzero(hot & (self.state >= self.state[self.index].max(axis=1)))

    def advance(
        self,
        dt: float,
        ring_speed: float,
        ring_lifetime: float,
        ring_sigma: float,
        spawn: float,
        spawn_sigma: float = 0.07,
    ) -> np.ndarray:
        signal = self.neighbour_signal()
        inside = (signal > self.activation_low) & (signal < self.activation_high)
        change = np.where(inside, self.growth, -self.wither)
        change = change + self.diffusion * (signal - self.state)
        change = change - self.inhibit * self.fatigue
        change = change + self.rng.uniform(-self.noise, self.noise, len(self.state)) - self.decay
        self.state = np.clip(self.state + change.astype(np.float32), 0.0, 1.0)
        self.fatigue = np.clip(
            self.fatigue + self.recovery * (self.state - self.fatigue), 0.0, 1.0
        ).astype(np.float32)

        surviving: list[dict] = []
        for ring in self.rings:
            ring["radius"] = float(ring["radius"]) + ring_speed * dt
            ring["age"] = float(ring["age"]) + dt
            offset = np.abs(np.linalg.norm(self.positions - ring["centre"], axis=1) - float(ring["radius"]))
            touched = offset < ring_sigma * 3.0
            if touched.any():
                impulse = np.exp(-((offset[touched] / ring_sigma) ** 2))
                self.state[touched] = np.clip(self.state[touched] + impulse.astype(np.float32) * 0.10, 0.0, 1.0)
            if float(ring["age"]) < ring_lifetime:
                surviving.append(ring)
        self.rings = surviving

        # A fresh colony now and then, and always one if the tissue has gone
        # quiet. Excitable media are mortal: every wave eventually runs into
        # another and annihilates, and without reseeding the dish ends the clip
        # black. Igniting rather than only ringing is what lets it restart from
        # nothing, which the impulse alone is far too small to do.
        if float(self.rng.random()) < spawn or float(self.state.max()) < 0.12:
            hot = np.flatnonzero(self.state > 0.4)
            cell = int(self.rng.choice(hot)) if len(hot) else int(self.rng.integers(len(self.positions)))
            self.ignite(cell, spawn_sigma)
        return self.state


def breath(phase: float, low: float = 0.72, high: float = 1.0) -> float:
    """One asymmetric cycle: fill slowly, empty quickly, rest, repeat.

    A sine spends equal time in both directions and reads as a pump. Drawing
    breath out over more than half the cycle, collapsing it in a fifth, then
    holding the pause is what makes the whole colony read as something alive
    rather than as a value being oscillated.
    """
    cycle = phase - math.floor(phase)
    if cycle < 0.55:
        eased = cycle / 0.55
        shape = eased * eased * (3.0 - 2.0 * eased)
    elif cycle < 0.75:
        eased = (cycle - 0.55) / 0.20
        shape = 1.0 - eased * eased * (3.0 - 2.0 * eased)
    else:
        shape = 0.0
    return low + (high - low) * shape
