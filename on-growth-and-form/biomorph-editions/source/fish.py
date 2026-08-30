#!/usr/bin/env python3
"""One fish, as numbers — built once, posed every frame.

The biomorph edition draws animals as dotted *curves*: the cosine creature is
ribs, the medusa is meridians. This is the medusa's construction applied to a
fish. Her bell is "a 3D dome drawn as dotted meridians, projected
orthographically with a small tilt, so it has a far side without ever turning",
and a body is the same problem — so the fish is a surface, drawn as the lines
that run over it, and it has a near flank and a far one.

Three body coordinates:

    ξ ∈ [0, 1]     along the spine, 0 at the snout, 1 at the tail tip
    ζ ∈ [0, 2π)    around the cross-section: 0 near flank, π/2 dorsal,
                   π far flank, -π/2 ventral
    the section    an ellipse, half-height d(ξ) by half-width beam·d(ξ)

`beam` is about 0.30, because a fish is laterally compressed; that one number
is most of what stops the body reading as a sausage. The outline is

    d(ξ) = depth · [ (1-wrist)·ξ^head·(1 - taper·ξ)^tail  +  wrist·ramp(ξ) ]

peak-normalised. The first term is the trunk, deepest wherever `head` and
`tail` put it — 28% along for a sardine, which is where a real one is deepest.
The second is a floor that keeps the caudal peduncle from pinching to nothing,
ramped in over the first few percent so the snout still comes to a point.

What earns its place:

**Rings sell the volume.** Meridians alone are what a flat cut-out already
looked like — nested contours. It is the cross-sections that make the eye read
a tube, exactly as the medusa's two latitude rings do for her dome.

**Two of everything that comes in twos.** Two lateral lines, two eyes, two
pectorals. The far one of each is dimmed by `nz`, and that asymmetry is a
stronger depth cue than any amount of shading on a single flank.

**The caudal fin is built in its own frame.** It hangs off the wrist rigidly
and is pitched by the spine's angle there *plus* a lag, because a real fin
flexes after the peduncle it hangs from. Sampling it along the continuing spine
skews it into an asymmetric wedge. The trailing edge reaches further back at
the lobe tips than in the middle, which is all a fork is; `caudal_fork` slides
continuously from a deep crescent through a paddle to a lanceolate point.

**The spine keeps its length.** The wave is applied by integrating the tangent
rather than by adding a sideways offset to fixed positions, so the animal
flexes instead of stretching. The offset version is cheaper and looks like a
rubber band, which is what it is.

**The accent is a band, not a switch.** `glow` rises and falls smoothly with
the phase and every stroke at that ξ picks it up, so what travels head to tail
is a lit ring around the whole animal rather than a dash appearing on one line.
The two shipped biomorphs threshold their accent hard — red where k² ≥ 15,
green where sin > 0.96 — which works for a line drawing and does not for a
solid. Deliberate departure, not drift. Colour still means exactly what it
means everywhere else in the account: the position of the wave, right now.

The lateral line carries the accent strongest because it is the organ a real
fish senses its neighbours with — pressure differences in the water, the
channel a real shoal synchronises through. It is drawn here on animals that
sense nothing at all.

Local frame: the snout is at the origin, the body trails towards +x, so the
animal faces -x. `pose` returns the lateral offset and the outward lateral
direction separately, and callers decide what depth means; nothing in here
knows about a frame, a ball or a camera.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import NamedTuple

import numpy as np


# Stroke labels, so a renderer can weight the parts differently.
MERIDIAN, RING, LINE, CAUDAL, MEDIAN, PECTORAL, EYE, FILAMENT, HEAD = range(9)

PART_NAMES = {
    MERIDIAN: "meridian", RING: "ring", LINE: "lateral line", CAUDAL: "caudal",
    MEDIAN: "dorsal/anal", PECTORAL: "pectoral", EYE: "eye",
    FILAMENT: "filament", HEAD: "operculum/jaw",
}


class Pose(NamedTuple):
    """One frame of one animal, in its own frame, in pixels."""

    x: np.ndarray       # along the body; snout at 0, tail trailing towards +x
    y: np.ndarray       # up
    z: np.ndarray       # lateral: + towards the near flank
    nz: np.ndarray      # outward lateral direction, -1 far flank .. +1 near
    glow: np.ndarray    # 0..1, the wave's crest right here, right now
    weight: np.ndarray  # how much this stroke carries the drawing
    part: np.ndarray


@dataclass(frozen=True)
class Species:
    """Everything that makes one kind of animal, and nothing else."""

    name: str

    # --- trunk
    depth: float = 0.105       # max half-depth / length
    beam: float = 0.30         # half-width / half-depth — how compressed it is
    head: float = 0.69         # low = blunt snout; high = pointed
    tail: float = 1.90         # high = narrows hard towards the wrist
    taper: float = 0.95
    wrist: float = 0.13        # half-depth at the peduncle, as a fraction of max
    peduncle: float = 0.84     # ξ where the trunk stops and the caudal starts
    belly: float = 0.10        # how much deeper the ventral half runs

    # --- the surface net
    meridians: int = 23
    rings: tuple[float, ...] = (0.22, 0.45, 0.68)

    # --- caudal fin
    caudal_span: float = 0.122  # half-height at the lobe tips / length
    caudal_fork: float = 0.56   # >0 forked, 0 paddle, <0 lanceolate point
    caudal_lag: float = 0.95    # radians the fin trails the wrist
    caudal_rays: int = 9

    # --- median fins: (ξ start, ξ end, height/length, sweep back)
    dorsal: tuple[float, float, float, float] = (0.31, 0.56, 0.078, 0.55)
    anal: tuple[float, float, float, float] = (0.60, 0.745, 0.050, 0.45)
    pectoral: tuple[float, float, float, float] = (0.29, 0.375, 0.056, 0.85)
    pectoral_zeta: float = -0.50   # where on the flank it is hinged
    fin_rays: int = 6

    # --- threads: (ξ anchor, ζ anchor, length/length, rise/length)
    filaments: tuple[tuple[float, float, float, float], ...] = ()
    filament_wave: float = 5.0

    # --- swimming
    wavenumber: float = 5.0    # waves along the body; ~1 is one S-curve
    amp: float = 0.078         # tail amplitude / length
    amp_shape: float = 1.70    # how hard the amplitude is pushed to the tail

    # --- head
    gill_xi: float = 0.205
    gill_bow: float = 0.042    # how far back the gill cover bows on the flank
    jaw: tuple[float, float] = (0.072, -0.62)   # (ξ it reaches, ζ it sits at)

    # --- eye, one per flank
    eye_xi: float = 0.078
    eye_zeta: float = 0.34     # how far up the flank
    eye_r: float = 0.028       # radius / length

    # --- lateral line, one per flank
    line_zeta: float = 0.38    # above the widest point, as a real one is
    line_span: tuple[float, float] = (0.17, 0.80)

    # --- the accent
    glow_sharp: float = 14.0   # how tight the lit band is along the body
    glow_twist: float = 0.55   # how far the band leans out of the cross-section

    # --- how the strokes are weighted when drawn
    weights: dict[int, float] = field(default_factory=lambda: {
        MERIDIAN: 0.40, RING: 0.30, LINE: 0.95, CAUDAL: 0.66,
        MEDIAN: 0.55, PECTORAL: 0.46, EYE: 0.85, FILAMENT: 0.50, HEAD: 0.72,
    })
    # How strongly each part carries the accent.
    carries: dict[int, float] = field(default_factory=lambda: {
        MERIDIAN: 0.85, RING: 0.95, LINE: 1.00, CAUDAL: 0.75,
        MEDIAN: 0.75, PECTORAL: 0.60, EYE: 0.30, FILAMENT: 0.50, HEAD: 0.50,
    })


SARDINE = Species(
    name="sardine",
    # The animal that actually forms a bait ball. Slender — full depth about a
    # fifth of the length — deepest at 28%, a narrow wrist, and a fork sharp
    # enough to still read at 170 px on a phone.
    depth=0.098, beam=0.30, head=0.69, tail=1.90, taper=0.95,
    wrist=0.13, peduncle=0.84, belly=0.10,
    caudal_span=0.122, caudal_fork=0.56, caudal_lag=0.95, caudal_rays=9,
    dorsal=(0.31, 0.56, 0.078, 0.55),
    anal=(0.60, 0.745, 0.050, 0.45),
    pectoral=(0.29, 0.375, 0.056, 0.85),
    wavenumber=5.0, amp=0.078, amp_shape=1.70,
    gill_xi=0.205, gill_bow=0.042, jaw=(0.072, -0.62),
    eye_xi=0.078, eye_zeta=0.34, eye_r=0.028,
)


ABYSSAL = Species(
    name="abyssal",
    # Nothing near the surface is shaped like this: the depth peaks at 15% and
    # then runs away to almost nothing, so the animal is a heavy head dragging a
    # whip. Rounder in section than the sardine, because the head is a bulb. The
    # eye is far too large for it, which is the one thing every deep-sea fish
    # actually has in common, and a crest of dorsal rays stands over the head
    # instead of a fin running the body. It sculls on a long slow wave where the
    # sardine beats on a short one.
    depth=0.158, beam=0.52, head=0.40, tail=2.40, taper=0.95,
    wrist=0.045, peduncle=0.855, belly=0.20,
    meridians=27, rings=(0.14, 0.30, 0.52),
    caudal_span=0.050, caudal_fork=-0.92, caudal_lag=1.60, caudal_rays=7,
    dorsal=(0.10, 0.40, 0.115, 0.42),
    anal=(0.46, 0.68, 0.038, 0.40),
    pectoral=(0.19, 0.29, 0.092, 1.00),
    pectoral_zeta=-0.38,
    fin_rays=12,
    filaments=((0.995, 0.0, 0.40, 0.010), (0.985, 0.9, 0.30, 0.075),
               (0.985, -0.9, 0.26, -0.070), (0.26, 1.571, 0.46, 0.130),
               (0.34, 1.571, 0.38, 0.165)),
    filament_wave=3.2,
    wavenumber=3.0, amp=0.095, amp_shape=1.25, glow_twist=0.85,
    gill_xi=0.185, gill_bow=0.055, jaw=(0.090, -0.70),
    eye_xi=0.070, eye_zeta=0.28, eye_r=0.060,
    line_zeta=0.30, line_span=(0.15, 0.80),
)


SPECIES = {s.name: s for s in (SARDINE, ABYSSAL)}

RAY = 0.62          # how far a fin ray sits under the margin it fills
SPINE_NODES = 160   # resolution the arc-length integration runs at


def _reach(fork: float, zeta):
    """How far back the caudal fin's trailing edge sits, at height η.

    Positive `fork` pulls the middle in and leaves the lobe tips out — a fork.
    Negative pushes the middle out instead, which is a lanceolate point. The
    normalisation keeps the longest part of the fin at exactly 1 either way, so
    `caudal_span` and the fin's length stay independent of its shape.
    """
    raw = 1.0 - fork * (1.0 - np.abs(zeta))
    return raw / max(1.0, 1.0 + abs(fork)) if fork < 0 else raw


class Fish:
    """A net of dotted strokes over a body surface, posed by `pose(t)`.

    Built once; every frame is a pure function of the phase, so a caller can
    hold hundreds of these and pose them all in a handful of array operations.
    `density` scales every stroke's point count together, so the same animal can
    be drawn at 170 px in a crowd or at 900 px on its own.
    """

    def __init__(
        self,
        species: Species = SARDINE,
        length: float = 170.0,
        density: float = 1.0,
        rng: np.random.Generator | None = None,
        vary: float = 0.0,
        jitter: float = 0.0013,
    ) -> None:
        rng = np.random.default_rng(0) if rng is None else rng
        if vary:
            # A shoal of identical animals reads as a texture. Only proportions
            # move; the parts and their arrangement stay the species'. The
            # wavenumber deliberately does *not* vary: a piece whose whole claim
            # is one wave read at N delays cannot have N different waves, and
            # the data block would stop being true.
            def v(scale: float) -> float:
                return float(1.0 + vary * scale * rng.normal())
            species = replace(
                species,
                depth=species.depth * v(0.10),
                beam=species.beam * v(0.10),
                amp=species.amp * v(0.20),
                caudal_span=species.caudal_span * v(0.12),
            )
            length *= v(0.16)
        self.s = species
        self.length = length
        sp, p = species, species.peduncle

        xi: list[np.ndarray] = []
        zeta: list[np.ndarray] = []
        eta: list[np.ndarray] = []
        aux: list[np.ndarray] = []
        part: list[np.ndarray] = []
        wmul: list[np.ndarray] = []

        def add(x, k, *, z=0.0, e=0.0, a=0.0, w=1.0) -> None:
            x = np.asarray(x, dtype=float)
            b = lambda q: np.broadcast_to(np.asarray(q, dtype=float), x.shape).copy()
            xi.append(x); zeta.append(b(z)); eta.append(b(e)); aux.append(b(a))
            part.append(np.full(x.size, k)); wmul.append(np.full(x.size, w))

        # `density` means total points. Spending it half on how many strokes
        # there are and half on how finely each is drawn keeps the animal
        # readable when it shrinks: at 170 px in a crowd, twenty-three sparse
        # meridians read as scattered dots, while twelve well-drawn ones still
        # read as a body.
        span = float(np.sqrt(max(density, 1e-6)))

        def n_for(base: int) -> int:
            return max(3, int(round(base * span)))

        def strokes(base: int, floor: int) -> int:
            return max(floor, int(round(base * span)))

        # --- meridians. The dorsal and ventral ones are the profile, so they
        # carry more than the flank lines they enclose.
        trunk = np.linspace(0.0, 1.0, n_for(58)) * p
        for z in np.linspace(0.0, 2 * np.pi, strokes(sp.meridians, 9), endpoint=False):
            add(trunk, MERIDIAN, z=z, w=0.55 + 0.60 * abs(np.sin(z)))

        # --- rings. These make the eye read a tube rather than a set of nested
        # contours. Few and faint, and the meridians dense: the medusa's exact
        # proportion, and hers is the note about enough hoop to read as a built
        # thing without reading as a lampshade. Equal weight makes a wire grid.
        ring = np.linspace(0.0, 2 * np.pi, n_for(58), endpoint=False)
        for x0 in sp.rings[: strokes(len(sp.rings), 2)]:
            add(np.full(ring.size, x0 * p), RING, z=ring)

        # --- lateral line, one per flank
        l0, l1 = sp.line_span
        for z in (sp.line_zeta, np.pi - sp.line_zeta):
            add(np.linspace(l0, l1, n_for(48)), LINE, z=z)

        # --- caudal fin: rays fanning from the wrist, plus the trailing edge.
        # `aux` is how far along its own ray a point sits, `eta` which ray.
        for level in np.linspace(-1.0, 1.0, sp.caudal_rays):
            add(np.full(n_for(13), p), CAUDAL, e=level, w=RAY,
                a=np.linspace(0.0, _reach(sp.caudal_fork, level), n_for(13)))
        edge = np.linspace(-1.0, 1.0, n_for(34))
        add(np.full(edge.size, p), CAUDAL, e=edge, a=_reach(sp.caudal_fork, edge))

        # --- median fins: rays off the body edge, plus the outer margin. ζ = ±π/2
        # puts them in the median plane, where cos ζ = 0 and they have no width.
        for spec, z in ((sp.dorsal, np.pi / 2), (sp.anal, -np.pi / 2)):
            x0, x1, _, _ = spec
            for u in np.linspace(0.06, 0.94, sp.fin_rays):
                add(np.full(n_for(9), x0 + (x1 - x0) * u), MEDIAN, z=z, w=RAY,
                    a=np.linspace(0.0, 1.0, n_for(9)))
            margin = np.linspace(0.02, 0.98, n_for(26))
            add(x0 + (x1 - x0) * margin, MEDIAN, z=z, a=1.0)

        # --- pectorals, one per flank, now with somewhere to stick out to
        x0, x1, _, _ = sp.pectoral
        for z in (sp.pectoral_zeta, np.pi - sp.pectoral_zeta):
            for u in np.linspace(0.1, 0.9, 4):
                add(np.full(n_for(7), x0 + (x1 - x0) * u), PECTORAL, z=z, w=RAY,
                    a=np.linspace(0.0, 1.0, n_for(7)))
            add(x0 + (x1 - x0) * np.linspace(0.05, 0.95, n_for(14)),
                PECTORAL, z=z, a=1.0)

        # --- the operculum, bowing back on both flanks, and the jaw
        g = np.linspace(0.0, 2 * np.pi, n_for(34), endpoint=False)
        add(sp.gill_xi + sp.gill_bow * np.abs(np.cos(g)), HEAD, z=g)
        j_xi, j_zeta = sp.jaw
        for side in (1.0, -1.0):
            add(np.linspace(0.0, j_xi, n_for(14)), HEAD,
                z=side * np.linspace(0.0, j_zeta, n_for(14)))

        # --- an eye on each cheek. `aux` is the angle round the orbit.
        orbit = np.linspace(0.0, 2 * np.pi, n_for(22), endpoint=False)
        for z in (sp.eye_zeta, np.pi - sp.eye_zeta):
            add(np.full(orbit.size, sp.eye_xi), EYE, z=z, a=orbit)

        # --- threads. `aux` packs which thread (integer) and how far along it.
        for j, (a_xi, a_zeta, _, _) in enumerate(sp.filaments):
            # Stops a hair short of 1.0: `aux` packs the thread index in its
            # integer part, and an exact 1.0 would roll into the next one.
            r = np.linspace(0.0, 1.0 - 1e-9, n_for(30))
            add(np.full(r.size, a_xi), FILAMENT, z=a_zeta, a=r + j)

        self.xi = np.concatenate(xi)
        self.zeta = np.concatenate(zeta)
        self.eta = np.concatenate(eta)
        self.aux = np.concatenate(aux)
        self.part = np.concatenate(part).astype(np.int8)
        self.weight = np.array([sp.weights[k] for k in range(9)])[self.part]
        self.weight *= np.concatenate(wmul)
        self.carries = np.array([sp.carries[k] for k in range(9)])[self.part]
        # Threads fade along their length; one as bright as a meridian reads as
        # a scratch on the frame rather than as part of the animal.
        _f = self.part == FILAMENT
        self.weight[_f] *= 1.0 - 0.55 * (self.aux[_f] % 1.0)

        # Perfectly regular dotted lines read as a chart. The medusa carries the
        # same nudge for the same reason — and it has to stay well under the
        # spacing between points, or the strokes come apart into caterpillars.
        self._jit = rng.normal(0.0, jitter * length, (3, self.xi.size))

        self._nodes = np.linspace(0.0, 1.0, SPINE_NODES)
        self._step = length / (SPINE_NODES - 1)

    def __len__(self) -> int:
        return self.xi.size

    # ------------------------------------------------------------------ shape

    def half(self, xi: np.ndarray) -> np.ndarray:
        """Half-depth of the trunk at ξ, in pixels, peak-normalised to `depth`."""
        sp = self.s
        x = np.clip(np.asarray(xi, dtype=float) / sp.peduncle, 0.0, 1.0)
        shape = x ** sp.head * np.maximum(1.0 - sp.taper * x, 1e-9) ** sp.tail
        peak_x = sp.head / ((sp.head + sp.tail) * sp.taper)
        peak = peak_x ** sp.head * (1.0 - sp.taper * peak_x) ** sp.tail
        # The floor ramps in over the first few percent, so the wrist stays
        # finite while the snout still comes to a point.
        floor = sp.wrist * np.clip(x / 0.05, 0.0, 1.0)
        return sp.depth * self.length * ((1.0 - sp.wrist) * shape / peak + floor)

    def _vertical(self, xi: np.ndarray, s_zeta: np.ndarray) -> np.ndarray:
        """Height above the spine, with the belly running deeper than the back.

        A fish is not mirror-symmetric about its spine; drawing it that way is
        most of why a symmetric outline reads as a blimp rather than an animal.
        """
        sp = self.s
        deeper = 1.0 + sp.belly * np.sin(np.pi * np.clip(xi / sp.peduncle, 0.0, 1.0))
        return s_zeta * self.half(xi) * np.where(s_zeta < 0, deeper, 1.0)

    # ------------------------------------------------------------------- pose

    def pose(self, t: float, phase: float = 0.0) -> Pose:
        """The animal at wave phase `t`, in its own frame, in pixels."""
        sp, L, nodes = self.s, self.length, self._nodes

        ph_nodes = sp.wavenumber * nodes - t + phase
        amp = sp.amp * L * (0.12 + 0.88 * nodes ** sp.amp_shape)
        w = amp * np.sin(ph_nodes)

        # Arc-length-preserving spine: every step is exactly one step long, so
        # the animal flexes rather than stretching.
        dw = np.diff(w)
        sx = np.concatenate([[0.0], np.cumsum(np.sqrt(np.maximum(self._step ** 2 - dw ** 2, 0.0)))])
        ang = np.arctan2(np.gradient(w), np.gradient(sx))

        xi, zt, eta, aux = self.xi, self.zeta, self.eta, self.aux
        cx = np.interp(xi, nodes, sx)
        cy = np.interp(xi, nodes, w)
        ca = np.interp(xi, nodes, ang)
        tx, ty = np.cos(ca), np.sin(ca)      # tangent
        nx, ny = -np.sin(ca), np.cos(ca)     # normal, in the horizontal plane

        half = self.half(xi)
        s_z, c_z = np.sin(zt), np.cos(zt)
        along = np.zeros(xi.size)
        across = self._vertical(xi, s_z)
        lat = sp.beam * half * c_z
        nz = c_z.copy()

        # Median fins: a sheet standing off the body edge, swept backwards. ζ is
        # ±π/2 there, so cos ζ = 0 and the sheet has no width of its own.
        for spec, mask in ((sp.dorsal, (self.part == MEDIAN) & (s_z > 0)),
                           (sp.anal, (self.part == MEDIAN) & (s_z < 0))):
            if not mask.any():
                continue
            x0, x1, h, sweep = spec
            u = np.clip((xi[mask] - x0) / (x1 - x0), 0.0, 1.0)
            height = h * L * np.sin(np.pi * u) ** 0.8
            across[mask] = across[mask] + np.sign(s_z[mask]) * height * aux[mask]
            along[mask] = sweep * height * aux[mask]

        # Pectorals: a blade hinged on the flank, sweeping down, out and back.
        is_p = self.part == PECTORAL
        if is_p.any():
            x0, x1, h, sweep = sp.pectoral
            u = np.clip((xi[is_p] - x0) / (x1 - x0), 0.0, 1.0)
            height = h * L * np.sin(np.pi * u) ** 0.7
            reach = height * aux[is_p]
            across[is_p] = across[is_p] - 0.55 * reach
            lat[is_p] = lat[is_p] + 0.83 * reach * np.sign(c_z[is_p])
            along[is_p] = sweep * reach

        # The eye sits on the cheek, so its orbit is a circle in the plane of
        # the flank rather than one lying across the body.
        is_e = self.part == EYE
        if is_e.any():
            r = sp.eye_r * L
            along[is_e] = r * np.cos(aux[is_e])
            across[is_e] = across[is_e] + r * np.sin(aux[is_e])

        x = cx + tx * along + nx * across
        y = cy + ty * along + ny * across
        z = lat

        # Caudal fin, in its own frame: rigid on the wrist, pitched by the
        # spine's angle there plus a lag. Sampling it along the continuing
        # spine instead skews it into an asymmetric wedge. It stands in the
        # median plane, so it has no lateral extent.
        is_c = self.part == CAUDAL
        if is_c.any():
            p = sp.peduncle
            wx, wy = np.interp(p, nodes, sx), np.interp(p, nodes, w)
            wrist_d = float(self.half(np.array([p]))[0])
            wa = float(np.interp(p, nodes, ang)) - sp.caudal_lag * np.cos(
                sp.wavenumber * p - t + phase
            ) * 0.30
            a = aux[is_c]
            span = wrist_d + (sp.caudal_span * L - wrist_d) * a ** 0.7
            fx, fy = a * (1.0 - p) * L, eta[is_c] * span
            x[is_c] = wx + np.cos(wa) * fx - np.sin(wa) * fy
            y[is_c] = wy + np.sin(wa) * fx + np.cos(wa) * fy
            z[is_c] = 0.0
            nz[is_c] = 0.0

        # Threads, carried on past the body, each with its own wave.
        is_f = self.part == FILAMENT
        if is_f.any() and sp.filaments:
            thread = aux[is_f].astype(int)
            r = aux[is_f] - thread
            anchors = np.asarray(sp.filaments)
            a_xi, a_zeta = anchors[thread, 0], anchors[thread, 1]
            a_len, a_rise = anchors[thread, 2], anchors[thread, 3]
            swing = 0.10 * L * r ** 1.4 * np.sin(
                sp.filament_wave * r - t + phase + thread * 1.7
            )
            x[is_f] = np.interp(a_xi, nodes, sx) + a_len * L * r
            y[is_f] = (np.interp(a_xi, nodes, w)
                       + self._vertical(a_xi, np.sin(a_zeta))
                       + a_rise * L * r ** 1.25 + swing)
            z[is_f] = sp.beam * self.half(a_xi) * np.cos(a_zeta)

        x = x + self._jit[0]
        y = y + self._jit[1]
        z = z + self._jit[2]

        # The accent: a band that rises and falls with the phase rather than a
        # switch, so what travels head to tail is a lit ring around the whole
        # animal. `glow_sharp` is how tight that ring is.
        # Helical rather than square to the spine: a band exactly perpendicular
        # to the axis reads as a wipe bar crossing the animal. The medusa's bell
        # carries the same lean, for the same reason — the crest should sweep
        # rather than drop.
        lit = 0.5 * (1.0 + np.sin(
            sp.wavenumber * xi - t + phase + sp.glow_twist * np.sin(zt)
        ))
        glow = lit ** sp.glow_sharp * self.carries
        return Pose(x, y, z, nz, glow, self.weight, self.part)
