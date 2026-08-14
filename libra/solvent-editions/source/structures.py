#!/usr/bin/env python3
"""Backbone extraction from mmCIF, and cheap physical motion for it.

Two jobs. First, pull backbone traces out of a PDBx/mmCIF file without pulling
in a structural-biology stack: only the `atom_site` loop is read, streamed line
by line so a large deposition never has to be held in memory at once.

Second, give those traces motion. This is *not* molecular dynamics. It is an
anisotropic network model: every residue is a node, every pair of nodes within a
cutoff is joined by an identical spring, and the low-frequency eigenvectors of
that spring network are the collective motions the fold is softest along. The
method is Tirion 1996 / Bahar 1997, it is a standard way to get a protein's
breathing and hinge modes, and it costs one eigendecomposition rather than the
weeks of setup, equilibration and nanosecond-scale integration that an actual MD
trajectory would.

For assemblies of thousands of residues the network is built on a subsample and
the resulting displacements are interpolated back onto every atom. That is an
approximation, and the reason it is a fair one is that the modes being kept are
the slowest and most delocalised in the structure -- they vary smoothly over
tens of angstroms, so resolving them per-residue buys nothing visible.
"""

from __future__ import annotations

import math
import subprocess
import urllib.request
from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from scipy.spatial import cKDTree


CIF_DIR = Path(__file__).resolve().parents[2] / "data" / "cif"

# Backbone representative atoms: one per residue for protein, one per nucleotide.
BACKBONE_ATOMS = {"CA", "P"}


def fetch_cif(pdb_id: str, cif_dir: Path = CIF_DIR) -> Path:
    """Return a local mmCIF path, downloading from RCSB only if it is absent."""
    cif_dir.mkdir(parents=True, exist_ok=True)
    path = cif_dir / f"{pdb_id.lower()}.cif"
    if path.exists() and path.stat().st_size > 0:
        return path
    url = f"https://files.rcsb.org/download/{pdb_id.upper()}.cif"
    print(f"  downloading {url}", flush=True)
    with urllib.request.urlopen(url, timeout=180) as response, path.open("wb") as handle:
        while chunk := response.read(1 << 20):
            handle.write(chunk)
    return path


def load_backbone(path: Path) -> dict[str, np.ndarray]:
    """Read backbone atoms from the `atom_site` loop of an mmCIF file.

    Returns per-atom coordinates, an integer chain index, and a flag marking
    nucleic-acid atoms, plus the chain identifiers themselves. Only the first
    model is kept: NMR depositions carry many, and overlaying them would read as
    noise rather than as one structure.
    """
    columns: dict[str, int] = {}
    in_loop = False
    reading = False

    coordinates: list[tuple[float, float, float]] = []
    chain_names: list[str] = []
    chain_of_atom: list[int] = []
    nucleic: list[bool] = []
    chain_index: dict[str, int] = {}
    first_model: str | None = None

    with path.open("r", errors="replace") as handle:
        for line in handle:
            if line.startswith("loop_"):
                in_loop, columns, reading = True, {}, False
                continue
            if in_loop and line.startswith("_atom_site."):
                columns[line.strip().split(".", 1)[1]] = len(columns)
                continue
            if columns and not reading:
                if line.startswith("_") or line.startswith("#"):
                    columns, in_loop = {}, False
                    continue
                reading = True
            if not reading:
                continue
            if line.startswith("#") or line.startswith("loop_") or line.startswith("_"):
                if coordinates:
                    break
                columns, reading, in_loop = {}, False, False
                continue

            fields = line.split()
            if len(fields) < len(columns):
                continue
            if fields[columns["label_atom_id"]].strip('"') not in BACKBONE_ATOMS:
                continue

            model_column = columns.get("pdbx_PDB_model_num")
            if model_column is not None:
                model = fields[model_column]
                if first_model is None:
                    first_model = model
                elif model != first_model:
                    break

            try:
                position = (
                    float(fields[columns["Cartn_x"]]),
                    float(fields[columns["Cartn_y"]]),
                    float(fields[columns["Cartn_z"]]),
                )
            except ValueError:
                continue

            chain_column = columns.get("auth_asym_id", columns.get("label_asym_id"))
            chain = fields[chain_column]
            if chain not in chain_index:
                chain_index[chain] = len(chain_index)
                chain_names.append(chain)

            coordinates.append(position)
            chain_of_atom.append(chain_index[chain])
            nucleic.append(fields[columns["label_atom_id"]].strip('"') == "P")

    if not coordinates:
        raise RuntimeError(f"No backbone atoms found in {path}")
    return {
        "coordinates": np.asarray(coordinates, dtype=np.float32),
        "chain": np.asarray(chain_of_atom, dtype=np.int32),
        "nucleic": np.asarray(nucleic, dtype=bool),
        "chain_names": np.asarray(chain_names),
    }


def network_modes(
    coordinates: np.ndarray,
    node_limit: int = 1100,
    mode_count: int = 8,
    cutoff_neighbours: int = 24,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Low-frequency modes of an elastic network over the structure.

    Returns the node positions, the mode displacement vectors at those nodes,
    and the mode eigenvalues. The cutoff is set from the local node spacing
    rather than a fixed distance in angstroms, so a subsampled network stays
    connected regardless of how large the assembly is.
    """
    stride = max(1, math.ceil(len(coordinates) / node_limit))
    nodes = coordinates[::stride].astype(np.float64)
    count = len(nodes)

    tree = cKDTree(nodes)
    spacing = float(np.median(tree.query(nodes, k=2)[0][:, 1]))
    cutoff = spacing * math.sqrt(cutoff_neighbours)
    pairs = np.asarray(list(tree.query_pairs(cutoff)), dtype=np.int64)
    if len(pairs) == 0:
        raise RuntimeError("Elastic network has no contacts; cutoff too small.")

    hessian = np.zeros((3 * count, 3 * count), dtype=np.float64)
    offset = nodes[pairs[:, 1]] - nodes[pairs[:, 0]]
    distance = np.linalg.norm(offset, axis=1)
    # Springs soften with separation, which keeps a distant shell of contacts
    # from stiffening the network into a single rigid body.
    strength = 1.0 / np.maximum(distance, 1e-6) ** 2
    blocks = -strength[:, None, None] * (offset[:, :, None] * offset[:, None, :]) / (
        distance[:, None, None] ** 2
    )
    for (first, second), block in zip(pairs, blocks):
        rows, columns = slice(3 * first, 3 * first + 3), slice(3 * second, 3 * second + 3)
        hessian[rows, columns] += block
        hessian[columns, rows] += block
        hessian[rows, rows] -= block
        hessian[columns, columns] -= block

    values, vectors = eigh(hessian)
    # The first six eigenvalues are the rigid-body translations and rotations.
    keep = slice(6, 6 + mode_count)
    return nodes.astype(np.float32), vectors[:, keep].T.reshape(mode_count, count, 3).astype(
        np.float32
    ), values[keep].astype(np.float32)


def interpolate_modes(
    coordinates: np.ndarray, nodes: np.ndarray, modes: np.ndarray, neighbours: int = 4
) -> np.ndarray:
    """Carry node displacements out to every backbone atom, smoothly.

    Inverse-distance weighting over the nearest few nodes. The modes kept are
    the slowest ones, which vary over tens of angstroms, so this loses nothing
    that would be visible at the scale the structure is drawn.
    """
    tree = cKDTree(nodes)
    distance, index = tree.query(coordinates, k=min(neighbours, len(nodes)))
    if distance.ndim == 1:
        distance, index = distance[:, None], index[:, None]
    weight = 1.0 / np.maximum(distance, 1e-3)
    weight /= weight.sum(axis=1, keepdims=True)
    # modes[:, index, :] is (mode, atom, neighbour, component); collapse the
    # neighbour axis against its weights.
    return np.einsum("makc,ak->mac", modes[:, index, :], weight).astype(np.float32)


def trace_topology(
    coordinates: np.ndarray,
    chain: np.ndarray,
    target_length: float,
    max_gap: float = 8.0,
    limit: int = 48,
) -> tuple[np.ndarray, np.ndarray]:
    """Plan a smooth curve through the backbone.

    Returns the four control atoms each drawn sample is built from and how far
    along its span it sits. Splitting the plan from the coordinates is what
    makes the animation cheap: the topology is computed once, and each frame
    only indexes the displaced atoms and evaluates the spline.

    A straight polyline through α-carbons is visibly kinked -- successive
    residues turn by tens of degrees -- so this is a uniform cubic B-spline
    through them instead, which is what molecular viewers draw for a backbone
    trace. It costs one extra pair of gathers and turns wire mesh into ribbon.

    Atoms are joined only within a chain and only when close enough to be
    genuinely bonded, so unmodelled loops are not stitched across into lines
    that do not exist.
    """
    step = coordinates[1:] - coordinates[:-1]
    length = np.linalg.norm(step, axis=1)
    joined = (chain[:-1] == chain[1:]) & (length <= max_gap)
    index = np.nonzero(joined)[0]
    if index.size == 0:
        raise RuntimeError("No bonded backbone segments found.")

    # Control points reach one atom either side of the span. Where the run ends,
    # the outer control point is clamped to the endpoint so the curve stops
    # cleanly instead of bending towards an unrelated chain.
    has_previous = np.zeros_like(joined)
    has_previous[1:] = joined[:-1]
    has_next = np.zeros_like(joined)
    has_next[:-1] = joined[1:]
    before = np.where(has_previous[index], index - 1, index)
    after = np.where(has_next[index], index + 2, index + 1)

    counts = np.clip(np.ceil(length[index] / max(target_length, 1e-9)), 1, limit).astype(np.int64)
    total = int(counts.sum())
    segment = np.repeat(np.arange(counts.size, dtype=np.int64), counts)
    starts = np.zeros(counts.size + 1, dtype=np.int64)
    np.cumsum(counts, out=starts[1:])
    fraction = ((np.arange(total, dtype=np.int64) - starts[segment]) / counts[segment]).astype(
        np.float32
    )
    control = np.stack(
        (before[segment], index[segment], index[segment] + 1, after[segment])
    ).astype(np.int64)
    return control, fraction


def spline_weights(fraction: np.ndarray) -> np.ndarray:
    """Uniform cubic B-spline basis, as four weights per sample."""
    t = fraction.astype(np.float32)
    t2, t3 = t * t, t * t * t
    return np.stack((
        (1.0 - 3.0 * t + 3.0 * t2 - t3) / 6.0,
        (4.0 - 6.0 * t2 + 3.0 * t3) / 6.0,
        (1.0 + 3.0 * t + 3.0 * t2 - 3.0 * t3) / 6.0,
        t3 / 6.0,
    ))


def draw_traces(coordinates: np.ndarray, control: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Evaluate the planned spline on a given set of atom positions."""
    return np.einsum("ks,ksc->sc", weights, coordinates[control]).astype(np.float32)


def exposure(coordinates: np.ndarray, radius: float = 12.0) -> np.ndarray:
    """Per-atom solvent exposure, approximated by how few neighbours it has.

    Returns 0 for buried atoms and 1 for the most exposed. Surface residues are
    the ones a solvent bath rattles hardest, so this is what the thermal jitter
    is scaled by.
    """
    tree = cKDTree(coordinates)
    counts = np.asarray(tree.query_ball_point(coordinates, radius, return_length=True), dtype=np.float32)
    low, high = np.percentile(counts, (5, 95))
    packed = np.clip((counts - low) / max(high - low, 1e-9), 0.0, 1.0)
    return (1.0 - packed).astype(np.float32)
