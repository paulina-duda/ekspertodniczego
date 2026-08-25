#!/usr/bin/env python3
"""A genetic algorithm looking for Lenia creatures, and the pedigree it leaves.

The companion piece in this edition, `soliton`, found its animal the way the
field usually does: nine thousand random draws, and the ones still alive at the
end were the ones worth keeping. That is search. This is *selection*, which is a
different thing and the distinction is the whole point of the piece -- nothing
here is cleverer than random search at any single step. The only change is that
the draws are no longer independent. Whatever survived one round is what the
next round is drawn from, with mistakes.

Every genome is the same seven numbers the other piece ships as a creature: the
growth curve (`mu`, `sigma`), the kernel's rings, and the four parameters of the
arc it starts from. Fitness is what the audition asked -- is it still alive, is
it still an individual, did it go anywhere -- so the two pieces are looking for
exactly the same thing in exactly the same space, and only the method differs.

What the piece draws is not the creature. It is the **pedigree**: every
individual of every generation, joined to its parent. Almost every line in it
ends. The ones that do not all turn out, on the way down, to meet.
"""

from __future__ import annotations

import numpy as np

import lenia


# The genome, in the order it is stored. `beta` is an index into RINGS rather
# than a number to mutate: kernels are a choice, not a quantity, and nudging
# "one ring" by 0.3 means nothing.
GENES = ("mu", "sigma", "ring", "thickness", "lobe", "amplitude")
BOUNDS = {
    "mu": (0.10, 0.30),
    "sigma": (0.012, 0.042),
    "ring": (0.35, 0.65),
    "thickness": (0.12, 0.30),
    "lobe": (1.4, 3.0),
    "amplitude": (0.5, 1.0),
}
RINGS = ((1.0,), (1.0, 0.66), (1.0, 0.5, 0.25))


def random_genome(generator: np.random.Generator) -> dict:
    genome = {gene: float(generator.uniform(*BOUNDS[gene])) for gene in GENES}
    genome["rings"] = int(generator.integers(0, len(RINGS)))
    genome["phase"] = float(generator.uniform(0.0, 2.0 * np.pi))
    return genome


def mutate(genome: dict, generator: np.random.Generator, rate: float = 0.35) -> dict:
    """Copy with mistakes: a nudge to some genes, rarely a new kernel.

    The nudge is a fraction of each gene's own range, so `sigma` -- which lives
    between 0.012 and 0.042 and decides life or death three decimal places in --
    is not swamped by the same absolute step that barely moves `lobe`.
    """
    child = dict(genome)
    for gene in GENES:
        if generator.random() < rate:
            low, high = BOUNDS[gene]
            child[gene] = float(
                np.clip(child[gene] + generator.normal(0.0, 0.08 * (high - low)), low, high)
            )
    if generator.random() < 0.06:
        child["rings"] = int(generator.integers(0, len(RINGS)))
    if generator.random() < 0.25:
        child["phase"] = float(generator.uniform(0.0, 2.0 * np.pi))
    return child


def fitness(
    genome: dict, radius: float = 13.0, domain: int = 128, settle: int = 200, hold: int = 300
) -> float:
    """Alive, still an individual, and going somewhere -- or zero.

    Identical in spirit to `lenia.audition`, and deliberately so: the two pieces
    have to be searching for the same thing for the comparison between them to
    mean anything. A genome that dies, floods the world, or smears into a
    texture scores nothing at all, which is what makes the landscape so hostile:
    almost everywhere, the gradient does not merely point the wrong way, it does
    not exist.
    """
    patch = lenia.crescent(
        radius,
        genome["ring"],
        genome["thickness"],
        genome["lobe"],
        genome["phase"],
        genome["amplitude"],
    )
    world = lenia.Lenia(
        domain, domain, radius=radius,
        mu=genome["mu"], sigma=genome["sigma"], beta=RINGS[genome["rings"]],
    )
    world.place(patch, domain // 2 - patch.shape[0] // 2, domain // 2 - patch.shape[1] // 2)

    world.step(settle)
    settled_mass, settled_centre = world.mass(), world.centre()
    if not 60.0 < settled_mass < 0.06 * domain * domain:
        return 0.0
    world.step(hold)
    mass, spread = world.mass(), world.spread()
    if not (0.5 < mass / max(settled_mass, 1e-9) < 1.6 and spread < radius * 2.6):
        return 0.0

    row, column = world.centre()
    travel = np.hypot(
        min(abs(row - settled_centre[0]), domain - abs(row - settled_centre[0])),
        min(abs(column - settled_centre[1]), domain - abs(column - settled_centre[1])),
    )
    return float(travel / radius + 0.3 * (radius * 2.6 - spread) / radius)


def evolve(
    population: int = 64,
    generations: int = 40,
    tournament: int = 3,
    elite: int = 2,
    seed: int = 11,
    report=None,
) -> list[list[dict]]:
    """Run the algorithm and keep the pedigree, not just the winner.

    Selection is a tournament: three individuals are drawn at random and the
    fittest of them becomes a parent. It is deliberately weak. Taking the best
    of the whole population every time collapses the pedigree to a single line
    within three generations, which is both a worse picture and worse
    engineering -- a population that has agreed with itself has nothing left to
    search with.

    Two elites are copied through untouched, so a lineage that solves the
    problem cannot be lost to a run of bad mutations.

    Every individual records the index of its parent in the previous generation
    and the index of the founder it ultimately descends from, which is all the
    renderer needs to draw the tree and all anyone needs to see the thing this
    piece is about: how few of the founders have any descendants left.
    """
    generator = np.random.default_rng(seed)
    first = []
    for index in range(population):
        genome = random_genome(generator)
        genome.update(fitness=fitness(genome), parent=-1, founder=index)
        first.append(genome)
    history = [first]
    if report is not None:
        alive = sum(1 for genome in first if genome["fitness"] > 0)
        report(f"  generation  0: {alive:3d}/{population} alive, best {max(g['fitness'] for g in first):5.2f}")

    for step in range(1, generations):
        previous = history[-1]
        order = np.argsort([-genome["fitness"] for genome in previous])
        children: list[dict] = []
        for rank in range(elite):
            parent = int(order[rank])
            children.append(dict(previous[parent], parent=parent))
        while len(children) < population:
            entrants = generator.integers(0, population, tournament)
            parent = int(max(entrants, key=lambda index: previous[index]["fitness"]))
            child = mutate(previous[parent], generator)
            child.update(
                fitness=fitness(child), parent=parent, founder=previous[parent]["founder"]
            )
            children.append(child)
        history.append(children)
        if report is not None:
            alive = sum(1 for genome in children if genome["fitness"] > 0)
            founders = len({genome["founder"] for genome in children if genome["fitness"] > 0})
            report(
                f"  generation {step:2d}: {alive:3d}/{population} alive, "
                f"best {max(g['fitness'] for g in children):5.2f}, "
                f"{founders} founder lines left"
            )
    return history
