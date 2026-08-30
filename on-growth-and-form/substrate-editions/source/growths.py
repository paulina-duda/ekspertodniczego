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
from scipy.spatial import cKDTree

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
