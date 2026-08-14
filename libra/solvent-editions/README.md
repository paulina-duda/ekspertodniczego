# Solvent Editions

Three deposited protein assemblies, breathing in solvent, rendered in the same
house style as the attractor pieces in
[`generative-science-art/trace-editions/`](../../generative-science-art/trace-editions/).

| Edition | Structure | Palette |
| --- | --- | --- |
| `clathrin_1xi4_orchid-gold` | 1XI4 — clathrin coat, 216 chains | orchid gold |
| `chaperonin_4b2t_ember-spectrum` | 4B2T — TRiC/CCT chaperonin, 8-fold double ring | ember → spectrum |
| `atp-synthase_6vq6_electric-citrus` | 6VQ6 — F₁F₀ ATP synthase | electric citrus |

## Why these three

The rendering draws backbone traces, and that only works when a structure has
architecture to show. Ribosome 4V6W and photosystem 6LY5 were both rendered and
rejected: at this scale they resolve as hairballs, because an asymmetric mass of
short kinked chains has no legible form. Phage capsid 8H2I was rejected for a
different reason — its deposited assembly carries a tail reaching 1251 Å from a
body of radius 320 Å, which drags the centre off the capsid and shrinks it.

What survives is structures with real symmetry or real machinery: a woven cage,
a ringed barrel, a stalked rotor. Three different architectures, so the set does
not repeat itself.

## Continuity with the mathematics posts

Everything about the look is carried over unchanged: black field, additive
splatting into a float buffer, multi-scale bloom, log-density tone mapping,
spaced title, monospace caption, one 360° turn, and a cover frame of the
finished object for the grid. The palettes are the same three ramps.

The one thing that had to be re-derived is what the colour *means*. In the
attractor pieces it was speed. Here it is how far each residue moves — its
amplitude across the low-frequency modes of an elastic network over the fold.
Both are intrinsic to the object and independent of the camera, which is what
lets the two sets read as one body of work rather than two.

Two details that mattered more than expected:

**A straight α-carbon polyline is visibly kinked**, because successive residues
turn by tens of degrees. Drawing a uniform cubic B-spline through them instead —
which is what molecular viewers do for a backbone trace — is what turns wire
mesh into ribbon and matches the attractor traces.

**Mobility is strongly skewed**: most of a fold is rigid, so a linear ramp
crowds all but the floppiest residues into one end of the palette. Ranking the
residues instead spreads the full palette across them, and what it reveals is
real — on the chaperonin the apical domains light up, and mobility correlates
with distance along the symmetry axis at 0.83.

## The motion, and what it is not

**It is not molecular dynamics.** No force field, no water box, no integrator,
no trajectory. If it were, this would be the GROMACS project you remember: build
topology, solvate, add ions, minimise, equilibrate in two ensembles, then run
production long enough for anything to happen — days of setup and a lot of
compute, for a result that at nanosecond scale would look like fuzz anyway.

What this does instead is an **anisotropic network model**. Every residue is a
node, every pair within a cutoff gets an identical spring, and the low-frequency
eigenvectors of that network are the directions the fold is softest along. It is
a standard method (Tirion 1996, Bahar 1997) for exactly this question, and it
costs **one eigendecomposition — about a second**, against days for MD.

Those modes are then driven as standing waves at whole-number frequencies, with
a thermal rattle added on the solvent-exposed residues, scaled by how few
neighbours each has. Measured on the chaperonin: 2.0 Å RMS displacement, 11 Å at
the most mobile residues, and displacement correlates with solvent exposure at
0.29.

Because every frequency is a whole number of cycles per clip, **the pose at the
end is exactly the pose at the start** — verified to 0.00 Å — so unlike the
emergence pieces these loop seamlessly.

For assemblies of hundreds of thousands of atoms the network is built on a
subsample and the displacements interpolated back onto every atom. The modes
being kept are the slowest and most delocalised in the structure, varying
smoothly over tens of ångströms, so resolving them per-residue would buy nothing
visible.

## Layout

```text
solvent-editions/
├── README.md
├── source/
│   ├── glow.py             # unchanged from the attractor editions
│   ├── structures.py       # mmCIF backbone reader, elastic network, spline traces
│   └── render_proteins.py  # orientation, motion, export
└── instagram/phone-9x16/   # 1080×1920 H.264 exports and cover stills
```

Coordinate files are fetched from RCSB on demand into `../data/cif/` and are not
committed; they range from 5 MB to 245 MB.

## Run

```bash
python3 libra/solvent-editions/source/render_proteins.py
```

One edition, or a fast preview (dimensions must be even — H.264 chroma
subsampling):

```bash
python3 libra/solvent-editions/source/render_proteins.py --edition clathrin
```

```bash
python3 libra/solvent-editions/source/render_proteins.py --width 300 --height 532 --duration 2 --fps 10 --nodes 400
```

Exports are `1080 × 1920`, 8 s, 30 fps, H.264, no audio.

Layout follows the attractor editions: a 64 px inset for the title and caption,
and the structure on the frame's centre line with a modest band of black around
it. `--margin` moves the text, `fill` in each edition's entry sets how much of
the frame the structure takes.

Insetting the text far enough to clear the Reel player's chrome was tried and
abandoned. It works — nothing is covered — but it pushes the title a fifth of
the way down the frame, shrinks the tallest piece from 5.7 to 3.9 px/Å, and
leaves so much empty black that the composition falls apart. The overlay is only
there while the clip plays in the app; the composition is there always.

Requirements beyond the attractor projects: `scipy`, for the eigendecomposition
and the neighbour searches. No structural-biology stack — the mmCIF reader is
about eighty lines and only looks at the `atom_site` loop.
