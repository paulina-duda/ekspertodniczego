#!/usr/bin/env python3
"""Five processes on a substrate: four taken from biology, one from arithmetic.

The companion set in `../source/` runs two mathematical processes and one
biological one. This one inverts that. `Hyphae`, `Cleavage`, `Excitable` and
`Condensate` are things a microscope can be pointed at; `Sandpile` is a rule
about integers that has no business producing an organism and does anyway.

Four of them make something out of nothing -- a colony, a partition, a heap, a
wave. `Condensate` is the odd one: it adds no material at all after the first
step, and only rearranges what is already in the dish.

Every model exposes the same three things -- `step`, `metric` and whatever the
renderer needs to draw -- so the renderer can measure a process it knows nothing
about and schedule frames by how much the picture is actually changing.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import ConvexHull, cKDTree

try:  # optional: Cahn-Hilliard wants a small timestep and many of them
    import torch
except ImportError:  # pragma: no cover
    torch = None


class Hyphae:
    """Fungal mycelium: tip growth, branching, and fusion.

    A hypha only ever extends at its tip. It wanders, it splits, and -- this is
    the part that makes it a fungus rather than a tree -- when a tip runs into
    another hypha it fuses with it and stops. That fusion is anastomosis, and it
    is why a mycelium is a *network* with loops in it, able to route around
    damage and carry material between distant points, instead of a branching
    tree where every path back to the trunk is unique.

    Tips also turn away from ground that has already been colonised, which is
    the cheapest honest stand-in for growing down a nutrient gradient: the
    substrate behind the front is spent.
    """

    def __init__(
        self,
        height: int,
        width: int,
        tips: int = 7,
        speed: float = 1.25,
        wander: float = 0.20,
        radius: float | None = None,
        sensor: float = 7.0,
        sensor_angle: float = math.radians(32.0),
        turn: float = math.radians(15.0),
        branch_rate: float = 0.030,
        max_tips: int = 2600,
        refractory: int = 90,
        seed: int = 20260815,
    ) -> None:
        self.height, self.width = height, width
        # Bounded like a plate culture: unbounded, the colony runs off every edge,
        # buries the caption and loses the black the house style is composed on.
        self.radius = float(min(height, width) * 0.44 if radius is None else radius)
        self.centre = np.array([width * 0.5, height * 0.5], dtype=np.float32)
        self.speed, self.wander = speed, wander
        self.sensor, self.sensor_angle, self.turn = sensor, sensor_angle, turn
        self.branch_rate, self.max_tips, self.refractory = branch_rate, max_tips, refractory
        self.generator = np.random.default_rng(seed)

        angle = np.linspace(0.0, 2.0 * math.pi, tips, endpoint=False)
        self.x = np.full(tips, width * 0.5, dtype=np.float32)
        self.y = np.full(tips, height * 0.5, dtype=np.float32)
        self.heading = angle.astype(np.float32)

        # When each pixel was last written to. Anastomosis needs to tell "another
        # hypha" from "the piece of myself I laid down two steps ago", and the
        # only difference between them is age.
        self.touched = np.full((height, width), -10_000, dtype=np.int32)
        self.step_index = 0

        self.points: list[np.ndarray] = []
        self.ages: list[np.ndarray] = []
        # Running count of pixels ever written, so the renderer can ask how far
        # along the growth is after every one of a thousand steps without
        # rescanning two million cells each time.
        self.lit = 0
        self._deposit()

    def _sample(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        column = np.clip(x.astype(np.int32), 0, self.width - 1)
        row = np.clip(y.astype(np.int32), 0, self.height - 1)
        return (self.touched[row, column] > -10_000).astype(np.float32)

    def _deposit(self) -> None:
        column = np.clip(self.x.astype(np.int32), 0, self.width - 1)
        row = np.clip(self.y.astype(np.int32), 0, self.height - 1)
        self.lit += int((self.touched[row, column] == -10_000).sum())
        self.touched[row, column] = self.step_index
        self.points.append(np.column_stack((self.x, self.y)).astype(np.float32))
        self.ages.append(np.full(len(self.x), self.step_index, dtype=np.float32))

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            if not len(self.x):
                return
            self.step_index += 1

            left = self._sample(
                self.x + self.sensor * np.cos(self.heading + self.sensor_angle),
                self.y + self.sensor * np.sin(self.heading + self.sensor_angle),
            )
            right = self._sample(
                self.x + self.sensor * np.cos(self.heading - self.sensor_angle),
                self.y + self.sensor * np.sin(self.heading - self.sensor_angle),
            )
            # Turn away from whichever side is more colonised; a tie leaves the
            # heading alone and lets the wander term decide.
            self.heading = self.heading + np.where(left > right, -self.turn, np.where(right > left, self.turn, 0.0))
            self.heading = (
                self.heading + self.generator.normal(0.0, self.wander, len(self.x))
            ).astype(np.float32)

            self.x = (self.x + self.speed * np.cos(self.heading)).astype(np.float32)
            self.y = (self.y + self.speed * np.sin(self.heading)).astype(np.float32)

            inside = (
                np.hypot(self.x - self.centre[0], self.y - self.centre[1]) < self.radius
            )
            column = np.clip(self.x.astype(np.int32), 0, self.width - 1)
            row = np.clip(self.y.astype(np.int32), 0, self.height - 1)
            fused = (self.step_index - self.touched[row, column]) < self.refractory
            fused = ~fused & (self.touched[row, column] > -10_000)
            alive = inside & ~fused
            self.x, self.y, self.heading = self.x[alive], self.y[alive], self.heading[alive]
            if not len(self.x):
                return

            self._deposit()

            room = self.max_tips - len(self.x)
            if room > 0:
                splitting = self.generator.random(len(self.x)) < self.branch_rate
                if splitting.any():
                    chosen = np.flatnonzero(splitting)[:room]
                    side = np.where(self.generator.random(len(chosen)) < 0.5, 1.0, -1.0)
                    self.x = np.concatenate((self.x, self.x[chosen]))
                    self.y = np.concatenate((self.y, self.y[chosen]))
                    self.heading = np.concatenate(
                        (self.heading, self.heading[chosen] + side * math.radians(38.0))
                    ).astype(np.float32)

    def metric(self) -> float:
        return float(self.lit)

    def samples(self) -> tuple[np.ndarray, np.ndarray]:
        return np.concatenate(self.points), np.concatenate(self.ages)


class Cleavage:
    """The first divisions of an embryo: a fixed volume cut into smaller cells.

    Cleavage is the one kind of growth that does not grow. The egg divides and
    divides without gaining any mass, so each round halves the cells rather than
    enlarging the animal, and what changes is not the size of the thing but how
    finely it is partitioned. That is why the disc here never widens.

    Between divisions the cells relax: each moves towards the centroid of its own
    Voronoi region, which is Lloyd's algorithm and also, near enough, what
    surface tension does to a sheet of packed cells. It is the reason a real
    epithelium looks like a honeycomb that has been sat on rather than like a
    random scatter.
    """

    def __init__(
        self,
        height: int,
        width: int,
        radius: float,
        divide_rate: float = 0.075,
        max_cells: int = 4200,
        relax: float = 0.55,
        seed: int = 20260815,
    ) -> None:
        self.height, self.width, self.radius = height, width, radius
        self.divide_rate, self.max_cells, self.relax = divide_rate, max_cells, relax
        self.generator = np.random.default_rng(seed)

        rows, columns = np.mgrid[0:height, 0:width]
        centre = np.array([width * 0.5, height * 0.5])
        inside = (columns - centre[0]) ** 2 + (rows - centre[1]) ** 2 < radius * radius
        self.lattice = np.column_stack((columns[inside], rows[inside])).astype(np.float32)
        self.inside = inside

        self.centres = centre[None, :].astype(np.float32)
        self.generation = np.zeros(1, dtype=np.float32)

    def _assign(self) -> np.ndarray:
        return cKDTree(self.centres).query(self.lattice, workers=-1)[1]

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            total = len(self.centres)
            splitting = self.generator.random(total) < self.divide_rate
            if total < 8:
                splitting[:] = True
            if total >= self.max_cells:
                splitting[:] = False
            if splitting.any():
                chosen = np.flatnonzero(splitting)
                # Offset by a fraction of the current mean cell radius, so the
                # daughters start apart at whatever scale the tissue has reached.
                spacing = math.sqrt(math.pi * self.radius**2 / total) * 0.30
                shift = self.generator.normal(0.0, spacing, (len(chosen), 2)).astype(np.float32)
                self.centres[chosen] -= shift * 0.5
                self.centres = np.concatenate((self.centres, self.centres[chosen] + shift))
                self.generation[chosen] += 1.0
                self.generation = np.concatenate((self.generation, self.generation[chosen]))

            labels = self._assign()
            counts = np.bincount(labels, minlength=len(self.centres)).astype(np.float32)
            moved = np.column_stack([
                np.bincount(labels, weights=self.lattice[:, axis], minlength=len(self.centres))
                for axis in (0, 1)
            ]).astype(np.float32)
            occupied = counts > 0
            moved[occupied] /= counts[occupied, None]
            self.centres[occupied] += self.relax * (moved[occupied] - self.centres[occupied])

    def metric(self) -> float:
        return float(len(self.centres))

    def fields(self) -> tuple[np.ndarray, np.ndarray]:
        """Cell walls as a density field, tinted by how many divisions deep."""
        labels = self._assign()
        label_grid = np.full((self.height, self.width), -1, dtype=np.int32)
        label_grid[self.inside] = labels

        wall = np.zeros((self.height, self.width), dtype=np.float32)
        for axis in (0, 1):
            difference = np.diff(label_grid, axis=axis) != 0
            both = np.logical_and(
                np.take(label_grid, np.arange(label_grid.shape[axis] - 1), axis=axis) >= 0,
                np.take(label_grid, np.arange(1, label_grid.shape[axis]), axis=axis) >= 0,
            )
            edge = difference & both
            if axis == 0:
                wall[:-1, :] += edge
                wall[1:, :] += edge
            else:
                wall[:, :-1] += edge
                wall[:, 1:] += edge

        depth = np.zeros((self.height, self.width), dtype=np.float32)
        span = max(float(self.generation.max()), 1.0)
        depth[self.inside] = self.generation[labels] / span
        # A faint wash inside every cell, so the tissue reads as filled rather
        # than as a wire mesh floating on black.
        density = np.clip(wall, 0.0, 1.0) + 0.11 * self.inside
        return density.astype(np.float32), depth


class Sandpile:
    """The abelian sandpile: drop grains on one square and let them topple.

    A cell holding four grains gives one to each neighbour, and that is the
    entire rule. Drop a few hundred thousand grains on a single square of an
    empty lattice and what stabilises is not a heap but a sharply bounded
    fractal with straight-edged regions, the same one every time, independent of
    the order the grains were added -- which is what "abelian" means here.

    It is in this set as the mathematics, and it earns the place by looking like
    a radiolarian while containing no biology whatsoever.
    """

    def __init__(self, size: int) -> None:
        self.size = size
        self.grid = np.zeros((size, size), dtype=np.int32)
        self.touched = np.zeros((size, size), dtype=bool)
        self.previous = np.zeros((size, size), dtype=np.int32)
        self.grains = 0

    def _window(self) -> slice:
        """The square the pile can possibly have reached, plus a margin.

        Toppling is a whole-array operation, and running it over a 541-square
        board while the pile is forty across wastes almost all of the work. The
        stable pile holds a little over two grains a cell, so its radius is close
        to sqrt(grains / 2 pi); taking that with a wide margin bounds the region
        cheaply, and the assertion below is what keeps the bound honest.
        """
        radius = int(math.sqrt(max(self.grains, 1) / (math.pi * 2.0)) * 1.30) + 12
        middle = self.size // 2
        return slice(max(middle - radius, 0), min(middle + radius + 1, self.size))

    def add(self, grains: int) -> None:
        middle = self.size // 2
        self.previous = self.grid.copy()
        self.grid[middle, middle] += grains
        self.grains += grains

        window = self._window()
        # A contiguous copy, and a shift instead of a divide. The slice of the
        # board is strided, and every toppling round touches it five times; on a
        # quarter-million cells that difference is most of the running time.
        block = np.ascontiguousarray(self.grid[window, window])
        while True:
            topple = block >> 2
            if not topple.any():
                break
            block -= topple << 2
            block[1:, :] += topple[:-1, :]
            block[:-1, :] += topple[1:, :]
            block[:, 1:] += topple[:, :-1]
            block[:, :-1] += topple[:, 1:]
        assert not block[0, :].any() and not block[-1, :].any(), "pile reached the window edge"
        self.grid[window, window] = block
        self.touched |= self.grid > 0

    def record(self, frames: int, total: int) -> list[np.ndarray]:
        """Every frame's stable configuration, kept as int8.

        Grains are added as the square of elapsed time, because the pile's area
        grows with the count and its radius therefore with the square root; that
        schedule is what makes the edge advance at a steady speed instead of
        bolting outwards and then crawling.

        The whole run is banked rather than simulated twice. A state is a quarter
        of a megabyte at this size, so the entire clip fits in about fifty, and
        the alternative is paying for every toppling in the piece a second time.
        """
        states: list[np.ndarray] = []
        for index in range(1, frames + 1):
            target = int(total * (index / frames) ** 2)
            if target > self.grains:
                self.add(target - self.grains)
            states.append(self.grid.astype(np.int8))
        return states

    def metric(self) -> float:
        return float(self.touched.sum())

    def fields(self) -> tuple[np.ndarray, np.ndarray]:
        """Grain count as colour, with the working edge lit while it moves."""
        shade = self.grid.astype(np.float32) / 3.0
        density = np.where(self.touched, 0.20 + 0.80 * shade, 0.0).astype(np.float32)
        # Wherever the pile is still rearranging, brighten it. The frontier is
        # the only part of a finished sandpile that was ever in motion, and
        # lighting it is what keeps a static fractal reading as a growing one.
        density += 0.55 * (self.grid != self.previous)
        return density.astype(np.float32), np.clip(shade, 0.0, 1.0)


class Excitable:
    """Spiral waves in a sheet of excitable tissue, and the beat that starts them.

    An excitable medium has one move: rest until a neighbour pushes it over a
    threshold, fire once, then refuse to fire again until it has recovered.
    Heart muscle does it, so do neurons and the Belousov-Zhabotinsky reaction,
    and the whole of it is two lines -- Barkley's model, a fast variable `u`
    that fires and diffuses and a slow one `v` that holds the tissue shut
    behind the front.

    Run that on a sheet and waves travel outwards and annihilate when they meet,
    because each one runs into the other's refractory wake. Nothing in the rule
    says *spiral*. A spiral needs a wave with a free end -- a break -- and the
    honest way to make one is the way a cardiology lab does it: deliver a second
    stimulus early, into the tail of the wave that just passed, so half of it
    lands on tissue that has recovered and half on tissue that has not. The half
    that can propagate curls around the half that cannot, and the free end
    starts to rotate. That is reentry: the wave re-enters tissue it has already
    been through, and it circulates until something stops it. In a heart, this
    is not a metaphor for the failure -- it *is* the failure.

    The sheet is deliberately not uniform. Real tissue is not, and a wave that
    meets a patch it cannot excite fast enough breaks there on its own, which is
    how one rotor becomes several without anyone stimulating anything.
    """

    def __init__(
        self,
        height: int,
        width: int,
        radius: float | None = None,
        a: float = 0.75,
        b: float = 0.02,
        epsilon: float = 0.05,
        diffusion: float = 1.0,
        dt: float = 0.10,
        roughness: float = 0.016,
        afterglow: float = 260.0,
        seed: int = 20260823,
    ) -> None:
        self.height, self.width = height, width
        self.a, self.epsilon, self.diffusion, self.dt = a, epsilon, diffusion, dt
        # The excited state is two cells wide and gone in a moment: rendered
        # honestly and nothing else, the piece is a few bright threads on black
        # with no record of where they have been. `afterglow` is the half-life,
        # in steps, of a decaying memory of the last firing -- a phosphor, and
        # the same thing an optical mapping rig sees when it images voltage dye.
        self.decay = float(0.5 ** (1.0 / max(afterglow, 1.0)))
        self.generator = np.random.default_rng(seed)

        rows, columns = np.mgrid[0:height, 0:width]
        centre = (width * 0.5, height * 0.5)
        self.radius = float(min(height, width) * 0.44 if radius is None else radius)
        self.dish = (
            (columns - centre[0]) ** 2 + (rows - centre[1]) ** 2 < self.radius**2
        )

        # Excitability varies from place to place, smoothly. Diffusing white
        # noise is the cheapest way to a field with a length scale: a few dozen
        # passes of the same laplacian the model itself uses turns a per-pixel
        # scatter into patches a wavelength or so across.
        rough = self.generator.normal(0.0, 1.0, (height, width)).astype(np.float32)
        for _ in range(40):
            rough += 0.25 * self._laplacian(rough)
        rough /= max(float(rough.std()), 1e-6)
        self.b = np.clip(b + rough * roughness, 0.004, 0.09).astype(np.float32)

        self.u = np.zeros((height, width), dtype=np.float32)
        self.v = np.zeros((height, width), dtype=np.float32)
        self.wake = np.zeros((height, width), dtype=np.float32)
        self.fired = np.zeros((height, width), dtype=bool)
        self.step_index = 0

    @staticmethod
    def _laplacian(field: np.ndarray) -> np.ndarray:
        # The dish is a hole in a much larger black frame and the wave never
        # reaches the array's edge, so wrapping costs nothing and `np.roll` is
        # the fastest five-point stencil numpy has.
        return (
            np.roll(field, 1, 0)
            + np.roll(field, -1, 0)
            + np.roll(field, 1, 1)
            + np.roll(field, -1, 1)
            - 4.0 * field
        )

    def stimulate(self, row: int, column: int, radius: int = 16) -> None:
        """Fire a small round patch of tissue, whatever state it is in.

        Round because a square one stays square: the wave it launches keeps the
        corners for long enough to be visible on screen as an electrode-shaped
        artefact, and there is nothing square anywhere else in the piece.
        """
        rows = slice(max(row - radius, 0), min(row + radius + 1, self.height))
        columns = slice(max(column - radius, 0), min(column + radius + 1, self.width))
        grid_rows, grid_columns = np.ogrid[rows, columns]
        patch = (grid_rows - row) ** 2 + (grid_columns - column) ** 2 <= radius * radius
        self.u[rows, columns][patch] = 1.0
        self.u *= self.dish

    def premature_site(self) -> tuple[int, int] | None:
        """A spot in the wake of the last wave, half recovered and half not.

        `v` is monotone in how long ago the tissue fired, so a band of it is
        exactly the S2 window: excite here and one side of the stimulus goes and
        the other cannot. Picking at random inside the band, rather than at the
        single best pixel, is what stops every rotor in the piece from being
        born in the same place.
        """
        window = self.dish & (self.v > 0.30) & (self.v < 0.55)
        candidates = np.flatnonzero(window)
        if not len(candidates):
            return None
        choice = int(self.generator.choice(candidates))
        return divmod(choice, self.width)

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            self.step_index += 1
            # Barkley: u fires fast (1/epsilon) once it passes the threshold
            # (v + b)/a and diffuses to its neighbours; v just follows u, and
            # its lag is the refractory period.
            self.u += self.dt * (
                self.diffusion * self._laplacian(self.u)
                + self.u * (1.0 - self.u) * (self.u - (self.v + self.b) / self.a) / self.epsilon
            )
            self.v += self.dt * (self.u - self.v)
            np.clip(self.u, 0.0, 1.0, out=self.u)
            np.clip(self.v, 0.0, 1.0, out=self.v)
            self.u *= self.dish
            self.v *= self.dish
            np.maximum(self.wake * self.decay, self.u, out=self.wake)
            self.fired |= self.u > 0.5

    def record(
        self, frames: int, steps_per_frame: int, stimuli: tuple[float, ...] = ()
    ) -> list[tuple[np.ndarray, np.ndarray]]:
        """Bank the whole clip, one state per frame, as bytes.

        Waves travel at a fixed speed, so unlike every other process in this set
        this one needs no schedule: equal steps of the clock already are equal
        steps of the process. Eight bits per variable is plenty -- both are
        bounded, and the bloom and the tone curve wash out the quantisation long
        before anyone could see it -- and it keeps the whole eight seconds under
        a quarter of a gigabyte instead of two.

        `stimuli` are the fractions of the clip at which a premature beat is
        delivered. The first wave is launched at the centre, in the clear.
        """
        planned = {max(int(fraction * frames), 1) for fraction in stimuli}
        self.stimulate(self.height // 2, self.width // 2, radius=22)
        states: list[tuple[np.ndarray, np.ndarray]] = []
        for index in range(frames):
            if index in planned:
                site = self.premature_site()
                if site is not None:
                    self.stimulate(*site)
            self.step(steps_per_frame)
            states.append(
                (
                    (self.u * 255.0).astype(np.uint8),
                    (self.wake * 255.0).astype(np.uint8),
                )
            )
        return states

    def metric(self) -> float:
        return float(self.fired.sum())

    @staticmethod
    def fields(state: tuple[np.ndarray, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
        """Brightness from what is firing now, colour from how long ago it did.

        `u` is the front: a couple of cells wide and, for the moment it lasts,
        the brightest thing in the dish. The afterglow behind it is one scalar
        running from just-fired to long-recovered, and that -- not where the
        wave is, but how recently it went past -- is the only thing about this
        medium worth colouring.
        """
        u = state[0].astype(np.float32) / 255.0
        wake = state[1].astype(np.float32) / 255.0
        density = u + 0.75 * wake
        shade = np.maximum(u, wake * 0.92)
        return density, shade


class Condensate:
    """Liquid-liquid phase separation: compartments with no wall around them.

    A cell keeps dozens of distinct chemical workshops going at once -- nucleoli,
    stress granules, P granules -- and for a century the assumption was that
    anything that stayed separate had to be wrapped in a membrane. Most of them
    are not. They are droplets: the same physics that pulls oil out of water,
    running on proteins and RNA, and it builds a compartment out of nothing but
    a preference for its own company.

    The model is Cahn and Hilliard's, which is the textbook statement of that
    preference. One field, `phi`, says which mixture is here. Its free energy has
    two wells, so any value in between is unstable and slides towards one or the
    other; and because `phi` is *conserved* -- material moves, it is not created
    -- what starts as noise cannot simply fade. It has to separate.

    What follows is not a pattern being drawn but a population of droplets
    negotiating: they round themselves off, and then the big ones eat the small
    ones, because a big drop has less surface per unit volume and surface is
    what costs. Nothing is added to the dish after the first step. Every later
    frame is the same material, arranged more cheaply.
    """

    def __init__(
        self,
        height: int,
        width: int,
        radius: float | None = None,
        epsilon: float = 1.0,
        mobility: float = 1.0,
        dt: float = 0.01,
        mixture: float = -0.35,
        noise: float = 0.05,
        reference_radius: float = 9.0,
        seed: int = 20260825,
        device: str | None = None,
    ) -> None:
        self.height, self.width = height, width
        self.epsilon, self.mobility, self.dt = epsilon, mobility, dt
        self.reference_radius = reference_radius

        rows, columns = np.mgrid[0:height, 0:width].astype(np.float32)
        radius = float(min(height, width) * 0.44 if radius is None else radius)
        # The disc is the cell, not a crop: no flux crosses it, so the material
        # inside is all the material there will ever be.
        self.dish = np.hypot(rows - height / 2.0, columns - width / 2.0) < radius

        generator = np.random.default_rng(seed)
        # `mixture` is how much of the dish ends up as droplets. At 0 the two
        # phases are equal and separate into interpenetrating worms; pushed
        # negative, the dense phase is the minority and rounds into drops, which
        # is both what a condensate looks like and the more legible picture.
        field = mixture + generator.normal(0.0, noise, (height, width))
        self.phi = (field * self.dish).astype(np.float32)
        self.age = np.where(self.phi > 0.0, 0.0, -1.0).astype(np.float32)
        self.step_index = 0

        if device is None:
            device = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
        self.device = device if torch is not None else "cpu"
        if self.device != "cpu":
            self._phi = torch.tensor(self.phi, device=self.device)
            self._dish = torch.tensor(self.dish, device=self.device)

    # ------------------------------------------------------------------

    def _laplacian_numpy(self, field: np.ndarray) -> np.ndarray:
        total = np.zeros_like(field)
        for shift, axis in ((1, 0), (-1, 0), (1, 1), (-1, 1)):
            neighbour = np.roll(field, shift, axis)
            inside = np.roll(self.dish, shift, axis)
            # A neighbour outside the dish is replaced by the cell itself, which
            # is what zero gradient means: nothing leaks out of the drop.
            total += np.where(inside, neighbour, field)
        return (total - 4.0 * field) * self.dish

    def _laplacian_torch(self, field):
        total = torch.zeros_like(field)
        for shift, axis in ((1, 0), (-1, 0), (1, 1), (-1, 1)):
            neighbour = torch.roll(field, shift, axis)
            inside = torch.roll(self._dish, shift, axis)
            total += torch.where(inside, neighbour, field)
        return (total - 4.0 * field) * self._dish

    def step(self, count: int = 1) -> None:
        """Explicit Euler, and the step size is not a free choice.

        The fourth-order term sets the stability limit: with `dx = 1` the
        largest eigenvalue of the five-point laplacian is 8, so the scheme needs
        `dt < 2 / (8 · (8·epsilon² - 1))`, which is about 0.017 at epsilon 1.4.
        Overrun it and the field does not drift or wobble -- it saturates
        everywhere on the first few steps and freezes into a frozen speckle that
        never coarsens again, while conserving mass perfectly and so looking
        entirely plausible in every summary statistic.
        """
        eps2 = self.epsilon * self.epsilon
        if self.device != "cpu":
            for _ in range(count):
                mu = self._phi**3 - self._phi - eps2 * self._laplacian_torch(self._phi)
                self._phi = (self._phi + self.dt * self.mobility * self._laplacian_torch(mu)) * self._dish
            self.phi = self._phi.detach().cpu().numpy()
        else:
            for _ in range(count):
                mu = self.phi**3 - self.phi - eps2 * self._laplacian_numpy(self.phi)
                self.phi = (self.phi + self.dt * self.mobility * self._laplacian_numpy(mu)) * self.dish
        self.step_index += count
        fresh = (self.phi > 0.0) & (self.age < 0.0)
        self.age[fresh] = float(self.step_index)

    # ------------------------------------------------------------------

    def metric(self) -> float:
        """Coarsening, measured as interface that has gone away.

        Total interface length only falls, from the moment the mixture first
        separates -- it is the thing the whole process is trying to get rid of.
        Negated, it rises monotonically, which is what the frame scheduler
        wants: equal steps of *coarsening* rather than equal steps of the clock,
        or the last six seconds are one still frame of nothing happening.
        """
        dense = self.phi > 0.0
        edges = 0
        for shift, axis in ((1, 0), (1, 1)):
            edges += int((dense != np.roll(dense, shift, axis))[self.dish].sum())
        # Area over perimeter, which is a length: how fat the droplets are. It
        # rises through both halves of the process -- while the mixture is still
        # separating and again while the drops eat each other -- where bare
        # interface length falls only in the second half and *rises* in the
        # first, which inverts the schedule exactly where the picture is
        # changing fastest.
        area = int(dense[self.dish].sum())
        return float(area) / max(float(edges), 1.0)

    def fields(self) -> tuple[np.ndarray, np.ndarray]:
        """Brightness from which phase, colour from how big a drop this is part of.

        Which is the process itself, not a summary of it. Ostwald ripening is
        the big drops eating the small ones -- a large drop carries less surface
        per unit volume, and surface is the whole cost -- so radius climbing
        across the dish *is* the coarsening, made visible without a caption
        explaining it.

        Measured against a fixed radius rather than ranked within the frame. A
        per-frame ranking would spread the palette across whatever is present at
        that moment and hide the one thing worth seeing: at the end every drop
        is bright because every drop is genuinely bigger, not because it happens
        to be the biggest one left.

        Age was tried first and reads worse. It records where a drop has
        drifted, so each one ends up with a hard bright crescent on whichever
        side it grew into -- true, but it looks like a rendering fault rather
        than like a droplet.
        """
        density = np.clip((self.phi + 0.35) / 1.1, 0.0, 1.0).astype(np.float32) * self.dish
        dense = (self.phi > 0.0) & self.dish
        shade = np.zeros_like(density)
        if dense.any():
            labelled, count = ndimage.label(dense)
            if count:
                areas = np.bincount(labelled.ravel())
                radius = np.sqrt(areas / np.pi) / self.reference_radius
                shade = np.clip(radius, 0.0, 1.0)[labelled].astype(np.float32) * dense
        return density, shade


class Packing:
    """A monolayer of rod-shaped bacteria growing in a dish.

    Each cell elongates, and when it is twice its birth length it divides down
    the middle. That is the whole rule: there is nothing in it about which way
    to point, and no cell can see another. What decides the orientations is that
    the cells are rigid rods in a plane and there is no room -- a colony packs
    itself into aligned domains for the same reason a box of dropped matches
    does, except that here the packing is being generated from the inside.

    The mechanics are position-based rather than force-based, and that is not a
    detail. A force solver trades stiffness against stability: push harder and
    it oscillates, so it settles at whatever overlap the springs and the
    timestep balance at, and rods end up passing through each other while every
    summary statistic still looks plausible. Projecting the contacts instead
    holds the overlap at a couple of percent of a cell width, which is about
    what a real cell deforms.

    The colony is also given room before the solver is asked for it. Local
    relaxation moves information about one rod per iteration, so pressure raised
    at the centre of a colony forty rods across cannot reach the rim within a
    step, and the interior stays crushed. Growing the biomass and then expanding
    the whole colony by the same factor leaves only the local rearrangement to
    solve. The expansion is gated on measured density, never applied blind: a
    colony with room to spare must not be inflated, and nothing may be pushed
    through the wall of the dish.
    """

    def __init__(
        self,
        dish: float,
        radius: float = 0.5,
        max_length: float = 4.0,
        length_spread: float = 0.10,
        growth: float = 0.0055,
        tilt: float = 0.06,
        density: float = 0.80,
        iterations: int = 24,
        relax: float = 0.9,
        settled: int = 150,
        adhesion: float = 0.0,
        adhesion_spread: float = 0.22,
        seed: int = 20260831,
    ) -> None:
        self.dish, self.radius = float(dish), float(radius)
        self.max_length, self.length_spread = float(max_length), float(length_spread)
        self.growth, self.tilt = float(growth), float(tilt)
        self.density, self.iterations, self.relax = float(density), int(iterations), float(relax)
        self.settled = int(settled)
        # Zero means the cells never leave the plane: the monolayer keeps
        # growing into itself and the packing stops being physical. A real
        # threshold is what makes confinement survivable.
        self.adhesion, self.adhesion_spread = float(adhesion), float(adhesion_spread)
        self.generator = np.random.default_rng(seed)

        # Two cells end to end, which is what a microcolony actually is for its
        # first few divisions: it is a chain long before it is a disc.
        self.head = np.array([[0.0, -1.8], [0.0, 0.9]], dtype=np.float64)
        self.tail = np.array([[0.0, -0.2], [0.0, 2.5]], dtype=np.float64)
        self.length = np.linalg.norm(self.tail - self.head, axis=1)
        self.limit = self._limits(2)
        self.vertical = np.zeros(2, dtype=bool)
        self.pressure = np.zeros(2)
        self.threshold = self._thresholds(2)
        self.steps = 0

    # -- geometry -----------------------------------------------------------

    def _limits(self, count: int) -> np.ndarray:
        spread = self.generator.standard_normal(count) * self.length_spread
        return self.max_length * (1.0 + spread)

    def _thresholds(self, count: int) -> np.ndarray:
        spread = self.generator.standard_normal(count) * self.adhesion_spread
        return self.adhesion * np.exp(spread)

    def cell_area(self) -> float:
        """Spherocylinder area: the cylinder plus the two caps."""
        return float(np.sum(self.length * 2.0 * self.radius + math.pi * self.radius**2))

    def colony_area(self) -> float:
        """Convex hull of the endpoints. Meaningless while the colony is a
        chain -- a straight line has no area -- so callers gate on cell count."""
        try:
            return float(ConvexHull(np.concatenate([self.head, self.tail])).volume)
        except Exception:  # pragma: no cover - degenerate hull
            return float("nan")

    def reach(self) -> float:
        centre = 0.5 * (self.head + self.tail).mean(axis=0)
        return float(np.linalg.norm(np.concatenate([self.head, self.tail]) - centre, axis=1).max())

    def _recentre(self) -> None:
        """Restore each rod to its rest length about its own midpoint."""
        axis = self.tail - self.head
        unit = axis / np.maximum(np.linalg.norm(axis, axis=1), 1e-9)[:, None]
        middle = 0.5 * (self.head + self.tail)
        self.head = middle - 0.5 * self.length[:, None] * unit
        self.tail = middle + 0.5 * self.length[:, None] * unit

    # -- the rule -----------------------------------------------------------

    def _elongate(self) -> None:
        # A cell that has tipped up keeps growing, but it grows into the layer
        # above; from directly overhead its footprint stops changing.
        self.length = np.where(self.vertical, self.length, self.length * math.exp(self.growth))
        self._recentre()

    def _relieve(self) -> None:
        """Expand the colony towards its jamming density, never past the wall."""
        if len(self.length) < self.settled:
            return
        area = self.colony_area()
        if not (area == area) or area <= 0.0:
            return
        packed = self.cell_area() / area
        if packed <= self.density:
            return
        centre = 0.5 * (self.head + self.tail).mean(axis=0)
        span = max(np.linalg.norm(np.concatenate([self.head, self.tail]) - centre, axis=1).max(), 1e-9)
        factor = min(math.sqrt(packed / self.density), 1.02, (self.dish - self.radius) / span)
        if factor > 1.0:
            self.head = centre + (self.head - centre) * factor
            self.tail = centre + (self.tail - centre) * factor

    def _divide(self) -> None:
        splitting = ((self.length + 2.0 * self.radius) >= self.limit) & ~self.vertical
        if not splitting.any():
            return
        chosen = np.flatnonzero(splitting)
        middle = 0.5 * (self.head[chosen] + self.tail[chosen])
        unit = (self.tail[chosen] - self.head[chosen]) / self.length[chosen][:, None]
        # Total length halves, so the cylinder loses a whole cell width: each
        # daughter needs two caps where the parent had one shared boundary.
        child = (self.length[chosen] + 2.0 * self.radius) / 2.0 - 2.0 * self.radius

        def placed(start: np.ndarray, stop: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            centre = 0.5 * (start + stop)
            angle = self.generator.normal(0.0, self.tilt, len(chosen))
            axis = (stop - start) / np.maximum(np.linalg.norm(stop - start, axis=1), 1e-9)[:, None]
            cosine, sine = np.cos(angle), np.sin(angle)
            turned = np.stack([
                axis[:, 0] * cosine - axis[:, 1] * sine,
                axis[:, 0] * sine + axis[:, 1] * cosine,
            ], axis=1)
            return centre - 0.5 * child[:, None] * turned, centre + 0.5 * child[:, None] * turned

        first = placed(self.head[chosen], middle - self.radius * unit)
        second = placed(middle + self.radius * unit, self.tail[chosen])
        keep = ~splitting
        self.head = np.concatenate([self.head[keep], first[0], second[0]])
        self.tail = np.concatenate([self.tail[keep], first[1], second[1]])
        self.length = np.concatenate([self.length[keep], child, child])
        self.limit = np.concatenate([self.limit[keep], self._limits(2 * len(chosen))])
        self.vertical = np.concatenate([self.vertical[keep], np.zeros(2 * len(chosen), dtype=bool)])
        self.pressure = np.concatenate([self.pressure[keep], np.zeros(2 * len(chosen))])
        self.threshold = np.concatenate([self.threshold[keep], self._thresholds(2 * len(chosen))])

    def _closest(self, first: np.ndarray, second: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Where two segments come nearest each other, as fractions along each."""
        along = self.tail[first] - self.head[first]
        other = self.tail[second] - self.head[second]
        gap = self.head[first] - self.head[second]
        aa = np.einsum("ij,ij->i", along, along)
        ab = np.einsum("ij,ij->i", along, other)
        bb = np.einsum("ij,ij->i", other, other)
        ag = np.einsum("ij,ij->i", along, gap)
        bg = np.einsum("ij,ij->i", other, gap)
        determinant = aa * bb - ab * ab
        parallel = determinant < 1e-9 * np.maximum(aa * bb, 1e-12)
        s = np.where(parallel, 0.0, (ab * bg - bb * ag) / np.where(parallel, 1.0, determinant))
        s = np.clip(s, 0.0, 1.0)
        t = np.clip((ab * s + bg) / np.maximum(bb, 1e-9), 0.0, 1.0)
        s = np.clip((ab * t - ag) / np.maximum(aa, 1e-9), 0.0, 1.0)
        return s, t

    def _solve(self) -> None:
        count = len(self.length)
        inverse = 1.0 / (self.length + 2.0 * self.radius)
        middle = 0.5 * (self.head + self.tail)
        cutoff = float(self.length.max() + 2.0 * self.radius + 1.0)
        pairs = np.asarray(list(cKDTree(middle).query_pairs(cutoff)), dtype=np.int64).reshape(-1, 2)
        first, second = pairs[:, 0], pairs[:, 1]

        load = np.zeros(count)
        for _ in range(self.iterations):
            shift_head = np.zeros_like(self.head)
            shift_tail = np.zeros_like(self.tail)
            contacts = np.zeros(count)
            if len(first):
                s, t = self._closest(first, second)
                on_first = self.head[first] + s[:, None] * (self.tail[first] - self.head[first])
                on_second = self.head[second] + t[:, None] * (self.tail[second] - self.head[second])
                offset = on_first - on_second
                distance = np.linalg.norm(offset, axis=1)
                touching = distance < 2.0 * self.radius
                if touching.any():
                    left, right = first[touching], second[touching]
                    s, t = s[touching], t[touching]
                    distance = np.maximum(distance[touching], 1e-9)
                    normal = offset[touching] / distance[:, None]
                    depth = 2.0 * self.radius - distance
                    # A point at fraction s along a rod is moved by sharing the
                    # correction between the two ends; the weights are what make
                    # the point itself land exactly where it was asked to.
                    weight_left = inverse[left] * ((1.0 - s) ** 2 + s**2)
                    weight_right = inverse[right] * ((1.0 - t) ** 2 + t**2)
                    impulse = (depth / (weight_left + weight_right))[:, None] * normal
                    np.add.at(shift_head, left, impulse * (inverse[left] * (1.0 - s))[:, None])
                    np.add.at(shift_tail, left, impulse * (inverse[left] * s)[:, None])
                    np.add.at(shift_head, right, -impulse * (inverse[right] * (1.0 - t))[:, None])
                    np.add.at(shift_tail, right, -impulse * (inverse[right] * t)[:, None])
                    np.add.at(contacts, left, 1.0)
                    np.add.at(contacts, right, 1.0)
                    # The force the constraints had to apply to keep this cell
                    # out of its neighbours: what a cell in a crowd feels.
                    np.add.at(load, left, depth)
                    np.add.at(load, right, depth)
            # Averaged Jacobi: every contact is solved against the same starting
            # positions, so a rod with six of them must not be moved six times.
            scale = (self.relax / np.maximum(contacts, 1.0))[:, None]
            self.head += shift_head * scale
            self.tail += shift_tail * scale
            self._recentre()
            limit = self.dish - self.radius
            for ends in (self.head, self.tail):
                spread = np.linalg.norm(ends, axis=1)
                outside = spread > limit
                if outside.any():
                    ends[outside] *= (limit / spread[outside])[:, None]
        self.pressure = load / self.iterations

    def _verticalize(self) -> None:
        """Squeezed past what holds it down, a cell tips out of the plane.

        This is the only thing in the model that removes area, and without it
        the colony has nowhere to put its biomass once the dish is full: the
        solver is then asked for a packing that does not exist and answers with
        rods lying through each other. A verticalised cell keeps its width and
        loses its length, because that is what it looks like from above.
        """
        if self.adhesion <= 0.0:
            return
        tipping = (~self.vertical) & (self.pressure > self.threshold)
        if not tipping.any():
            return
        self.vertical |= tipping
        self.length[tipping] = 0.0
        self._recentre()

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            self._elongate()
            self._relieve()
            self._divide()
            self._solve()
            self._verticalize()
            self.steps += 1

    def full(self) -> bool:
        """The colony has reached the wall and can no longer be given room."""
        return self.reach() >= self.dish - self.radius - 1.0

    def metric(self) -> float:
        """Wall-to-wall extent rises with the root of the cell count, the same
        way `Cleavage`'s does: area is what the frame shows, and area is the
        square of what the eye reads as progress."""
        return math.sqrt(float(len(self.length)))

    def upright(self) -> float:
        return float(self.vertical.mean()) if len(self.vertical) else 0.0

    def state(self) -> tuple[np.ndarray, ...]:
        return (
            self.head.copy(), self.tail.copy(), self.length.copy(),
            self.vertical.copy(), self.pressure.copy(), self.threshold.copy(),
        )

    def overlap(self) -> dict:
        """How far the solver is from a physical packing, for the record."""
        middle = 0.5 * (self.head + self.tail)
        cutoff = float(self.length.max() + 2.0 * self.radius + 1.0)
        pairs = np.asarray(list(cKDTree(middle).query_pairs(cutoff)), dtype=np.int64).reshape(-1, 2)
        first, second = pairs[:, 0], pairs[:, 1]
        s, t = self._closest(first, second)
        on_first = self.head[first] + s[:, None] * (self.tail[first] - self.head[first])
        on_second = self.head[second] + t[:, None] * (self.tail[second] - self.head[second])
        distance = np.linalg.norm(on_first - on_second, axis=1)
        share = np.clip(2.0 * self.radius - distance, 0.0, None) / (2.0 * self.radius)
        touching = share > 1e-6
        area = self.colony_area()
        return {
            "cells": len(self.length),
            "contacts": int(touching.sum()),
            "mean": float(share[touching].mean()) if touching.any() else 0.0,
            "p90": float(np.percentile(share[touching], 90.0)) if touching.any() else 0.0,
            "max": float(share.max()) if len(share) else 0.0,
            "density": self.cell_area() / area if area == area and area > 0 else float("nan"),
        }

    def order(self) -> float:
        """Local nematic order: how well each cell agrees with the six nearest.

        Random orientations do not read zero -- averaging seven unit phasors
        leaves about 0.33 -- so that is the floor this number is judged against,
        not 0.

        Cells that have tipped up are excluded. A vertical cell has no length
        and therefore no in-plane angle; leaving them in gives every one of them
        an angle of zero, so they read as a single enormous aligned domain and
        the number climbs on its own as the monolayer breaks up.
        """
        flat = np.flatnonzero(~self.vertical)
        if len(flat) < 8:
            return 1.0
        middle = 0.5 * (self.head[flat] + self.tail[flat])
        axis = self.tail[flat] - self.head[flat]
        angle = np.arctan2(axis[:, 1], axis[:, 0])
        neighbours = cKDTree(middle).query(middle, k=7)[1]
        return float(np.abs(np.exp(2j * angle)[neighbours].mean(axis=1)).mean())

    def domains(self, tolerance: float = 15.0) -> tuple[int, float]:
        """Nematic domains: neighbours within `tolerance` degrees, joined up.

        Returns the count and the mass-weighted mean size -- weighted because
        the unweighted mean is dominated by the single-cell domains at the
        boundaries and barely moves while the patches themselves grow.
        """
        flat = np.flatnonzero(~self.vertical)
        count = len(flat)
        if count < 8:
            return count, 1.0
        middle = 0.5 * (self.head[flat] + self.tail[flat])
        axis = self.tail[flat] - self.head[flat]
        angle = np.arctan2(axis[:, 1], axis[:, 0])
        neighbours = cKDTree(middle).query(middle, k=7)[1][:, 1:]
        source = np.repeat(np.arange(count), neighbours.shape[1])
        target = neighbours.ravel()
        joined = np.abs(np.cos(angle[source] - angle[target])) > math.cos(math.radians(tolerance))
        graph = coo_matrix(
            (np.ones(int(joined.sum())), (source[joined], target[joined])), shape=(count, count)
        )
        total, labels = connected_components(graph, directed=False)
        sizes = np.bincount(labels)
        return total, float(np.sum(sizes.astype(float) ** 2) / sizes.sum())

    def samples(self, scale: float, centre: tuple[float, float], spacing: float = 0.55,
                mode: str = "load"):
        """Screen points for the colony, flat cells and upright cells apart.

        Sampled by length rather than a fixed count per rod: a fixed count turns
        the long cells into dotted rules across the frame while the short ones
        stay solid, which reads as a layout fault rather than a sampling one.
        Each rod is also given its width -- five lines across the short axis --
        or a colony of line segments reads as a scribble rather than as packed
        bodies.

        A cell that has tipped up is seen end-on, so it is drawn as the disc it
        actually looks like from above, and handed back separately because it is
        no longer on the ramp: it has already done the thing the ramp measures.

        The scalar returned for the flat cells is how close each one is to
        standing up -- its contact load against the load it can hold. Load is
        skewed, so the house answer would be to rank it; ranking it per frame is
        wrong here for the same reason it was wrong for `Condensate`, because a
        per-frame rank hides the one thing worth seeing, which is that the whole
        colony is being squeezed harder as the dish fills. The fixed reference is
        each cell's own threshold, so the top of the ramp means one thing all
        clip: about to leave the plane.
        """
        flat = np.flatnonzero(~self.vertical)
        axis = self.tail[flat] - self.head[flat]
        length = self.length[flat]
        angle = np.arctan2(axis[:, 1], axis[:, 0])
        unit = axis / np.maximum(np.linalg.norm(axis, axis=1), 1e-9)[:, None]
        along = np.maximum((length * scale / spacing).astype(np.int64), 2)
        index = np.repeat(np.arange(len(flat)), along)
        fraction = np.concatenate([np.linspace(-0.5, 0.5, n) for n in along])

        spine = (
            0.5 * (self.head[flat][index] + self.tail[flat][index])
            + fraction[:, None] * length[index][:, None] * unit[index]
        )
        side = np.stack([-unit[index][:, 1], unit[index][:, 0]], axis=1)

        lines = 5
        across = (np.arange(lines) - (lines - 1) / 2.0) / (lines - 1) * 2.0 * self.radius
        points = np.empty((len(index) * lines, 2), dtype=np.float32)
        for slot, offset in enumerate(across):
            screen = (spine + offset * side) * scale
            points[slot::lines] = np.column_stack([screen[:, 0] + centre[0], screen[:, 1] + centre[1]])
        if mode == "orientation":
            # Nematic: a rod and the same rod turned by pi are the same rod, so
            # the scalar has period pi and the ramp it indexes has to be cyclic.
            scalar = np.mod(angle, math.pi) / math.pi
        else:
            scalar = np.clip(self.pressure[flat] / np.maximum(self.threshold[flat], 1e-9), 0.0, 1.0)
        phase = np.repeat(scalar, along).astype(np.float32)

        standing = np.flatnonzero(self.vertical)
        if len(standing):
            ring = np.array([[0.0, 0.0]] + [
                [math.cos(a) * 0.62, math.sin(a) * 0.62] for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)
            ] + [
                [math.cos(a) * 0.34, math.sin(a) * 0.34] for a in np.linspace(0.4, 0.4 + 2 * math.pi, 5, endpoint=False)
            ])
            middle = 0.5 * (self.head[standing] + self.tail[standing])
            disc = (middle[:, None, :] + ring[None, :, :] * self.radius) * scale
            upright = disc.reshape(-1, 2) + np.asarray(centre, dtype=np.float64)
            upright = upright.astype(np.float32)
        else:
            upright = np.zeros((0, 2), dtype=np.float32)
        return points, np.repeat(phase, lines), upright


class Plaque:
    """A phage epidemic on a bacterial lawn, and the mutants that were already in it.

    Four quantities on the plate: susceptible cells, cells already infected and
    counting down to lysis, free phage, and a handful of resistant cells that
    were there before any phage landed. Phage diffuse; nothing else moves much,
    because a lawn is immobile by construction.

    The resistant cells are seeded at the first step, as single cells at random
    positions, and this is the whole point rather than a modelling convenience.
    Luria and Delbruck's argument was that resistance is not acquired from the
    encounter: the survivors carry it beforehand, and the phage only reveals
    which ones they were. Seeding them afterwards, or as a smooth mutation rate
    over the whole plate, would be telling the opposite story -- and the smooth
    version was tried first, at which point resistance appeared everywhere at
    once and refilled the plate uniformly instead of as discrete colonies.

    Infection is gated on the room left in the lawn, because phage need a host
    that is actually growing. That single term is what makes a plaque a plaque:
    without it the epidemic eats the entire plate and the finished frame is a
    black disc with a few colonies on it, and with it the plaques stop at a
    finite size and the picture is the one a plate assay actually produces -- a
    turbid lawn with clear circles punched in it.
    """

    def __init__(
        self,
        size: int,
        radius: float,
        founders: int = 34,
        landings: int = 11,
        phage_diffusion: float = 0.13,
        resistant_diffusion: float = 0.030,
        lawn_rate: float = 0.60,
        resistant_rate: float = 0.42,
        adsorption: float = 9.0,
        latent: float = 1.2,
        burst: float = 30.0,
        decay: float = 0.02,
        lawn_start: float = 0.04,
        landing_span: int = 0,
        landing_delay: int = 0,
        dt: float = 0.05,
        seed: int = 20260831,
    ) -> None:
        self.size, self.radius = int(size), float(radius)
        self.phage_diffusion, self.resistant_diffusion = phage_diffusion, resistant_diffusion
        self.lawn_rate, self.resistant_rate = lawn_rate, resistant_rate
        self.adsorption, self.latent = adsorption, latent
        self.burst, self.decay, self.dt = burst, decay, dt
        self.generator = np.random.default_rng(seed)

        rows, columns = np.mgrid[0:size, 0:size]
        middle = size * 0.5
        self.dish = np.hypot(rows - middle, columns - middle) <= radius
        # How near confluence the lawn is when the phage lands is what sets the
        # size a plaque stops at: the phage can only exploit the growth the lawn
        # has left. Plated thin, the epidemic outruns the lawn and the plaques
        # merge into one cleared region instead of staying discrete circles.
        noise = 1.0 + 0.25 * self.generator.standard_normal((size, size))
        self.susceptible = np.where(self.dish, lawn_start * noise, 0.0).clip(0.0, 1.0).astype(np.float32)
        self.infected = np.zeros((size, size), dtype=np.float32)
        self.resistant = np.zeros((size, size), dtype=np.float32)
        self.phage = np.zeros((size, size), dtype=np.float32)
        self.lysed = np.zeros((size, size), dtype=bool)
        self.steps = 0

        self._scatter(self.resistant, founders, 0.02, 0.86)
        # Phage do not all adsorb at the same instant, and landing them together
        # is what makes every plaque the same age: they open as one wave, stop as
        # one wave, and the last third of the clip has nothing happening in it.
        # Spread over the run, a plaque is always opening somewhere.
        self.landing_span = int(landing_span)
        if self.landing_span <= 0:
            self._scatter(self.phage, landings, 3.0, 0.80)
            self.pending: list[tuple[int, int, int]] = []
        else:
            self.pending = []
            for _ in range(landings):
                angle = self.generator.uniform(0.0, 2.0 * math.pi)
                reach = self.radius * math.sqrt(self.generator.uniform(0.0, 0.80))
                self.pending.append((
                    int(landing_delay + self.generator.integers(0, self.landing_span)),
                    int(size * 0.5 + reach * math.sin(angle)),
                    int(size * 0.5 + reach * math.cos(angle)),
                ))
            self.pending.sort()

    def _scatter(self, field: np.ndarray, count: int, value: float, extent: float) -> None:
        for _ in range(count):
            angle = self.generator.uniform(0.0, 2.0 * math.pi)
            reach = self.radius * math.sqrt(self.generator.uniform(0.0, extent))
            row = int(self.size * 0.5 + reach * math.sin(angle))
            column = int(self.size * 0.5 + reach * math.cos(angle))
            field[row, column] = value

    @staticmethod
    def _laplacian(field: np.ndarray) -> np.ndarray:
        return (
            np.roll(field, 1, 0) + np.roll(field, -1, 0)
            + np.roll(field, 1, 1) + np.roll(field, -1, 1) - 4.0 * field
        )

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            while self.pending and self.pending[0][0] <= self.steps:
                _, row, column = self.pending.pop(0)
                self.phage[row, column] = 3.0
            room = np.clip(1.0 - (self.susceptible + self.infected + self.resistant), 0.0, 1.0)
            # Phage need a host that is dividing. Gating adsorption on the room
            # left is what stops a plaque once the lawn around it is confluent.
            catching = self.adsorption * self.susceptible * self.phage * room
            self.susceptible = np.clip(
                self.susceptible + self.dt * (self.lawn_rate * self.susceptible * room - catching), 0.0, None
            )
            self.infected = np.clip(self.infected + self.dt * (catching - self.infected / self.latent), 0.0, None)
            self.resistant = np.clip(
                self.resistant
                + self.dt * (
                    self.resistant_rate * self.resistant * room
                    + self.resistant_diffusion * self._laplacian(self.resistant)
                ),
                0.0, None,
            )
            self.phage = np.clip(
                self.phage
                + self.dt * (
                    self.phage_diffusion * self._laplacian(self.phage)
                    + (self.burst / self.latent) * self.infected
                    - self.decay * self.phage
                    - catching
                ),
                0.0, None,
            )
            for field in ("susceptible", "infected", "resistant", "phage"):
                setattr(self, field, np.where(self.dish, getattr(self, field), 0.0).astype(np.float32))
            self.lysed |= self.infected > 0.02
            self.steps += 1

    # -- what the renderer and the gate ask for -----------------------------

    def covered(self) -> float:
        return float(((self.susceptible + self.infected) > 0.10).sum())

    def cleared(self) -> float:
        return float(self.lysed.sum())

    def colonies(self) -> float:
        return float((self.resistant > 0.10).sum())

    def lawn(self) -> float:
        return float((self.susceptible > 0.10).sum())

    def metric(self) -> float:
        """Cleared plate and colonised plate, added. Neither paces the clip on
        its own: the plaques open early and stop, and the colonies only get
        going once there is somewhere for them to go."""
        area = max(float(self.dish.sum()), 1.0)
        return self.cleared() / area + self.colonies() / area

    def state(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self.susceptible.copy(), self.infected.copy(), self.resistant.copy()

    def report(self) -> dict:
        area = max(float(self.dish.sum()), 1.0)
        return {
            "cleared": self.cleared() / area,
            "colonies": self.colonies() / area,
            "lawn": self.lawn() / area,
            "front": float((self.infected > 0.02).sum()) / area,
        }


class Nematic:
    """An active nematic: microtubules, kinesin and ATP, and not one cell.

    Take microtubules out of a cell, add the motor that walks along them and
    the fuel that motor runs on, and let the mixture spread into a film one
    filament thick. Nothing in there is alive. There is no membrane, no
    genome, no signal, and nothing that could be said to be deciding
    anything. What the film does is tear itself apart, for ever.

    The filaments line up with their neighbours -- that is all "nematic"
    means, the alignment a liquid crystal has without any of the ordering a
    solid has. Kinesin walks along one filament carrying another, so
    neighbouring filaments slide past each other, and sliding along a
    direction pushes fluid along that direction. That is the whole rule:
    **alignment is turned into flow**. And the flow it produces bends the
    alignment that produced it, which bends the flow, and an aligned film
    turns out to be unstable to its own activity -- the *bend instability*,
    and there is no parameter at which it is not there.

    A bend that grows far enough cannot stay a bend. The director has to
    break, and where it breaks the film is left with a point around which
    the alignment turns by half a turn -- a topological defect, +1/2 or
    -1/2, and the halves are why the fabric cannot simply heal. Charge is
    conserved, so they are born in pairs; the +1/2 has a comet's head and
    swims, the -1/2 has three-fold symmetry and mostly sits; and when a +1/2
    finds a -1/2 they annihilate and that piece of film is whole again. The
    steady state is not order and not disorder but a fixed rate of tearing:
    active turbulence.

    Modelled the standard way -- Beris-Edwards for the alignment, one elastic
    constant, coupled to Stokes flow for the fluid, with an active stress
    proportional to the alignment itself, `sigma = -zeta Q`. Extensile
    filaments are `zeta > 0`.

    **The film is a drop, not a crop.** `radius` masks the *activity* and the
    ordering, not the drawing: outside it the Landau term has no well to sit
    in, so the alignment decays to isotropic and there is no film there to
    photograph. The fluid outside is still solved -- a real drop drags the
    bath around it.
    """

    def __init__(
        self,
        size: int,
        radius: float | None = None,
        elasticity: float = 0.04,
        landau: float = 1.0,
        rotation: float = 1.0,
        alignment: float = 0.7,
        activity: float = 0.030,
        viscosity: float = 1.0,
        dt: float = 0.05,
        seeded_order: float = 0.4,
        disorder: float = 0.05,
        afterglow: float = 150.0,
        edge: float = 3.0,
        seed: int = 20260903,
        device: str | None = None,
    ) -> None:
        self.size = size
        self.elasticity, self.landau = elasticity, landau
        self.rotation, self.alignment = rotation, alignment
        self.activity, self.viscosity, self.dt = activity, viscosity, dt
        self.radius = float(size * 0.44 if radius is None else radius)
        # The phosphor half-life, in steps. A defect is one pixel and it is
        # past in a moment; without a memory of where they have been the frame
        # is a texture with no events in it. Same device as `Excitable`.
        self.decay = float(0.5 ** (1.0 / max(afterglow, 1.0)))
        self.step_index = 0

        generator = np.random.default_rng(seed)
        rows, columns = np.mgrid[0:size, 0:size].astype(np.float32)
        distance = np.hypot(rows - (size - 1) / 2.0, columns - (size - 1) / 2.0)
        # Smooth, because a step in the mask is a step in the free energy and
        # the solver answers it with a ring of spurious order at the rim.
        self.mask = (0.5 * (1.0 - np.tanh((distance - self.radius) / edge))).astype(np.float32)
        self.dish = distance < self.radius

        # An aligned film, with just enough noise for the instability to have
        # something to grow from. Frame one is the turbulence; this is what the
        # clip cuts back to.
        angle = disorder * generator.standard_normal((size, size)).astype(np.float32)
        self.qxx = (seeded_order * np.cos(2.0 * angle) * self.mask).astype(np.float32)
        self.qxy = (seeded_order * np.sin(2.0 * angle) * self.mask).astype(np.float32)
        self.wake = np.zeros((size, size), dtype=np.float32)
        self.speed = np.zeros((size, size), dtype=np.float32)

        wave = 2.0 * np.pi * np.fft.fftfreq(size)
        kx, ky = np.meshgrid(wave, wave, indexing="ij")
        self.kx, self.ky = kx.astype(np.float32), ky.astype(np.float32)
        k2 = (kx * kx + ky * ky).astype(np.float32)
        self.k2 = k2
        safe = k2.copy()
        safe[0, 0] = 1.0
        self.k2_safe = safe

        if device is None:
            device = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
        self.device = device if torch is not None else "cpu"
        if self.device != "cpu":
            to = lambda a: torch.tensor(a, device=self.device)
            self._qxx, self._qxy = to(self.qxx), to(self.qxy)
            self._wake, self._speed = to(self.wake), to(self.speed)
            self._mask = to(self.mask)
            self._kx, self._ky = to(self.kx), to(self.ky)
            self._k2, self._k2_safe = to(self.k2), to(self.k2_safe)

    # ------------------------------------------------------------------
    # Spectral operators. Everything is periodic; the drop never touches the
    # box, so wrapping costs nothing and buys an exact Stokes solve.

    def _pack(self):
        if self.device != "cpu":
            return (torch, torch.fft, self._qxx, self._qxy, self._mask,
                    self._kx, self._ky, self._k2, self._k2_safe)
        return (np, np.fft, self.qxx, self.qxy, self.mask,
                self.kx, self.ky, self.k2, self.k2_safe)

    def _flow(self, qxx, qxy):
        """Stokes velocity driven by the active stress `sigma = -zeta m Q`.

        Incompressible, so the pressure is eliminated by projecting the force
        transverse to `k`. This is the one part of the model that is not
        local: activity anywhere moves fluid everywhere, which is why a bend
        on one side of the drop is felt on the other.
        """
        lib, fft, *_ = self._pack()
        kx, ky, k2s = (self._kx, self._ky, self._k2_safe) if self.device != "cpu" \
            else (self.kx, self.ky, self.k2_safe)
        mask = self._mask if self.device != "cpu" else self.mask
        sxx = -self.activity * mask * qxx
        sxy = -self.activity * mask * qxy
        fxx, fxy, fyy = fft.fft2(sxx), fft.fft2(sxy), fft.fft2(-sxx)
        fx = 1j * (kx * fxx + ky * fxy)
        fy = 1j * (kx * fxy + ky * fyy)
        projection = (kx * fx + ky * fy) / k2s
        ux = fft.ifft2((fx - kx * projection) / (self.viscosity * k2s)).real
        uy = fft.ifft2((fy - ky * projection) / (self.viscosity * k2s)).real
        return ux, uy

    def _grad(self, field):
        lib, fft, *_ = self._pack()
        kx, ky = (self._kx, self._ky) if self.device != "cpu" else (self.kx, self.ky)
        spectrum = fft.fft2(field)
        return fft.ifft2(1j * kx * spectrum).real, fft.ifft2(1j * ky * spectrum).real

    def _laplacian(self, field):
        lib, fft, *_ = self._pack()
        k2 = self._k2 if self.device != "cpu" else self.k2
        return fft.ifft2(-k2 * fft.fft2(field)).real

    # ------------------------------------------------------------------

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            self.step_index += 1
            if self.device != "cpu":
                qxx, qxy, mask = self._qxx, self._qxy, self._mask
            else:
                qxx, qxy, mask = self.qxx, self.qxy, self.mask

            ux, uy = self._flow(qxx, qxy)
            dx_ux, dy_ux = self._grad(ux)
            dx_uy, dy_uy = self._grad(uy)
            vorticity = 0.5 * (dy_ux - dx_uy)
            strain_xx = dx_ux
            strain_xy = 0.5 * (dy_ux + dx_uy)

            gxx_x, gxx_y = self._grad(qxx)
            gxy_x, gxy_y = self._grad(qxy)

            # The molecular field. `mask` is where the ordered well is: inside
            # the drop the equilibrium is |Q| = 1/sqrt(2), outside there is no
            # well and the alignment relaxes away.
            square = qxx * qxx + qxy * qxy
            h_xx = self.elasticity * self._laplacian(qxx) + self.landau * (mask - 2.0 * square) * qxx
            h_xy = self.elasticity * self._laplacian(qxy) + self.landau * (mask - 2.0 * square) * qxy

            # Advection, co-rotation with the vorticity, flow alignment with
            # the strain, and relaxation towards the molecular field.
            qxx = qxx + self.dt * (
                -(ux * gxx_x + uy * gxx_y) + 2.0 * vorticity * qxy
                + self.alignment * strain_xx + self.rotation * h_xx
            )
            qxy = qxy + self.dt * (
                -(ux * gxy_x + uy * gxy_y) - 2.0 * vorticity * qxx
                + self.alignment * strain_xy + self.rotation * h_xy
            )

            speed = (ux * ux + uy * uy) ** 0.5
            if self.device != "cpu":
                self._qxx, self._qxy, self._speed = qxx, qxy, speed
                self._wake = torch.maximum(self._wake * self.decay, self._defect_field(qxx, qxy))
            else:
                self.qxx, self.qxy, self.speed = qxx, qxy, speed
                self.wake = np.maximum(self.wake * self.decay, self._defect_field(qxx, qxy))

    # ------------------------------------------------------------------

    def _charge(self, qxx, qxy):
        """Topological charge on each plaquette, by the winding of the director.

        The director is a line, not an arrow: it comes back to itself after
        half a turn, so every angle difference is wrapped onto a half-turn
        before it is added up. Do that with a full turn and every defect
        reads as zero.
        """
        lib = torch if self.device != "cpu" else np
        angle = 0.5 * lib.arctan2(qxy, qxx) if lib is np else 0.5 * torch.atan2(qxy, qxx)
        roll = (lambda a, s, ax: np.roll(a, s, ax)) if lib is np else (lambda a, s, ax: torch.roll(a, s, ax))
        pi = math.pi

        def difference(first, second):
            return (second - first + pi / 2.0) % pi - pi / 2.0

        a = angle
        b = roll(angle, -1, 0)
        c = roll(roll(angle, -1, 0), -1, 1)
        d = roll(angle, -1, 1)
        winding = difference(a, b) + difference(b, c) + difference(c, d) + difference(d, a)
        return winding / (2.0 * pi)

    def _defect_field(self, qxx, qxy):
        """1 where a defect core sits, 0 elsewhere -- what the phosphor records."""
        charge = self._charge(qxx, qxy)
        if self.device != "cpu":
            return (charge.abs() > 0.2).to(charge.dtype) * self._mask
        return ((np.abs(charge) > 0.2).astype(np.float32)) * self.mask

    def defects(self) -> tuple[int, int]:
        """Counts of +1/2 and -1/2 defects inside the drop."""
        qxx, qxy = (self._qxx, self._qxy) if self.device != "cpu" else (self.qxx, self.qxy)
        charge = self._charge(qxx, qxy)
        if self.device != "cpu":
            charge = charge.cpu().numpy()
        inside = self.dish
        return int(((charge > 0.2) & inside).sum()), int(((charge < -0.2) & inside).sum())

    def order(self) -> float:
        """How aligned the drop still is as a whole, 1 at the start and ~0 in turbulence.

        Averaging Q over the drop and dividing by the average magnitude: a
        film pointing one way keeps its average, a torn one cancels itself.
        """
        qxx, qxy = self.arrays()[:2]
        inside = self.dish
        magnitude = float(np.hypot(qxx[inside], qxy[inside]).mean())
        vector = math.hypot(float(qxx[inside].mean()), float(qxy[inside].mean()))
        return vector / max(magnitude, 1e-9)

    def arrays(self) -> tuple[np.ndarray, ...]:
        if self.device != "cpu":
            return tuple(a.cpu().numpy() for a in (self._qxx, self._qxy, self._speed, self._wake))
        return self.qxx, self.qxy, self.speed, self.wake

    def state(self) -> tuple[np.ndarray, ...]:
        """One banked frame, compressed.

        Q and the wake are bounded -- by the Landau well and by construction --
        so eight bits is plenty, and the bloom and the tone curve wash the
        quantisation out long before anyone could see it. The speed is not
        bounded ahead of time and it is what the brightness is made of, so it
        is kept as float16 rather than given a reference the run has not
        finished measuring yet. Half a megabyte a state against two, which is
        the difference between banking the run in memory and not.
        """
        qxx, qxy, speed, wake = self.arrays()
        scale = 1.0 / (2.0 * 0.7071067811865476)
        return (
            np.clip((qxx * scale + 0.5) * 255.0, 0, 255).astype(np.uint8),
            np.clip((qxy * scale + 0.5) * 255.0, 0, 255).astype(np.uint8),
            speed.astype(np.float16),
            np.clip(wake * 255.0, 0, 255).astype(np.uint8),
        )

    @staticmethod
    def unpack(state: tuple[np.ndarray, ...]) -> tuple[np.ndarray, ...]:
        scale = 2.0 * 0.7071067811865476
        qxx = (state[0].astype(np.float32) / 255.0 - 0.5) * scale
        qxy = (state[1].astype(np.float32) / 255.0 - 0.5) * scale
        return qxx, qxy, state[2].astype(np.float32), state[3].astype(np.float32) / 255.0

    def metric(self) -> float:
        """Not used -- the schedule is built from the banked run, not read live."""
        return float(sum(self.defects()))

    # ------------------------------------------------------------------

    def samples(
        self,
        state: tuple[np.ndarray, ...],
        scale: float,
        centre: tuple[float, float],
        seeds: int = 320_000,
        walk: int = 9,
        stride: float = 0.55,
        generator: np.random.Generator | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Short streamlines along the director: the film's own brush strokes.

        A director field drawn as a value per pixel is a smooth wash with no
        filaments in it, and filaments are what the subject is made of. Walking
        a few steps along the alignment from a scatter of seeds puts the
        strokes back, and because the walk follows the field, the strokes bunch
        where the film bends -- which is where the tearing happens.

        Returns points in frame coordinates, a value per point, and a weight
        per point. Q is interpolated, not the angle: an angle cannot be
        averaged across the wrap and every stroke crossing it would kink.
        """
        qxx, qxy, speed, wake = self.unpack(state)
        size = self.size
        generator = np.random.default_rng(4) if generator is None else generator

        # Seeds inside the drop only. The black margin is black because there
        # is no film there, not because the drawing stops.
        angle = generator.uniform(0.0, 2.0 * math.pi, seeds)
        span = self.radius * np.sqrt(generator.uniform(0.0, 1.0, seeds))
        x = (size - 1) / 2.0 + span * np.cos(angle)
        y = (size - 1) / 2.0 + span * np.sin(angle)

        def bilinear(field, px, py):
            x0 = np.floor(px).astype(np.int32)
            y0 = np.floor(py).astype(np.int32)
            fx, fy = px - x0, py - y0
            x0 %= size
            y0 %= size
            x1, y1 = (x0 + 1) % size, (y0 + 1) % size
            return (field[y0, x0] * (1 - fx) * (1 - fy) + field[y0, x1] * fx * (1 - fy)
                    + field[y1, x0] * (1 - fx) * fy + field[y1, x1] * fx * fy)

        points = np.empty((walk * seeds, 2), dtype=np.float32)
        values = np.empty(walk * seeds, dtype=np.float32)
        weights = np.empty(walk * seeds, dtype=np.float32)
        inside = np.empty(walk * seeds, dtype=bool)
        previous_x = np.zeros(seeds)
        previous_y = np.zeros(seeds)
        for index in range(walk):
            axx = bilinear(qxx, x, y)
            axy = bilinear(qxy, x, y)
            heading = 0.5 * np.arctan2(axy, axx)
            step_x, step_y = np.cos(heading), np.sin(heading)
            if index:
                # The director has no sign, so `arctan2` flips arbitrarily from
                # one cell to the next. Keep walking the way we were walking.
                flipped = (step_x * previous_x + step_y * previous_y) < 0.0
                step_x = np.where(flipped, -step_x, step_x)
                step_y = np.where(flipped, -step_y, step_y)
            else:
                sign = np.where(generator.random(seeds) < 0.5, -1.0, 1.0)
                step_x, step_y = step_x * sign, step_y * sign
            previous_x, previous_y = step_x, step_y

            block = slice(index * seeds, (index + 1) * seeds)
            points[block, 0] = centre[0] + (x - (size - 1) / 2.0) * scale
            points[block, 1] = centre[1] + (y - (size - 1) / 2.0) * scale
            values[block] = bilinear(wake, x, y)
            weights[block] = bilinear(speed, x, y)
            # A stroke started inside can walk out, and nine of them abreast draw
            # a fringe of hair round the drop -- a structure the model never made
            # and the one thing in the frame that looks like a bug. Seeding
            # further in would thin the rim instead; dropping the samples that
            # left keeps the density even right up to the edge.
            inside[block] = np.hypot(x - (size - 1) / 2.0, y - (size - 1) / 2.0) <= self.radius
            x = x + stride * step_x
            y = y + stride * step_y
        return points[inside], values[inside], weights[inside]
