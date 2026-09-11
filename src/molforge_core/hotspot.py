"""Receptor-hotspot parsing and docking-box center calculation."""

from __future__ import annotations

from pathlib import Path
import re


def parse_hotspot(text: str) -> set[tuple[str, int]]:
    """Parse comma-separated A:123, 123:A, and residue-range expressions."""
    selected: set[tuple[str, int]] = set()
    for raw in text.split(","):
        token = raw.strip().replace(" ", "")
        if not token:
            continue
        match = re.fullmatch(r"([A-Za-z0-9]):(-?\d+)(?:-(-?\d+))?", token)
        reverse = re.fullmatch(r"(-?\d+)(?:-(-?\d+))?:([A-Za-z0-9])", token)
        if match:
            chain, start_text, end_text = match.groups()
        elif reverse:
            start_text, end_text, chain = reverse.groups()
        else:
            raise ValueError(f"Invalid hotspot '{raw.strip()}'. Use A:195, A:203-206, or 195:A.")
        start = int(start_text)
        end = int(end_text) if end_text is not None else start
        if end < start:
            raise ValueError(f"Hotspot range must increase: {raw.strip()}")
        selected.update((chain, residue) for residue in range(start, end + 1))
    if not selected:
        raise ValueError("Enter at least one receptor hotspot residue.")
    return selected


def calculate_center(pdb_path: Path, hotspot: str) -> tuple[tuple[float, float, float], int, int]:
    """Return the heavy-atom centroid, matched atom count, and residue count."""
    path = pdb_path.expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".pdb":
        raise ValueError("Select an existing receptor PDB before calculating the hotspot center.")
    requested = parse_hotspot(hotspot)
    coordinates: list[tuple[float, float, float]] = []
    matched_residues: set[tuple[str, int]] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("ENDMDL"):
            break
        if not line.startswith(("ATOM  ", "HETATM")) or len(line) < 54:
            continue
        altloc = line[16].strip()
        if altloc not in ("", "A"):
            continue
        element = line[76:78].strip().upper() if len(line) >= 78 else ""
        atom_name = line[12:16].strip().upper()
        if element == "H" or (not element and atom_name.startswith("H")):
            continue
        try:
            residue = (line[21].strip() or "_", int(line[22:26]))
            xyz = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
        except ValueError:
            continue
        if residue in requested:
            coordinates.append(xyz)
            matched_residues.add(residue)
    missing = requested - matched_residues
    if missing:
        labels = ", ".join(f"{chain}:{number}" for chain, number in sorted(missing))
        raise ValueError(f"Hotspot residues were not found in the receptor PDB: {labels}")
    count = len(coordinates)
    center = tuple(sum(point[axis] for point in coordinates) / count for axis in range(3))
    return center, count, len(matched_residues)
