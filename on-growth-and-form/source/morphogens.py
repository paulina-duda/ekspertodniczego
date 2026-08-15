#!/usr/bin/env python3
"""Three growth processes, each one an algorithm that is also a biology.

The common thread is not a look, it is a claim: that form can be *computed*.
Each of these is a rule simple enough to write in a few lines and rich enough
that a living thing appears to be running it.

* Gray-Scott reaction-diffusion — Turing's morphogens. The man who formalised
  computation spent his last years on why a tiger has stripes, and the answer
  was that two chemicals racing each other are enough.
* Physarum transport network — a slime mould with no brain, no neurons and one
  cell solves shortest-path problems by laying down and following its own
  trail. Computation with no computer in it.
* Differential growth — a closed curve that must lengthen but may not touch
  itself. Cortex, coral and gut villi all fold for the same reason, and the
  reason is a constraint, not a plan.

Everything here is vectorised over the whole population or grid; nothing steps
one cell at a time.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.spatial import cKDTree


def _laplacian(field: np.ndarray) -> np.ndarray:
    """Five-point stencil on a wrapping grid."""
    return (
        np.roll(field, 1, 0)
        + np.roll(field, -1, 0)
        + np.roll(field, 1, 1)
        + np.roll(field, -1, 1)
        - 4.0 * field
    )


def _blur3(field: np.ndarray) -> np.ndarray:
    """3x3 mean on a wrapping grid, as four rolls rather than a convolution."""
    return (
        field
        + np.roll(field, 1, 0)
        + np.roll(field, -1, 0)
        + np.roll(field, 1, 1)
        + np.roll(field, -1, 1)
    ) * 0.2


class GrayScott:
    """Turing morphogenesis: two chemicals, one autocatalytic, both diffusing.

        du/dt = Du * lap(u) - u v^2 + F (1 - u)
        dv/dt = Dv * lap(v) + u v^2 - (F + k) v

    The whole zoo -- spots, stripes, labyrinths, endlessly dividing cells --
    lives in the two numbers F and k. Nothing else changes between them.
    """

    def __init__(
        self,
        height: int,
        width: int,
        feed: float,
        kill: float,
        diffusion: tuple[float, float] = (0.16, 0.08),
        seeds: int = 28,
        seed: int = 20260814,
    ) -> None:
        generator = np.random.default_rng(seed)
        self.u = np.ones((height, width), dtype=np.float32)
        self.v = np.zeros((height, width), dtype=np.float32)
        self.feed, self.kill = feed, kill
        self.diffusion_u, self.diffusion_v = diffusion

        # Seed with a few blots of v. A perfectly uniform field is a fixed
        # point and would sit there forever; the pattern is what the
        # instability does to a disturbance.
        radius = max(3, min(height, width) // 90)
        for _ in range(seeds):
            row = generator.integers(radius, height - radius)
            column = generator.integers(radius, width - radius)
            self.v[row - radius : row + radius, column - radius : column + radius] = 1.0
        self.v += 0.02 * generator.random((height, width)).astype(np.float32)
        np.clip(self.v, 0.0, 1.0, out=self.v)

        # When each cell first crossed into the patterned state. The colony
        # spreads outwards at a roughly constant speed, so this is effectively
        # a growth ring -- the same quantity the folding curve is coloured by,
        # and the reason the two pieces read as one idea.
        self.activation = np.full((height, width), -1.0, dtype=np.float32)
        self.step_index = 0

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            reaction = self.u * self.v * self.v
            self.u += self.diffusion_u * _laplacian(self.u) - reaction + self.feed * (1.0 - self.u)
            self.v += self.diffusion_v * _laplacian(self.v) + reaction - (self.feed + self.kill) * self.v
            np.clip(self.u, 0.0, 1.0, out=self.u)
            np.clip(self.v, 0.0, 1.0, out=self.v)
            self.step_index += 1
            fresh = (self.v > 0.15) & (self.activation < 0.0)
            if fresh.any():
                self.activation[fresh] = float(self.step_index)

    def field(self) -> np.ndarray:
        return self.v

    def growth_rings(self) -> np.ndarray:
        """Activation time normalised to 0..1 over the cells that ever lit."""
        lit = self.activation >= 0.0
        rings = np.zeros_like(self.activation)
        if lit.any():
            values = self.activation[lit]
            low, high = values.min(), values.max()
            rings[lit] = (values - low) / max(high - low, 1e-9)
        return rings


class Physarum:
    """Slime mould transport network, after Jones 2010.

    Every agent does the same three things forever: smell ahead and to each
    side, turn towards whichever smells strongest, walk forward and leave a
    smell of its own. The trail diffuses and evaporates. That is the entire
    model -- there is no graph, no path-finding, no memory of where anything
    is -- and out of it comes a network that keeps rewiring itself towards
    shorter, fatter routes.

    Two populations run at once, each following only its own trail and avoiding
    the other's. They partition the frame between them rather than merging,
    which is what gives the two-colour braid.
    """

    def __init__(
        self,
        height: int,
        width: int,
        agents: int,
        sensor_distance: float = 9.0,
        sensor_angle: float = math.radians(28.0),
        turn_angle: float = math.radians(34.0),
        speed: float = 1.35,
        decay: float = 0.92,
        deposit: float = 1.0,
        avoidance: float = 0.55,
        seed: int = 20260814,
    ) -> None:
        generator = np.random.default_rng(seed)
        self.height, self.width = height, width
        self.sensor_distance = sensor_distance
        self.sensor_angle = sensor_angle
        self.turn_angle = turn_angle
        self.speed = speed
        self.decay = decay
        self.deposit = deposit
        self.avoidance = avoidance

        # Scattered over the whole frame, not released from a central disc.
        # With an empty trail every sensor reads zero, so agents starting
        # together simply fly straight until something is deposited -- which
        # bakes in a radial burst and then reinforces it. Seeding everywhere
        # means there is trail to follow from the first step, and what the clip
        # shows is the network condensing out of noise.
        self.x = generator.uniform(0.0, width, agents).astype(np.float32)
        self.y = generator.uniform(0.0, height, agents).astype(np.float32)
        self.heading = generator.uniform(0.0, 2.0 * math.pi, agents).astype(np.float32)
        self.species = (generator.random(agents) < 0.5).astype(np.int8)
        self.trail = np.zeros((2, height, width), dtype=np.float32)
        self.generator = generator

    def _sample(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Trail strength each agent perceives: own species minus the other."""
        column = np.mod(np.floor(x).astype(np.int64), self.width)
        row = np.mod(np.floor(y).astype(np.int64), self.height)
        own = self.trail[self.species, row, column]
        other = self.trail[1 - self.species, row, column]
        return own - self.avoidance * other

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            for offset, target in (
                (0.0, "front"),
                (self.sensor_angle, "left"),
                (-self.sensor_angle, "right"),
            ):
                angle = self.heading + offset
                value = self._sample(
                    self.x + self.sensor_distance * np.cos(angle),
                    self.y + self.sensor_distance * np.sin(angle),
                )
                if target == "front":
                    front = value
                elif target == "left":
                    left = value
                else:
                    right = value

            # Steer towards the strongest side; when the sides tie but beat the
            # centre, pick one at random -- without that the agents lock into
            # symmetric standoffs and the network never breaks its own grid.
            turn = np.zeros_like(self.heading)
            straight = (front >= left) & (front >= right)
            turn = np.where(left > right, self.turn_angle, -self.turn_angle)
            random_turn = np.where(
                self.generator.random(len(turn)) < 0.5, self.turn_angle, -self.turn_angle
            ).astype(np.float32)
            turn = np.where((left == right) & ~straight, random_turn, turn)
            self.heading = np.where(straight, self.heading, self.heading + turn).astype(np.float32)

            self.x = np.mod(self.x + self.speed * np.cos(self.heading), self.width).astype(np.float32)
            self.y = np.mod(self.y + self.speed * np.sin(self.heading), self.height).astype(np.float32)

            # Clamp rather than trust the wrap: in float32, np.mod of a value a
            # hair below zero rounds up to exactly the modulus, which lands one
            # cell past the end of the grid.
            column = np.minimum(self.x.astype(np.int32), self.width - 1)
            row = np.minimum(self.y.astype(np.int32), self.height - 1)
            flat = row.astype(np.int64) * self.width + column
            for index in (0, 1):
                mask = self.species == index
                if mask.any():
                    self.trail[index].reshape(-1)[:] += np.bincount(
                        flat[mask], minlength=self.height * self.width
                    ).astype(np.float32) * self.deposit

            self.trail[0] = _blur3(self.trail[0]) * self.decay
            self.trail[1] = _blur3(self.trail[1]) * self.decay

    def field(self) -> tuple[np.ndarray, np.ndarray]:
        return self.trail[0], self.trail[1]


class DifferentialGrowth:
    """A closed curve that must lengthen and may not touch itself.

    Neighbouring nodes pull together to keep the spacing even, every node
    pushes away anything that comes too close, and new nodes are inserted
    wherever an edge stretches too far. Length has to go somewhere and the only
    direction left is sideways, so the curve folds -- the same argument that
    explains a brain's gyri, a coral's rim and the villi of a gut.
    """

    def __init__(
        self,
        centre: tuple[float, float],
        radius: float,
        nodes: int = 220,
        spacing: float = 5.0,
        repulsion_radius: float = 13.0,
        attraction: float = 0.42,
        repulsion: float = 0.62,
        node_limit: int = 90_000,
        seed: int = 20260814,
    ) -> None:
        angle = np.linspace(0.0, 2.0 * math.pi, nodes, endpoint=False)
        generator = np.random.default_rng(seed)
        wobble = 1.0 + 0.03 * generator.standard_normal(nodes)
        self.points = np.column_stack((
            centre[0] + radius * wobble * np.cos(angle),
            centre[1] + radius * wobble * np.sin(angle),
        )).astype(np.float32)
        self.spacing = spacing
        self.repulsion_radius = repulsion_radius
        self.attraction = attraction
        self.repulsion = repulsion
        self.node_limit = node_limit
        self.generator = generator
        # Age in growth steps, so the render can show which folds are old.
        self.age = np.zeros(len(self.points), dtype=np.float32)
        self.step_index = 0

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            self.step_index += 1
            points = self.points
            total = len(points)

            following = np.roll(points, -1, axis=0)
            preceding = np.roll(points, 1, axis=0)
            pull = (following + preceding) * 0.5 - points

            tree = cKDTree(points)
            pairs = tree.query_pairs(self.repulsion_radius, output_type="ndarray")
            push = np.zeros_like(points)
            if len(pairs):
                # Skip immediate neighbours along the curve: they are supposed
                # to be close, and pushing them apart just fights the spacing
                # term. Wrapping makes index 0 and the last node adjacent too.
                gap = np.abs(pairs[:, 0] - pairs[:, 1])
                separated = (gap > 1) & (gap < total - 1)
                pairs = pairs[separated]
            if len(pairs):
                offset = points[pairs[:, 0]] - points[pairs[:, 1]]
                distance = np.linalg.norm(offset, axis=1, keepdims=True)
                strength = offset / np.maximum(distance, 1e-6) ** 2
                np.add.at(push, pairs[:, 0], strength)
                np.add.at(push, pairs[:, 1], -strength)

            points = points + self.attraction * pull + self.repulsion * push
            self.points = points.astype(np.float32)
            self._resample()

    def _resample(self) -> None:
        """Insert a node in the middle of every over-stretched edge."""
        if len(self.points) >= self.node_limit:
            return
        following = np.roll(self.points, -1, axis=0)
        length = np.linalg.norm(following - self.points, axis=1)
        split = np.nonzero(length > self.spacing)[0]
        if not len(split):
            return

        midpoints = (self.points[split] + following[split]) * 0.5
        # Jitter the new node off the chord. On a straight run the midpoint is
        # exactly collinear, the repulsion term is then perfectly balanced, and
        # the curve grows without ever choosing a side to fold towards.
        midpoints += 0.01 * self.spacing * self.generator.standard_normal(midpoints.shape)

        order = np.argsort(split)
        self.points = np.insert(self.points, split[order] + 1, midpoints[order], axis=0)
        self.age = np.insert(
            self.age, split[order] + 1, np.full(len(split), float(self.step_index)), axis=0
        ).astype(np.float32)

    def curvature(self) -> np.ndarray:
        """Turning angle at each node, as a stand-in for local fold tightness."""
        following = np.roll(self.points, -1, axis=0)
        preceding = np.roll(self.points, 1, axis=0)
        incoming = self.points - preceding
        outgoing = following - self.points
        incoming /= np.maximum(np.linalg.norm(incoming, axis=1, keepdims=True), 1e-9)
        outgoing /= np.maximum(np.linalg.norm(outgoing, axis=1, keepdims=True), 1e-9)
        cosine = np.clip((incoming * outgoing).sum(axis=1), -1.0, 1.0)
        return np.arccos(cosine).astype(np.float32)
