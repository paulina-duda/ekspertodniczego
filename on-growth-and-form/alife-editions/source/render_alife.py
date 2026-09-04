#!/usr/bin/env python3
"""Artificial life in the luminous house style: rules that were found, not written.

The substrate and wetware sets film processes biology already knows about. This
one films the other direction -- rules invented in a computer that turn out to
behave like living things, which is the claim artificial life has been making
since Langton and is the only claim in this account that is genuinely arguable.

**The frame carries a population, not an organism.** The other editions compose
a single thing in the middle of a black field; these wrap at the edges, so there
is no middle and no boundary for a structure to have been built against.
`soliton` wraps in both directions. `affinity` wraps left to right only and is
held top to bottom by a soft spring, which keeps the black the title and the
hook are set on -- a swarm that fills the frame corner to corner leaves the
typography nothing to sit on.

**Eight seconds, and the clip is a loop**, as everywhere else: it opens on the
organised frame, cuts to the gas it started as, and assembles back into exactly
the frame it opened on.

**This one is paced by the clock, and that is the exception.** Everywhere else
in this project the frames are placed at equal intervals of a measured
progress, because the process accelerates or stalls. Here the population
condenses out of the gas in the first second and then simply swims, at a speed
the friction fixes, so equal steps of the clock already are equal steps of the
process -- and a progress schedule built on how much structure there is would
spend seven of the eight seconds sitting still on the flat part of that curve,
which is to say on the part where all the swimming happens.

**It ends at the top of the population, not at the end of the run.** Left
running, the swimmers meet, merge and thin out, and the frame slowly empties --
true, and a worse picture. The clip stops where there are most of them.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import evolution
import glow
import lenia
import loops as langton
import swarm


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "instagram" / "phone-9x16"

# One colour per species, and that is the whole colour scheme: there is nothing
# else about a particle to measure. Four hues that stay in the family -- the
# magenta and mint of the wetware set, the amber of the mycelium, and a
# near-white for whichever species ends up as skin.
SPECIES_COLOURS = [
    (255, 62, 168),
    (255, 168, 44),
    (86, 255, 176),
    (214, 240, 255),
]

# The same four species in saturated neon. The soft cut could afford a pale
# near-white species and a muted amber, because the bloom was doing the work and
# every core washed towards white anyway; with the halo turned down those two
# read as pastel and the frame loses its edge. These sit at full chroma so the
# colour survives a tone curve that no longer bleaches it.
NEON_SPECIES = {
    "family": SPECIES_COLOURS,
    "neon": [(255, 0, 140), (0, 245, 255), (170, 255, 0), (150, 40, 255)],
    "signs": [(255, 0, 128), (0, 255, 240), (255, 230, 0), (180, 0, 255)],
    "ember": [(255, 0, 110), (0, 255, 200), (255, 140, 0), (140, 60, 255)],
}

# Found by `swarm.search` with the defaults below -- best of twenty tables drawn
# at random, scored on how much of the population assembles and how fast the
# assemblies then move -- and kept so the piece renders the same thing twice.
# Re-ranked once the frame became a band rather than a torus, because a table
# is only best in the world it was scored in: the same twenty were run again in
# the new geometry at the same density, and this one won there too (1.016; it
# scored 1.459 on the torus, where the coverage term had a bigger frame to fill).
# Run with --search to look for another one.
FOUND_MATRIX = np.array(
    [
        [0.328, -0.189, -0.411, 0.656],
        [-0.450, 0.542, -0.505, -0.958],
        [0.621, -0.755, 0.269, -0.574],
        [-0.388, 0.170, -0.384, 0.418],
    ],
    dtype=np.float32,
)

# The creature this piece is built out of, and everything needed to rebuild it:
# a growth curve, a two-ring kernel, and the six numbers of the arc it starts
# from. Found by `lenia.audition` -- 105 survivors out of 9,000 seeds tried at
# radius 18, of which 98 were still self-limiting when re-run at the radius the
# piece is filmed at, and this one travelled furthest.
FOUND_SOLITON = {
    "mu": 0.2220,
    "sigma": 0.0286,
    "beta": (1.0, 0.66),
    "ring": 0.4655,
    "thickness": 0.2940,
    "lobe": 1.9034,
    "amplitude": 0.8705,
}

# Signed growth, from the wake to the front: near-black where the field is
# dying back, deep magenta through the body that is holding steady, and amber
# into white along the edge the creature is advancing into. The dark half of
# the ramp is long on purpose -- most of a settled colony is growing at very
# nearly zero, and a palette that puts that in the middle turns the whole frame
# into one flat mid-tone.
PLASMA = [(2, 1, 9), (26, 3, 44), (70, 8, 86), (150, 20, 120), (240, 80, 90), (255, 235, 205)]

# Steps since a cell last changed, ranked. Eight of the ten stops are dark,
# for the same reason PLASMA's are, and the arithmetic says how many. Ranking
# spreads a skewed quantity evenly over the ramp *by construction* -- half the
# cells land above the midpoint whatever the quantity does -- so a colony that
# is three quarters dead came out an even lavender until the ramp was shaped.
# Measured on the last frame: 9% of drawn cells changed within the last five
# steps, 12% within twenty, and the median cell last moved 461 steps ago. So
# the burn is given the top fifth and the climb through indigo takes the rest.
# Dark, but never black: that lattice is the whole picture at thumbnail size.
FORGE = [
    (6, 5, 16), (10, 8, 26), (15, 12, 38), (21, 16, 52), (29, 21, 70),
    (40, 27, 92), (58, 36, 118), (96, 50, 150), (240, 120, 70), (255, 246, 214),
]

# The same ramp in oxidised bronze. What the two palettes differ on is not
# taste: the colour is how long ago a cell last moved, so the husks and the
# working rim want to be *different* hues rather than neighbouring ones. FORGE
# runs indigo to cream and the diamond reads as one material with a brighter edge;
# VERDIGRIS puts the dead body in patina and keeps gold for the cells the
# machine is touching this instant, which is the distinction the piece is about.
VERDIGRIS = [
    (4, 10, 9), (7, 18, 16), (10, 28, 24), (14, 40, 34), (18, 54, 46),
    (24, 72, 60), (32, 94, 76), (44, 120, 96), (235, 150, 60), (255, 244, 214),
]

LOOP_PALETTES = {"forge": FORGE, "verdigris": VERDIGRIS}

# One hue per founder, cycled: sixty-four distinguishable colours do not exist
# in this family and would not survive Instagram's compression if they did.
# Eight is enough to see a line take over the frame, which is the only thing
# the colour has to say.
LINEAGE = [
    (255, 62, 168),
    (255, 168, 44),
    (86, 255, 176),
    (150, 92, 255),
    (255, 108, 96),
    (64, 226, 226),
    (236, 214, 92),
    (214, 240, 255),
]

# Fitness, ranked: the score that decided which of these had descendants. It
# runs violet through magenta to amber and white, and unlike PLASMA it never
# reaches black -- a genome that scored nothing is not a wake to be swallowed by
# the background, it is one of the two ways of failing and has to be visible.
LADDER = [(96, 44, 208), (176, 40, 200), (255, 62, 138), (255, 150, 62), (255, 242, 214)]

EDITIONS: dict[str, dict] = {
    "affinity": {
        "title": "Affinity",
        "slug": "affinity_particle-life_alife",
        "exposure": 1.16,
        "boost": 1.22,
        "caption": (
            "particle life · four species",
            "attract · repel · never symmetrically",
            "16 numbers are enough to make them chase",
        ),
        "hook": (
            "Being alive is a matter of organization,",
            "so it can be built from numbers",
        ),
    },
    "soliton": {
        "title": "Soliton",
        "slug": "soliton_lenia_alife",
        "palette": PLASMA,
        "exposure": 0.95,
        "boost": 1.06,
        "caption": (
            "Lenia · continuous automaton (Chan 2019)",
            "one ring kernel · one growth curve",
            "twelve creatures, found by search",
        ),
        "hook": ("Every one of these was stable on its own.",),
    },
    "cohort": {
        "title": "Cohort",
        "slug": "cohort_genetic-algorithm_alife",
        "palette": LADDER,
        "exposure": 0.98,
        "boost": 1.10,
        "caption": (
            "genetic algorithm · 64 genomes, 40 generations",
            "copy with mistakes · compare · keep the winner",
            "a row is one generation · its four fittest",
            "colour is the fitness that decided them",
        ),
        "hook": (
            "Not one of the first sixty-four was alive.",
            "Everything alive here is a copy of one.",
        ),
    },
    "shoal": {
        "title": "Shoal",
        "slug": "shoal_genetic-algorithm_alife",
        "palette": LADDER,
        "exposure": 0.98,
        "boost": 1.10,
        "caption": (
            "genetic algorithm · 64 genomes, 40 generations",
            "a lane is one generation's best, five copies of it",
            "fitness rewarded travel · so the lanes are a race",
            "colour is the fitness that decided them",
        ),
        "hook": (
            "Generation zero could only fill its world.",
            "Forty generations later it crosses it.",
        ),
    },
    "replicator": {
        "title": "Replicator",
        "slug": "replicator_langtons-loops_alife",
        "palette": FORGE,
        "exposure": 1.00,
        "boost": 1.05,
        # `sharp`, pinned here rather than left to the command line: the piece
        # is a lattice of 3 px walls and the default halo smears it to haze.
        "bloom_threshold": 0.55,
        "bloom_strength": 0.25,
        "caption": (
            "Langton's loops \u00b7 self-replicating automaton (1984)",
            "circulate \u00b7 extend \u00b7 turn left \u00b7 cut free",
            "one loop becomes 345 \u00b7 100 still working",
            "colour is steps since a cell last changed",
        ),
        "hook": (
            "Each was built by the one beside it.",
            "Only the edge is still building.",
        ),
    },
    "descent": {
        "title": "Descent",
        "slug": "descent_genetic-algorithm_alife",
        "exposure": 1.10,
        "boost": 1.16,
        "caption": (
            "genetic algorithm · 64 genomes, 40 generations",
            "mutate · test · keep whatever lived",
            "colour is which founder it came from",
        ),
        "hook": ("Everything at the top has one ancestor.",),
    },
}


# --------------------------------------------------------------------------
# Encoding
# --------------------------------------------------------------------------


def find_encoder() -> tuple[str, list[str]]:
    """Pick an ffmpeg that can actually encode H.264 (conda builds cannot)."""
    candidates: list[str] = []
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / "ffmpeg"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            candidates.append(str(candidate))
    candidates.append("/usr/bin/ffmpeg")
    fallback: tuple[str, list[str]] | None = None
    for ffmpeg in dict.fromkeys(candidates):
        try:
            encoders = subprocess.run(
                [ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, check=True
            ).stdout
        except (OSError, subprocess.CalledProcessError):
            continue
        if " libx264 " in encoders:
            return ffmpeg, ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high"]
        if fallback is None and " libopenh264 " in encoders:
            fallback = (ffmpeg, ["-c:v", "libopenh264", "-threads", "1", "-b:v", "12M", "-maxrate", "16M"])
    if fallback is not None:
        return fallback
    raise RuntimeError("No ffmpeg with an H.264 encoder was found.")


def start_encoder(output: Path, width: int, height: int, fps: int) -> subprocess.Popen[bytes]:
    if width % 2 or height % 2:
        raise ValueError(f"H.264 needs even dimensions; got {width}x{height}.")
    ffmpeg, codec = find_encoder()
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}", "-r", str(fps), "-i", "-",
        "-an", *codec, "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output),
    ]
    return subprocess.Popen(command, stdin=subprocess.PIPE)


# --------------------------------------------------------------------------
# Shared pieces — the house layout, identical to the substrate set
# --------------------------------------------------------------------------


def build_overlay(width: int, height: int, spec: dict, args) -> Image.Image:
    """Title, hook and data block: Plex, 240 px down, 190 px up, hook centred."""
    overlay = glow.make_caption(
        width,
        height,
        spec["title"],
        spec["caption"],
        equation_size=args.caption_size,
        margin=args.margin,
        top_margin=args.title_top,
        bottom_margin=args.caption_bottom,
        scrim=args.scrim,
    )
    lines = spec.get("hook") if args.hook else None
    if not lines:
        return overlay

    ink_top = glow.caption_ink_top(height, spec["caption"], args.caption_size, args.caption_bottom)
    font = ImageFont.truetype(str(glow.MONO_FONT), args.hook_size)
    draw = ImageDraw.Draw(overlay)
    text = "\n".join(lines)
    spacing = max(6, args.hook_size // 3)
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing)
    draw.multiline_text(
        ((width - (box[2] - box[0])) // 2, ink_top - args.hook_gap - box[3]),
        text,
        font=font,
        fill=(255, 255, 255, 244),
        spacing=spacing,
        align="center",
        stroke_width=4,
        stroke_fill=(0, 0, 0, 165),
    )
    return overlay


def stamp(radius: float) -> tuple[np.ndarray, np.ndarray]:
    """Offsets and weights that turn a point into a small soft body.

    A particle is a point and a point is one pixel, which the bloom then turns
    into a faint smudge with no core. Splatting a handful of offsets instead
    gives it a body with a bright middle and a soft edge -- and because the
    offsets are fractional, the body does not snap to the pixel grid as the
    thing moves.
    """
    offsets = [(0.0, 0.0)]
    for ring, count in ((radius * 0.6, 6), (radius, 8)):
        angles = np.linspace(0.0, 2.0 * np.pi, count, endpoint=False)
        offsets += [(ring * np.cos(a), ring * np.sin(a)) for a in angles]
    weights = np.array(
        [1.0] + [0.55] * 6 + [0.22] * 8, dtype=np.float32
    )
    return np.asarray(offsets, dtype=np.float32), weights / weights.sum() * 2.4


def tone(colour_sum: np.ndarray, density: np.ndarray, reference: float, spec: dict, args) -> np.ndarray:
    linear = glow.flame_map(colour_sum, density, reference, boost=spec["boost"])
    threshold = args.bloom_threshold
    strength = args.bloom_strength
    linear = glow.bloom(
        linear,
        threshold=spec.get("bloom_threshold", 0.30) if threshold is None else threshold,
        strength=spec.get("bloom_strength", 0.60) if strength is None else strength,
    )
    return glow.to_bytes(glow.tone_map(linear, exposure=spec["exposure"]))


# --------------------------------------------------------------------------
# The timeline
# --------------------------------------------------------------------------


def affinity_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    height, width = args.height, args.width

    matrix = FOUND_MATRIX
    if args.matrix_file is not None:
        matrix = np.load(args.matrix_file)[args.matrix_rank]
    if args.search:
        ranked = swarm.search(
            height,
            width,
            species=args.species,
            candidates=args.candidates,
            seed=args.search_seed,
            count=args.count,
            r_min=args.r_min,
            r_max=args.r_max,
            strength=args.strength,
            speed_limit=args.speed_limit,
            band=(args.band_top, args.band_bottom),
            wall=args.wall,
        )
        np.save(args.output_dir / "searched-matrices.npy", np.array([m for _, m in ranked]))
        matrix = ranked[args.matrix_rank][1]
        print(
            f"  best score {ranked[0][0]:.3f}, taking rank {args.matrix_rank}\n"
            f"{np.array2string(matrix, precision=3)}",
            flush=True,
        )

    band = (args.band_top, args.band_bottom)
    model = swarm.ParticleLife(
        height,
        width,
        matrix,
        count=args.count,
        r_min=args.r_min,
        r_max=args.r_max,
        strength=args.strength,
        speed_limit=args.speed_limit,
        band=band,
        wall=args.wall,
        seed=args.model_seed,
    )
    states: list[np.ndarray] = []
    for _ in range(args.duration_frames):
        model.step(1)
        states.append(model.position.astype(np.float32))
    bound, speed = model.motility()
    print(
        f"  affinity: {args.count:,} particles, "
        f"{args.duration_frames:,} steps, "
        f"{bound:.0%} of them in a body moving at {speed:.2f} px/step, "
        f"{model.occupancy(32):.0%} of the frame occupied",
        flush=True,
    )

    colours = (
        np.asarray(NEON_SPECIES[args.species_palette], dtype=np.float32)[model.species] / 255.0
    )
    offsets, stamp_weights = stamp(args.body)
    caption = build_overlay(width, height, spec, args)
    reference = 1.0

    def splat_state(index: int, gain: float) -> tuple[np.ndarray, np.ndarray]:
        points = states[index]
        screen = (points[:, None, :] + offsets[None, :, :]).reshape(-1, 2)
        weights = np.tile(stamp_weights * gain, len(points))
        return glow.splat(width, height, screen, np.repeat(colours, len(offsets), axis=0), weights)

    def frame_at(index: int) -> tuple[np.ndarray, np.ndarray]:
        # A short tail of earlier positions. Particle life is only legible in
        # motion -- a still frame of it is a scatter of dots -- and three fading
        # copies of where each thing just was put the motion back into the still.
        colour_sum, density = splat_state(index, 1.0)
        for back, gain in enumerate(args.trail, start=1):
            previous = index - back * args.trail_stride
            if previous < 0:
                break
            more_colour, more_density = splat_state(previous, gain)
            colour_sum += more_colour
            density += more_density
        return colour_sum, density

    def draw(u: float) -> np.ndarray:
        index = min(int(u * (len(states) - 1)), len(states) - 1)
        colour_sum, density = frame_at(index)
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    _, final_density = frame_at(len(states) - 1)
    reference = float(np.percentile(final_density[final_density > 0], 92.0))
    # The title/cover frame is the actual first simulated state, not the last:
    # a plain swap of which end of the timeline gets held open and written to
    # .cover.png. The growing sequence itself is untouched, so the loop no
    # longer closes seamlessly -- it cuts from the organized closing frame back
    # to this scattered opening one each time it repeats.
    return draw, draw(0.0)


def soliton_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    height, width = args.height, args.width
    recipe = FOUND_SOLITON
    world = lenia.Lenia(
        height // 2,
        width // 2,
        radius=args.lenia_radius,
        mu=recipe["mu"],
        sigma=recipe["sigma"],
        beta=recipe["beta"],
    )

    # Twelve copies of one animal, each turned a different way -- `phase` is
    # which way the arc faces and therefore which way the creature swims -- and
    # dealt out with a minimum separation. Left to chance, two of them start
    # close enough to touch in the first half second, and the piece needs them
    # apart long enough to be seen swimming before the first contact.
    generator = np.random.default_rng(args.lenia_seed)
    placed: list[tuple[float, float]] = []
    for _ in range(args.creatures):
        # The requested gap is a wish, not a constraint: twelve discs 170 cells
        # across do not fit in this field however long you shuffle them. Relax
        # it until one lands, rather than quietly dropping the creature -- or,
        # worse, stacking it on top of the last one that did fit.
        separation = args.separation
        while True:
            row = float(generator.integers(0, world.height))
            column = float(generator.integers(0, world.width))
            gaps = [
                np.hypot(
                    min(abs(row - other[0]), world.height - abs(row - other[0])),
                    min(abs(column - other[1]), world.width - abs(column - other[1])),
                )
                for other in placed
            ]
            if not gaps or min(gaps) > separation:
                placed.append((row, column))
                break
            separation *= 0.995
        patch = lenia.crescent(
            args.lenia_radius,
            recipe["ring"],
            recipe["thickness"],
            recipe["lobe"],
            float(generator.uniform(0.0, 2.0 * np.pi)),
            recipe["amplitude"],
        )
        world.place(patch, int(placed[-1][0]), int(placed[-1][1]))

    # The run is a fixed number of steps, and the clip length only decides how
    # fast it is played. Where this piece stops is a composition decision -- far
    # enough for the colonies to be the subject, not so far that they cover the
    # frame and it goes flat -- and tying it to the frame count instead would
    # mean a longer cut quietly becomes a different, worse picture.
    states: list[tuple[np.ndarray, np.ndarray]] = []
    rate = args.lenia_total / args.duration_frames
    advanced = 0
    for frame in range(args.duration_frames):
        target = int(round(rate * (frame + 1)))
        world.step(target - advanced)
        advanced = target
        states.append(
            (
                (np.clip(world.field, 0.0, 1.0) * 255.0).astype(np.uint8),
                # Amplified before it is stored: growth is ±1 at a creature's
                # rim and a few thousandths through the body of a settled
                # colony, so the honest signed value leaves everything but the
                # edges sitting on one palette entry.
                (np.clip(0.5 + 0.5 * args.growth_gain * world.growth, 0.0, 1.0) * 255.0).astype(
                    np.uint8
                ),
            )
        )
    print(
        f"  soliton: {len(placed)} creatures, "
        f"{advanced:,} steps at {rate:.2f} per frame, "
        f"{world.mass() / (world.height * world.width):.0%} of the field alive at the end",
        flush=True,
    )

    palette = glow.build_palette(spec["palette"])
    caption = build_overlay(width, height, spec, args)
    reference = 1.0

    def fields_at(index: int) -> tuple[np.ndarray, np.ndarray]:
        field, growth = states[index]
        return (
            np.repeat(np.repeat(field.astype(np.float32) / 255.0, 2, axis=0), 2, axis=1)[:height, :width],
            np.repeat(np.repeat(growth.astype(np.float32) / 255.0, 2, axis=0), 2, axis=1)[:height, :width],
        )

    def draw(u: float) -> np.ndarray:
        density, shade = fields_at(min(int(u * (len(states) - 1)), len(states) - 1))
        colour_sum = glow.sample_palette(palette, shade) * density[:, :, None]
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    final_density, _ = fields_at(len(states) - 1)
    reference = float(np.percentile(final_density[final_density > 0], 92.0))
    return draw, draw(1.0)


def cohort_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    """The same run `descent` draws as a pedigree, filmed as the animals it made.

    A row is a generation and a panel is one individual of it, run alone in its
    own world -- which is how it was scored, and the only way it can be run,
    because every genome carries its own kernel and its own growth curve and two
    of them in one field would have no rule for the overlap.

    What separates the rows is not decoration: generation 0 is sixty-four
    independent random draws and not one of them scored, so its row is the two
    ways a Lenia genome fails -- the field collapses, or it never stops growing.
    Every row below it is descended from that, and the bottom row is four
    animals.
    """
    height, width = args.height, args.width
    history = evolution.evolve(
        population=args.population,
        generations=args.generations,
        seed=args.ga_seed,
        report=print,
    )

    rows = [int(value) for value in args.cohort_rows.split(",")]
    recipes: list[dict] = []
    for generation in rows:
        # The fittest of each generation, which in generation 0 is a tie between
        # sixty-four scores of zero: nothing is being flattered, there is simply
        # nothing there to rank.
        chosen = sorted(history[generation], key=lambda genome: -genome["fitness"])
        for genome in chosen[: args.cohort_columns]:
            recipes.append(dict(genome, beta=evolution.RINGS[genome["rings"]]))
    print(
        "  cohort: generations " + ", ".join(str(value) for value in rows) + " · "
        + " ".join(f"{recipe['fitness']:.2f}" for recipe in recipes),
        flush=True,
    )

    radius = args.cohort_radius
    patches = [
        lenia.crescent(
            radius,
            recipe["ring"],
            recipe["thickness"],
            recipe["lobe"],
            recipe["phase"],
            recipe["amplitude"],
        )
        for recipe in recipes
    ]

    # The run is done twice, and the first time is only a survey.
    #
    # Three things have to be true at once and they pull against each other: a
    # creature has to be large enough on screen to have a shape, its panel has
    # to be small enough that twenty of them fit, and nothing may be cut in half
    # by the edge of its own world -- which is the one thing that reads as a
    # broken render rather than as a small round world. Pinning the camera to
    # each creature solves the last two and kills the piece: a soliton is a
    # steady travelling wave, so filmed in its own moving frame it is a
    # photograph. It has to swim across something.
    #
    # So the survey runs every genome in a world far too big to wrap, keeps the
    # highest value each cell ever held, and reads off the box each creature
    # actually used. That box is the answer to all three: the world is made just
    # big enough to hold the largest of them, which is as much magnification as
    # can be had; and every seed is placed so that its own box is centred, which
    # is why nothing ever reaches an edge. It also makes the fitness visible --
    # the box *is* the travel that was selected for, so a poor genome sits in a
    # corner of its world and a good one crosses it.
    survey = lenia.Cohort(recipes, size=args.cohort_survey, radius=radius)
    survey.seed(patches)
    peak = np.zeros_like(survey.field)
    for _ in range(args.cohort_total):
        survey.step(1)
        np.maximum(peak, survey.field, out=peak)

    origin = args.cohort_survey // 2
    used = np.zeros((len(recipes), 2), dtype=np.float64)
    shifts = np.zeros((len(recipes), 2), dtype=int)
    individual = (survey.mass() > 20.0) & (survey.mass() < 0.12 * args.cohort_survey ** 2)
    for index in range(len(recipes)):
        rows_used, columns_used = np.nonzero(peak[index] > 0.06)
        if not len(rows_used):
            continue
        for axis, seen in enumerate((rows_used, columns_used)):
            used[index, axis] = seen.max() - seen.min() + 1
            shifts[index, axis] = int(round(origin - (seen.max() + seen.min()) / 2.0))

    domain = args.cohort_domain or int(
        np.ceil((used[individual].max() + 2 * args.cohort_clearance) / 2.0) * 2
    )
    ceiling = 0.12 * domain * domain
    print(
        f"  cohort: the widest track an individual left is {used[individual].max():.0f} cells; "
        f"world set to {domain}",
        flush=True,
    )
    if used[individual].max() + 2 > domain:
        raise ValueError("a creature would touch the edge of its world; raise --cohort-domain")

    world = lenia.Cohort(recipes, size=domain, radius=radius)
    world.seed(patches, shifts)

    # Grid geometry. The box is what is left between the title's ink and the
    # hook's, and the panels are square and as large as fit in it -- the same
    # magnification everywhere, or a small creature and a large one would look
    # alike and the picture would be lying about the only thing it compares.
    top = args.title_top + args.grid_top
    bottom = height - args.caption_bottom - args.grid_bottom
    columns = args.cohort_columns
    tile = min(
        (width - 2 * args.margin - (columns - 1) * args.gutter) // columns,
        (bottom - top - (len(rows) - 1) * args.gutter) // len(rows),
    )
    grid_width = columns * tile + (columns - 1) * args.gutter
    grid_height = len(rows) * tile + (len(rows) - 1) * args.gutter
    left = (width - grid_width) // 2
    top += (bottom - top - grid_height) // 2
    print(
        f"  cohort: {len(recipes)} worlds of {domain}² at radius {radius:g}, "
        f"{tile} px panels at {tile / domain:.2f}×",
        flush=True,
    )

    # Colour is fitness, ranked rather than scaled. The scores in a converged
    # run are hopelessly bunched -- four zeros at one end and 5.39, 5.39, 5.38,
    # 5.38 at the other -- so dividing by the best would put three of the five
    # rows inside a fifth of the ramp and the picture would say the run stopped
    # improving after generation four. Ranking spends the whole ramp on the
    # order, which is the only part of a fitness anyone selects on anyway: a
    # tournament compares, it never asks by how much.
    scores = np.asarray([recipe["fitness"] for recipe in recipes], dtype=np.float64)
    order = np.argsort(np.argsort(scores)).astype(np.float64)
    for value in np.unique(scores):  # ties share a rank, or a row of four equals
        tied = scores == value       # would be dealt four different colours
        order[tied] = order[tied].mean()
    rank = (order / max(len(scores) - 1, 1)).astype(np.float32)

    # At least one step per frame, or the schedule rounds two frames onto the
    # same state and the clip carries exact repeats -- which is not slow motion,
    # it is a stutter, and it is visible.
    states: list[tuple[np.ndarray, np.ndarray]] = []
    rate = args.cohort_total / args.duration_frames
    if rate < 1.0:
        raise ValueError(
            f"--cohort-total {args.cohort_total} is fewer steps than the "
            f"{args.duration_frames} frames it has to fill."
        )
    advanced = 0
    for frame in range(args.duration_frames):
        target = int(round(rate * (frame + 1)))
        world.step(target - advanced)
        advanced = target
        states.append(
            (
                (np.clip(world.field, 0.0, 1.0) * 255.0).astype(np.uint8),
                (np.clip(0.5 + 0.5 * args.growth_gain * world.growth, 0.0, 1.0) * 255.0).astype(
                    np.uint8
                ),
            )
        )
    # A runaway is told from an individual by how much of its world it is
    # holding, not by raw mass: a creature's mass is its own and does not change
    # with the size of the world, while a flood's is a fixed fraction of it.
    mass = world.mass()
    flooded = int((mass > ceiling).sum())
    alive = int(((mass > 20.0) & (mass <= ceiling)).sum())
    print(
        f"  cohort: {advanced:,} steps at {rate:.2f} per frame · "
        f"{alive} individuals, {flooded} runaway, {len(recipes) - alive - flooded} empty",
        flush=True,
    )

    palette = glow.build_palette(spec["palette"])
    caption = build_overlay(width, height, spec, args)
    reference = 1.0

    def fields_at(index: int) -> tuple[np.ndarray, np.ndarray]:
        field, shade = states[index]
        density_frame = np.zeros((height, width), dtype=np.float32)
        shade_frame = np.zeros((height, width), dtype=np.float32)
        for panel in range(len(recipes)):
            row, column = divmod(panel, columns)
            y = top + row * (tile + args.gutter)
            x = left + column * (tile + args.gutter)
            sources = [(field[panel], density_frame)]
            if args.cohort_colour == "growth":
                sources.append((shade[panel], shade_frame))
            else:
                shade_frame[y : y + tile, x : x + tile] = rank[panel]
            for source, target in sources:
                target[y : y + tile, x : x + tile] = np.asarray(
                    Image.fromarray(source.astype(np.float32) / 255.0, mode="F").resize(
                        (tile, tile), Image.BILINEAR
                    ),
                    dtype=np.float32,
                )
        return density_frame, shade_frame

    def draw(u: float) -> np.ndarray:
        density, shade = fields_at(min(int(u * (len(states) - 1)), len(states) - 1))
        colour_sum = glow.sample_palette(palette, shade) * density[:, :, None]
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    final_density, _ = fields_at(len(states) - 1)
    reference = float(np.percentile(final_density[final_density > 0], 92.0))
    return draw, draw(1.0)


def shoal_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    """The same run again, as a race: one lane per generation, six copies abreast.

    `cohort` puts every individual in a panel of its own and is the stillest cut
    in the account, because a panel caps how far anything can travel and these
    creatures move a fifth of a cell per step. A lane lifts the cap in one
    direction: it runs the full width of the frame and wraps there, the way
    `soliton` wraps, so a creature can swim as far as the clip is long.

    Copies of one genome can share a field -- they are the same rule, so there is
    no question about what an overlap obeys, which is the question that keeps two
    *different* genomes apart. They are seeded abreast and, being identical, hold
    formation: no collisions, and the lane reads as a shoal.

    What the lanes then show is the thing the fitness actually rewarded. Travel
    is two thirds of the score, and it separates: generation 0's best is a
    runaway that only fills its world, generation 5's champion crosses at 0.073
    cells a step, generation 8's at 0.170 and generation 39's at 0.203.

    **The lane follows them across, and never along.** These creatures do not
    swim along an axis -- every fast one goes off at 27 to 44 degrees, and over a
    clip that is 130 cells of wander sideways for a body 16 cells across. A lane
    tall enough to contain that leaves the creature a third the size it could be.
    So the lane is a window that slides sideways with the shoal, which on a torus
    is a change of origin and nothing else, and cancels exactly the component of
    the motion that is not the race. The component along the lane -- the one
    being compared, the one the fitness paid for -- is untouched.
    """
    height, width = args.height, args.width
    history = evolution.evolve(
        population=args.population,
        generations=args.generations,
        seed=args.ga_seed,
        report=print,
    )

    lanes = [int(value) for value in args.shoal_rows.split(",")]
    recipes = []
    for generation in lanes:
        genome = sorted(history[generation], key=lambda entry: -entry["fitness"])[0]
        recipes.append(dict(genome, beta=evolution.RINGS[genome["rings"]]))
    print(
        "  shoal: generations " + ", ".join(str(value) for value in lanes) + " · fitness "
        + " ".join(f"{recipe['fitness']:.2f}" for recipe in recipes),
        flush=True,
    )

    radius = args.cohort_radius
    # Every copy keeps its genome's own phase. It is a gene, not a free
    # parameter: swept through 24 orientations in a world too big to wrap, the
    # generation 12 champion survives all of them, the generation 1 champion 19,
    # and the generation 39 champion **none** -- it holds together at the
    # orientation it was selected at and at no other. So the direction each lane
    # swims is whatever its genome does, and the lane is built around that rather
    # than the creature being turned to suit the lane.
    patches = [
        lenia.crescent(
            radius,
            recipe["ring"],
            recipe["thickness"],
            recipe["lobe"],
            recipe["phase"],
            recipe["amplitude"],
        )
        for recipe in recipes
    ]

    top = args.title_top + args.shoal_top
    bottom = height - args.caption_bottom - args.shoal_bottom
    lane_height = (bottom - top - (len(lanes) - 1) * args.gutter) // len(lanes)
    top += (bottom - top - (lane_height * len(lanes) + (len(lanes) - 1) * args.gutter)) // 2

    # The lane wraps left to right and must not wrap top to bottom, so the run
    # is surveyed first and the world is made exactly tall enough for the widest
    # track across it. These creatures swim diagonally -- 27 to 44 degrees off
    # the axis, every one of the fast ones -- so this is the measurement the
    # whole layout hangs on.
    def band_of(peak: np.ndarray, size: int) -> tuple[float, float]:
        """The rows a creature used, measured on the torus, and their middle.

        A track long enough to wrap leaves ink near row 0 and near the last row,
        and a plain max-minus-min then reports the whole world -- which sizes the
        lane to the survey instead of to the creature. The widest empty gap is
        the honest complement of the band.
        """
        rows_used = np.nonzero(peak.any(axis=1))[0]
        gaps = np.diff(np.r_[rows_used, rows_used[0] + size])
        widest = int(np.argmax(gaps))
        span = size - gaps[widest]
        return float(span), float((rows_used[(widest + 1) % len(rows_used)] + span / 2.0) % size)

    def survey_at(tall: int, wide: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        probe = lenia.Cohort(recipes, shape=(tall, wide), radius=radius)
        probe.seed(patches)
        peak = np.zeros_like(probe.field)
        for _ in range(args.shoal_total):
            probe.step(1)
            np.maximum(peak, probe.field, out=peak)
        # A runaway fills whatever world it is put in, so its track means
        # nothing -- and it needs nothing, since it will fill its lane whatever
        # the lane is. Only the individuals get a say in the scale.
        keeps = probe.mass() < 0.12 * tall * wide
        across = np.zeros(len(recipes))
        centre = np.full(len(recipes), tall / 2.0)
        for index in range(len(recipes)):
            if keeps[index]:
                across[index], centre[index] = band_of(peak[index] > 0.06, tall)
        return keeps, across, centre, probe.mass()

    # The lane has to be sized in the lane, not in some larger stand-in. These
    # creatures are chaotic enough that the same genome run in a different world
    # takes a slightly different path, so a band measured in a square survey
    # does not transfer -- the first cut of this piece sized the lane from a
    # 192² probe and the shoal came out straddling the lane's own edge, drawn
    # twice, once along each margin. So the survey is re-run in the geometry it
    # is sizing until the answer stops changing.
    tall = args.cohort_survey
    for attempt in range(5):
        wide = int(round(width / (lane_height / args.shoal_window)))
        individual, across, centre, alone = survey_at(tall, wide)
        if not individual.any():
            raise ValueError("every lane ran away; there is nothing to set the scale by")
        needed = int(np.ceil(across.max()) + 2 * args.shoal_clearance)
        print(
            f"  shoal: pass {attempt + 1} · world {tall}×{wide} · "
            f"widest track {across.max():.0f} cells · wants {needed}",
            flush=True,
        )
        if needed <= tall and tall - needed < 2 * args.shoal_clearance:
            break
        tall = needed
    else:
        raise ValueError("the lane height would not settle; raise --cohort-clearance")

    # The world holds the whole wander; the lane only shows a window of it, and
    # the window is what sets the magnification.
    tall += args.shoal_window
    scale = lane_height / args.shoal_window
    wide = int(round(width / scale))
    print(
        f"  shoal: worlds {tall}×{wide}, showing {args.shoal_window} cells at "
        f"{scale:.2f}× · creature ≈ {16 * scale:.0f} px",
        flush=True,
    )

    world = lenia.Cohort(recipes, shape=(tall, wide), radius=radius)
    for index, patch in enumerate(patches):
        # Abreast, evenly along the lane, and far enough apart that no two are
        # inside each other's kernel. They are identical and hold formation, so
        # the gap set here is the gap for the whole clip.
        gap = wide / args.shoal_copies
        if gap - patch.shape[1] < radius:
            raise ValueError(f"--shoal-copies {args.shoal_copies} packs them within a kernel")
        for copy in range(args.shoal_copies):
            world.place(
                index,
                patch,
                int(round(tall - centre[index])) - patch.shape[0] // 2,
                int(round(copy * gap)) - patch.shape[1] // 2,
            )

    rate = args.shoal_total / args.duration_frames
    if rate < 1.0:
        raise ValueError(f"--shoal-total {args.shoal_total} is fewer steps than frames")
    states: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    advanced = 0
    for frame in range(args.duration_frames):
        target = int(round(rate * (frame + 1)))
        world.step(target - advanced)
        advanced = target
        # Where the shoal is across its lane. They are identical copies in
        # formation, so one number does for the whole lane; a runaway has no
        # such number and does not need one, since it fills the lane anyway.
        tracked = np.full(len(recipes), tall / 2.0, dtype=np.float32)
        for index in range(len(recipes)):
            if individual[index] and world.field[index].sum() > 20.0:
                tracked[index] = _centre_of_mass(world.field[index])[0]
        states.append(
            (
                (np.clip(world.field, 0.0, 1.0) * 255.0).astype(np.uint8),
                (np.clip(0.5 + 0.5 * args.growth_gain * world.growth, 0.0, 1.0) * 255.0).astype(
                    np.uint8
                ),
                tracked,
            )
        )
    # Every copy has to still be there at the end, and that is not a formality.
    # The champions of the early generations are *metastable*: generation 1's
    # best passes the 500-step audition and then, run on, either grows or dies
    # depending on nothing that can be pointed at -- seeded at seven different
    # heights in the same lane it ends up with anywhere between 1.1 and 6.3
    # copies' worth of mass. Generation 5 onwards holds five copies at every one
    # of those placements. So the lanes are picked from the genomes that are
    # stably alive, and the count is checked against the survey's single copy.
    survivors = world.mass() / np.where(individual, alone, np.inf)
    print(
        f"  shoal: {advanced:,} steps at {rate:.2f} per frame · "
        + " · ".join(
            f"gen {lane}: " + ("runaway" if not keep else f"{count:.1f}/{args.shoal_copies} copies")
            for lane, keep, count in zip(lanes, individual, survivors)
        ),
        flush=True,
    )
    lost = individual & (survivors < 0.85 * args.shoal_copies)
    if lost.any():
        raise ValueError(
            f"lanes {[lanes[i] for i in np.nonzero(lost)[0]]} lost copies over the run; "
            "pick generations whose champion is stably alive"
        )

    # And nothing may have touched the top or bottom of its lane at any point in
    # the clip -- a creature drawn half along one margin and half along the other
    # is the one thing here that reads as a broken render.
    for index in range(len(recipes)):
        if not individual[index]:
            continue
        for field, _, tracked in states:
            rows = np.nonzero((field[index] > 15).any(axis=1))[0]
            if not len(rows):
                continue
            offset = rows - tracked[index]
            offset = np.where(offset > tall / 2, offset - tall, offset)
            offset = np.where(offset < -tall / 2, offset + tall, offset)
            if np.abs(offset).max() > args.shoal_window / 2 - 2:
                raise ValueError(
                    f"lane {lanes[index]} overflows the window it is shown in; "
                    "raise --shoal-window"
                )

    scores = np.asarray([recipe["fitness"] for recipe in recipes], dtype=np.float64)
    order = np.argsort(np.argsort(scores)).astype(np.float64)
    for value in np.unique(scores):
        tied = scores == value
        order[tied] = order[tied].mean()
    rank = (order / max(len(scores) - 1, 1)).astype(np.float32)

    palette = glow.build_palette(spec["palette"])
    caption = build_overlay(width, height, spec, args)
    reference = 1.0

    def fields_at(index: int) -> tuple[np.ndarray, np.ndarray]:
        field, shade, tracked = states[index]
        density_frame = np.zeros((height, width), dtype=np.float32)
        shade_frame = np.zeros((height, width), dtype=np.float32)
        for lane in range(len(recipes)):
            y = top + lane * (lane_height + args.gutter)
            # Roll the shoal to the middle of its world in whole cells, then take
            # the remainder out in pixels after the resize: a lane that is only
            # ever centred to the nearest cell twitches by six pixels every few
            # frames, on creatures that are otherwise gliding.
            shift = int(round(tall / 2.0 - tracked[lane]))
            residual = (tall / 2.0 - tracked[lane]) - shift
            start = int(round((tall / 2.0 - residual) * scale - lane_height / 2.0))
            start = int(np.clip(start, 0, int(round(tall * scale)) - lane_height))
            sources = [(field[lane], density_frame)]
            if args.cohort_colour == "growth":
                sources.append((shade[lane], shade_frame))
            else:
                shade_frame[y : y + lane_height, :] = rank[lane]
            for source, target in sources:
                rolled = np.roll(source.astype(np.float32) / 255.0, shift, axis=0)
                grown = np.asarray(
                    Image.fromarray(rolled, mode="F").resize(
                        (width, int(round(tall * scale))), Image.BILINEAR
                    ),
                    dtype=np.float32,
                )
                target[y : y + lane_height, :] = grown[start : start + lane_height, :]
        return density_frame, shade_frame

    def draw(u: float) -> np.ndarray:
        density, shade = fields_at(min(int(u * (len(states) - 1)), len(states) - 1))
        colour_sum = glow.sample_palette(palette, shade) * density[:, :, None]
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    final_density, _ = fields_at(len(states) - 1)
    reference = float(np.percentile(final_density[final_density > 0], 92.0))
    return draw, draw(1.0)


def _centre_of_mass(field: np.ndarray) -> np.ndarray:
    """Where the creature is, on a torus, by the circular mean of each axis.

    An animal sitting on the seam has half its mass at row 2 and half at row
    126, and an arithmetic mean puts its centre in the middle of a world where
    there is nothing at all.
    """
    total = max(float(field.sum()), 1e-9)
    centres = []
    for axis, length in ((1, field.shape[0]), (0, field.shape[1])):
        profile = field.sum(axis=axis)
        angle = np.arange(length) * (2.0 * np.pi / length)
        mean = np.arctan2(
            float((profile * np.sin(angle)).sum() / total),
            float((profile * np.cos(angle)).sum() / total),
        )
        centres.append(float(mean % (2.0 * np.pi)) * length / (2.0 * np.pi))
    return np.asarray(centres, dtype=np.float32)


def descent_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    height, width = args.height, args.width
    history = evolution.evolve(
        population=args.population,
        generations=args.generations,
        seed=args.ga_seed,
        report=print,
    )
    survivors = [genome for genome in history[-1] if genome["fitness"] > 0]
    print(
        f"  descent: {len(survivors)}/{args.population} alive in the last generation, "
        f"{len({genome['founder'] for genome in survivors})} founder line left, "
        f"best {max(genome['fitness'] for genome in history[-1]):.2f}",
        flush=True,
    )

    # Laid out as a pedigree, which is not the same as laying out a population.
    # Plotting a gene on the horizontal draws the population converging into a
    # thread up the middle of the frame -- true, and an empty picture. Spreading
    # every generation evenly across the width instead fills the frame but hides
    # the only thing worth seeing, because a line that has just ended looks
    # exactly like one that is about to go somewhere.
    #
    # So: the last generation is dealt across the width in order of ancestry,
    # every earlier individual that still has descendants sits at the mean of
    # its own, and everything else -- which is most of it -- hangs off its
    # parent as a stub that stops. What that draws is a canopy over a trunk.
    generations = len(history)
    children: list[list[list[int]]] = [[[] for _ in generation] for generation in history]
    for index in range(1, generations):
        for child, genome in enumerate(history[index]):
            children[index - 1][genome["parent"]].append(child)

    survives = [np.zeros(len(generation), dtype=bool) for generation in history]
    survives[-1][:] = True
    for index in range(generations - 2, -1, -1):
        for parent, offspring in enumerate(children[index]):
            survives[index][parent] = any(survives[index + 1][child] for child in offspring)

    def ancestry(index: int, individual: int) -> tuple[int, ...]:
        chain = [individual]
        for step in range(index, 0, -1):
            individual = history[step][individual]["parent"]
            chain.append(individual)
        return tuple(reversed(chain))

    columns: list[np.ndarray] = [np.zeros(len(generation)) for generation in history]
    order = sorted(range(len(history[-1])), key=lambda i: ancestry(generations - 1, i))
    columns[-1][order] = np.linspace(0.0, 1.0, len(order))
    for index in range(generations - 2, -1, -1):
        for individual in range(len(history[index])):
            kept = [child for child in children[index][individual] if survives[index + 1][child]]
            if kept:
                columns[index][individual] = float(
                    np.mean([columns[index + 1][child] for child in kept])
                )
    # The founders with nothing left of them are spread evenly across the
    # bottom of the frame: sixty-four tries laid out in a row, of which the
    # trunk is one.
    barren = [i for i in range(len(history[0])) if not survives[0][i]]
    if barren:
        columns[0][barren] = np.linspace(0.02, 0.98, len(barren))

    # Every later dead end hangs off its parent, fanned out a little so that a
    # parent with nine of them reads as nine rather than as one bright line.
    for index in range(1, generations):
        dying = [i for i in range(len(history[index])) if not survives[index][i]]
        for rank, individual in enumerate(dying):
            parent = history[index][individual]["parent"]
            columns[index][individual] = float(
                np.clip(columns[index - 1][parent] + 0.012 * ((rank % 7) - 3), 0.0, 1.0)
            )

    # No re-centring: the canopy is dealt across the full width by construction,
    # so the drawing already touches both margins and there is nowhere to slide
    # it to. Which side the surviving trunk comes up on is an accident of the
    # run, and the empty quarter it leaves is the shape of that accident.
    top, bottom = args.title_top + args.tree_top, height - args.caption_bottom - args.tree_bottom
    rows = np.linspace(bottom, top, len(history))
    inset = args.margin + args.tree_inset

    def screen_x(position: np.ndarray) -> np.ndarray:
        return inset + position * (width - 2 * inset)

    best = max(
        max(genome["fitness"] for genome in generation) for generation in history
    )
    palette = np.asarray(LINEAGE, dtype=np.float32) / 255.0

    segments = []
    for index in range(1, len(history)):
        generation = history[index]
        for child, genome in enumerate(generation):
            parent = genome["parent"]
            weight = 0.16 + 1.0 * (genome["fitness"] / max(best, 1e-9))
            segments.append(
                (
                    index,
                    float(screen_x(columns[index - 1])[parent]),
                    float(rows[index - 1]),
                    float(screen_x(columns[index])[child]),
                    float(rows[index]),
                    float(weight),
                    palette[genome["founder"] % len(palette)],
                )
            )

    # Sampled by length, not by count. A fixed number of points per line looks
    # right for the short ones and turns the long ones -- a child whose parent
    # stood two hundred pixels away -- into a dotted rule across the frame.
    ladders = {
        count: np.linspace(0.0, 1.0, count, dtype=np.float32)
        for count in {int(np.clip(np.hypot(x1 - x0, y1 - y0) / args.spacing, 14, 260))
                      for _, x0, y0, x1, y1, _, _ in segments}
    }
    caption = build_overlay(width, height, spec, args)
    reference = 1.0

    def draw_upto(front: float) -> tuple[np.ndarray, np.ndarray]:
        """Every segment below the growing front, and the partial one at it."""
        points, colours, weights = [], [], []
        for index, x0, y0, x1, y1, weight, colour in segments:
            share = float(np.clip(front - (index - 1), 0.0, 1.0))
            if share <= 0.0:
                continue
            length = float(np.hypot(x1 - x0, y1 - y0))
            count = int(np.clip(length / args.spacing, 14, 260))
            reach = ladders[count] * share
            line = np.column_stack((x0 + (x1 - x0) * reach, y0 + (y1 - y0) * reach))
            # A line one pixel wide is a line with no mass in it, and this house
            # gets its brightness from how much of something is there. Two
            # dimmer copies a pixel to either side give it a core and an edge.
            across = np.array([(y1 - y0) / max(length, 1e-6), -(x1 - x0) / max(length, 1e-6)])
            for offset, share_of_ink in ((0.0, 1.0), (args.thickness, 0.5), (-args.thickness, 0.5)):
                points.append(line + across * offset)
                colours.append(np.repeat(colour[None, :], count, axis=0))
                weights.append(
                    np.full(count, weight * args.ink * share_of_ink, dtype=np.float32)
                )
        if not points:
            return (
                np.zeros((height, width, 3), dtype=np.float32),
                np.zeros((height, width), dtype=np.float32),
            )
        return glow.splat(
            width,
            height,
            np.concatenate(points).astype(np.float32),
            np.concatenate(colours).astype(np.float32),
            np.concatenate(weights),
        )

    def draw(u: float) -> np.ndarray:
        colour_sum, density = draw_upto(u * (len(history) - 1))
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    _, final_density = draw_upto(len(history) - 1)
    reference = float(np.percentile(final_density[final_density > 0], 92.0))
    return draw, draw(1.0)


def replicator_timeline(spec: dict, args) -> tuple[Callable[[float], np.ndarray], np.ndarray]:
    height, width = args.height, args.width
    spec = dict(spec, palette=LOOP_PALETTES[args.loops_palette])
    cell = args.loops_cell
    world = langton.Loops(height // cell, width // cell, args.loops_row, args.loops_column)

    # Where the seed sits is decided by the text, not by the middle of the
    # frame. The colony is a diamond -- four neighbours cannot grow a circle --
    # and the seed carries its construction arm to the right, so growth is not
    # symmetric about the seed and centring it means offsetting the seed left.
    # At 2,250 steps the diamond is 963 x 903 px: 54 px of black to its left,
    # 60 to its right, 141 under the title's ink and 146 over the hook.
    #
    # Where the run *stops* is a composition decision too, and a sharper one
    # than it looks. The replication period is 151 steps, so the phase of the
    # colony at the last frame decides how much of it is caught mid-copy:
    # 2,250 steps leaves 100 of 345 loops still working, where 2,200 and 2,300
    # leave 50 and 54. The cover frame is the one that has to carry the piece.
    # Pacing, and this piece needs it more than anything else in the account.
    # Replication is exponential, so equal steps per frame spend the first four
    # seconds on a speck: at 3 px a cell one loop is 30 px, and the finished cut
    # measured 40.6% of its frames under the freeze threshold with every one of
    # them in the opening half. A power law over the frame index gets that to
    # 8.4% and then puts freezes back at the *end*, because it is a guess at the
    # curve rather than the curve.
    #
    # So the curve is measured, and measured on the right quantity. Counting
    # the cells that *change* reads 15.5%: it counts the signal train cycling
    # on the spot, which at 135 px is not a picture changing at all. What the
    # eye reacts to is the difference between one banked state and the next, so
    # the probe run stores a coarse map of where there is any ink, walks the
    # distance between consecutive maps, and banks where that running distance
    # crosses equal shares. Every frame then carries the same amount of change
    # and the clip plays straight through with no scheduler at all.
    probe = langton.Loops(height // cell, width // cell, args.loops_row, args.loops_column)
    block = 10
    signature = np.empty(
        (args.loops_total + 1, (height // cell) // block, (width // cell) // block),
        dtype=np.float32,
    )

    def coarse(grid: np.ndarray) -> np.ndarray:
        rows, columns = signature.shape[1], signature.shape[2]
        return (grid[: rows * block, : columns * block] > 0).reshape(
            rows, block, columns, block
        ).mean(axis=(1, 3))

    signature[0] = coarse(probe.grid)
    for index in range(args.loops_total):
        probe.step()
        signature[index + 1] = coarse(probe.grid)
    walk = np.abs(np.diff(signature, axis=0)).mean(axis=(1, 2))
    running = np.cumsum(walk)
    wanted = running[-1] * (np.arange(1, args.duration_frames + 1) / args.duration_frames)
    targets = np.searchsorted(running, wanted) + 1
    # Never hand the same state to two frames: a repeated state *is* the stutter.
    targets = np.minimum(np.maximum.accumulate(targets), args.loops_total)
    targets = np.maximum(targets, np.arange(1, args.duration_frames + 1))

    states: list[tuple[np.ndarray, np.ndarray]] = []
    advanced = 0
    for frame in range(args.duration_frames):
        target = int(targets[frame])
        world.step(target - advanced)
        advanced = target
        states.append(
            (world.grid.copy(), np.clip(world.age, 0, args.loops_total).astype(np.uint16))
        )

    total_loops, alive = world.census()
    top, bottom, left, right = world.extent()
    print(
        f"  replicator: {advanced:,} steps, first frame at step {int(targets[0])}, "
        f"{total_loops} loops, {alive} still working, "
        f"{int((world.grid > 0).sum()):,} cells drawn; "
        f"rows {top * cell}-{bottom * cell} px, columns {left * cell}-{right * cell} px",
        flush=True,
    )

    # Colour is steps since a cell last changed, and that is hopelessly skewed:
    # nearly every cell in a finished colony is a husk that has not moved for
    # hundreds of steps, while the machine works on a handful. Scaled, the
    # whole frame lands on one palette entry. Ranked against the distribution
    # the last frame actually has, the ramp is spent where the cells are.
    final_grid, final_age = states[-1]
    ladder = np.sort(final_age[final_grid > 0])
    span = np.arange(args.loops_total + 2, dtype=np.int64)
    rank = np.searchsorted(ladder, span, side="left") / max(len(ladder), 1)
    # Fresh at the top of the ramp: what is bright is what is being worked on.
    shade_ladder = (1.0 - rank).astype(np.float32)

    offsets, weights = stamp(args.loops_body)
    palette = glow.build_palette(spec["palette"])
    caption = build_overlay(width, height, spec, args)
    reference = 1.0

    def fields_at(index: int) -> tuple[np.ndarray, np.ndarray]:
        grid, age = states[index]
        rows, columns = np.nonzero(grid)
        shade = shade_ladder[np.clip(age[rows, columns], 0, len(shade_ladder) - 1)]
        centres = np.stack(
            [(columns + 0.5) * cell, (rows + 0.5) * cell], axis=1
        ).astype(np.float32)
        # Every cell weighs the same. A cell is one unit of stuff, so density
        # stays what the house says it is -- how much is there -- and the live
        # rim reads because its colour is at the bright end, not because it was
        # given extra weight.
        screen = (centres[:, None, :] + offsets[None, :, :]).reshape(-1, 2)
        colours = np.repeat(glow.sample_palette(palette, shade), len(offsets), axis=0)
        sample_weights = np.tile(weights, len(centres)).astype(np.float32)
        return glow.splat(width, height, screen, colours, sample_weights)

    def draw(u: float) -> np.ndarray:
        colour_sum, density = fields_at(min(int(u * (len(states) - 1)), len(states) - 1))
        return glow.compose(tone(colour_sum, density, reference, spec, args), caption)

    _, final_density = fields_at(len(states) - 1)
    reference = float(np.percentile(final_density[final_density > 0], 92.0))
    return draw, draw(1.0)


TIMELINES = {
    "affinity": affinity_timeline,
    "soliton": soliton_timeline,
    "cohort": cohort_timeline,
    "shoal": shoal_timeline,
    "descent": descent_timeline,
    "replicator": replicator_timeline,
}


def render_edition(name: str, args: argparse.Namespace) -> Path:
    spec = EDITIONS[name]
    draw, finished = TIMELINES[name](spec, args)

    stem = f"{spec['slug']}_{args.width}x{args.height}_{args.duration:g}s_{args.fps}fps"
    if args.hook and spec.get("hook"):
        stem += "_hook_plex"
    if args.tag:
        # A variant cut of the same piece, written alongside rather than over it.
        stem += f"_{args.tag}"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(finished).save(args.output_dir / f"{stem}.cover.png")
    if args.preview:
        return args.output_dir / f"{stem}.cover.png"

    output = args.output_dir / f"{stem}.mp4"
    encoder = start_encoder(output, args.width, args.height, args.fps)
    assert encoder.stdin is not None
    try:
        payload = finished.tobytes()
        for _ in range(args.hold):
            encoder.stdin.write(payload)
        growing = args.duration_frames - args.hold
        for index in range(growing):
            # Ends on u = 1, the frame the clip opened on: no seam in the loop.
            encoder.stdin.write(draw((index + 1) / growing).tobytes())
            if (index + 1) % 60 == 0:
                print(f"  {name}: frame {index + 1}/{growing}", flush=True)
    finally:
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError(f"ffmpeg failed while rendering {name}.")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", choices=sorted(EDITIONS), action="append")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--preview", action="store_true", help="Save the cover still and stop.")
    parser.add_argument("--tag", help="suffix for a variant cut, e.g. sharp")
    parser.add_argument(
        "--species-palette", choices=sorted(NEON_SPECIES), default="family",
        help="which four hues the species get",
    )
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--duration", type=float, default=8)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--hold", type=int, default=11, help="frames held on the finished form")
    parser.add_argument("--margin", type=int, default=64)
    parser.add_argument("--title-top", type=int, default=240)
    parser.add_argument("--caption-bottom", type=int, default=190)
    parser.add_argument("--caption-size", type=int, default=27)
    parser.add_argument("--scrim", type=float, default=0.95)
    parser.add_argument("--no-hook", dest="hook", action="store_false")
    parser.add_argument("--hook-size", type=int, default=34)
    parser.add_argument("--hook-gap", type=int, default=82)
    # Default None so a piece may pin its own look in the spec and still be
    # overridden from the command line. `replicator` pins `sharp`: a lattice
    # of 3 px walls is exactly what a wide halo smears into haze.
    parser.add_argument("--bloom-threshold", type=float, default=None)
    parser.add_argument("--bloom-strength", type=float, default=None)
    # Scaled to the band, not to the frame. What these rules do depends on how
    # many neighbours a particle has, so keeping the count while shrinking the
    # area by two fifths would quietly hand the piece a denser world and a
    # different answer.
    parser.add_argument("--count", type=int, default=11667)
    parser.add_argument("--species", type=int, default=4)
    parser.add_argument("--r-min", type=float, default=7.5)
    parser.add_argument("--r-max", type=float, default=36.0)
    parser.add_argument("--strength", type=float, default=0.50)
    parser.add_argument("--speed-limit", type=float, default=3.0)
    parser.add_argument("--body", type=float, default=3.0, help="radius of a particle's splat")
    parser.add_argument("--trail", type=float, nargs="*", default=[0.5, 0.3, 0.16, 0.08])
    parser.add_argument("--trail-stride", type=int, default=1)
    # The band leaves black for the text to sit on: the title's ink ends at 270,
    # the hook's top line starts near 1460, and nothing may swim through either.
    # Held by a spring rather than a wall, so the population thins into the
    # margin instead of stacking against a line -- which is also why the band is
    # set well inside the clearance it has to keep. A cluster straddling the
    # edge drags its own members out however stiff the spring is, and measured
    # over a whole clip the excursion is about 90 px: with these numbers the
    # furthest any particle ever gets is 293 at the top and 1424 at the bottom.
    parser.add_argument("--band-top", type=float, default=385.0)
    parser.add_argument("--band-bottom", type=float, default=1345.0)
    parser.add_argument("--wall", type=float, default=0.25)
    parser.add_argument("--model-seed", type=int, default=20260823)
    parser.add_argument("--search", action="store_true", help="look for a new interaction table")
    parser.add_argument("--matrix-file", type=Path, help="load tables saved by an earlier --search")
    parser.add_argument("--matrix-rank", type=int, default=0, help="which of the ranked tables to use")
    parser.add_argument("--candidates", type=int, default=24)
    parser.add_argument("--search-seed", type=int, default=7)
    parser.add_argument("--lenia-radius", type=float, default=30.0)
    parser.add_argument(
        "--lenia-total", type=int, default=480,
        help="simulation steps in the whole run, spread over however many frames",
    )
    parser.add_argument("--growth-gain", type=float, default=0.8)
    parser.add_argument("--creatures", type=int, default=12)
    parser.add_argument("--separation", type=float, default=170.0, help="minimum gap between seeds")
    parser.add_argument("--lenia-seed", type=int, default=4)
    parser.add_argument("--population", type=int, default=64)
    parser.add_argument("--generations", type=int, default=40)
    parser.add_argument("--ga-seed", type=int, default=11)
    # The cohort is filmed at the size it was selected at: `evolution.fitness`
    # scores every genome at radius 13 in a world 128 across, and Lenia is only
    # approximately scale-invariant, so re-running one of these any larger would
    # be running a different equation and could quietly lose the creature.
    parser.add_argument("--cohort-rows", default="0,1,4,12,39", help="which generations, as rows")
    parser.add_argument("--cohort-columns", type=int, default=4)
    # Scored at 128, filmed at 64. The domain is not the discretisation -- the
    # radius is -- so halving it is not the change Lenia is fragile about; it
    # only brings the far side of the torus nearer, and at 64 the creatures are
    # still 40 cells clear of their own image. Checked rather than assumed: the
    # twelve genomes come out with the same fates and the same masses at 128, 96
    # and 64, and only break at 48. What it buys is magnification -- a creature
    # is a quarter of its world instead of an eighth.
    parser.add_argument(
        "--cohort-domain", type=int, default=0,
        help="cells per world; 0 measures it from the survey run",
    )
    parser.add_argument(
        "--cohort-survey", type=int, default=192,
        help="world for the survey run: any size too big for a track to wrap in",
    )
    parser.add_argument("--cohort-clearance", type=int, default=4, help="cells of black to keep")
    parser.add_argument("--cohort-radius", type=float, default=13.0)
    parser.add_argument(
        "--cohort-total", type=int, default=240,
        help="steps in the whole run; at or above the frame count, or frames repeat",
    )
    parser.add_argument(
        "--cohort-colour", choices=("fitness", "growth"), default="fitness",
        help="the ranked score that decided the run, or the front-and-wake field",
    )
    parser.add_argument("--gutter", type=int, default=10, help="black between panels")
    parser.add_argument("--shoal-rows", default="0,5,8,39", help="which generations, as lanes")
    parser.add_argument("--shoal-copies", type=int, default=5, help="copies of the genome per lane")
    parser.add_argument(
        "--shoal-window", type=int, default=56,
        help="cells of the lane's world shown; the window slides with the shoal",
    )
    parser.add_argument("--shoal-top", type=int, default=150, help="gap under the title")
    parser.add_argument("--shoal-bottom", type=int, default=350, help="gap over the hook")
    parser.add_argument("--shoal-clearance", type=int, default=10, help="cells of margin")
    parser.add_argument(
        "--shoal-total", type=int, default=720,
        help="steps in the whole run; more travel, but a taller world to hold the drift",
    )
    parser.add_argument("--grid-top", type=int, default=90, help="gap under the title")
    parser.add_argument("--grid-bottom", type=int, default=320, help="gap over the hook")
    parser.add_argument("--tree-top", type=int, default=90, help="gap under the title")
    parser.add_argument("--tree-bottom", type=int, default=250, help="gap over the data block")
    parser.add_argument("--tree-inset", type=int, default=20)
    parser.add_argument("--spacing", type=float, default=1.5, help="pixels between splatted points")
    parser.add_argument(
        "--loops-total", type=int, default=2250,
        help="simulation steps in the whole run; where it stops is a composition choice",
    )
    parser.add_argument("--loops-cell", type=int, default=3, help="pixels per automaton cell")
    parser.add_argument("--loops-row", type=int, default=298, help="seed row, in cells")
    parser.add_argument("--loops-column", type=int, default=171, help="seed column, in cells")
    parser.add_argument("--loops-body", type=float, default=1.8, help="splat radius of one cell")
    parser.add_argument(
        "--loops-palette", choices=sorted(LOOP_PALETTES), default="forge",
        help="which ramp the staleness is read through",
    )
    parser.add_argument("--ink", type=float, default=0.85)
    parser.add_argument("--thickness", type=float, default=1.1, help="pixels either side of a line")
    parser.add_argument("--exposure", type=float)
    parser.add_argument("--boost", type=float)
    args = parser.parse_args()
    args.duration_frames = round(args.duration * args.fps)
    return args


if __name__ == "__main__":
    options = parse_args()
    for edition_name in options.edition or list(EDITIONS):
        for key in ("exposure", "boost"):
            if getattr(options, key) is not None:
                EDITIONS[edition_name][key] = getattr(options, key)
        print(f"Rendering {edition_name} ...", flush=True)
        print(f"Saved {render_edition(edition_name, options)}", flush=True)
