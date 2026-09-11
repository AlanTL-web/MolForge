"""Conservative PDBFixer runner used by MolForge inside its WSL environment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from openmm.app import PDBFile
from pdbfixer import PDBFixer


def residue_label(residue) -> str:
    chain = residue.chain.id or "_"
    return f"{residue.name} {chain}:{residue.id}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_pdb", type=Path)
    parser.add_argument("output_pdb", type=Path)
    parser.add_argument("report_json", type=Path)
    args = parser.parse_args()

    fixer = PDBFixer(filename=str(args.input_pdb))
    fixer.findMissingResidues()
    ignored_missing_residues = [
        {"chain_index": chain, "insertion_index": index, "residues": names}
        for (chain, index), names in sorted(fixer.missingResidues.items())
    ]
    # Never invent absent backbone residues or loops automatically.
    fixer.missingResidues = {}
    fixer.findNonstandardResidues()
    nonstandard = [residue_label(residue) for residue, _replacement in fixer.nonstandardResidues]
    fixer.findMissingAtoms()
    added_heavy_atoms = {
        residue_label(residue): sorted(atom.name for atom in atoms)
        for residue, atoms in fixer.missingAtoms.items()
        if atoms
    }
    fixer.addMissingAtoms()
    fixer.addMissingHydrogens(7.0)

    args.output_pdb.parent.mkdir(parents=True, exist_ok=True)
    with args.output_pdb.open("w", encoding="utf-8") as handle:
        PDBFile.writeFile(fixer.topology, fixer.positions, handle, keepIds=True)
    report = {
        "input": str(args.input_pdb),
        "output": str(args.output_pdb),
        "ph": 7.0,
        "added_heavy_atoms": added_heavy_atoms,
        "ignored_missing_residues": ignored_missing_residues,
        "nonstandard_residues_left_unchanged": nonstandard,
        "original_preserved": True,
    }
    args.report_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
