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
        band: tuple[float, float] | None = None,
        seed: int = 20260814,
    ) -> None:
        generator = np.random.default_rng(seed)
        self.height, self.width = height, width
        # A band turns the frame into a cylinder: it still wraps left to right,
        # and top to bottom the agents turn back at the margin. Reflection
        # rather than a spring, because an agent has a heading rather than a
        # velocity -- there is nothing to decelerate, so the honest equivalent
        # of a soft wall is to bounce it and let its own sensors take over
        # again. The trail is not deposited outside the band either, so the
        # network genuinely ends there instead of being cropped.
        self.band = None if band is None else (float(band[0]), float(band[1]))
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
        low, high = self.band if self.band else (0.0, float(height))
        self.x = generator.uniform(0.0, width, agents).astype(np.float32)
        self.y = generator.uniform(low, high, agents).astype(np.float32)
        self.heading = generator.uniform(0.0, 2.0 * math.pi, agents).astype(np.float32)
        self.species = (generator.random(agents) < 0.5).astype(np.int8)
        self.trail = np.zeros((2, height, width), dtype=np.float32)
        self.generator = generator

    def _sample(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Trail strength each agent perceives: own species minus the other.

        With a band the vertical does not wrap, so the sensor is clamped rather
        than wrapped: letting an agent at the top of the band smell the trail at
        the bottom would stitch the network across the black margin, which is
        the one thing the margin exists to prevent.
        """
        column = np.mod(np.floor(x).astype(np.int64), self.width)
        if self.band is None:
            row = np.mod(np.floor(y).astype(np.int64), self.height)
        else:
            row = np.clip(np.floor(y).astype(np.int64), 0, self.height - 1)
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
            if self.band is None:
                self.y = np.mod(self.y + self.speed * np.sin(self.heading), self.height).astype(np.float32)
            else:
                # Reflect at the band: mirror the position back inside and flip
                # the heading's vertical component, which is what a wall does to
                # something that walks rather than falls.
                low, high = self.band
                stepped = self.y + self.speed * np.sin(self.heading)
                turned = (stepped < low) | (stepped > high)
                stepped = np.where(stepped < low, 2.0 * low - stepped, stepped)
                stepped = np.where(stepped > high, 2.0 * high - stepped, stepped)
                self.y = np.clip(stepped, low, high).astype(np.float32)
                self.heading = np.where(turned, -self.heading, self.heading).astype(np.float32)

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

    Pass `wall` to run the same rule inside a circle it may not grow past,
    which is the cortex case rather than the coral one: growth is free until
    the form reaches the boundary, and after that lengthening can only be paid
    for by crowding inward. Growth here is stretch-driven -- an edge subdivides
    when it is pulled past `spacing` -- so confinement does not just redirect
    the growth, it slows it. That is measured and it is why the wall belongs
    late in a clip rather than early.
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
        wall: float | None = None,
        wall_stiffness: float = 0.35,
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
        # An optional circular wall the curve may not grow past -- a skull, in
        # effect. It is a *soft* restoring force that only switches on outside
        # the radius: a hard clamp stacks every arriving node on the same
        # circle and draws a bright rim the rule never made. With this the
        # boundary presses flat but stays ragged (measured: about 8 px of
        # spread on the outermost shell at the shipped scale).
        self.centre = np.array(centre, dtype=np.float32)
        self.wall = wall
        self.wall_stiffness = wall_stiffness
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
            if self.wall is not None:
                radial = points - self.centre
                distance = np.linalg.norm(radial, axis=1, keepdims=True)
                excess = np.maximum(distance - self.wall, 0.0)
                points = points - self.wall_stiffness * excess * (
                    radial / np.maximum(distance, 1e-6)
                )
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


class SegmentationClock:
    """The vertebrate segmentation clock: an oscillator and a receding front.

    Every cell in the presomitic mesoderm runs the same oscillator, and its
    period lengthens with distance from the tail. Nothing travels, but the
    phase lag between neighbours draws a band that sweeps forward anyway --
    the trick a row of blinking lights plays, or a stadium wave. A
    determination front sits a fixed distance ahead of the tail and recedes
    with it as the body elongates; the moment it passes a cell, that cell
    stops oscillating and keeps whatever phase it was holding.

    One turn of the clock at the tail is one segment, because the front covers
    exactly one segment's worth of tissue in one period. The body is therefore
    counted rather than measured, and a snake gets its several hundred
    vertebrae from a faster clock rather than from a longer body (Gomez 2008).

    Frame coordinates throughout: the axis runs down the frame, anterior at the
    top, the tail advancing towards the bottom. `steps` is the length of the
    run, not of the clip -- it fixes how far the tail gets, and everything else
    is derived from it, so a longer clip plays the same process more slowly
    rather than a different process.
    """

    def __init__(
        self,
        height: int,
        width: int,
        steps: int,
        somite: float = 135.0,
        psm_ratio: float = 4.5,
        band: float = 135.0,
        gap: float = 46.0,
        tail_start: float = 520.0,
        tail_end: float = 1400.0,
        spacing: float = 5.0,
        decay: float = 2.4,
        coupling: float = 0.08,
        wander: float = 0.26,
        phase_noise: float = 0.0025,
        densify: float = 1.50,
        cohesion: float = 0.09,
        tension: float = 0.006,
        pressure: float = 0.35,
        wall: float = 0.05,
        tip: float = 110.0,
        grow_zone: float = 170.0,
        seed: int = 20260829,
    ) -> None:
        self.height, self.width = height, width
        self.centre = width * 0.5
        self.somite = somite
        self.psm = somite * psm_ratio
        self.band, self.gap = band, gap
        self.tip, self.grow_zone = tip, grow_zone
        self.tail_start, self.tail_end = tail_start, tail_end
        self.speed = (tail_end - tail_start) / max(steps, 1)
        self.period = somite / self.speed
        self.omega = 2.0 * math.pi / self.period
        self.decay = decay
        self.coupling = coupling
        self.wander = wander
        self.phase_noise = phase_noise
        self.densify = densify
        self.cohesion = cohesion
        self.tension = tension
        self.pressure = pressure
        self.wall = wall
        self.density = 1.0 / (spacing * spacing)
        self.generator = np.random.default_rng(seed)
        self.step_index = 0

        # Grid for the density and phase averages. It has to reach above the
        # frame: the front starts off the top edge, so the first segments are
        # made out of sight and would otherwise pile into row zero.
        self.cell_size = 7.0
        self.grid_top = -320.0
        self.grid_rows = int(math.ceil((height - self.grid_top) / self.cell_size)) + 1
        self.grid_columns = int(math.ceil(width / self.cell_size)) + 1

        capacity = 4096
        self.x = np.zeros(capacity, dtype=np.float32)
        self.y = np.zeros(capacity, dtype=np.float32)
        self.phase = np.zeros(capacity, dtype=np.float32)
        self.side = np.zeros(capacity, dtype=np.int8)
        self.frozen = np.zeros(capacity, dtype=bool)
        self.segment = np.zeros(capacity, dtype=np.int64)
        self.slot = np.full(capacity, -1, dtype=np.int32)
        self.count = 0

        self.slot_x: list[float] = []
        self.slot_y: list[float] = []
        self.slot_r: list[float] = []
        self.slot_key: dict[tuple[int, int], int] = {}
        self.closed: set[int] = set()

        self._seed_tissue()

    # -- geometry ---------------------------------------------------------

    def tail(self) -> float:
        return self.tail_start + self.speed * self.step_index

    def front(self) -> float:
        return self.tail() - self.psm

    def outline(self, u):
        """Inner and outer half-width of the tissue `u` ahead of the tail.

        The two bands of mesoderm are separated by the neural tube everywhere
        except at the tail, where they are still one mass -- so the gap closes
        and the whole thing rounds off into the bud rather than ending on a
        straight cut.
        """
        t = np.clip(u / self.tip, 0.0, 1.0)
        outer = (self.gap + self.band) * np.sqrt(t)
        inner = self.gap * np.clip(u / (self.tip * 0.75), 0.0, 1.0)
        return inner, outer

    def initial_phase(self, u):
        """Steady-state phase profile, so the clip opens mid-process.

        Integrating the frequency gradient along a cell's trip from the tail:
        the lag grows almost linearly once the frequency has dropped, and is
        flat at the tail itself, which is why the bud pulses as one piece.
        """
        span = np.clip(u / self.psm, 0.0, 1.0)
        return (
            -2.0 * math.pi * u / self.somite
            + 2.0 * math.pi * self.psm / (self.decay * self.somite)
            * (1.0 - np.exp(-self.decay * span))
        ).astype(np.float32)

    # -- population -------------------------------------------------------

    def _grow_arrays(self, extra: int) -> None:
        if self.count + extra <= len(self.x):
            return
        size = len(self.x)
        while size < self.count + extra:
            size *= 2
        for name, fill in (
            ("x", 0.0), ("y", 0.0), ("phase", 0.0), ("side", 0),
            ("frozen", False), ("segment", 0), ("slot", -1),
        ):
            old = getattr(self, name)
            new = np.full(size, fill, dtype=old.dtype)
            new[: self.count] = old[: self.count]
            setattr(self, name, new)

    def _spawn(self, low: float, high: float, number: int, phase=None) -> None:
        if number <= 0:
            return
        self._grow_arrays(number)
        tail = self.tail()
        u = self.generator.uniform(low, high, number)
        inner, outer = self.outline(u)
        radius = self.generator.uniform(inner, outer)
        side = np.where(self.generator.random(number) < 0.5, -1, 1)
        start, end = self.count, self.count + number
        self.x[start:end] = (self.centre + side * radius).astype(np.float32)
        self.y[start:end] = (tail - u).astype(np.float32)
        self.side[start:end] = side.astype(np.int8)
        self.frozen[start:end] = False
        self.slot[start:end] = -1
        if phase is None:
            # A new cell is a daughter of the ones already there, so it starts
            # on their phase, not on a fresh one. Where there is nothing yet --
            # the very tip -- it takes the tail's.
            local, known = self._local_phase(self.x[start:end], self.y[start:end])
            phase = np.where(known, local, self.omega * self.step_index)
        self.phase[start:end] = phase
        self.count = end

    def _seed_tissue(self) -> None:
        """One presomitic mesoderm, no segments yet, already oscillating."""
        area = 2.0 * self.band * self.psm
        number = int(area * self.density)
        self._spawn(0.0, self.psm, number, phase=None)
        u = self.tail() - self.y[: self.count]
        self.phase[: self.count] = self.initial_phase(u)

    def _replenish(self) -> None:
        """Top the growth zone back up to density as the tail runs away.

        Cells are added where the tissue is short of what its own outline
        allows, which is both how a tail bud works and the only way to keep the
        density constant while the bands widen out behind the tip.
        """
        tail = self.tail()
        edges = np.linspace(0.0, self.grow_zone, 18)
        u = tail - self.y[: self.count]
        counts, _ = np.histogram(u, bins=edges)
        for index in range(len(edges) - 1):
            low, high = float(edges[index]), float(edges[index + 1])
            inner, outer = self.outline(0.5 * (low + high))
            area = 2.0 * max(float(outer) - float(inner), 0.0) * (high - low)
            missing = int(round(area * self.density)) - int(counts[index])
            if missing > 0:
                self._spawn(low, high, missing)

    # -- fields -----------------------------------------------------------

    def _bins(self, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        column = np.clip((x / self.cell_size).astype(np.int64), 0, self.grid_columns - 1)
        row = np.clip(((y - self.grid_top) / self.cell_size).astype(np.int64), 0, self.grid_rows - 1)
        return row, column

    def _local_phase(self, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Mean phase of the oscillating cells around each position."""
        live = ~self.frozen[: self.count]
        row, column = self._bins(self.x[: self.count][live], self.y[: self.count][live])
        flat = row * self.grid_columns + column
        size = self.grid_rows * self.grid_columns
        total = np.bincount(flat, weights=self.phase[: self.count][live], minlength=size)
        weight = np.bincount(flat, minlength=size)
        total = _blur3(total.reshape(self.grid_rows, self.grid_columns).astype(np.float32))
        weight = _blur3(weight.reshape(self.grid_rows, self.grid_columns).astype(np.float32))
        row, column = self._bins(x, y)
        near = weight[row, column]
        return total[row, column] / np.maximum(near, 1e-6), near > 0.05

    def _crowding_gradient(self) -> tuple[np.ndarray, np.ndarray]:
        """Downhill push out of crowding -- and only out of crowding.

        Taking the gradient of the density itself puts an outward force on
        every edge in the picture, which walks the population into the walls
        and lights a rim along them. What a packed tissue actually resists is
        being *over*filled, so the field is the excess over the resting density
        and is flat everywhere the tissue is merely full.
        """
        row, column = self._bins(self.x[: self.count], self.y[: self.count])
        flat = row * self.grid_columns + column
        field = np.bincount(flat, minlength=self.grid_rows * self.grid_columns)
        field = field.reshape(self.grid_rows, self.grid_columns).astype(np.float32)
        for _ in range(3):
            field = _blur3(field)
        field = np.clip(field - self.density * self.cell_size ** 2, 0.0, None)
        gradient_x = 0.5 * (np.roll(field, -1, 1) - np.roll(field, 1, 1))
        gradient_y = 0.5 * (np.roll(field, -1, 0) - np.roll(field, 1, 0))
        return -gradient_x[row, column], -gradient_y[row, column]

    # -- the rule ---------------------------------------------------------

    def _widen(self) -> None:
        """Carry the tissue outwards with the outline as the bands open up.

        Every slice of tissue spends its first hundred pixels inside the tail's
        taper, where the two bands are still separating and the section is
        still growing. A tissue that widens takes its own cells with it; it
        does not slide them through itself. Evicting them with a wall instead
        pushes the entire population past the inner edge on its way out of the
        bud and lights a rim down the axis that the rule never made.
        """
        count = self.count
        distance = self.tail() - self.y[:count]
        inside = (~self.frozen[:count]) & (distance < self.tip + self.speed)
        if not inside.any():
            return
        now = np.clip(distance[inside], 0.0, None)
        before = np.clip(now - self.speed, 0.0, None)
        inner_before, outer_before = self.outline(before)
        inner_now, outer_now = self.outline(now)
        reach = np.abs(self.x[:count][inside] - self.centre)
        fraction = np.clip(
            (reach - inner_before) / np.maximum(outer_before - inner_before, 0.5), 0.0, 1.0
        )
        direction = np.sign(self.x[:count][inside] - self.centre)
        direction = np.where(direction == 0.0, 1.0, direction)
        moved = inner_now + fraction * (outer_now - inner_now)
        self.x[np.flatnonzero(inside)] = (self.centre + direction * moved).astype(np.float32)

    def _oscillate(self) -> None:
        count = self.count
        live = ~self.frozen[:count]
        if not live.any():
            return
        u = np.clip(self.tail() - self.y[:count], 0.0, None)
        rate = self.omega * np.exp(-self.decay * np.clip(u / self.psm, 0.0, 1.0))
        noise = self.generator.standard_normal(count).astype(np.float32) * self.phase_noise
        self.phase[:count] = np.where(live, self.phase[:count] + rate + noise, self.phase[:count])
        if self.coupling > 0.0:
            # Neighbours pull each other back into step. Without it the cells
            # added at the tail drift apart and the bands smear into mush --
            # which is also what happens to a real embryo that loses its
            # Delta-Notch coupling: the segments come out ragged.
            mean, known = self._local_phase(self.x[:count], self.y[:count])
            adjust = np.where(live & known, self.coupling * (mean - self.phase[:count]), 0.0)
            self.phase[:count] += adjust.astype(np.float32)

    def _arrest(self) -> None:
        count = self.count
        crossed = (~self.frozen[:count]) & (self.y[:count] <= self.front())
        if not crossed.any():
            return
        self.frozen[:count] = self.frozen[:count] | crossed
        turns = np.floor(self.phase[:count] / (2.0 * math.pi)).astype(np.int64)
        self.segment[:count] = np.where(crossed, turns, self.segment[:count])

    def _close(self) -> None:
        """A segment that has stopped accreting rounds up and packs tighter.

        Epithelialisation, and the reason the column reads as beads rather than
        as a stripe: the block pulls itself in until it is denser than the
        tissue it came out of, and a fissure opens where it has drawn away from
        its neighbour.
        """
        count = self.count
        frozen = self.frozen[:count]
        if not frozen.any():
            return
        segments = self.segment[:count][frozen]
        newest = int(segments.max())
        homeless = frozen & (self.slot[:count] < 0)
        if not homeless.any():
            return
        for index in np.unique(self.segment[:count][homeless]):
            index = int(index)
            if index >= newest:
                continue
            for side in (-1, 1):
                mask = homeless & (self.segment[:count] == index) & (self.side[:count] == side)
                number = int(mask.sum())
                if not number:
                    continue
                key = (index, side)
                if key in self.slot_key:
                    # A cell whose phase lagged crosses the front late and
                    # arrests into a block that has already closed. It belongs
                    # to that block; leaving it behind scatters loose cells
                    # down the fissures that the rule never put there.
                    self.slot[:count] = np.where(mask, self.slot_key[key], self.slot[:count])
                    continue
                if number < 12:
                    continue
                self.slot_key[key] = len(self.slot_x)
                self.slot[:count] = np.where(mask, len(self.slot_x), self.slot[:count])
                self.slot_x.append(float(self.x[:count][mask].mean()))
                self.slot_y.append(float(self.y[:count][mask].mean()))
                self.slot_r.append(math.sqrt(number / (math.pi * self.density * self.densify)))
            self.closed.add(index)

    def _relax(self) -> None:
        count = self.count
        x, y = self.x[:count], self.y[:count]
        live = ~self.frozen[:count]
        push_x, push_y = self._crowding_gradient()
        move_x = self.pressure * push_x
        move_y = self.pressure * push_y

        held = self.slot[:count] >= 0
        if held.any():
            slot = self.slot[:count][held]
            centre_x = np.asarray(self.slot_x, dtype=np.float32)[slot]
            centre_y = np.asarray(self.slot_y, dtype=np.float32)[slot]
            target = np.asarray(self.slot_r, dtype=np.float32)[slot]
            offset_x = x[held] - centre_x
            offset_y = y[held] - centre_y
            square = offset_x * offset_x + offset_y * offset_y
            # Contract the block as a whole, rather than dragging whatever
            # lies outside a target circle onto it. The second is what a
            # surface tension does to a block that is already the right size,
            # and it empties the middle out into a ring.
            spread = np.bincount(slot, weights=square, minlength=len(self.slot_r))
            members = np.bincount(slot, minlength=len(self.slot_r))
            reached = np.sqrt(2.0 * spread / np.maximum(members, 1))
            shrink = np.clip(1.0 - target / np.maximum(reached[slot], 1e-3), 0.0, 1.0)
            corner = np.clip(1.0 - target / np.maximum(np.sqrt(square), 1e-3), 0.0, None)
            pull = self.cohesion * shrink + self.tension * corner
            move_x[held] -= pull * offset_x
            move_y[held] -= pull * offset_y

        if live.any():
            tail = self.tail()
            inner, outer = self.outline(np.clip(tail - y, 0.0, None))
            reach = np.abs(x - self.centre)
            direction = np.sign(x - self.centre)
            direction = np.where(direction == 0.0, 1.0, direction)
            # Only a net for what the wander walks out; the widening is what
            # actually keeps the section full.
            over = np.clip(reach - outer, 0.0, None)
            under = np.clip(inner - reach, 0.0, None)
            move_x += np.where(live, self.wall * direction * (under - over), 0.0)
            move_y += np.where(live, -self.wall * np.clip(y - tail, 0.0, None), 0.0)
            wander = self.generator.standard_normal((2, count)).astype(np.float32) * self.wander
            move_x += np.where(live, wander[0], 0.0)
            move_y += np.where(live, wander[1], 0.0)

        self.x[:count] = (x + move_x).astype(np.float32)
        self.y[:count] = (y + move_y).astype(np.float32)

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            self.step_index += 1
            self._widen()
            self._replenish()
            self._oscillate()
            self._arrest()
            self._close()
            self._relax()

    # -- output -----------------------------------------------------------

    def cells(self) -> tuple[np.ndarray, np.ndarray]:
        """Positions, and the clock phase each cell is holding, wrapped to 0..1."""
        count = self.count
        points = np.column_stack((self.x[:count], self.y[:count])).astype(np.float32)
        shade = np.mod(self.phase[:count] / (2.0 * math.pi), 1.0).astype(np.float32)
        return points, shade



def _capsule(x, y, a, b, radius):
    """Inside test for a thick line segment, used to draw the section."""
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    length = dx * dx + dy * dy
    t = np.clip(((x - ax) * dx + (y - ay) * dy) / max(length, 1e-9), 0.0, 1.0)
    return (x - (ax + t * dx)) ** 2 + (y - (ay + t * dy)) ** 2 <= radius * radius


def _element_stiffness(poisson: float = 0.3) -> np.ndarray:
    """Stiffness of a unit square bilinear element, unit modulus, plane stress."""
    k = np.array([
        1 / 2 - poisson / 6, 1 / 8 + poisson / 8, -1 / 4 - poisson / 12, -1 / 8 + 3 * poisson / 8,
        -1 / 4 + poisson / 12, -1 / 8 - poisson / 8, poisson / 6, 1 / 8 - 3 * poisson / 8,
    ])
    order = np.array([
        [0, 1, 2, 3, 4, 5, 6, 7],
        [1, 0, 7, 6, 5, 4, 3, 2],
        [2, 7, 0, 5, 6, 3, 4, 1],
        [3, 6, 5, 0, 7, 2, 1, 4],
        [4, 5, 6, 7, 0, 1, 2, 3],
        [5, 4, 3, 2, 1, 0, 7, 6],
        [6, 3, 4, 1, 2, 7, 0, 5],
        [7, 2, 1, 4, 3, 6, 5, 0],
    ])
    return (k[order] / (1.0 - poisson * poisson)).astype(np.float64)


class Trabecula:
    """Bone remodelling: every patch of bone thickens if it is worked hard.

    A coronal section of the proximal femur, loaded the three ways one leg is
    loaded, with one rule running everywhere inside its cortex: measure how
    much strain energy this patch is storing per unit of its own mass, and
    move its density towards a set point. Above it, deposit. Below it, resorb.
    That is Frost's mechanostat, and it is Wolff's law written as something a
    cell could actually execute -- an osteocyte is walled into the mineral and
    can feel its own neighbourhood and nothing else. There is no budget, no
    target shape, and no coordination between two patches that are not
    touching.

    What comes out is trabecular architecture: a compressive group running
    from the head down the medial calcar, a tensile group arcing over the neck
    to the greater trochanter, and the hollow between them that Ward named in
    1838. Nobody put an arch in the rule.

    The stiffness fed back into the next solve goes as the cube of density,
    which is not a numerical convenience -- it is the measured relation for
    trabecular bone (Carter & Hayes 1977), and it is also what makes the rule
    unstable in the useful direction. A strut that thickens takes a
    disproportionate share of the load, so a smooth sheet of tissue breaks up
    into separate struts instead of staying a sheet.
    """

    # The section, in units of the frame width so a circle stays a circle.
    # Head up and to the right, which is where the title is not; the shaft is
    # cut flat below the lesser trochanter, which is where a section of this
    # bone is actually cut, so the black under it is an anatomical fact rather
    # than a margin.
    HEAD = (0.6889, 0.5333)
    HEAD_RADIUS = 0.1611
    NECK_JUNCTION = (0.5000, 0.7889)
    NECK_RADIUS = 0.0889
    TROCHANTER = (0.2889, 0.6333)
    TROCHANTER_RADIUS = 0.1500
    CORTEX = ((0.2778, 0.6667), (0.4667, 0.9556), 0.0889)
    LESSER = ((0.3889, 0.8667), (0.3222, 0.9333), 0.0444)
    SHAFT = (0.3667, 0.6000, 0.7556, 1.3000)   # left, right, top, bottom

    # The load history, not a load. Standing on one leg is one of three
    # postures this bone is asked to survive, and the weights are how often
    # each is met -- the three-case history bone-remodelling work has used
    # since Carter, Orr and Fyhrie (1989). Angles are from the vertical in the
    # frontal plane, positive towards the lateral side; the joint presses down
    # into the head, the abductors pull the trochanter back up.
    #
    # This is the piece. Under a single load case the head comes out hollow
    # and the answer is a bare truss, because one load has exactly one
    # cheapest path and nothing has to be spent covering the others. The
    # arcades only appear once no single path will do.
    STANCE = (
        (0.6, 2.317, 24.0, 1.55, 28.0),    # midstance of gait
        (0.2, 1.548, -15.0, 0.78, -8.0),   # extreme abduction
        (0.2, 1.548, 56.0, 0.78, 35.0),    # extreme adduction
    )

    # Trabecular bone's stiffness against its apparent density: E goes as the
    # cube. Measured, not chosen.
    EXPONENT = 3.0

    def __init__(
        self,
        height: int,
        width: int,
        divisor: int = 3,
        sensing: float = 2.6,
        setpoint: float = 0.5,
        rate: float = 0.055,
        seed_density: float = 0.32,
        floor_density: float = 0.02,
        modulus_floor: float = 1e-9,
    ) -> None:
        from scipy.ndimage import distance_transform_edt
        from scipy.sparse import coo_matrix
        from scipy.sparse.linalg import splu

        self._splu = splu
        self._coo = coo_matrix
        self.divisor = divisor
        self.nelx, self.nely = width // divisor, height // divisor
        self.rate = rate
        self.floor_density = floor_density
        self.floor = modulus_floor
        self.iteration = 0

        nelx, nely = self.nelx, self.nely
        columns = (np.arange(nelx) + 0.5) / nelx
        rows = (np.arange(nely) + 0.5) / nelx
        grid_x, grid_y = np.meshgrid(columns, rows)

        section = _capsule(grid_x, grid_y, self.HEAD, self.HEAD, self.HEAD_RADIUS)
        section |= _capsule(grid_x, grid_y, self.HEAD, self.NECK_JUNCTION, self.NECK_RADIUS)
        section |= _capsule(grid_x, grid_y, self.TROCHANTER, self.TROCHANTER, self.TROCHANTER_RADIUS)
        section |= _capsule(grid_x, grid_y, *self.CORTEX)
        left, right, top, bottom = self.SHAFT
        section |= (grid_x > left) & (grid_x < right) & (grid_y > top) & (grid_y < bottom)
        section |= _capsule(grid_x, grid_y, *self.LESSER)
        self.section = section

        # A cortex, held solid, and only what is inside it is remodelled.
        # Cortical bone is dense lamellar bone turning over on a different
        # clock from the trabeculae, so holding it fixed is the honest model;
        # it is also the only reason the frame still reads as a bone rather
        # than as a diagram of one. Thick down the shaft, thin over the head
        # and the trochanter, which is how the section is actually built.
        depth = distance_transform_edt(section)
        thickness = np.where(grid_y > self.NECK_JUNCTION[1], 5.0, 2.0)
        shell = section & (depth <= thickness)

        # Element and node bookkeeping in the usual order: element (column,
        # row) is column*nely + row, node (column, row) is column*(nely+1) +
        # row, both counting rows from the top of the frame.
        active = np.nonzero(section.ravel(order="F"))[0]
        self.active = active
        self.count = len(active)
        self.solid = shell.ravel(order="F")[active]
        self.design = np.nonzero(~self.solid)[0]

        column = active // nely
        row = active % nely
        first = (nely + 1) * column + row
        second = (nely + 1) * (column + 1) + row
        self.dofs = np.column_stack((
            2 * first + 2, 2 * first + 3, 2 * second + 2, 2 * second + 3,
            2 * second, 2 * second + 1, 2 * first, 2 * first + 1,
        ))

        self.stiffness = _element_stiffness()
        self._template = self.stiffness.ravel()

        # Only the section is solved. Filling the void with a token modulus is
        # the textbook trick, but four fifths of this frame is void and the
        # conditioning it buys is not worth paying for on every frame.
        touched = np.unique(self.dofs)
        self.free = np.setdiff1d(touched, self._support(nelx, nely))
        self._index = np.full(2 * (nelx + 1) * (nely + 1), -1, dtype=np.int64)
        self._index[self.free] = np.arange(len(self.free))
        local = self._index[self.dofs]
        keep = (local[:, :, None] >= 0) & (local[:, None, :] >= 0)
        self._keep = keep.ravel()
        self._sparse_rows = np.repeat(local, 8, axis=1).ravel()[self._keep]
        self._sparse_columns = np.tile(local, 8).ravel()[self._keep]
        self._load(nelx, nely)

        centres = np.column_stack((column.astype(np.float64), row.astype(np.float64)))
        # Over the design elements only: smoothing across the cortex would
        # blur the one edge in the picture that is meant to be sharp.
        self._sensors(centres[self.design], sensing)

        self.physical = np.ones(self.count)
        self.physical[self.design] = seed_density
        self.compression = np.zeros(self.count)
        self.tension = np.zeros(self.count)

        # The set point is read off the section's own first state rather than
        # carried in as a number: a body weight and a frame width do not
        # between them fix what "worked hard" means. Taking a quantile means a
        # known fraction of the tissue starts above its set point and the rest
        # below, and the architecture is what that split does over a few
        # hundred turns.
        stimulus = self._stimulus(self._measure())
        self.setpoint = float(np.quantile(stimulus, setpoint))
        self.scale = 1.0 / max(float(np.abs(stimulus - self.setpoint).mean()), 1e-30)

    # ---- the section's boundary conditions -------------------------------

    def _node(self, x: float, y: float) -> int:
        return (self.nely + 1) * int(round(x * self.nelx)) + int(round(y * self.nelx))

    def _support(self, nelx: int, nely: int) -> np.ndarray:
        """The distal cut is held. A section of bone ends where it was sawn."""
        left, right, _, bottom = self.SHAFT
        row = int(round(bottom * nelx))
        columns = np.arange(int(round(left * nelx)), int(round(right * nelx)) + 1)
        nodes = (nely + 1) * columns + row
        return np.concatenate((2 * nodes, 2 * nodes + 1))

    def _load(self, nelx: int, nely: int) -> None:
        self.force = np.zeros((len(self.free), len(self.STANCE)))
        self.share = np.array([case[0] for case in self.STANCE])
        for case, (_, joint, joint_angle, pull, pull_angle) in enumerate(self.STANCE):
            for centre, radius, angle, magnitude, spread, sense in (
                (self.HEAD, self.HEAD_RADIUS, joint_angle, joint, 26.0, 1.0),
                (self.TROCHANTER, self.TROCHANTER_RADIUS, pull_angle, pull, 22.0, -1.0),
            ):
                theta = math.radians(angle)
                direction = sense * np.array([-math.sin(theta), math.cos(theta)])
                # Spread over the contact patch the force comes through. A
                # point load invents a stress singularity, and the tissue will
                # happily build a rosette around one.
                surface = math.atan2(-direction[1], -direction[0])
                nodes = {
                    self._node(centre[0] + radius * math.cos(surface + offset),
                               centre[1] + radius * math.sin(surface + offset))
                    for offset in np.linspace(-math.radians(spread), math.radians(spread), 9)
                }
                portion = magnitude / len(nodes)
                for node in nodes:
                    for dof, component in ((2 * node, direction[0]), (2 * node + 1, direction[1])):
                        slot = self._index[dof]
                        if slot >= 0:
                            self.force[slot, case] += portion * component

    def _sensors(self, centres: np.ndarray, distance: float) -> None:
        """How far a cell can feel, as a weight that falls off with range.

        The influence of an osteocyte decays exponentially with distance,
        after Mullender and Huiskes. It is the only length in the rule, and it
        is what decides how thick a trabecula comes out and how far apart they
        stand -- without it every element would remodel alone and the answer
        would be noise at the resolution of the grid.
        """
        size = len(centres)
        tree = cKDTree(centres)
        pairs = tree.query_pairs(4.0 * distance, output_type="ndarray")
        span = np.linalg.norm(centres[pairs[:, 0]] - centres[pairs[:, 1]], axis=1)
        weight = np.exp(-span / distance)
        rows = np.concatenate((pairs[:, 0], pairs[:, 1], np.arange(size)))
        columns = np.concatenate((pairs[:, 1], pairs[:, 0], np.arange(size)))
        values = np.concatenate((weight, weight, np.ones(size)))
        self.weights = self._coo((values, (rows, columns)), shape=(size, size)).tocsr()
        self.weight_sum = np.asarray(self.weights.sum(axis=1)).ravel()

    # ---- one turn of the rule --------------------------------------------

    def _matrix(self):
        modulus = self.floor + self.physical ** self.EXPONENT * (1.0 - self.floor)
        values = (self._template[None, :] * modulus[:, None]).ravel()[self._keep]
        size = len(self.free)
        return self._coo(
            (values, (self._sparse_rows, self._sparse_columns)), shape=(size, size)
        ).tocsc()

    def _measure(self) -> np.ndarray:
        """Solve every stance, then read off the rule's number and the eye's.

        The rule needs one number per element -- how much strain energy it
        stores, over the postures and weighted by how often each is met. The
        colour needs a second: whether an element spends its working life
        being pulled or being pushed, which is how an anatomist tells the two
        trabecular groups apart.

        All three stances share a stiffness matrix, so they share one
        factorisation and cost little more than a single solve between them.
        """
        solution = self._splu(self._matrix()).solve(self.force)
        full = np.zeros((len(self._index), solution.shape[1]))
        full[self.free] = solution

        poisson = 0.3
        energy = np.zeros(self.count)
        pulled = np.zeros(self.count)
        pushed = np.zeros(self.count)
        for case in range(solution.shape[1]):
            local = full[self.dofs, case]
            weight = self.share[case]
            energy += weight * np.einsum("ij,jk,ik->i", local, self.stiffness, local)

            # Strain at the element centre, straight off the corner
            # displacements. Node order in `dofs` is bottom-left,
            # bottom-right, top-right, top-left.
            xx = 0.5 * ((local[:, 4] - local[:, 6]) + (local[:, 2] - local[:, 0]))
            yy = 0.5 * ((local[:, 1] - local[:, 7]) + (local[:, 3] - local[:, 5]))
            xy = 0.5 * ((local[:, 0] - local[:, 6]) + (local[:, 2] - local[:, 4])) \
                + 0.5 * ((local[:, 5] - local[:, 7]) + (local[:, 3] - local[:, 1]))
            sigma_x = (xx + poisson * yy) / (1.0 - poisson * poisson)
            sigma_y = (yy + poisson * xx) / (1.0 - poisson * poisson)
            shear = xy / (2.0 * (1.0 + poisson))
            mean = 0.5 * (sigma_x + sigma_y)
            spread = np.sqrt((0.5 * (sigma_x - sigma_y)) ** 2 + shear * shear)
            pulled += weight * np.maximum(mean + spread, 0.0)
            pushed += weight * np.maximum(-(mean - spread), 0.0)

        total = pulled + pushed
        self.tension = np.where(total > 1e-30, pulled / np.maximum(total, 1e-30), 0.5)
        self.compression = 1.0 - self.tension
        return energy

    def _stimulus(self, energy: np.ndarray) -> np.ndarray:
        """Strain energy per unit of mass, as the neighbourhood reports it."""
        interior = self.physical[self.design]
        signal = 0.5 * energy[self.design] * interior ** (self.EXPONENT - 1.0)
        return self.weights.dot(signal) / self.weight_sum

    def step(self, count: int = 1) -> None:
        """Deposit where the tissue works above its set point, resorb below.

        Local, and only local: an element's next density depends on what its
        own neighbourhood feels and on nothing else. No total is held fixed,
        so how much bone ends up in the section is an outcome rather than a
        constraint -- which is the whole difference between this and the
        engineering procedure that arrives at the same picture.
        """
        for _ in range(count):
            stimulus = self._stimulus(self._measure())
            change = self.rate * self.scale * (stimulus - self.setpoint)
            interior = self.physical[self.design] + np.clip(change, -0.12, 0.12)
            self.physical[self.design] = np.clip(interior, self.floor_density, 1.0)
            self.iteration += 1

    # ---- what the renderer sees ------------------------------------------

    def _grid(self, values: np.ndarray) -> np.ndarray:
        flat = np.zeros(self.nelx * self.nely, dtype=np.float32)
        flat[self.active] = values
        return flat.reshape((self.nelx, self.nely)).T

    def field(self) -> tuple[np.ndarray, np.ndarray]:
        """Material split into what is being pushed and what is being pulled.

        Two channels rather than one palette across a signed scalar, which is
        the shape the two-species renderer already takes: the two trabecular
        groups cross each other at right angles, and summing two coloured
        densities is what lets a crossing read as a crossing.

        Interpolated up to the frame rather than block-repeated. The struts
        are the picture and their edges are diagonal; repeating cells puts a
        staircase on every one of them.
        """
        from scipy.ndimage import zoom

        density = self.physical.astype(np.float32)
        return tuple(
            np.clip(zoom(self._grid(density * share), self.divisor, order=1), 0.0, None)
            for share in (self.compression, self.tension)
        )


class Phyllotaxis:
    """A meristem placing organs where the ones already there object least.

    One rule, applied once per plastochrone: look around the rim of the
    growing tip and start the next primordium at whatever angle is furthest,
    in the inhibitory sense, from the primordia already placed. Then let the
    tissue underneath grow, which carries every existing primordium outwards
    and clears the rim for the next one. Douady and Couder, 1992.

    Nothing in that rule mentions an angle, a spiral or a number. What comes
    out is the golden angle and two families of counter-rotating spirals whose
    counts are consecutive Fibonacci numbers -- and, because the rim gets
    relatively flatter as the head widens, the counts climb the sequence as
    you read outwards, which is why a real sunflower has few spirals near its
    centre and many at its edge.

    Growth is r proportional to the square root of age, which is the only
    choice that keeps the areal density constant: organs are added at a steady
    rate, so the area they occupy has to grow at a steady rate too. It is also
    what makes the head fill out rather than thin as it widens.

    The same authors got this pattern out of ferrofluid drops repelling each
    other in a dish of oil, with no biology in it at all, which is the useful
    thing to remember about it.
    """

    def __init__(
        self,
        height: int,
        width: int,
        radius: float = 500.0,
        centre: tuple[float, float] | None = None,
        primordia: int = 1196,
        apex: float = 0.8,
        neighbours: int = 60,
        samples: int = 1440,
        falloff: float = 2.0,
        seed: int = 20260829,
    ) -> None:
        self.centre = centre if centre is not None else (width * 0.5, height * 0.448)
        # Area per organ, fixed, so that the oldest organ is at the head's edge
        # once the run has finished and the density is the same throughout.
        self.area = math.pi * radius * radius / primordia
        self.spacing = math.sqrt(self.area)
        # The apex has a size of its own and keeps it: organs are laid down on
        # a rim of fixed radius and it is the tissue underneath that expands.
        #
        # This is the parameter, and getting it wrong is visible. The rule has
        # ordered windows separated by disordered ones, and each ordered window
        # sits on a different angle: at 1.0 the pattern locks near five
        # thirteenths of a turn and throws the organs into thirteen separate
        # arms with gaps between them, at 1.2 onto a different fraction again,
        # and above about 1.4 the placement stops settling at all. At 0.8 the
        # angle it finds is 137.37 degrees, which is the golden angle to within
        # a seventh of a degree. **Measured, not assumed** -- nothing in the
        # rule refers to an angle, so the only way to know which window a
        # setting is in is to run it and take the median.
        self.apex = apex * self.spacing
        self.neighbours = neighbours
        self.falloff = falloff
        self.generator = np.random.default_rng(seed)
        self.grid = np.linspace(0.0, 2.0 * math.pi, samples, endpoint=False)
        self.angles = np.zeros(0, dtype=np.float64)
        self.count = 0

    def radii(self) -> np.ndarray:
        """Oldest first. Age in plastochrones is the only clock here.

        An organ of age a has a - 1 younger organs inside it, each holding the
        same area, so it has been carried out to wherever the annulus between
        the apex and itself has exactly that much room. The head therefore
        widens as the square root of its age -- the only law that adds area at
        the rate organs are added.
        """
        age = np.arange(self.count, 0, -1, dtype=np.float64)
        return np.sqrt(self.apex * self.apex + (age - 1.0) * self.area / math.pi)

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            # The candidate ring is rotated by a fraction of its own spacing
            # each turn. Without it the answer can only ever be one of a fixed
            # set of angles, and the pattern locks to the sampling grid rather
            # than to the rule.
            offset = self.generator.random() * (self.grid[1] - self.grid[0])
            candidates = self.grid + offset
            if self.count == 0:
                self.angles = np.array([candidates[0]])
                self.count = 1
                continue

            # Only the youngest few matter: the inhibition falls off as a
            # cube, and everything older has been carried out of range by the
            # growth underneath it.
            near = min(self.neighbours, self.count)
            radii = self.radii()[-near:]
            angles = self.angles[-near:]
            x, y = radii * np.cos(angles), radii * np.sin(angles)
            offset_x = self.apex * np.cos(candidates)[:, None] - x[None, :]
            offset_y = self.apex * np.sin(candidates)[:, None] - y[None, :]
            square = np.maximum(offset_x * offset_x + offset_y * offset_y, 1e-9)
            inhibition = (square ** (-0.5 * self.falloff)).sum(axis=1)
            self.angles = np.append(self.angles, candidates[int(inhibition.argmin())])
            self.count += 1

    def cells(self) -> tuple[np.ndarray, np.ndarray]:
        """Positions, and how recently each organ was laid down.

        Same quantity `folding` and `turing` are coloured by -- when it grew --
        which here runs the other way round: the youngest organ is the one in
        the middle, and the rim is the oldest thing in the picture.
        """
        radii = self.radii()
        points = np.column_stack((
            self.centre[0] + radii * np.cos(self.angles),
            self.centre[1] + radii * np.sin(self.angles),
        )).astype(np.float32)
        shade = (np.arange(self.count) / max(self.count - 1, 1)).astype(np.float32)
        return points, shade


class Venation:
    """A vein network growing towards whatever is not yet drained.

    Auxin is made all over a young leaf and has to leave it. Wherever it
    flows, the flow makes the cells better at carrying it, so a route that
    carried a little carries more, and the tissue quietly sorts itself into
    conduits and lamina. Sachs called it canalisation; the discrete form used
    here is the space-colonisation rule of Runions and Prusinkiewicz.

    One step: every source of auxin still waiting looks for the nearest vein
    tip within reach and pulls on it, each tip advances along the sum of the
    pulls it received, and any source a vein has now arrived at stops
    existing. Nothing in that says branch, and every branch in the picture is
    a tip that was pulled two ways at once and had to choose both.

    Where a vein *goes* is therefore not a route between two places. It is
    wherever the tissue still had something to drain -- which is why a leaf's
    venation fills the blade rather than taking the short way across it.
    """

    def __init__(
        self,
        height: int,
        width: int,
        root: tuple[float, float] | None = None,
        spacing: float = 15.2,
        stride: float = 4.0,
        kill: float = 13.0,
        influence: float = 130.0,
        margin: float = 40.0,
        span: int = 500,
        blade: float = 0.34,
        eagerness: float = 0.55,
        seed: int = 20260829,
    ) -> None:
        generator = np.random.default_rng(seed)
        self.height, self.width = height, width
        self.stride = stride
        self.kill = kill
        self.influence = influence

        # Auxin is made everywhere in the blade, so the sources are scattered
        # over the whole frame rather than seeded in a shape. A jittered grid
        # rather than uniform noise: uniform noise clumps, and a clump is
        # drained by one vein in one step, which puts holes in the network the
        # rule never made.
        columns = np.arange(-margin, width + margin, spacing)
        rows = np.arange(-margin, height + margin, spacing)
        grid_x, grid_y = np.meshgrid(columns, rows)
        offsets = generator.uniform(-0.42, 0.42, (2,) + grid_x.shape) * spacing
        self.sources = np.column_stack((
            (grid_x + offsets[0]).ravel(), (grid_y + offsets[1]).ravel()
        )).astype(np.float32)

        # The blade is not a fixed field of auxin waiting to be drained -- it
        # is a young leaf that widens, and the veins chase its margin. This is
        # the whole difference between a leaf and a brush: hold the lamina
        # still and every tip races the same direction at the same speed, and
        # what comes out is a fan of near-parallel filaments with no midrib,
        # no secondaries and nothing to branch around. Let it grow and the
        # veins have to keep reaching sideways into tissue that was not there
        # a moment ago, which is what puts an order into the network.
        self.span = span
        self.blade = blade
        self.eagerness = eagerness
        self.length = height * 1.30
        self.breadth = width * 0.75

        # One vein, entering the blade at the base of the midrib.
        start = root if root is not None else (width * 0.5, height * 0.995)
        self.root = start
        self.points = np.array([start], dtype=np.float32)
        self.parent = np.array([0], dtype=np.int64)
        self.age = np.zeros(1, dtype=np.float32)
        self.step_index = 0
        self.generator = generator

    # Ovate: widest a little below halfway, tapering to a tip. Normalised so
    # the widest point of the outline is exactly one breadth across.
    PEAK = 0.4834

    def _lamina(self) -> np.ndarray:
        """Which sources are inside the blade at its current size."""
        # Front-loaded, because a blade expands fast and then slows, and
        # because a clip that spends its first quarter nearly empty has spent
        # the part of it anyone actually watches.
        progress = min(1.0, self.step_index / self.span) ** self.eagerness
        scale = self.blade + (1.0 - self.blade) * progress
        along = (self.root[1] - self.sources[:, 1]) / (scale * self.length)
        inside = (along >= 0.0) & (along <= 1.0)
        half = np.zeros(len(self.sources), dtype=np.float32)
        good = np.nonzero(inside)[0]
        u = along[good]
        half[good] = np.sqrt(u) * (1.0 - u) ** 0.55 / self.PEAK
        return inside & (np.abs(self.sources[:, 0] - self.root[0]) <= scale * self.breadth * half)

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            self.step_index += 1
            if not len(self.sources):
                # Drained. The clock still runs, so a caller stepping towards a
                # target step does not spin here forever.
                continue
            # Only tissue the blade has actually reached is making auxin.
            live = np.nonzero(self._lamina())[0]
            if not len(live):
                continue
            tree = cKDTree(self.points)
            distance, nearest = tree.query(self.sources[live])

            reachable = distance < self.influence
            if not reachable.any():
                continue
            pull = self.sources[live][reachable] - self.points[nearest[reachable]]
            pull /= np.maximum(np.linalg.norm(pull, axis=1, keepdims=True), 1e-6)
            votes = np.zeros_like(self.points)
            np.add.at(votes, nearest[reachable], pull)

            length = np.linalg.norm(votes, axis=1)
            growing = np.nonzero(length > 1e-6)[0]
            if not len(growing):
                continue
            heading = votes[growing] / length[growing][:, None]
            # A tip pulled equally from two sides gets a null sum and would
            # stall forever; the nudge is small enough to be invisible and is
            # the only thing that lets it commit to one side and then branch.
            heading += 0.06 * self.generator.standard_normal(heading.shape)
            heading /= np.maximum(np.linalg.norm(heading, axis=1, keepdims=True), 1e-6)

            fresh = (self.points[growing] + self.stride * heading).astype(np.float32)
            self.points = np.concatenate((self.points, fresh))
            self.parent = np.concatenate((self.parent, growing))
            self.age = np.concatenate((
                self.age, np.full(len(fresh), float(self.step_index), dtype=np.float32)
            ))

            # A source the veins have reached has been drained and stops
            # pulling. This is what stops the network doubling back over
            # tissue it has already served.
            arrived = cKDTree(fresh).query(self.sources)[0] < self.kill
            if arrived.any():
                self.sources = self.sources[~arrived]

    @property
    def drained(self) -> bool:
        return not len(self.sources)

    @property
    def count(self) -> int:
        return len(self.points)

    def segments(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Every vein as a parent-to-child pair, with the age of the child.

        Ranked rather than scaled: the tip count grows roughly with the front's
        length, so raw age piles most of the network into the top of the ramp
        and the whole thing comes out one colour.
        """
        rank = (np.argsort(np.argsort(self.age)) / max(len(self.age) - 1, 1)).astype(np.float32)
        return self.points[self.parent[1:]], self.points[1:], rank[1:]


class Sorting:
    """Two kinds of cell that differ only in how strongly they stick.

    Take an amphibian embryo, dissociate two germ layers into single cells,
    shake them together and let them settle. They sort themselves back out --
    and the layer that ends up inside is always the one whose cells stick to
    each other most strongly. Steinberg's point, in 1963, was that no cell in
    that dish is following an instruction. The tissue is behaving like two
    immiscible liquids, and the arrangement it reaches is the one with the
    least interface, for exactly the reason oil and water reach theirs.

    The rule per cell is only about its own neighbours: hold your distance
    from everyone, pull a little harder on your own kind, push a little on
    the other. Nothing is global, nothing counts how well the sorting is
    going, and no cell can tell where the middle of the dish is.

    What gets drawn is the interface itself -- the wall between two cells,
    lit where the cells on either side are of different kinds. So the frame
    opens as a bright mesh of noise, because in a mixed tissue almost every
    wall is a boundary, and resolves into a few clean curves around dark
    territories. The picture is the quantity the rule is minimising.
    """

    def __init__(
        self,
        height: int,
        width: int,
        cells: int = 2600,
        spacing_force: float = 0.34,
        like: float = 0.10,
        unlike: float = 0.30,
        motility: float = 0.55,
        damping: float = 0.72,
        margin: float = 90.0,
        seed: int = 20260830,
    ) -> None:
        from scipy.spatial import Delaunay, Voronoi

        self._delaunay = Delaunay
        self._voronoi = Voronoi
        generator = np.random.default_rng(seed)
        self.height, self.width = height, width
        self.margin = margin
        self.spacing_force = spacing_force
        self.like = like
        self.unlike = unlike
        self.motility = motility
        self.damping = damping
        self.generator = generator

        # Seeded past the frame edge on every side. The outermost cells have
        # no wall on their far side, and a tissue that stops at the frame
        # would show that as a ragged rim the rule never made.
        low_x, high_x = -margin, width + margin
        low_y, high_y = -margin, height + margin
        area = (high_x - low_x) * (high_y - low_y)
        total = int(cells * area / (width * height))
        self.points = np.column_stack((
            generator.uniform(low_x, high_x, total),
            generator.uniform(low_y, high_y, total),
        )).astype(np.float64)
        self.velocity = np.zeros_like(self.points)
        # The two layers, in equal number and mixed completely.
        self.kind = (generator.random(total) < 0.5).astype(np.int8)
        # Resting separation, from the density they were sown at.
        self.rest = math.sqrt(area / total) * 1.03
        self.step_index = 0

    def _pairs(self) -> np.ndarray:
        """Who is touching whom, as the tessellation sees it."""
        mesh = self._delaunay(self.points)
        edges = np.vstack((
            mesh.simplices[:, [0, 1]], mesh.simplices[:, [1, 2]], mesh.simplices[:, [2, 0]]
        ))
        edges.sort(axis=1)
        return np.unique(edges, axis=0)

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            self.step_index += 1
            pairs = self._pairs()
            offset = self.points[pairs[:, 1]] - self.points[pairs[:, 0]]
            distance = np.maximum(np.linalg.norm(offset, axis=1), 1e-9)
            unit = offset / distance[:, None]

            # Hold the packing: every neighbour pair wants the same gap. This
            # is the term that keeps cells cells rather than letting the two
            # kinds collapse into two lumps with nothing between them.
            strength = self.spacing_force * (distance - self.rest)
            # Then the only thing that distinguishes the two kinds at all.
            same = self.kind[pairs[:, 0]] == self.kind[pairs[:, 1]]
            strength += np.where(same, self.like, -self.unlike) * self.rest

            force = np.zeros_like(self.points)
            np.add.at(force, pairs[:, 0], strength[:, None] * unit)
            np.add.at(force, pairs[:, 1], -strength[:, None] * unit)

            # Cells crawl. Without the jostle the tissue freezes into whatever
            # arrangement it fell into and the sorting stops half done -- the
            # same reason a real sorting assay needs the cells to be alive.
            force += self.motility * self.generator.standard_normal(self.points.shape)
            self.velocity = self.damping * (self.velocity + force)
            self.points += self.velocity

            low_x, high_x = -self.margin, self.width + self.margin
            low_y, high_y = -self.margin, self.height + self.margin
            np.clip(self.points[:, 0], low_x, high_x, out=self.points[:, 0])
            np.clip(self.points[:, 1], low_y, high_y, out=self.points[:, 1])

    @property
    def count(self) -> int:
        return len(self.points)

    def mixing(self) -> float:
        """Fraction of walls that separate unlike cells. The thing being minimised."""
        pairs = self._pairs()
        return float((self.kind[pairs[:, 0]] != self.kind[pairs[:, 1]]).mean())

    def walls(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Every cell wall as a segment, and whether it is an interface.

        The wall between two cells is the Voronoi ridge they share, so the
        drawing is the tessellation's own edges rather than lines between
        centres -- which is what makes it read as tissue instead of a graph.
        """
        diagram = self._voronoi(self.points)
        ridges = np.asarray(diagram.ridge_vertices)
        owners = np.asarray(diagram.ridge_points)
        finite = (ridges[:, 0] >= 0) & (ridges[:, 1] >= 0)
        ridges, owners = ridges[finite], owners[finite]
        start = diagram.vertices[ridges[:, 0]]
        end = diagram.vertices[ridges[:, 1]]

        # Drop walls that lie wholly outside the frame; they cost samples and
        # bleed bloom in from the seeded margin.
        inside = (
            (np.maximum(start[:, 0], end[:, 0]) > -20) & (np.minimum(start[:, 0], end[:, 0]) < self.width + 20)
            & (np.maximum(start[:, 1], end[:, 1]) > -20) & (np.minimum(start[:, 1], end[:, 1]) < self.height + 20)
        )
        start, end, owners = start[inside], end[inside], owners[inside]
        interface = (self.kind[owners[:, 0]] != self.kind[owners[:, 1]]).astype(np.float32)
        return start.astype(np.float32), end.astype(np.float32), interface


class Aggregation:
    """A hundred thousand separate animals deciding to become one.

    A starving Dictyostelium amoeba is a whole organism on its own. Starve a
    lawn of them and a few begin to pulse cAMP; every cell that smells a pulse
    relays it and crawls a step towards where it came from. The pulses become
    waves that sweep the plate, the cells step inwards once per wave, and
    because a cell is both a receiver and a transmitter, a line of cells
    carries the signal better than bare agar does -- so the lines recruit more
    cells and thicken into rivers. The rivers run into a few mounds, and the
    mounds crawl away as one animal with a front and a back.

    **The cell has to ignore half of every wave.** A pulse arrives, passes and
    leaves, and its gradient points towards the source on the way in and away
    from it on the way out; a cell that simply climbed the gradient would be
    carried back exactly as far as it came. So it responds only while the
    signal is rising and goes deaf on the falling edge. That adaptation is not
    a detail -- without it there is no net movement at all, and this is the
    piece.

    The medium is Barkley's, the same two lines as `reentry`, with one
    addition: the threshold is lowered where cells are dense. That is the only
    coupling from the population back to the signal, and it is what makes the
    streams reinforce themselves rather than dissolving.
    """

    def __init__(
        self,
        height: int,
        width: int,
        cells: int = 150_000,
        divisor: int = 3,
        a: float = 0.75,
        b: float = 0.055,
        epsilon: float = 0.05,
        diffusion: float = 1.0,
        dt: float = 0.10,
        relay: float = 0.045,
        crowd: float = 4.5,
        sensitivity: float = 14.0,
        rising: float = 0.004,
        wander: float = 0.10,
        speed_limit: float = 1.2,
        afterglow: float = 26.0,
        pacemakers: int = 7,
        period: int = 86,
        trail_stride: int = 16,
        trail_points: int = 6,
        seed: int = 20260830,
    ) -> None:
        from scipy.ndimage import gaussian_filter

        self._gaussian = gaussian_filter
        generator = np.random.default_rng(seed)
        self.height, self.width = height, width
        self.divisor = divisor
        self.rows, self.columns = height // divisor, width // divisor
        self.a, self.epsilon, self.diffusion, self.dt = a, epsilon, diffusion, dt
        self.base = b
        self.relay, self.crowd = relay, crowd
        self.sensitivity, self.rising = sensitivity, rising
        self.wander, self.speed_limit = wander, speed_limit
        self.decay = float(0.5 ** (1.0 / max(afterglow, 1.0)))
        self.period = period
        self.generator = generator

        # A lawn of separate cells over the whole plate. This is not a colony
        # spreading from a point; every one of them was already an animal.
        self.x = generator.uniform(0.0, width, cells).astype(np.float32)
        self.y = generator.uniform(0.0, height, cells).astype(np.float32)
        # How far the signal has carried each cell, summed as a vector so it
        # is net movement rather than path length. This is the piece's argument
        # in one number: a wave passes over every cell in both directions, and
        # a cell ends up somewhere only because it answers half of one. The
        # wander is deliberately left out -- it is noise, every cell has the
        # same amount of it, and including it floods the measurement.
        self.drift = np.zeros((cells, 2), dtype=np.float32)
        # The last stretch of each cell's actual path, kept as a handful of
        # positions rather than one lagging point. Drawing that instead of a
        # dot is what turns a stream into a filament instead of a heap of
        # grain, and a cell that is not going anywhere collapses to the point
        # it always was -- which is the honest difference between a recruited
        # amoeba and one still sitting where it starved.
        #
        # It has to be a real path and not a chord. These cells move on the
        # rising edge of a wave and stop in between, so over 96 steps a cell
        # walks in a series of pulls and a straight line between the endpoints
        # would draw a journey nobody took. Sized by measurement: at a lag of
        # 8 steps the median trail is 0.36 px and invisible; at 96 it is
        # 2.78 px with a 90th percentile of 12.2, and half the lawn has a
        # streak over 3 px.
        self.trail_stride = trail_stride
        self.trail_points = trail_points
        here = np.column_stack((self.x, self.y)).astype(np.float32)
        self.history = np.repeat(here[None, :, :], trail_points, axis=0)
        self.trail_phase = 0.0
        # How recently this cell last took a step, as a decaying memory. The
        # excited state passes in a moment, and without a phosphor the wave is
        # a two-pixel thread with no record of where it has been.
        self.lit = np.zeros(cells, dtype=np.float32)

        self.u = np.zeros((self.rows, self.columns), dtype=np.float32)
        self.v = np.zeros((self.rows, self.columns), dtype=np.float32)
        # A handful of cells start pulsing on their own. Real plates have
        # pacemakers too, and an excitable medium left alone does nothing.
        self.pacemakers = np.column_stack((
            generator.integers(self.rows // 8, self.rows - self.rows // 8, pacemakers),
            generator.integers(self.columns // 8, self.columns - self.columns // 8, pacemakers),
        ))
        self.offsets = generator.integers(0, period, pacemakers)
        self.step_index = 0

    @staticmethod
    def _laplacian(field: np.ndarray) -> np.ndarray:
        """The isotropic nine-point stencil, (1/6)[[1,4,1],[4,-20,4],[1,4,1]].

        Not a refinement. A five-point laplacian carries the square grid's own
        symmetry into the wave front, the front runs faster on the diagonals
        than along the axes, and every aggregate comes out as a four-armed X --
        the mesh showing through, not anything an amoeba does. It is visible at
        a glance and it does not show up in a four-fold FFT statistic, which
        reads 0.039 on the broken version. Look at the picture.
        """
        orthogonal = (
            np.roll(field, 1, 0) + np.roll(field, -1, 0)
            + np.roll(field, 1, 1) + np.roll(field, -1, 1)
        )
        diagonal = (
            np.roll(np.roll(field, 1, 0), 1, 1) + np.roll(np.roll(field, 1, 0), -1, 1)
            + np.roll(np.roll(field, -1, 0), 1, 1) + np.roll(np.roll(field, -1, 0), -1, 1)
        )
        return (4.0 * orthogonal + diagonal - 20.0 * field) / 6.0

    def _bins(self) -> tuple[np.ndarray, np.ndarray]:
        row = np.clip((self.y / self.divisor).astype(np.int32), 0, self.rows - 1)
        column = np.clip((self.x / self.divisor).astype(np.int32), 0, self.columns - 1)
        return row, column

    def density(self) -> np.ndarray:
        row, column = self._bins()
        grid = np.zeros((self.rows, self.columns), dtype=np.float32)
        np.add.at(grid, (row, column), 1.0)
        return self._gaussian(grid, 1.6, mode="nearest")

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            self.step_index += 1
            row, column = self._bins()

            # Dense ground relays better, so it is easier to excite. The only
            # way the population talks back to the signal it is following.
            crowding = self.density()
            crowding /= max(float(crowding.mean()), 1e-6)
            threshold = np.maximum(self.base - self.relay * np.minimum(crowding, self.crowd), 0.004)

            for site, offset in zip(self.pacemakers, self.offsets):
                if (self.step_index + int(offset)) % self.period == 0:
                    self.u[site[0] - 2 : site[0] + 3, site[1] - 2 : site[1] + 3] = 1.0

            previous = self.u.copy()
            self.u += self.dt * (
                self.diffusion * self._laplacian(self.u)
                + self.u * (1.0 - self.u) * (self.u - (self.v + threshold) / self.a) / self.epsilon
            )
            self.v += self.dt * (self.u - self.v)
            np.clip(self.u, 0.0, 1.0, out=self.u)
            np.clip(self.v, 0.0, 1.0, out=self.v)

            # Smoothed before differencing. A five-point laplacian on a square
            # grid has the grid's own symmetry, and cells reading its raw
            # gradient walk along the axes and the diagonals: the aggregates
            # come out as four-pointed stars, which is the mesh showing
            # through and not anything the biology does.
            smooth = self._gaussian(self.u, 1.2, mode="nearest")
            gradient_x = 0.5 * (np.roll(smooth, -1, 1) - np.roll(smooth, 1, 1))
            gradient_y = 0.5 * (np.roll(smooth, -1, 0) - np.roll(smooth, 1, 0))
            change = self.u - previous

            # Only while the signal is rising. On the falling edge the cell is
            # deaf, which is the entire reason the population goes anywhere.
            moving = change[row, column] > self.rising
            step_x = np.where(moving, self.sensitivity * gradient_x[row, column], 0.0)
            step_y = np.where(moving, self.sensitivity * gradient_y[row, column], 0.0)
            speed = np.sqrt(step_x * step_x + step_y * step_y)
            fast = speed > self.speed_limit
            if fast.any():
                scale = self.speed_limit / np.maximum(speed[fast], 1e-9)
                step_x[fast] *= scale
                step_y[fast] *= scale

            self.lit *= self.decay
            np.maximum(self.lit, np.minimum(speed / self.speed_limit, 1.0), out=self.lit)

            jitter = self.wander * self.generator.standard_normal((2, len(self.x))).astype(np.float32)
            # The medium is periodic -- the laplacian rolls -- so the lawn has
            # to be periodic too. Clamping instead stacks cells against the
            # frame edge and draws a bright rim there, a structure the rule
            # never made. Clamped after the modulus because float32 `np.mod`
            # can return exactly the modulus for a value a hair below zero.
            self.drift[:, 0] += step_x
            self.drift[:, 1] += step_y
            x = np.mod(self.x + step_x + jitter[0], self.width)
            y = np.mod(self.y + step_y + jitter[1], self.height)
            self.x = np.clip(x, 0.0, self.width - 1e-3).astype(np.float32)
            self.y = np.clip(y, 0.0, self.height - 1e-3).astype(np.float32)

            if self.step_index % self.trail_stride == 0:
                self.history[:-1] = self.history[1:]
                self.history[-1] = np.column_stack((self.x, self.y))
            self.trail_phase = (self.step_index % self.trail_stride) / self.trail_stride

    @property
    def count(self) -> int:
        return len(self.x)

    def cells(self) -> tuple[np.ndarray, np.ndarray]:
        """Positions, and how recently each cell last stepped."""
        points = np.column_stack((self.x, self.y)).astype(np.float32)
        return points, np.clip(self.lit, 0.0, 1.0).astype(np.float32)

    def trails(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Each cell's recent path, plus its colour and its phosphor.

        Returns the path as `(points + 1, cells, 2)` -- oldest first, the cell's
        current position last -- then how far the signal has carried it and how
        recently it stepped. Segments crossing the frame edge come back the
        width of the plate and are the caller's to drop: the cell is one cell,
        but the line between its two sides is a stripe nothing walked.
        """
        here = np.column_stack((self.x, self.y)).astype(np.float32)

        # The buffer only takes a sample every `trail_stride` steps, so read
        # straight out it is a polyline that jumps once every stride and holds
        # still in between -- which the render shows as a stutter, 15.1% frozen
        # with every one of those frames in the opening two seconds. Resampling
        # the stored path at a continuously advancing offset makes the whole
        # trail slide along itself instead, one frame at a time.
        size = np.array([self.width, self.height], dtype=np.float32)
        older, newer = self.history[:-1], self.history[1:]
        step = newer - older
        step -= np.round(step / size) * size          # shortest way round the torus
        slid = np.mod(older + self.trail_phase * step, size).astype(np.float32)
        path = np.concatenate((slid, here[None, :, :]), axis=0).astype(np.float32)

        travel = np.linalg.norm(self.drift, axis=1).astype(np.float32)
        return path, travel, np.clip(self.lit, 0.0, 1.0).astype(np.float32)

    def swarm(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Positions, how far the signal has carried each cell, and its phosphor.

        Three separate quantities because they do three separate jobs in the
        render: where, what colour, how bright. Brightness is the phosphor, so
        a wave sweeping the plate is a wave sweeping the plate; hue is the
        distance travelled, so a cell that has been recruited into a stream
        looks different from one still sitting where it starved.
        """
        points = np.column_stack((self.x, self.y)).astype(np.float32)
        travel = np.linalg.norm(self.drift, axis=1).astype(np.float32)
        return points, travel, np.clip(self.lit, 0.0, 1.0).astype(np.float32)


class Comet:
    """A bacterium that does not swim. It builds ground and falls off it.

    Listeria escapes into a host cell's cytoplasm and hijacks the machinery
    that cell uses to build its own skeleton. On one face of the bacterium it
    nucleates a branched actin network; the network grows against that face,
    and growing is all it does. There is no motor, no flagellum, nothing that
    pulls. The bacterium is pushed away from the thing it is making, and what
    it leaves behind -- the comet tail -- is the network it has already
    outrun, depolymerising from the far end at the same rate the near end is
    built.

    So the tail is not an exhaust and not a wake. It is the ground the
    bacterium is standing on, and the reason it moves is that the ground keeps
    being built underneath it in one direction only.

    Each cell divides on its own clock, and both daughters keep pushing, so a
    single bacterium becomes a cytoplasm full of them. That is also how the
    infection spreads: at the far wall a comet drives the bacterium into a
    finger of membrane that the neighbouring cell then swallows, and it never
    once touches the outside of a cell.
    """

    def __init__(
        self,
        height: int,
        width: int,
        founders: int = 10,
        capacity: int = 320,
        speed: float = 6.4,
        trail: int = 52,
        doubling: int = 170,
        curvature: float = 0.013,
        wobble: float = 0.010,
        spread: float = 0.42,
        seed: int = 20260830,
    ) -> None:
        generator = np.random.default_rng(seed)
        self.height, self.width = height, width
        self.speed = speed
        self.length = trail
        self.doubling = doubling
        self.wobble = wobble
        self.spread = spread
        self.generator = generator

        self.x = np.zeros(capacity, dtype=np.float32)
        self.y = np.zeros(capacity, dtype=np.float32)
        self.heading = np.zeros(capacity, dtype=np.float32)
        # Every comet has a persistent turn of its own. A real one travels in
        # an arc or a helix rather than a straight line, because the network
        # is never quite symmetrical about the face it is built on -- and a
        # frame of straight lines reads as a screensaver.
        self.turn = np.zeros(capacity, dtype=np.float32)
        self.age = np.zeros(capacity, dtype=np.int32)
        self.count = founders

        self.x[:founders] = generator.uniform(0.0, width, founders)
        self.y[:founders] = generator.uniform(0.0, height, founders)
        self.heading[:founders] = generator.uniform(0.0, 2.0 * math.pi, founders)
        self.turn[:founders] = curvature * generator.standard_normal(founders)

        # The tail, newest first. Held as positions rather than splatted into
        # a field so it can be drawn as the curve it is, and so the far end can
        # simply stop existing -- which is what depolymerisation does.
        self.trail = np.zeros((capacity, trail, 2), dtype=np.float32)
        self.trail[:founders, :, 0] = self.x[:founders, None]
        self.trail[:founders, :, 1] = self.y[:founders, None]
        self.step_index = 0

    def _divide(self) -> None:
        """Both daughters keep pushing, and each takes its own line."""
        room = len(self.x) - self.count
        if room <= 0:
            return
        parents = np.arange(min(self.count, room))
        daughters = self.count + np.arange(len(parents))
        self.x[daughters] = self.x[parents]
        self.y[daughters] = self.y[parents]
        self.heading[daughters] = self.heading[parents] + self.spread * self.generator.standard_normal(len(parents))
        self.heading[parents] -= self.spread * self.generator.standard_normal(len(parents))
        self.turn[daughters] = -self.turn[parents] + 0.004 * self.generator.standard_normal(len(parents))
        self.age[daughters] = 0
        # A daughter has no tail yet. Starting it stacked on its own position
        # means its first frames draw nothing, which is right: it has not
        # built any ground.
        self.trail[daughters] = np.stack((self.x[daughters], self.y[daughters]), axis=1)[:, None, :]
        self.count += len(parents)

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            self.step_index += 1
            if self.step_index % self.doubling == 0:
                self._divide()

            live = slice(0, self.count)
            self.heading[live] += self.turn[live] + self.wobble * self.generator.standard_normal(self.count)
            self.x[live] = np.mod(self.x[live] + self.speed * np.cos(self.heading[live]), self.width)
            self.y[live] = np.mod(self.y[live] + self.speed * np.sin(self.heading[live]), self.height)
            self.age[live] += 1

            self.trail[live] = np.roll(self.trail[live], 1, axis=1)
            self.trail[live, 0, 0] = self.x[live]
            self.trail[live, 0, 1] = self.y[live]

    def heads(self) -> np.ndarray:
        """The bacteria themselves.

        Drawn separately and brighter than any tail. Without them the frame is
        a tangle of arcs and reads as light-painting; with them every arc has
        an object at one end and the picture is a hundred things travelling.
        """
        return np.column_stack((self.x[:self.count], self.y[:self.count])).astype(np.float32)

    def segments(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Every stretch of tail as a pair, with how new the actin in it is.

        Segments older than the cell are dropped rather than drawn, and so are
        the ones that straddle the wrap: a comet leaving the right edge and
        arriving at the left is one bacterium, but the line between those two
        positions is a stripe across the frame that nothing ever travelled.
        """
        live = self.count
        head = self.trail[:live, :-1]
        tail = self.trail[:live, 1:]
        rung = np.arange(self.length - 1, dtype=np.float32)
        real = rung[None, :] < (self.age[:live, None] - 1)
        jump = np.abs(head - tail).max(axis=2) < 3.0 * self.speed
        keep = real & jump
        shade = np.repeat(1.0 - rung / max(self.length - 2, 1), live).reshape(self.length - 1, live).T
        return head[keep], tail[keep], shade[keep].astype(np.float32)


class Spindle:
    """A cell finds its own chromosomes by guessing, and checks the guesses.

    A chromosome has to be attached to both poles of the spindle before the
    cell is allowed to pull it apart, and nothing in the cell knows where the
    chromosomes are. What it does instead is guess: each pole throws out
    microtubules in every direction, each one grows for a while, gives up at
    random and shrinks all the way back, and the whole population is replaced
    over and over. A filament that happens to run into a kinetochore -- the
    plate a chromosome presents on each of its two faces -- stops being
    disposable and becomes a fibre under tension. That is search and capture,
    and it is a random search with a check on the answer rather than a plan.

    Two things here are not decoration. The first is that the search is
    biased: chromatin holds a gradient of RanGTP around itself that lowers the
    catastrophe rate of any microtubule that strays close, so filaments live
    longer exactly where the targets are. Without it a blind search does not
    finish inside a mitosis, which is the standing objection to naive
    search-and-capture, and it does not finish inside this clip either --
    measured, at 27 of 92 kinetochores held after a full run.

    The second is that being attached is not the same as being right. Both
    sisters can be caught by the same pole, which would send both copies of a
    chromosome into one daughter cell; that attachment carries no tension, and
    an untensioned attachment is released again. So the back half of the run
    is not more capturing, it is the cell taking wrong answers apart -- and it
    is why the last chromosome reaches the plate as late as it does.

    Colour is how long a filament has survived. Almost every microtubule in
    the frame is seconds old; the ones that found something stop being torn
    down, so a k-fibre lights up simply by lasting.
    """

    def __init__(
        self,
        height: int,
        width: int,
        chromosomes: int = 46,
        per_pole: int = 380,
        radius: float = 460.0,
        separation: float = 250.0,
        seed: int = 20260902,
    ) -> None:
        generator = np.random.default_rng(seed)
        self.generator = generator
        self.height, self.width = height, width
        # The model works in its own units and is drawn through one scale, so
        # the numbers below are the ones the gate measured rather than a set
        # re-derived in pixels. The pole axis stands up the portrait frame:
        # model x becomes screen y, which is the only sane way to put an
        # object this elongated in 9:16.
        self.scale = height / 960.0
        self.radius = radius
        self.separation = separation
        self.count = per_pole * 2
        self.chromosomes = chromosomes
        self.step_index = 0

        self.pole = np.repeat([0, 1], per_pole)
        self.theta = generator.uniform(0.0, 2.0 * math.pi, self.count)
        self.length = generator.uniform(0.0, 60.0, self.count)
        self.growing = np.ones(self.count, bool)
        self.age = np.zeros(self.count, dtype=np.int32)
        self.held = np.full(self.count, -1)          # which kinetochore, or -1

        angle = generator.uniform(0.0, 2.0 * math.pi, chromosomes)
        spread = 0.60 * radius * np.sqrt(generator.uniform(0.02, 1.0, chromosomes))
        self.centre = np.column_stack((spread * np.cos(angle), spread * np.sin(angle)))
        self.phi = generator.uniform(0.0, 2.0 * math.pi, chromosomes)
        self.arm = 26.0
        # The drawn body: half-length across the axis, and the half-thickness
        # of one strand. The two chromatids sit at 0.42 of the arm either side
        # of the centre, close enough to read as one body with a seam down it
        # and far enough that the seam is visible at 200 px.
        self.span, self.waist = 22.0, 3.6
        # Its own generator: the drawing must not pull numbers out of the
        # stream the run is measured on.
        self.coil = self._chromatids(np.random.default_rng(seed + 1))
        self.kin_pole = np.full((chromosomes, 2), -1)
        self.kin_mt = np.full((chromosomes, 2), -1)
        self.events: list[tuple[int, str]] = []

        # Dynamic instability, per step. Growth is slower than shrinkage
        # because it is: a microtubule builds at a few micrometres a minute
        # and comes apart an order faster once it starts.
        self.grow_rate, self.shrink_rate = 3.0, 5.0
        self.catastrophe, self.rescue, self.cortex = 0.030, 0.012, 0.35
        # RanGTP: how close counts as near chromatin, and what it does to the
        # catastrophe rate there. 0.22 was chosen by sweep -- at 1.0 (no
        # gradient) the search stalls at 27 of 92, at 0.30 it finishes inside
        # the first half of the clip.
        self.ran, self.ran_gain = 130.0, 0.22
        self.capture = 10.0
        self.poleward, self.congress, self.glide = 1.2, 1.6, 1.5
        self.release = 0.010
        self.eject = 46.0


    def _chromatids(self, generator) -> np.ndarray:
        """One sampled body in local coordinates: two coiled strands.

        Sampled finer than a pixel along and across, so a strand fills rather
        than beading, and jittered a little so the two are not a printed pair.
        """
        step = 0.8 / self.scale
        along = np.arange(-self.span, self.span + 1e-9, step)
        thickness = np.arange(-self.waist, self.waist + 1e-9, step)
        points = []
        for side in (-1.0, 1.0):
            offset = side * 0.42 * self.arm
            wobble = 1.3 * np.sin(along * (math.pi / self.span) * 2.0 + generator.uniform(0, 6.2))
            taper = np.sqrt(np.clip(1.0 - (along / self.span) ** 2, 0.0, 1.0)) ** 0.35
            for across in thickness:
                keep = np.abs(across) <= self.waist * taper
                points.append(np.column_stack((
                    along[keep], np.full(keep.sum(), offset) + wobble[keep] + across
                )))
        return np.concatenate(points).astype(np.float32)

    # -- geometry -----------------------------------------------------------
    def poles(self) -> np.ndarray:
        """The centrosomes separate over the first third and then hold."""
        travel = min(1.0, self.step_index / 300.0)
        distance = 60.0 + (self.separation - 60.0) * (travel * (2.0 - travel))
        return np.array([[-distance, 0.0], [distance, 0.0]])

    def kinetochores(self) -> np.ndarray:
        """Two per chromosome, back to back, facing opposite ways."""
        facing = np.column_stack((np.cos(self.phi), np.sin(self.phi)))
        return np.stack(
            (self.centre + self.arm * facing, self.centre - self.arm * facing), axis=1
        )

    def tips(self) -> np.ndarray:
        base = self.poles()[self.pole]
        along = np.column_stack((np.cos(self.theta), np.sin(self.theta)))
        return base + self.length[:, None] * along

    def _ejection(self, point: np.ndarray, poles: np.ndarray) -> np.ndarray:
        """The polar ejection force: an aster pushes chromosome arms away.

        It is what keeps a singly-attached chromosome off its own pole, and
        that matters mechanically -- a chromosome sitting on a pole hides the
        free sister from the other pole, and the run deadlocks. Measured: with
        no ejection force, 2 of 18 chromosomes ever bi-orient.
        """
        push = np.zeros(2)
        for pole in poles:
            offset = point - pole
            distance = np.linalg.norm(offset) + 1e-6
            push += self.eject * offset / distance / distance
        return push

    # -- the rule -----------------------------------------------------------
    def step(self, count: int = 1) -> None:
        generator = self.generator
        for _ in range(count):
            self.step_index += 1
            poles = self.poles()
            kinetochores = self.kinetochores()
            self.age += 1

            free = self.held < 0
            growing = free & self.growing
            shrinking = free & ~self.growing
            self.length[growing] += self.grow_rate
            self.length[shrinking] -= self.shrink_rate
            self.length[self.length < 0.0] = 0.0

            tips = self.tips()
            outside = np.linalg.norm(tips, axis=1) > self.radius
            near = (
                np.linalg.norm(tips[:, None, :] - self.centre[None, :, :], axis=2).min(axis=1)
                < self.ran
            )
            rate = np.where(near, self.catastrophe * self.ran_gain, self.catastrophe)
            flip = growing & (
                (generator.random(self.count) < rate)
                | (outside & (generator.random(self.count) < self.cortex))
            )
            self.growing[flip] = False
            back = shrinking & (generator.random(self.count) < self.rescue) & (self.length > 4.0)
            self.growing[back] = True
            # A filament that shrank all the way back is gone, and what
            # replaces it is a new one pointing somewhere else. Its age starts
            # again, which is what makes age worth colouring by.
            spent = free & ~self.growing & (self.length <= 0.0)
            replaced = int(spent.sum())
            if replaced:
                self.theta[spent] = generator.uniform(0.0, 2.0 * math.pi, replaced)
                self.length[spent] = 0.0
                self.growing[spent] = True
                self.age[spent] = 0

            self._capture(tips, kinetochores, free)
            self._correct(generator)
            self._move(poles, generator)
            self._track(poles)

    def _capture(self, tips: np.ndarray, kinetochores: np.ndarray, free: np.ndarray) -> None:
        """A growing tip that lands on the face of a free kinetochore binds it."""
        open_sites = np.argwhere(self.kin_pole < 0)
        if not len(open_sites):
            return
        candidates = np.argwhere(free & self.growing & (self.length > 20.0)).ravel()
        if not len(candidates):
            return
        reach = tips[candidates]
        facing = np.column_stack((np.cos(self.phi), np.sin(self.phi)))
        for chromosome, sister in open_sites:
            site = kinetochores[chromosome, sister]
            distance = np.linalg.norm(reach - site, axis=1)
            # A kinetochore is a plate on one side of the centromere, not a
            # sphere: only a microtubule arriving at that face can bind it.
            # Without this the capture rate is roughly twentyfold too high and
            # the whole search is over inside the first quarter of the clip.
            normal = facing[chromosome] * (1.0 if sister == 0 else -1.0)
            distance = np.where((reach - site) @ normal > -2.0, distance, 1e9)
            nearest = int(np.argmin(distance))
            if distance[nearest] < self.capture:
                filament = candidates[nearest]
                if self.held[filament] >= 0:
                    continue
                self.held[filament] = chromosome * 2 + sister
                self.kin_pole[chromosome, sister] = self.pole[filament]
                self.kin_mt[chromosome, sister] = filament
                self.events.append((self.step_index, "capture"))

    def _correct(self, generator) -> None:
        """Both sisters on one pole carries no tension, so it is let go."""
        wrong = np.argwhere(
            (self.kin_pole[:, 0] >= 0) & (self.kin_pole[:, 0] == self.kin_pole[:, 1])
        ).ravel()
        for chromosome in wrong:
            if generator.random() >= self.release:
                continue
            sister = int(generator.integers(2))
            filament = self.kin_mt[chromosome, sister]
            self.held[filament] = -1
            self.growing[filament] = False
            self.kin_pole[chromosome, sister] = -1
            self.kin_mt[chromosome, sister] = -1
            self.events.append((self.step_index, "release"))

    def _move(self, poles: np.ndarray, generator) -> None:
        holding = self.kin_pole >= 0
        count = holding.sum(axis=1)
        bioriented = (count == 2) & (self.kin_pole[:, 0] != self.kin_pole[:, 1])
        single = (count == 1) | ((count == 2) & (self.kin_pole[:, 0] == self.kin_pole[:, 1]))
        loose = count == 0

        for chromosome in np.argwhere(loose).ravel():
            self.centre[chromosome] += self._ejection(self.centre[chromosome], poles)
            self.centre[chromosome] += generator.normal(0.0, 1.5, 2)
            self.phi[chromosome] += generator.normal(0.0, 0.035)
            distance = np.linalg.norm(self.centre[chromosome])
            if distance > 0.86 * self.radius:
                self.centre[chromosome] *= 0.86 * self.radius / distance

        for chromosome in np.argwhere(single).ravel():
            sister = int(np.argmax(holding[chromosome]))
            target = poles[self.kin_pole[chromosome, sister]]
            offset = target - self.centre[chromosome]
            distance = np.linalg.norm(offset) + 1e-6
            # Walked along its own k-fibre towards the midplane while it is
            # pulled poleward along the same fibre. That is what puts the free
            # sister where the far pole can reach it.
            slide = np.array([-math.tanh(self.centre[chromosome, 0] / 90.0), 0.0]) * self.glide
            self.centre[chromosome] += (
                self.poleward * offset / distance
                + self._ejection(self.centre[chromosome], poles)
                + slide
                + generator.normal(0.0, 0.5, 2)
            )
            want = math.atan2(offset[1], offset[0]) + (math.pi if sister else 0.0)
            self.phi[chromosome] += 0.06 * math.atan2(
                math.sin(want - self.phi[chromosome]), math.cos(want - self.phi[chromosome])
            )

        for chromosome in np.argwhere(bioriented).ravel():
            # Held from both sides, a chromosome does not sit still on the
            # plate; it oscillates across it for as long as the cell waits.
            swing = 1.4 * math.sin(0.06 * self.step_index + chromosome)
            self.centre[chromosome, 0] += (
                -self.congress * math.tanh(self.centre[chromosome, 0] / 40.0) + swing
            )
            self.centre[chromosome, 1] += generator.normal(0.0, 0.35)
            want = 0.0 if self.kin_pole[chromosome, 0] == 1 else math.pi
            self.phi[chromosome] += 0.10 * math.atan2(
                math.sin(want - self.phi[chromosome]), math.cos(want - self.phi[chromosome])
            )

    def _track(self, poles: np.ndarray) -> None:
        """A bound filament is no longer searching: it spans pole to kinetochore."""
        bound = np.argwhere(self.held >= 0).ravel()
        if not len(bound):
            return
        sites = self.kinetochores().reshape(-1, 2)[self.held[bound]]
        offset = sites - poles[self.pole[bound]]
        self.length[bound] = np.linalg.norm(offset, axis=1)
        self.theta[bound] = np.arctan2(offset[:, 1], offset[:, 0])

    # -- what the renderer asks for ----------------------------------------
    def _screen(self, points: np.ndarray) -> np.ndarray:
        """Model to frame, with the pole axis standing up the portrait."""
        return np.column_stack((
            self.width * 0.5 + points[:, 1] * self.scale,
            self.height * 0.5 + points[:, 0] * self.scale,
        )).astype(np.float32)

    def segments(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Every microtubule as pole-to-tip, shaded by how long it has lived.

        Ranked, not scaled. Survival time here is about as skewed as a
        quantity gets -- at the end of a run the median filament is 117 steps
        old and the oldest is 717, because a fibre that found a chromosome
        stops being torn down and simply keeps ageing. Divided through by any
        reference a third of the population saturates and the cut comes out
        white; ranked, the disposable majority spreads across the dark end of
        the ramp and only the genuinely oldest fibres reach the top of it.
        """
        start = self._screen(self.poles()[self.pole])
        end = self._screen(self.tips())
        order = np.argsort(np.argsort(self.age))
        shade = (order / max(self.count - 1, 1)).astype(np.float32)
        return start, end, shade

    def heads(self) -> np.ndarray:
        """The chromosomes themselves: two sister chromatids, side by side.

        Drawn as the brightest thing in the frame. Without them the picture is
        two starbursts and the thing the whole search is *for* is invisible.

        Three drawings were measured before this one. Disc samples scattered
        along the body draw stubble; a filled grid draws a white domino; a
        filled ellipse draws a cloud, and forty-six overlapping ellipses draw
        one cloud with no chromosomes in it. What reads is the object itself
        -- a chromosome at metaphase is two copies lying against each other,
        each a condensed coil, joined where the kinetochores are. Two wavy
        strands with a dark line between them have an edge, a texture and a
        reason, and they lie *across* the axis, because sister kinetochores
        sit back to back at the centromere and face opposite poles. That is
        also what a metaphase plate looks like down a microscope: a band of
        bodies lying across the spindle, not a row of marks standing along it.

        The waveform is drawn once in the constructor and carried, so a
        chromosome keeps its own coil instead of boiling from frame to frame.
        """
        facing = np.column_stack((np.cos(self.phi), np.sin(self.phi)))
        across = np.column_stack((-facing[:, 1], facing[:, 0]))
        body = (
            self.centre[:, None, :]
            + across[:, None, :] * self.coil[None, :, 0, None]
            + facing[:, None, :] * self.coil[None, :, 1, None]
        )
        return self._screen(body.reshape(-1, 2))

    # -- scalars ------------------------------------------------------------
    def attached(self) -> int:
        return int((self.kin_pole >= 0).sum())

    def bioriented(self) -> int:
        held = self.kin_pole
        return int(((held[:, 0] >= 0) & (held[:, 1] >= 0) & (held[:, 0] != held[:, 1])).sum())

    def plate(self) -> float:
        """Mean distance from the midplane, in model units."""
        return float(np.abs(self.centre[:, 0]).mean())


class Stripe:
    """Turing was right about the stripes. He was wrong about the morphogens.

    A zebrafish stripe is not two chemicals racing each other across a sheet.
    It is two kinds of cell -- black melanophores and yellow xanthophores --
    each one reading how many of the other kind are nearby and, if the answer
    is wrong, becoming the other kind. The interaction has the shape Turing
    needed: a cell is supported by its own kind close in and suppressed by its
    own kind further out, which is short-range activation and long-range
    inhibition with whole cells standing where the chemicals were. Nakamasu
    and colleagues measured the two ranges by killing cells with a laser and
    watching what grew back.

    So the pattern is computed by the tissue rather than painted onto it, and
    the machinery is visible: every pixel of a stripe is an individual animal
    cell that decided, and can still change its mind.

    **The fish does not stop growing, and that is the piece.** The two ranges
    are fixed -- they are the reach of one cell's processes, and a cell does
    not get longer because the fish does. A stripe therefore has a width it
    wants, and skin that keeps widening carries the existing stripes apart
    until the gap between them is wide enough to hold another one, at which
    point a new stripe nucleates in the middle of it. A zebrafish adds its
    adult stripes exactly this way, ventrally and dorsally, as it grows. There
    is no counter anywhere and nothing decides how many stripes to make: the
    number is whatever the skin's height divided by that fixed width comes to.

    Two consequences worth stating, because both cost a rebuild to find:

    * **The radius has to advance by a fixed amount per step, not a fixed
      fraction.** The stripe count goes as the radius, so only linear growth
      spreads the splitting evenly across a clip; exponential growth puts two
      thirds of it in the last quarter and the first half is a still.
    * **The long-range term has to be strong enough to break a stripe from
      the inside.** Under a weak one the pattern is stable to stretching and
      the stripes simply get fatter as the skin grows -- which is a picture of
      a disc being scaled up, not of a pattern being recomputed. Measured as
      boundary length over radius: flat means stretching, rising means
      splitting.
    """

    def __init__(
        self,
        height: int,
        width: int,
        radius: float | None = None,
        seed_radius: float = 220.0,
        per_cell: float = 6.0,
        divisor: int = 3,
        sigma_short: float = 4.6,
        sigma_long: float = 13.6,
        # Stripes run along the body axis because the ranges are not the same
        # in both directions. Straight parallel bands need a much stronger bias
        # than this and stop looking like an animal -- at 7 the disc reads as a
        # barcode. 3.5 keeps them horizontal and lets them wander.
        anisotropy: float = 3.5,
        weight: float = 1.70,
        rate: float = 0.30,
        growth: float | None = None,
        wander: float = 0.80,
        recency: float = 26.0,
        seed: int = 20260904,
    ) -> None:
        from scipy.ndimage import gaussian_filter

        self._gaussian = gaussian_filter
        self.height, self.width, self.divisor = height, width, divisor
        self.rows, self.columns = height // divisor, width // divisor
        self.limit = radius if radius is not None else 0.44 * min(height, width)
        self.radius = float(seed_radius)
        self.centre = np.array([width * 0.5, height * 0.5], dtype=np.float64)
        self.per_cell, self.rate, self.wander = per_cell, rate, wander
        self.sigma_short = (sigma_short, sigma_short * anisotropy)
        self.sigma_long = (sigma_long, sigma_long * anisotropy)
        self.weight, self.recency = weight, recency
        self.growth = growth if growth is not None else 0.34
        self.generator = np.random.default_rng(seed)

        count = int(math.pi * self.radius ** 2 / per_cell)
        span = self.radius * np.sqrt(self.generator.random(count))
        angle = self.generator.uniform(0.0, 2.0 * math.pi, count)
        self.x = (self.centre[0] + span * np.cos(angle)).astype(np.float32)
        self.y = (self.centre[1] + span * np.sin(angle)).astype(np.float32)
        self.kind = (self.generator.random(count) < 0.5).astype(np.int8)
        self.age = np.zeros(count, dtype=np.float32)
        self.switches = 0

    def _bins(self) -> tuple[np.ndarray, np.ndarray]:
        row = np.clip((self.y / self.divisor).astype(np.int32), 0, self.rows - 1)
        column = np.clip((self.x / self.divisor).astype(np.int32), 0, self.columns - 1)
        return row, column

    def drive(self) -> np.ndarray:
        """Short-range support for one's own kind, minus long-range suppression.

        Smoothed with `mode="nearest"`, never wrapped: the skin has an edge and
        a cell at the rim must not read the far side of the disc as a
        neighbour, or stripes stitch themselves across the black.
        """
        row, column = self._bins()
        field = np.zeros((self.rows, self.columns), dtype=np.float32)
        np.add.at(field, (row, column), np.where(self.kind == 1, 1.0, -1.0))
        short = self._gaussian(field, self.sigma_short, mode="nearest")
        long_range = self._gaussian(field, self.sigma_long, mode="nearest")
        return short - self.weight * long_range

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            if self.radius < self.limit:
                previous = self.radius
                self.radius = min(self.radius + self.growth, self.limit)
                scale = self.radius / previous
                self.x = (self.centre[0] + (self.x - self.centre[0]) * scale).astype(np.float32)
                self.y = (self.centre[1] + (self.y - self.centre[1]) * scale).astype(np.float32)

            drive = self.drive()
            row, column = self._bins()
            want = (drive[row, column] > 0).astype(np.int8)
            # Only a fraction of the skin is up for replacement on any step.
            # Switching every cell that disagrees at once makes the boundary a
            # hard line that snaps between frames instead of a border being
            # argued over, which is what the clip is of.
            hot = self.generator.random(len(self.x)) < self.rate
            flip = hot & (want != self.kind)
            self.switches += int(flip.sum())
            self.kind = np.where(flip, want, self.kind)
            self.age = np.where(flip, 0.0, np.minimum(self.age + 1.0, 4.0 * self.recency)).astype(np.float32)

            self.x += (self.wander * self.generator.standard_normal(len(self.x))).astype(np.float32)
            self.y += (self.wander * self.generator.standard_normal(len(self.y))).astype(np.float32)

            # New skin is new cells, not existing ones spread thinner: hold the
            # areal density and let the population follow the area.
            target = int(math.pi * self.radius ** 2 / self.per_cell)
            missing = target - len(self.x)
            if missing > 0:
                span = self.radius * np.sqrt(self.generator.random(missing))
                angle = self.generator.uniform(0.0, 2.0 * math.pi, missing)
                born_x = (self.centre[0] + span * np.cos(angle)).astype(np.float32)
                born_y = (self.centre[1] + span * np.sin(angle)).astype(np.float32)
                born_row = np.clip((born_y / self.divisor).astype(np.int32), 0, self.rows - 1)
                born_column = np.clip((born_x / self.divisor).astype(np.int32), 0, self.columns - 1)
                self.x = np.concatenate((self.x, born_x))
                self.y = np.concatenate((self.y, born_y))
                self.kind = np.concatenate((self.kind, (drive[born_row, born_column] > 0).astype(np.int8)))
                self.age = np.concatenate((self.age, np.zeros(missing, dtype=np.float32)))

            # Confine the model, not the render: a cell pushed past the margin
            # is put back on it, so the black outside is black because nothing
            # was ever allowed to be there.
            offset = np.hypot(self.x - self.centre[0], self.y - self.centre[1])
            outside = offset > self.radius
            if outside.any():
                scale = self.radius / np.maximum(offset[outside], 1e-6)
                self.x[outside] = (self.centre[0] + (self.x[outside] - self.centre[0]) * scale).astype(np.float32)
                self.y[outside] = (self.centre[1] + (self.y[outside] - self.centre[1]) * scale).astype(np.float32)

    def boundary(self) -> int:
        """Stripe border on screen, in pixels. The quantity the piece is about.

        Divided by the radius it says which of the two things is happening: a
        flat ratio is stripes being stretched, a rising one is stripes being
        split.
        """
        drive = self.drive()
        grid_y, grid_x = np.mgrid[: self.rows, : self.columns]
        inside = (
            (grid_y - self.centre[1] / self.divisor) ** 2
            + (grid_x - self.centre[0] / self.divisor) ** 2
        ) < (self.radius / self.divisor - 2.0) ** 2
        warm = (drive > 0) & inside
        total = int((warm[:-1, :] != warm[1:, :])[inside[:-1, :] & inside[1:, :]].sum())
        total += int((warm[:, :-1] != warm[:, 1:])[inside[:, :-1] & inside[:, 1:]].sum())
        return total * self.divisor

    @property
    def count(self) -> int:
        return len(self.x)

    def species(self) -> np.ndarray:
        return self.kind

    def weights(self) -> np.ndarray:
        """A cell that has just changed its mind is worth more light.

        Density is otherwise flat everywhere inside the disc -- two-valued
        cells at one areal density give the log-density map a solid block to
        work on and the frame reads as a printed pattern rather than a
        population. Recency is the one thing about a cell that is neither its
        type nor its position, it is intrinsic, and it is concentrated exactly
        where the pattern is being decided.
        """
        return (1.0 + 2.4 * np.exp(-self.age / self.recency)).astype(np.float32)

    def cells(self) -> tuple[np.ndarray, np.ndarray]:
        """Positions, and how recently each cell last changed type."""
        points = np.column_stack((self.x, self.y)).astype(np.float32)
        return points, np.exp(-self.age / self.recency).astype(np.float32)


class Closure:
    """Dorsal closure: a hole in the epidermis pulsed shut, then zipped.

    Two tissues in one sheet. Inside the hole sit the amnioserosa cells --
    large, flat, and each one contracting and relaxing on its own phase. The
    contraction *ratchets*: a cell gives back less than it took, so the sheet
    loses area without any cell being told the plan. Around the hole is the
    lateral epidermis, finer-grained and passive, which stretches to keep the
    sheet whole and closes over whatever the amnioserosa gives up.

    Nothing here scripts the shape. The zipper is one rule -- two epidermal
    cells that face each other across the hole pull together -- and because the
    hole is a lens, they are closest at its two ends, so it seams from the
    canthi inward and the hole goes from a lens to a slit on its own. The
    ingression events are the same story: a cell that has contracted past a
    threshold leaves the sheet, and its neighbours close over the gap.

    Colour is how hard a cell is pulling right now -- the rate it is
    commanding its own apical area down, which is the myosin channel a real
    dorsal closure movie is filmed in. That is what makes the beat visible:
    roughly six contractions per cell over an 8 s clip, all out of phase. The
    epidermis never contracts, so it sits at the dark end for free, and the
    separation is exact -- every cell above half the colour reference is an
    amnioserosa cell, measured, at both ends of the clip.
    """

    def __init__(
        self,
        height: float = 1920.0,
        width: float = 1080.0,
        seed: int = 1,
        lens: tuple[float, float] = (0.36, 0.34),
        amnio_radius: float = 32.0,
        epi_radius: float = 13.0,
        period: float = 42.0,
        period_sd: float = 0.18,
        amp: float = 0.34,
        ratchet: float = 0.010,
        ratchet_sd: float = 0.35,
        ingress: float = 0.34,
        margin: float = 0.25,
        lloyd: float = 0.55,
        gain: float = 0.06,
        pitch: float = 5.0,
        seam: float = 1.6,
        seam_range: float = 8.0,
        rim_boost: float = 1.5,
    ) -> None:
        self.h, self.w = float(height), float(width)
        # The sheet runs well past the frame. It has to: the epidermis closes
        # the hole by *flowing in*, and with the tissue clamped to the frame
        # edges there is nowhere for it to flow from -- the last cut left 65
        # amnioserosa cells owning enormous territories because the epidermis
        # around them was jammed against the wall and could not advance. The
        # epidermis really does wrap the whole embryo, so this is the honest
        # geometry as well as the one that works. 0.25 puts the outer edge
        # 270 px clear of the frame, against the ~80 px of inward travel the
        # 698,000 px^2 the hole gives up actually asks of it.
        self.pad = margin * float(width)
        self._pitch = float(pitch)
        self.rng = np.random.default_rng(seed)
        self.amp, self.lloyd, self.gain = amp, lloyd, gain
        self.seam, self.seam_range = seam, seam_range
        self.ingress, self.epi_radius = ingress, epi_radius
        self.rim_boost = rim_boost
        self.t = 0.0

        rng = self.rng
        ax, ay = lens[0] * self.w, lens[1] * self.h
        cx, cy = self.w * 0.5, self.h * 0.5

        # Amnioserosa on a jittered hex lattice inside the lens, epidermis on
        # the same lattice outside it. Seeding both from one lattice rather
        # than at random is what lets the sheet be packed at frame one instead
        # of spending the opening seconds relaxing out of an overlap.
        pts, kind = [], []
        for r0, inside in ((amnio_radius, True), (epi_radius, False)):
            lattice = r0 * 1.86
            lo_x, hi_x = -self.pad, self.w + self.pad
            lo_y, hi_y = -self.pad, self.h + self.pad
            rows = int((hi_y - lo_y) / (lattice * 0.866)) + 3
            cols = int((hi_x - lo_x) / lattice) + 3
            for j in range(rows):
                for i in range(cols):
                    x = lo_x + (i + 0.5 * (j % 2)) * lattice
                    y = lo_y + j * lattice * 0.866
                    if not (lo_x <= x <= hi_x and lo_y <= y <= hi_y):
                        continue
                    u = (x - cx) / ax
                    v = (y - cy) / ay
                    # The lens: two circular arcs, so it is pointed at the ends
                    # rather than elliptical. The points are where it zips.
                    inlens = abs(u) <= math.sqrt(max(1.0 - v * v, 0.0)) ** 0.72
                    if inlens != inside:
                        continue
                    if inside is False and inlens:
                        continue
                    # 0.30, not 0.16: at 0.16 the relaxed sheet keeps the seeding
                    # lattice and draws as a honeycomb, which is a beehive rather
                    # than an epithelium. Amnioserosa cells are irregular.
                    pts.append((x + rng.normal(0, r0 * 0.30), y + rng.normal(0, r0 * 0.30)))
                    kind.append(1 if inside else 0)

        self.p = np.asarray(pts, dtype=np.float64)
        self.kind = np.asarray(kind, dtype=np.int8)          # 1 amnioserosa, 0 epidermis
        n = len(self.p)
        self.r0 = np.where(self.kind == 1, amnio_radius, epi_radius).astype(np.float64)
        self.A0 = np.pi * self.r0 ** 2
        self.A_amnio_0 = float(self.A0[self.kind == 1].sum())
        # The cell's volume, fixed. Apical area is what changes; the cell keeps
        # what it has and gets taller, which is what `heights` reports.
        self.vol = self.A0.copy()
        self.phase = rng.uniform(0, 2 * np.pi, n)
        self.per = period * np.exp(rng.normal(0, period_sd, n))
        # Per-cell ratchet rate. One shared rate puts every ingression event in
        # the same handful of steps -- measured at the gate, the sheet emptied
        # at step 132 of 255. The spread is what spaces them over the clip.
        self.rate = ratchet * np.exp(rng.normal(0, ratchet_sd, n))
        self.floor = ingress * np.pi * amnio_radius ** 2
        # The power weight, in radius units. It is a *state variable* chased
        # toward whatever makes the cell's territory match its preferred area,
        # not a number read off the preferred area directly -- reading it off
        # was the whole failure: a weight that does not match the territory the
        # diagram actually hands out steals slivers from the neighbours, and
        # the last second of the clip came out as radial fans.
        self.rw = np.sqrt(self.A0 / np.pi)
        # `self._pitch`, not `pitch`. The seeding loop above used to rebind the
        # name, so the mechanics grid was built at 24.18 px instead of 5 and
        # `_px` was 585 instead of 25 -- every territory area, `hole()` and
        # `heights()` wrong by 23x, and an amnioserosa cell resolved by four
        # grid points. It is the reason the tiling would not hold still.
        xs = np.arange(-self.pad + self._pitch * 0.5, self.w + self.pad, self._pitch)
        ys = np.arange(-self.pad + self._pitch * 0.5, self.h + self.pad, self._pitch)
        self._grid = np.stack(np.meshgrid(xs, ys, indexing="xy"), -1).reshape(-1, 2)
        self._px = self._pitch * self._pitch
        self.area = np.pi * self.rw ** 2
        # How hard the cell is pulling: the fractional rate at which it is
        # commanding its own apical area down, smoothed. This is the myosin
        # channel -- medial myosin is what a dorsal closure movie is actually
        # filmed in, and it is what pulses -- and it is intrinsic to the cell
        # and independent of anything about the camera.
        #
        # The obvious alternative, the rate the cell's *territory* shrinks, was
        # tried and does not work: the sheet jostles its neighbours as it
        # closes, so a resting epidermal tile fluctuates as fast as an
        # amnioserosa cell contracts. Measured, 98th percentile of the pulse:
        # amnioserosa 0.0237, epidermis 0.0200. No separation to colour with.
        #
        # Fractional, not absolute, so a large cell and a small one pulling
        # equally hard read the same; the colour is effort, not size.
        self.pulse = np.zeros(len(self.p))
        self.gone = 0

    # ------------------------------------------------------------------ state
    def _pref(self) -> np.ndarray:
        """Preferred apical area. The beat is on the amnioserosa only."""
        beat = 1.0 + self.amp * np.sin(2 * np.pi * self.t / self.per + self.phase)
        return np.where(self.kind == 1, self.A0 * beat, self.A0)

    def _radii(self) -> np.ndarray:
        """Radius of the territory the cell actually holds."""
        return np.sqrt(np.maximum(self.area, 1.0) / np.pi)

    @property
    def count(self) -> int:
        return len(self.p)

    def relax(self, n: int = 80) -> None:
        """Pack the sheet without advancing the clock.

        Stepping to settle would ratchet as well, and 60 settle steps cost 26%
        of the hole before frame one -- the opening picture is the hole.
        """
        for _ in range(n):
            self._mechanics()

    # ------------------------------------------------------------------- step
    def step(self, n: int = 1) -> None:
        for _ in range(n):
            self._one()

    def _one(self) -> None:
        # Sampled before the clock moves, or the difference below sees only the
        # ratchet increment and not the beat -- which cost an ending: the
        # survivors of the ingression are the cells with the *slowest* ratchet,
        # so a colour built on the ratchet alone dims to nothing exactly as the
        # clip finishes. The beat term is 0.051 a step at peak against the
        # ratchet's 0.010, and it is amplitude-independent, so a cell pulls as
        # visibly in the last second as in the first.
        was = self._pref()
        self.t += 1.0

        # The ratchet: area is only partly given back after each contraction.
        amnio = self.kind == 1
        ph = 2 * np.pi * self.t / self.per + self.phase
        pull = amnio & (np.cos(ph) < 0.0)
        # A cell contracts harder the more of its neighbourhood is epidermis --
        # it is the one taking the tension. That is what puts the zipper in:
        # the lens is pointed at its two ends, so a cell there is surrounded on
        # three sides rather than two, ratchets faster, and leaves sooner. The
        # canthi retreat first and nothing had to be told where they are.
        self.A0 = np.where(pull, self.A0 * (1.0 - self.rate * (1.0 + self.rim_boost * self._rim())),
                           self.A0)

        # The epidermis stretches as well as flows. Both are needed and each
        # fails alone: clamped to the frame it has nowhere to flow from and the
        # last cells end up owning enormous territories, and flowing without
        # stretching leaves the sheet under-packed once the hole has given up
        # its area -- 4.41M px^2 of preferred area in a 4.91M px^2 field -- at
        # which point the packing falls apart into radial fans.
        epi = ~amnio
        if epi.any():
            released = self.A_amnio_0 - float(self.A0[amnio].sum())
            share = released / int(epi.sum())
            self.A0 = np.where(epi, np.pi * self.epi_radius ** 2 + share, self.A0)

        self._mechanics()
        # 0.28 over a 42-step beat keeps the pulse and drops the step noise.
        drop = (was - self._pref()) / np.maximum(was, 1.0)
        self.pulse = 0.72 * self.pulse + 0.28 * drop

        # Ingression: a cell that has contracted past the floor leaves the
        # sheet, and the neighbours close over it.
        leaving = amnio & (self.A0 < self.floor)
        if leaving.any():
            keep = ~leaving
            self.gone += int(leaving.sum())
            for name in ("p", "kind", "r0", "A0", "phase", "per", "rate",
                         "vol", "rw", "area", "pulse"):
                setattr(self, name, getattr(self, name)[keep])

    def _rim(self) -> np.ndarray:
        """Fraction of each cell's neighbourhood that is epidermis."""
        out = np.zeros(len(self.p))
        who = np.flatnonzero(self.kind == 1)
        if not len(who):
            return out
        near = cKDTree(self.p).query_ball_point(self.p[who], 2.4 * float(self.r0.max()))
        epi = (self.kind == 0).astype(np.float64)
        out[who] = [epi[j].mean() if len(j) else 0.0 for j in near]
        return out

    def _mechanics(self) -> None:
        """One Laguerre-Lloyd pass with an area target.

        Soft discs cannot do this job. They constrain overlap, not territory,
        so nothing stops a cell's drawn tile from disagreeing with the area it
        wants -- four cuts died on that, ending as scattered discs in a void,
        as sixty cells owning enormous polygons, and twice as radial fans.
        Lloyd relaxation constrains the tiling itself and is strongly
        regularising, and the weight feedback is what makes each tile the size
        the cell is asking for. Tearing is impossible by construction: the
        diagram partitions the plane whatever the cells do.
        """
        g = self._grid
        n = len(self.p)
        k = min(8, n)
        d, idx = cKDTree(self.p).query(g, k=k)
        if k == 1:
            idx = idx[:, None]; d = d[:, None]
        power = d ** 2 - self.rw[idx] ** 2
        own = idx[np.arange(len(g)), np.argmin(power, axis=1)]

        count = np.bincount(own, minlength=n).astype(np.float64)
        cx = np.bincount(own, weights=g[:, 0], minlength=n)
        cy = np.bincount(own, weights=g[:, 1], minlength=n)
        live = count > 0.0
        centre = np.zeros((n, 2))
        centre[live] = np.column_stack((cx[live], cy[live])) / count[live, None]
        self.p[live] += self.lloyd * (centre[live] - self.p[live])

        self.area = count * self._px
        want = np.sqrt(np.maximum(self._pref(), 1.0) / np.pi)
        have = np.sqrt(np.maximum(self.area, 1.0) / np.pi)
        # Bounded, and bounded twice. A power diagram is violently sensitive to
        # weight differences -- once a weight exceeds a neighbour's by more
        # than the distance between them it swallows that neighbour whole -- so
        # an unbounded integrator here does not converge, it rings. Measured on
        # the first version at gain 0.35 with no clamp: weights ran 32 -> 274,
        # amnioserosa territories collapsed to three grid cells and recovered
        # to 7,600 px^2 and back, every cell, every few steps, and the beat was
        # buried under the ringing (98th percentile of the pulse: 0.0000).
        step = np.clip(self.gain * (want - have), -0.5, 0.5)
        self.rw = np.clip(self.rw + step, 0.55 * want, 1.7 * want)

        self._seam()
        np.clip(self.p[:, 0], -self.pad, self.w + self.pad, out=self.p[:, 0])
        np.clip(self.p[:, 1], -self.pad, self.h + self.pad, out=self.p[:, 1])

    def _seam(self) -> None:
        """The zipper: two epidermal cells facing each other across the hole pull together.

        The lens is narrowest at its two ends, so that is where this bites
        first and the seam runs inward from both canthi. Nothing tells it where
        they are.
        """
        p = self.p
        eps = np.flatnonzero(self.kind == 0)
        ams = np.flatnonzero(self.kind == 1)
        if len(eps) < 2 or not len(ams):
            return
        reach = self.seam_range * self.epi_radius
        near = np.asarray(list(cKDTree(p[eps]).query_pairs(reach)), dtype=np.int64)
        if not len(near):
            return
        a, b = eps[near[:, 0]], eps[near[:, 1]]
        delta = p[b] - p[a]
        L = np.maximum(np.hypot(delta[:, 0], delta[:, 1]), 1e-9)
        r = self._radii()
        far = L > 1.35 * (r[a] + r[b])
        mid = 0.5 * (p[a] + p[b])
        gap, who = cKDTree(p[ams]).query(mid)
        across = far & (gap < r[ams][who])
        if not across.any():
            return
        # Falloff with distance, so the closest facing pairs pull hardest.
        # `reach` is the number that decides whether any of this happens: at
        # 3.2 x the epidermal radius the rule fired once in a whole step,
        # because two epidermal cells with an amnioserosa cell between them are
        # at least 100 px apart and the reach was 58. Across-pairs per step at
        # 58 / 144 / 252 px: 1 / 138 / 440 at the start, 0 / 28 / 107 by 180.
        lam = np.clip(1.0 - L[across] / reach, 0.0, 1.0)
        f = delta[across] * (self.seam * lam / L[across])[:, None]
        np.add.at(p, a[across], +f)
        np.add.at(p, b[across], -f)

    # ----------------------------------------------------------------- probes
    def radii(self) -> np.ndarray:
        """The power weights, which is what the renderer tiles with."""
        return self.rw

    def heights(self) -> np.ndarray:
        """How tall each cell is now, as a multiple of its resting height.

        Apical constriction conserves volume: a cell that halves its apical
        area is twice as tall, so there is twice as much of it under every
        pixel it still covers. That is the one honest brightness signal in the
        sheet -- the amnioserosa thickens as it pulls and the epidermis thins
        as it stretches, which is exactly the separation the picture needs, and
        neither is a decision anyone made about the look.
        """
        return np.clip(self.vol / np.maximum(self.area, 1e-9), 0.25, 4.0)

    def hole(self) -> float:
        """Area the amnioserosa still holds, in px^2. Territory, not preference."""
        return float(self.area[self.kind == 1].sum())

    def cells(self) -> tuple[np.ndarray, np.ndarray]:
        """Positions, and how fast each cell is contracting right now.

        Not ranked. The scalar is bimodal rather than skewed -- the epidermis
        sits near zero by construction -- so ranking would drag the resting
        sheet up the ramp and spend the palette on cells doing nothing.
        """
        return self.p.astype(np.float32), np.maximum(self.pulse, 0.0).astype(np.float32)
