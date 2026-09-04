#!/usr/bin/env python3
"""Langton's ant, and what happens when a hundred of them share one grid.

The rule is nine words long. An ant sits on a cell, and: on a white cell it
turns right, on a black cell it turns left; either way it flips the cell it
was standing on and steps forward. There is no state in the ant beyond which
way it is facing, no memory, no goal, and no randomness anywhere -- the whole
system is determined by where the ants started.

Left alone on a blank grid an ant spends about ten thousand steps making a
small symmetric mess, and then, with nothing changing about the rule, it starts
emitting a *highway*: a 104-step cycle that translates the pattern two cells
diagonally and repeats forever. Nobody has proved why it happens and nobody has
found a starting configuration where it does not.

Sharing a grid is what makes it a population rather than a demonstration. The
cells are the only thing an ant can sense and the only thing it can change, so
an ant driving down a highway through another ant's rubbish reads the wrong
colours, turns the wrong way, and drops back into chaos; a mess that another
ant has already tidied can launch a road early. The ants never touch each
other. Everything they do to each other, they do through the floor.

Two fields come out of it and the renderer wants both:

- **`visits`** -- how many times each cell has been stepped on. This is the
  material: a highway cell is stepped on once, a cell in the middle of a
  chaotic core several hundred times, and that span is what the log-density map
  in `glow` was built for.
- **`last_seen`** -- the step at which each cell was last stepped on. This is
  the only thing that separates a road being built right now from one that was
  abandoned four seconds ago, which on a purely cumulative field are the same
  picture. `venation` was rejected for being that picture.
"""

from __future__ import annotations

import numpy as np

# Headings, in the order a right turn walks through them: up, right, down,
# left. A right turn is +1, a left turn is +3 -- both modulo four, which is
# what the & 3 does.
DX = np.array([0, 1, 0, -1], dtype=np.int64)
DY = np.array([-1, 0, 1, 0], dtype=np.int64)


class Ants:
    """A colony of Langton's ants on a shared torus.

    The grid wraps in both directions. That is not a convenience: a highway is
    a straight line that never stops, so on any finite grid it either wraps or
    it hits a wall the rule knows nothing about. Wrapping means a road that
    leaves the top of the frame is the same road arriving at the bottom, and
    every structure on screen was built by the rule rather than by an edge.
    """

    def __init__(
        self,
        width: int,
        height: int,
        count: int,
        seed: int = 3,
        spread: float = 0.30,
    ) -> None:
        generator = np.random.default_rng(seed)
        self.width = width
        self.height = height
        self.cell = np.zeros((height, width), dtype=np.uint8)
        self.visits = np.zeros((height, width), dtype=np.uint32)
        # Zero means "never", and step numbering starts at one so it stays
        # distinguishable from "stepped on at the very first step".
        self.last_seen = np.zeros((height, width), dtype=np.uint32)
        # Started in a central band rather than over the whole frame. Scattered
        # everywhere, the chaotic cores merge into one grey mass before the
        # first highways launch (measured: 60 ants over the full frame read as
        # a single blob at 200 px); started in a band they stay separable and
        # the roads have empty grid to be seen against.
        self.x = generator.integers(
            int(width * (0.5 - spread)), int(width * (0.5 + spread)), count
        ).astype(np.int64)
        self.y = generator.integers(
            int(height * (0.5 - spread)), int(height * (0.5 + spread)), count
        ).astype(np.int64)
        self.d = generator.integers(0, 4, count).astype(np.int64)
        self.steps = 0

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            self.steps += 1
            state = self.cell[self.y, self.x]
            self.d = (self.d + np.where(state == 0, 1, 3)) & 3
            # Two ants on one cell in the same step flip it twice, which is to
            # say not at all. That is the interaction, not a race to be fixed:
            # the floor is the only channel they have.
            self.cell[self.y, self.x] ^= 1
            np.add.at(self.visits, (self.y, self.x), 1)
            self.last_seen[self.y, self.x] = self.steps
            self.x = (self.x + DX[self.d]) % self.width
            self.y = (self.y + DY[self.d]) % self.height

    def touched(self) -> int:
        """Cells that have ever been stepped on -- the extent of the structure."""
        return int((self.visits > 0).sum())

    def travelled(self, since: np.ndarray) -> np.ndarray:
        """Distance each ant has covered since a recorded position, on the torus.

        A chaotic ant stays inside its own core and reads a few cells; an ant
        on a highway moves 2.83 cells every 104 steps and reads tens. This is
        how the pitch counted how many ants were on a road.
        """
        now = np.stack([self.x, self.y], axis=1).astype(np.float64)
        delta = np.abs(now - since)
        delta = np.minimum(delta, np.array([self.width, self.height]) - delta)
        return np.hypot(delta[:, 0], delta[:, 1])

    def positions(self) -> np.ndarray:
        return np.stack([self.x, self.y], axis=1).astype(np.float64)
