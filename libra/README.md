# LIBRA PDB annotations

This directory contains a local chain/domain index and a small renderer for
turning an RCSB PDB coordinate file into a publication-quality PNG.

## Data files

| File | Meaning |
| --- | --- |
| `data/chains.json` | Chain ID, Pfam domain names and lengths, and chain length. |
| `data/chains.tsv` | Flat list of chain IDs. |
| `data/chains_info.tsv` | Experimental method, resolution, R factor, and free R factor. |
| `data/structure_chains_map.tsv` | PDB structure ID to all chain IDs in that structure. |
| `data/identity_map.txt` | Groups of equivalent or normalized chain IDs. |
| `data/cif/*.cif` | Local PDBx/mmCIF inputs for structures too large for legacy PDB. |

`chains.json` describes annotated chains, while a downloaded coordinate file
may contain additional chains without a Pfam annotation. For example, 7EKO has
8 annotated chains in this snapshot and 15 coordinate chains in its legacy PDB
file.

## Select, download, and plot

```bash
python libra/source/download_and_plot_pdb.py
```

Without arguments, the script ranks each structure by:

```text
annotated chain count / unique Pfam domain count
```

Ties are resolved by annotated chain count and then PDB ID. In this dataset the
selected structure is **7EKO**: 8 annotated chains, 1 unique Pfam domain, ratio
8. The script downloads the official file from
`https://files.rcsb.org/download/7EKO.pdb` and writes:

```text
renders/
├── pdb/7eko.pdb
└── png/7eko_ca-traces.png
```

To use an explicit ID:

```bash
python libra/source/download_and_plot_pdb.py --pdb-id 4b2t
```

The classic `.pdb` format cannot represent every very large modern structure.
If RCSB only provides PDBx/mmCIF for an ID, the script reports that limitation
instead of silently downloading a different format.

## High-quality mmCIF rendering with ChimeraX

For large assemblies, mmCIF is the preferred source. It preserves unrestricted,
multi-character chain identifiers, complete assembly and entity metadata, and
the same deposited atomic coordinates without forcing them into legacy PDB
columns. It does not automatically add experimental density or atoms that were
never modeled; those remain separate deposition files.

The included 8CKB model is an electron-microscopy reconstruction of the
crAss001 virion: a 1,445-chain author-defined assembly with 492,428 modeled
polymer residues. Render it from the repository root with:

```bash
chimerax --offscreen libra/source/render_8ckb.cxc
```

The command file uses a cartoon representation, chain-aware colors, soft
lighting, depth, and silhouettes. It writes:

```text
renders/png/8ckb_virion-cartoon.png
```

The 429 MB source CIF stays local under `data/cif/`; generated scripts and PNGs
remain small enough for normal Git hosting.

## Solvent editions

[`solvent-editions/`](solvent-editions/) selects three structures from this
index by architecture rather than by ratio — a clathrin cage, a chaperonin
barrel, a rotary ATP synthase — and renders each as a glowing backbone trace set
moving with an elastic-network model of its own low-frequency motion, in the
same house style as [`../generative-science-art/`](../generative-science-art/).
See its README for the method and what it does and does not claim to simulate.
