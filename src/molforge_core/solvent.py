"""Shared residue-based exclusions for display/export, never simulation inputs."""
from pathlib import Path

# Includes common GROMACS, Amber, CHARMM and PDB water/ion residue names.
# Match residue names, not atom names: protein CA (C-alpha) must remain intact.
WATER_RESIDUES = frozenset({
    "SOL", "HOH", "WAT", "H2O", "DOD", "D2O", "OH2", "TIP", "TIP3", "TIP4",
    "TIP5", "TIP3P", "TIP4P", "TIP5P", "SPC", "SPCE", "T3P", "T4P", "T5P",
})
ION_RESIDUES = frozenset({
    "NA", "NA+", "SOD", "CL", "CL-", "CLA", "K", "K+", "POT", "LI", "LI+",
    "RB", "RB+", "CS", "CS+", "F", "F-", "BR", "BR-", "IOD", "I", "I-",
    "CA", "CA2", "CA2+", "CAL", "MG", "MG2", "MG2+", "ZN", "ZN2", "ZN2+",
    "MN", "MN2", "FE", "FE2", "FE3", "CU", "CU1", "CU2", "CO", "CO2",
    "NI", "NI2", "CD", "CD2", "SR", "BA", "AL", "AG", "AU", "HG", "PB",
    "CES", "CLA-", "SOD+", "NH4", "SO4", "PO4", "NO3",
})
HIDDEN_RESIDUES = WATER_RESIDUES | ION_RESIDUES


def is_solvent_or_ion(residue: str) -> bool:
    return residue.strip().upper() in HIDDEN_RESIDUES


def pdb_residue(line: str) -> str:
    # GROMACS also emits four-character water names (e.g. TIP3) in 17:21.
    return line[17:21].strip().upper()


def filter_pdb_solvent(source: Path, destination: Path) -> dict:
    """Stream all frames to a solute-only PDB, preserving coordinates and serials.

    CONECT records retain only links between exported atoms; obsolete MASTER
    counts are omitted. An empty solute raises instead of producing an animation
    containing only solvent. Source and destination must be different files.
    """
    if source.resolve() == destination.resolve():
        raise ValueError("Filter into a separate file to preserve the source trajectory.")
    kept = removed = frames = 0
    residues: set[str] = set()
    serials: set[str] = set()
    with source.open(encoding="ascii", errors="replace") as incoming, destination.open("w", encoding="ascii") as outgoing:
        for line in incoming:
            record = line[:6].strip()
            if record == "MODEL":
                frames += 1
                serials.clear()
            if record in {"ATOM", "HETATM"}:
                residue = pdb_residue(line)
                if is_solvent_or_ion(residue):
                    removed += 1
                    residues.add(residue)
                    continue
                kept += 1
                serials.add(line[6:11].strip())
            elif record in {"ANISOU", "TER"}:
                if is_solvent_or_ion(pdb_residue(line)):
                    continue
            elif record == "CONECT":
                fields = [line[i:i + 5].strip() for i in range(6, len(line.rstrip()), 5)]
                if not fields or fields[0] not in serials:
                    continue
                bonded = [serial for serial in fields[1:] if serial in serials]
                if not bonded:
                    continue
                line = "CONECT" + "".join(f"{serial:>5}" for serial in [fields[0], *bonded]) + "\n"
            elif record == "MASTER":
                continue
            outgoing.write(line)
    if not kept:
        raise ValueError("No protein/ligand atoms remain after hiding water and salt ions.")
    return {"frames": frames or 1, "retained_atom_records": kept,
            "removed_atom_records": removed, "excluded_residues_present": sorted(residues)}
