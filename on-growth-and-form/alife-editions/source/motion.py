#!/usr/bin/env python3
"""The primordial particle system: one motion law, and cells come out of it.

Thomas Schmickl, Martin Stefanec and Karl Crailsheim published this in 2016
(*How a life-like system emerges from a simple particle motion law*). Every
particle carries a position and a heading, and one rule moves it:

    count the neighbours inside r, split them into those on the left of the
    heading and those on the right, turn by alpha + beta * N * sign(R - L),
    then step forward v.

That is all of it. No forces, no attraction, no species, no chemistry, no
membrane and nothing anywhere that mentions a cell. The particles do not even
have a velocity -- only a direction they are pointed in.

What comes out are **cells**: bounded blobs a few dozen particles across, with
a dense core, a ring around it and free particles drifting between them. They
hold together, they deform, they shove each other, and they keep appearing for
as long as there is loose material to make them out of.

**They do not divide, and this file will not pretend they do.** Measured on
this implementation: when a new cell appears, the median distance to the
nearest cell that already existed is 42.6 units against a cell diameter of
about 20, and only 3% appear within one diameter. At the paper's own density
of 0.08 it is 0%. New cells condense out of the soup on their own account;
they are not children of the ones next to them.

**The soup is topped up**, which is the one thing here that is not in the
paper. Left alone, a world this size organises what it has in the first
quarter of a clip and then only coarsens -- the failure that killed `sorting`
and `condensate`. A trickle of new particles is the drive `BRIEF.md` allows
against that: it keeps the loose material coming, so cells keep condensing for
the whole eight seconds instead of the first two.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

# The paper's numbers. Everything except the radius is dimensionless, so the
# radius sets the scale of the whole picture: a cell comes out about four r
# across, which at r = 30 px is a 120 px body on a 1080 px frame.
ALPHA = np.deg2rad(180.0)
BETA = np.deg2rad(17.0)
SPEED = 0.67 / 5.0  # per unit of radius, so it scales with it


class PrimordialParticles:
    """Particles on a torus in pixel coordinates, and one turning rule.

    Working directly in pixels rather than in the paper's arbitrary units means
    the renderer never converts anything, and the only number that decides how
    big a cell is on screen is `radius`.
    """

    def __init__(
        self,
        width: int,
        height: int,
        count: int,
        radius: float = 30.0,
        seed: int = 11,
        seeds: int = 3,
    ) -> None:
        self.width = float(width)
        self.height = float(height)
        self.radius = float(radius)
        self.speed = SPEED * self.radius
        self.generator = np.random.default_rng(seed)
        self.position = np.stack(
            [
                self.generator.uniform(0.0, self.width, count),
                self.generator.uniform(0.0, self.height, count),
            ],
            axis=1,
        )
        # Three cells to start with rather than one. With a single seed the
        # first quarter of the clip is one blob sitting on its own -- the
        # profile passes and there is nothing to watch, which is the same
        # mistake `somite` made in a different edition.
        for _ in range(seeds):
            self.position = np.concatenate([self.position, self._disc()])
        self.heading = self.generator.uniform(-np.pi, np.pi, len(self.position))
        self.neighbours = np.zeros(len(self.position), dtype=np.int32)
        self.pending = 0.0
        self.steps = 0

    def _disc(self, particles: int = 200) -> np.ndarray:
        """A blob dense enough to become a cell instead of dispersing."""
        angle = self.generator.uniform(0.0, 2.0 * np.pi, particles)
        # 1.8 r across, which is roughly the size the rule settles a cell at.
        # Seeded much tighter than that it blows itself apart before it closes;
        # sqrt so the disc is uniform rather than a pinprick with a skirt.
        spread = 1.8 * self.radius * np.sqrt(self.generator.uniform(0.0, 1.0, particles))
        centre = (
            self.generator.uniform(0.2 * self.width, 0.8 * self.width),
            self.generator.uniform(0.2 * self.height, 0.8 * self.height),
        )
        return np.stack(
            [centre[0] + spread * np.cos(angle), centre[1] + spread * np.sin(angle)], axis=1
        )

    def inject(self, rate: float) -> None:
        """Drop `rate` new particles a step into the world, at random."""
        self.pending += rate
        arriving = int(self.pending)
        self.pending -= arriving
        if not arriving:
            return
        fresh = np.stack(
            [
                self.generator.uniform(0.0, self.width, arriving),
                self.generator.uniform(0.0, self.height, arriving),
            ],
            axis=1,
        )
        self.position = np.concatenate([self.position, fresh])
        self.heading = np.concatenate(
            [self.heading, self.generator.uniform(-np.pi, np.pi, arriving)]
        )
        self.neighbours = np.zeros(len(self.position), dtype=np.int32)

    def step(self, count: int = 1, inject: float = 0.0) -> None:
        box = np.array([self.width, self.height])
        for _ in range(count):
            if inject:
                self.inject(inject)
            tree = cKDTree(self.position, boxsize=box)
            pairs = tree.query_pairs(self.radius, output_type="ndarray")
            first, second = pairs[:, 0], pairs[:, 1]
            separation = self.position[second] - self.position[first]
            # Shortest image on the torus, or a pair either side of the seam
            # reads as being the width of the world apart.
            separation -= box * np.round(separation / box)
            cosine, sine = np.cos(self.heading), np.sin(self.heading)
            left = np.zeros(len(self.position), np.int32)
            right = np.zeros(len(self.position), np.int32)
            # The cross product of the heading with the separation is positive
            # for a neighbour on the left. Each pair is counted from both ends,
            # and the separation simply flips sign for the second.
            cross = cosine[first] * separation[:, 1] - sine[first] * separation[:, 0]
            np.add.at(left, first, (cross > 0).astype(np.int32))
            np.add.at(right, first, (cross <= 0).astype(np.int32))
            cross = -cosine[second] * separation[:, 1] + sine[second] * separation[:, 0]
            np.add.at(left, second, (cross > 0).astype(np.int32))
            np.add.at(right, second, (cross <= 0).astype(np.int32))

            self.neighbours = left + right
            self.heading = self.heading + ALPHA + BETA * self.neighbours * np.sign(right - left)
            self.heading = (self.heading + np.pi) % (2.0 * np.pi) - np.pi
            self.position = self.position + self.speed * np.stack(
                [np.cos(self.heading), np.sin(self.heading)], axis=1
            )
            self.position = np.mod(self.position, box)
            # float mod can return exactly the modulus for a value a hair below
            # zero, and cKDTree(boxsize=...) refuses the whole array for one
            # point sitting on the wall of a half-open box.
            self.position = np.clip(self.position, 0.0, np.nextafter(box, 0.0))
            self.steps += 1

    def cells(self, membrane: int = 15, floor: int = 6) -> int:
        """Blobs of particles that are inside a membrane, counted.

        A particle with fifteen or more neighbours is in a cell rather than in
        the soup; bin those, close the bins, and count the connected regions
        big enough not to be two particles that happened to pass.
        """
        from scipy import ndimage

        bin_size = self.radius / 2.0
        columns = int(self.width / bin_size)
        rows = int(self.height / bin_size)
        inside = self.neighbours >= membrane
        x = np.clip((self.position[inside, 0] / self.width * columns).astype(int), 0, columns - 1)
        y = np.clip((self.position[inside, 1] / self.height * rows).astype(int), 0, rows - 1)
        grid = np.zeros((rows, columns), bool)
        grid[y, x] = True
        grid = ndimage.binary_closing(grid, np.ones((3, 3)))
        labels, found = ndimage.label(grid, structure=np.ones((3, 3)))
        if not found:
            return 0
        return int((np.bincount(labels.ravel())[1:] >= floor).sum())
