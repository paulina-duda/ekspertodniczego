#!/usr/bin/env python3
"""Particle life: a table of numbers, and the things that come out of it.

Give every particle a species, and give every ordered pair of species one
number saying whether the first is drawn to the second or pushed away. Add one
rule that applies to everything regardless of species -- close in, everything
repels everything, because two things cannot be in the same place. That is the
entire model. There is no cell in it, no membrane, no organism, no metabolism
and no goal.

What comes out are cells with skins, clusters that swallow other clusters,
pairs that chase each other across the frame and knots that spit particles out
and pull them back. The reason is the one asymmetry: the table does not have to
be symmetric. If red chases green while green flees red, neither can settle, and
the pair keeps moving forever -- a predator and its prey written as two numbers
that disagree. Symmetric tables make crystals. The interesting ones are the
tables that cannot make up their mind.

The matrix here is not designed. It is *found*: a few dozen random tables are
each run for a few hundred steps and scored on whether they build structure and
keep moving, and the best one is kept. That is the smallest honest version of
what the field actually does -- search a space of rules for the ones that look
alive.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

try:  # optional, and worth an order of magnitude when it is there
    import torch
except ImportError:  # pragma: no cover - torch is in the environment, not the API
    torch = None


class ParticleLife:
    """Particles on a torus, one interaction table, no other structure.

    The force between two particles depends only on their distance and on the
    two species involved. Inside `r_min` it is a hard universal repulsion, which
    is what stops every cluster from collapsing to a point. Between `r_min` and
    `r_max` it is a tent -- rising to full strength halfway out, back to nothing
    at the rim -- scaled by the table entry for the ordered pair. Beyond
    `r_max`, nothing: the particle cannot see that far, which is what makes the
    whole thing local and what makes a neighbour tree the right tool.

    The frame wraps in both directions. A torus has no walls to pile up against
    and no corners to hide in, so any structure on screen is one the rule built
    rather than one the boundary imposed.

    There are two implementations of that one force law, and they have to agree.
    On a GPU every pair is evaluated and the ones past `r_max` are multiplied by
    zero, which sounds wasteful and is roughly twenty times faster than being
    clever: twenty thousand particles is four hundred million pairs, and that is
    a rounding error to a card that was built for matrix multiplication. Without
    a GPU the same law runs off a neighbour tree, which does the same arithmetic
    on the couple of hundred thousand pairs that are actually within range.
    """

    def __init__(
        self,
        height: int,
        width: int,
        matrix: np.ndarray,
        count: int = 6000,
        r_min: float = 15.0,
        r_max: float = 72.0,
        strength: float = 0.62,
        friction: float = 0.88,
        speed_limit: float = 6.0,
        band: tuple[float, float] | None = None,
        wall: float = 0.010,
        seed: int = 20260823,
        device: str | None = None,
        chunk: int = 4096,
    ) -> None:
        self.height, self.width = height, width
        self.matrix = np.asarray(matrix, dtype=np.float32)
        self.species_count = len(self.matrix)
        self.r_min, self.r_max = r_min, r_max
        self.strength, self.friction, self.speed_limit = strength, friction, speed_limit
        self.generator = np.random.default_rng(seed)

        # A band turns the torus into a cylinder: it still wraps left to right,
        # and top to bottom it is held by a soft spring that only pulls once a
        # particle is outside. The spring is linear and weak rather than a wall,
        # so the population thins towards the margin instead of piling against
        # a line -- a hard boundary would put a bright rim in the frame, which
        # is a structure the rule did not make.
        self.band = None if band is None else (float(band[0]), float(band[1]))
        self.wall = wall
        low, high = self.band if self.band else (0.0, height)

        self.position = np.column_stack(
            (
                self.generator.uniform(0, width, count),
                self.generator.uniform(low, high, count),
            )
        ).astype(np.float64)
        self.velocity = np.zeros((count, 2), dtype=np.float64)
        self.species = self.generator.integers(0, self.species_count, count)
        self.box = np.array([width, height], dtype=np.float64)
        # What the neighbour search and the minimum-image convention wrap in.
        # With a band, the vertical is not periodic at all, and the cheapest way
        # to say so to both of them is a box far taller than the frame: no image
        # of any particle is ever the nearest one.
        self.wrap = np.array([width, height if self.band is None else 8.0 * height], dtype=np.float64)

        self.chunk = chunk
        if device is None:
            device = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
        self.device = device if torch is not None else "cpu"
        if self.device != "cpu":
            self._position = torch.tensor(self.position, dtype=torch.float32, device=self.device)
            self._velocity = torch.zeros_like(self._position)
            self._species = torch.tensor(self.species, dtype=torch.long, device=self.device)
            self._matrix = torch.tensor(self.matrix, dtype=torch.float32, device=self.device)
            self._wrap = torch.tensor(self.wrap, dtype=torch.float32, device=self.device)

    def _sync(self) -> None:
        """Bring the GPU's copy back to numpy, which is where everything reads it.

        The clamp is not cosmetic. A float32 modulo can return exactly the
        modulus for a value a hair below zero, which puts a particle precisely
        on the far wall of a box that is supposed to be half-open -- and the
        neighbour tree, told the box is periodic, refuses the whole array with a
        message about the data being larger than the box.
        """
        if self.device != "cpu":
            position = self._position.detach().cpu().numpy().astype(np.float64)
            position[:, 0] = np.mod(position[:, 0], self.width)
            if self.band is None:
                position[:, 1] = np.mod(position[:, 1], self.height)
            self.position = np.clip(position, 0.0, self.box - 1e-6)
            self.velocity = self._velocity.detach().cpu().numpy().astype(np.float64)

    def _step_torch(self, count: int) -> None:
        position, velocity, box = self._position, self._velocity, self._wrap
        span = self.r_max - self.r_min
        low, high = self.band if self.band else (0.0, float(self.height))
        for _ in range(count):
            force = torch.zeros_like(position)
            for start in range(0, len(position), self.chunk):
                stop = min(start + self.chunk, len(position))
                delta = position.unsqueeze(0) - position[start:stop].unsqueeze(1)
                delta -= box * torch.round(delta / box)
                distance = torch.linalg.vector_norm(delta, dim=2)
                inside = (distance > 1e-6) & (distance < self.r_max)

                tent = (1.0 - (2.0 * distance - self.r_max - self.r_min).abs() / span).clamp(0.0, 1.0)
                close = distance < self.r_min
                affinity = self._matrix[self._species[start:stop]][:, self._species]
                magnitude = torch.where(close, distance / self.r_min - 1.0, affinity * tent)
                magnitude = torch.where(inside, magnitude, torch.zeros_like(magnitude))

                force[start:stop] = torch.einsum(
                    "ij,ijk->ik", magnitude / distance.clamp(min=1e-6), delta
                )

            if self.band is not None:
                rows = position[:, 1]
                force[:, 1] += self.wall * (
                    (low - rows).clamp(min=0.0) - (rows - high).clamp(min=0.0)
                )

            velocity = velocity * self.friction + force * self.strength
            speed = torch.linalg.vector_norm(velocity, dim=1, keepdim=True)
            velocity = torch.where(
                speed > self.speed_limit, velocity * (self.speed_limit / speed), velocity
            )
            position = position + velocity
            if self.band is None:
                position = position % self._wrap
            else:
                position = torch.stack(
                    (
                        position[:, 0] % self.width,
                        position[:, 1].clamp(0.0, float(self.height) - 1e-3),
                    ),
                    dim=1,
                )
        self._position, self._velocity = position, velocity
        self._sync()

    def _pairs(self, radius: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Every pair within `radius`, with the shortest wrapped separation.

        `cKDTree` knows about the torus and will find the pairs across the seam
        for us, but it hands back indices only -- the displacement still has to
        be wrapped by hand, and getting that wrong shows up as a thin band of
        particles being flung along the edge of the frame.
        """
        tree = cKDTree(self.position, boxsize=self.wrap)
        pairs = tree.query_pairs(radius, output_type="ndarray")
        if not len(pairs):
            return pairs, np.empty((0, 2)), np.empty(0)
        first, second = pairs[:, 0], pairs[:, 1]
        delta = self.position[second] - self.position[first]
        delta -= self.wrap * np.round(delta / self.wrap)
        return pairs, delta, np.hypot(delta[:, 0], delta[:, 1])

    def step(self, count: int = 1) -> None:
        if self.device != "cpu":
            self._step_torch(count)
            return
        for _ in range(count):
            pairs, delta, distance = self._pairs(self.r_max)
            force = np.zeros_like(self.position)
            if len(pairs):
                first, second = pairs[:, 0], pairs[:, 1]
                alive = distance > 1e-9
                first, second = first[alive], second[alive]
                delta, distance = delta[alive], distance[alive]
                unit = delta / distance[:, None]

                # The tent: nothing at r_min, full strength halfway out, nothing
                # again at r_max. Species enters only as a multiplier on it.
                span = self.r_max - self.r_min
                tent = np.clip(
                    1.0 - np.abs(2.0 * distance - self.r_max - self.r_min) / span, 0.0, 1.0
                )
                close = distance < self.r_min
                repulsion = np.where(close, distance / self.r_min - 1.0, 0.0)

                on_first = repulsion + np.where(
                    close, 0.0, self.matrix[self.species[first], self.species[second]] * tent
                )
                on_second = repulsion + np.where(
                    close, 0.0, self.matrix[self.species[second], self.species[first]] * tent
                )

                for axis in (0, 1):
                    # Newton's third law does not hold here and that is the
                    # point: the pull red feels towards green is not the pull
                    # green feels towards red, so momentum is not conserved and
                    # a pair can chase itself across the frame forever.
                    force[:, axis] += np.bincount(
                        first, weights=on_first * unit[:, axis], minlength=len(force)
                    )
                    force[:, axis] -= np.bincount(
                        second, weights=on_second * unit[:, axis], minlength=len(force)
                    )

            if self.band is not None:
                low, high = self.band
                rows = self.position[:, 1]
                force[:, 1] += self.wall * (
                    np.clip(low - rows, 0.0, None) - np.clip(rows - high, 0.0, None)
                )

            self.velocity = self.velocity * self.friction + force * self.strength
            speed = np.hypot(self.velocity[:, 0], self.velocity[:, 1])
            fast = speed > self.speed_limit
            if fast.any():
                self.velocity[fast] *= (self.speed_limit / speed[fast])[:, None]
            self.position = self.position + self.velocity
            self.position[:, 0] %= self.width
            if self.band is None:
                self.position[:, 1] %= self.height
            else:
                self.position[:, 1] = np.clip(self.position[:, 1], 0.0, self.height - 1e-6)

    def metric(self) -> float:
        """How much structure there is: pairs packed within half a radius.

        A uniform gas has a predictable number of these and a frame full of
        membranes has several times as many, so the count rises as the thing
        assembles and flattens once it has -- which is exactly the curve the
        renderer needs to place frames by progress instead of by the clock.
        """
        tree = cKDTree(self.position, boxsize=self.wrap)
        return float(tree.count_neighbors(tree, self.r_max * 0.42) - len(self.position))

    def liveliness(self) -> float:
        return float(np.hypot(self.velocity[:, 0], self.velocity[:, 1]).mean())

    def motility(self, radius: float | None = None, minimum: int = 8) -> tuple[float, float]:
        """What fraction of the particles are in a body, and how fast those move.

        This is the measurement the whole search turns on. Mean speed over
        everything cannot tell a swimmer from a gas: loose particles rattling
        around at random move faster than anything organised ever does. Speed
        measured *only over particles that are part of something* can, because a
        crystal scores zero on it however tightly it is packed, and a thing that
        has assembled itself and is now going somewhere scores high — which is
        the entire difference between a pattern and an animal.
        """
        # Counted inside the repulsion radius, not the interaction radius: at
        # this density a particle has neighbours within the second no matter
        # what it is doing, so a looser test calls the gas bound too and the
        # measurement stops discriminating between anything at all.
        tree = cKDTree(self.position, boxsize=self.wrap)
        neighbours = tree.query_ball_point(
            self.position, (radius or self.r_min * 1.3), return_length=True, workers=-1
        )
        bound = neighbours >= minimum
        if not bound.any():
            return 0.0, 0.0
        speed = np.hypot(self.velocity[bound, 0], self.velocity[bound, 1])
        return float(bound.mean()), float(speed.mean())

    def occupancy(self, cells: int = 24) -> float:
        """Fraction of a coarse grid that has anything in it.

        The failure mode a structure score cannot see: everything collapses into
        one dense lump in a corner of an otherwise empty frame. That scores well
        on packing and looks like nothing at all. Measured over the band rather
        than the frame, because with a band the black margins are not somewhere
        the population failed to reach -- they are somewhere it was never
        allowed to be, and counting them would flatter every candidate equally.
        """
        low, high = self.band if self.band else (0.0, float(self.height))
        columns = np.minimum((self.position[:, 0] / self.width * cells).astype(int), cells - 1)
        rows = np.clip(((self.position[:, 1] - low) / (high - low) * cells).astype(int), 0, cells - 1)
        return float(len(np.unique(rows * cells + columns)) / (cells * cells))


def random_matrix(generator: np.random.Generator, species: int) -> np.ndarray:
    """A table with a diagonal that likes itself and off-diagonals that do not agree.

    Self-attraction on the diagonal is what gives a species something to be a
    clump *of*; the rest is left to the search. Drawing the off-diagonals
    independently is the whole trick -- it is what makes A→B and B→A disagree,
    and a table that disagrees with itself is the only kind that stays in motion.
    """
    matrix = generator.uniform(-1.0, 1.0, (species, species))
    matrix[np.diag_indices(species)] = generator.uniform(0.25, 1.0, species)
    return matrix.astype(np.float32)


def search(
    height: int,
    width: int,
    species: int = 4,
    candidates: int = 16,
    burn_in: int = 220,
    seed: int = 7,
    report=print,
    **model_arguments,
) -> list[tuple[float, np.ndarray]]:
    """Score random tables on how much of the population assembles into bodies,
    how fast those bodies move, and how much of the frame they end up using.

    Any one of the three alone picks something dull. Packing alone finds a
    crystal, which assembles in two seconds and then holds perfectly still.
    Speed alone finds a gas, which never stops moving because nothing ever
    happens to it — so the speed here is measured only over particles that are
    part of a body, which is what makes the difference between a pattern and an
    animal measurable at all. The frame-coverage term throws out the tables
    whose answer to everything is one lump.

    Every candidate runs at the particle count and the interaction radii the
    finished piece uses, because none of this is scale-free: what a table does
    depends on how many neighbours a particle has, and a table ranked in a
    thinner box is a table ranked for a different world. On a GPU that costs a
    few seconds each, which is the only reason it is affordable to be strict
    about it.

    Returns every candidate, best first, so a runner-up can be looked at when
    the winner turns out to be a beautiful score and a dull picture.
    """
    generator = np.random.default_rng(seed)
    ranked: list[tuple[float, np.ndarray]] = []
    for index in range(candidates):
        matrix = random_matrix(generator, species)
        model = ParticleLife(height, width, matrix, seed=seed + index, **model_arguments)
        model.step(burn_in)
        bound, speed = model.motility()
        frame = model.occupancy(32)
        score = bound * speed * frame
        report(
            f"  candidate {index:2d}: bound {bound:4.2f} "
            f"speed {speed:4.2f} frame {frame:4.2f} -> {score:6.3f}"
        )
        ranked.append((float(score), matrix))
    ranked.sort(key=lambda entry: entry[0], reverse=True)
    return ranked
