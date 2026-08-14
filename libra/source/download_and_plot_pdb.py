#!/usr/bin/env python3
"""Select, download, and render a PDB structure from the LIBRA annotations."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/libra-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/libra-cache")


RCSB_PDB_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"


@dataclass(frozen=True)
class StructureStats:
    pdb_id: str
    chain_ids: tuple[str, ...]
    domains: tuple[str, ...]

    @property
    def chain_count(self) -> int:
        return len(self.chain_ids)

    @property
    def domain_count(self) -> int:
        return len(self.domains)

    @property
    def chains_per_domain(self) -> float:
        return self.chain_count / self.domain_count


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).parents[1]
    parser = argparse.ArgumentParser(
        description=(
            "Download and plot a requested PDB ID, or automatically select the "
            "LIBRA structure with the most annotated chains per unique Pfam domain."
        )
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        default=project_root / "data" / "chains.json",
    )
    parser.add_argument(
        "--pdb-id",
        help="Optional four-character PDB ID; omit to use the LIBRA ranking.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "renders",
    )
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--dpi", type=int, default=220)
    return parser.parse_args()


def load_structure_stats(path: Path) -> dict[str, StructureStats]:
    records = json.loads(path.read_text(encoding="utf-8"))
    chains: dict[str, set[str]] = defaultdict(set)
    domains: dict[str, set[str]] = defaultdict(set)

    for record in records:
        chain_id = record["chain_id"]
        pdb_id, separator, _ = chain_id.partition("_")
        if not separator or len(pdb_id) != 4:
            continue
        pdb_id = pdb_id.lower()
        chains[pdb_id].add(chain_id)
        domains[pdb_id].update(name for name in record["domain_names"] if name)

    return {
        pdb_id: StructureStats(
            pdb_id=pdb_id,
            chain_ids=tuple(sorted(chain_ids)),
            domains=tuple(sorted(domains[pdb_id])),
        )
        for pdb_id, chain_ids in chains.items()
        if domains[pdb_id]
    }


def select_top_structure(stats: dict[str, StructureStats]) -> StructureStats:
    """Use ratio, chain count, and newest-looking PDB ID as deterministic keys."""
    return max(
        stats.values(),
        key=lambda item: (
            item.chains_per_domain,
            item.chain_count,
            item.pdb_id,
        ),
    )


def download_pdb(pdb_id: str, destination: Path, force: bool = False) -> Path:
    if destination.exists() and not force:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    url = RCSB_PDB_URL.format(pdb_id=pdb_id.upper())
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "libra-pdb-renderer/1.0 (+https://www.rcsb.org/)"},
    )
    temporary = destination.with_suffix(".pdb.part")
    try:
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open(
            "wb"
        ) as output:
            shutil.copyfileobj(response, output)
    except urllib.error.HTTPError as exc:
        temporary.unlink(missing_ok=True)
        if exc.code == 404:
            raise RuntimeError(
                f"RCSB does not provide {pdb_id.upper()} in legacy .pdb format; "
                "large structures may only be available as PDBx/mmCIF."
            ) from exc
        raise

    if temporary.stat().st_size < 100 or not any(
        line.startswith(("ATOM  ", "HETATM"))
        for line in temporary.read_text(encoding="ascii", errors="replace").splitlines()
    ):
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded file for {pdb_id.upper()} is not a valid PDB file.")
    temporary.replace(destination)
    return destination


def parse_ca_traces(path: Path) -> dict[str, list[tuple[int, tuple[float, float, float]]]]:
    traces: dict[str, list[tuple[int, tuple[float, float, float]]]] = defaultdict(list)
    seen: set[tuple[str, str, str]] = set()

    with path.open(encoding="ascii", errors="replace") as handle:
        for line in handle:
            if line.startswith("ENDMDL"):
                break
            if not line.startswith("ATOM  ") or line[12:16].strip() != "CA":
                continue
            alternate = line[16]
            if alternate not in (" ", "A"):
                continue
            chain_id = line[21].strip() or "_"
            residue_number = line[22:26].strip()
            insertion_code = line[26].strip()
            key = (chain_id, residue_number, insertion_code)
            if key in seen:
                continue
            seen.add(key)
            try:
                coordinates = (
                    float(line[30:38]),
                    float(line[38:46]),
                    float(line[46:54]),
                )
                sequence_number = int(residue_number)
            except ValueError:
                continue
            traces[chain_id].append((sequence_number, coordinates))

    if not traces:
        raise RuntimeError(f"No C-alpha atoms found in {path}.")
    return dict(sorted(traces.items()))


def split_trace(
    residues: list[tuple[int, tuple[float, float, float]]],
) -> list[list[tuple[float, float, float]]]:
    """Break lines at missing residues or implausibly long C-alpha distances."""
    import numpy as np

    segments: list[list[tuple[float, float, float]]] = []
    current: list[tuple[float, float, float]] = []
    previous_number: int | None = None
    previous_coordinates: tuple[float, float, float] | None = None
    for residue_number, coordinates in residues:
        should_break = previous_number is not None and (
            residue_number - previous_number > 1
            or np.linalg.norm(np.subtract(coordinates, previous_coordinates)) > 4.5
        )
        if should_break and current:
            segments.append(current)
            current = []
        current.append(coordinates)
        previous_number = residue_number
        previous_coordinates = coordinates
    if current:
        segments.append(current)
    return segments


def render_structure(
    pdb_path: Path,
    output_path: Path,
    stats: StructureStats | None,
    dpi: int,
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    traces = parse_ca_traces(pdb_path)
    colors = plt.get_cmap("turbo")(np.linspace(0.03, 0.97, len(traces)))
    figure = plt.figure(figsize=(8, 8), facecolor="#05070c")
    axis = figure.add_subplot(111, projection="3d", facecolor="#05070c")

    all_coordinates: list[tuple[float, float, float]] = []
    for (chain_id, residues), color in zip(traces.items(), colors, strict=True):
        first = True
        for segment in split_trace(residues):
            if len(segment) < 2:
                continue
            xyz = np.asarray(segment)
            all_coordinates.extend(segment)
            axis.plot(
                xyz[:, 0],
                xyz[:, 1],
                xyz[:, 2],
                color=color,
                linewidth=2.2,
                alpha=0.92,
                label=f"chain {chain_id}" if first else None,
            )
            first = False

    coordinates = np.asarray(all_coordinates)
    spans = np.ptp(coordinates, axis=0)
    centers = np.mean(coordinates, axis=0)
    radius = max(spans) * 0.54
    axis.set_xlim(centers[0] - radius, centers[0] + radius)
    axis.set_ylim(centers[1] - radius, centers[1] + radius)
    axis.set_zlim(centers[2] - radius, centers[2] + radius)
    axis.set_box_aspect((1, 1, 1))
    axis.view_init(elev=20, azim=132)
    axis.set_axis_off()

    pdb_id = pdb_path.stem.upper()
    if stats:
        subtitle = (
            f"{stats.chain_count} annotated chains · {stats.domain_count} unique Pfam "
            f"domain · ratio {stats.chains_per_domain:g}"
        )
    else:
        subtitle = f"{len(traces)} coordinate chains"
    figure.text(0.05, 0.94, pdb_id, color="white", fontsize=26, weight="bold")
    figure.text(0.05, 0.905, subtitle, color="#aeb8cc", fontsize=10)
    figure.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 0.025),
        ncol=min(8, len(traces)),
        frameon=False,
        labelcolor="white",
        fontsize=8,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=dpi, facecolor=figure.get_facecolor())
    plt.close(figure)
    return output_path


def main() -> None:
    args = parse_args()
    all_stats = load_structure_stats(args.annotations)

    if args.pdb_id:
        pdb_id = args.pdb_id.lower()
        if len(pdb_id) != 4 or not pdb_id.isalnum():
            raise SystemExit("--pdb-id must be a four-character alphanumeric PDB ID")
        selected = all_stats.get(pdb_id)
    else:
        selected = select_top_structure(all_stats)
        pdb_id = selected.pdb_id

    pdb_path = download_pdb(
        pdb_id,
        args.output_dir / "pdb" / f"{pdb_id}.pdb",
        force=args.force_download,
    )
    png_path = render_structure(
        pdb_path,
        args.output_dir / "png" / f"{pdb_id}_ca-traces.png",
        selected,
        args.dpi,
    )
    if selected:
        print(
            f"Selected {pdb_id.upper()}: {selected.chain_count} annotated chains, "
            f"{selected.domain_count} unique domains, "
            f"{selected.chains_per_domain:g} chains/domain."
        )
    print(f"PDB: {pdb_path}")
    print(f"PNG: {png_path}")


if __name__ == "__main__":
    main()
