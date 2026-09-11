"""Validate conformer smoke-test jobs produced by the public Linux CLI."""
import argparse
import csv
import json
import math
from pathlib import Path

from rdkit import Chem


def validate(folder: Path, smiles: str) -> dict:
    status = json.loads((folder / 'status.json').read_text(encoding='utf-8'))
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    protocol = json.loads((folder / 'outputs' / 'conformer_protocol.json').read_text(encoding='utf-8'))
    molecules = list(Chem.SDMolSupplier(str(folder / 'outputs' / 'conformers.sdf'), removeHs=False))
    expected = Chem.MolToSmiles(Chem.MolFromSmiles(smiles), isomericSmiles=True)
    identities = [Chem.MolToSmiles(Chem.RemoveHs(mol), isomericSmiles=True)
                  for mol in molecules if mol is not None]
    with (folder / 'outputs' / 'conformer_ranking.csv').open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    energies = [float(row['MMFF_energy_kcal_mol']) for row in rows]
    checks = {
        'status_completed': status.get('status') == 'completed',
        'manifest_completed': manifest.get('status') == 'completed',
        'all_sdf_records_readable': len(identities) == len(molecules) > 0,
        'molecular_identity_preserved': identities == [expected] * len(identities),
        'all_energies_finite': bool(energies) and all(math.isfinite(value) for value in energies),
        'energies_sorted': energies == sorted(energies),
        'all_retained_conformers_converged': all(row['MMFF_converged'] == 'True' for row in rows),
    }
    if not all(checks.values()):
        raise RuntimeError(f'Smoke validation failed for {folder}: {checks}')
    return {'job': str(folder.resolve()), 'smiles': smiles, 'canonical_smiles': expected,
            'retained_conformers': len(molecules), 'best_energy_kcal_mol': min(energies),
            'rdkit_version': protocol['rdkit_version'], 'checks': checks}


def main():
    parser = argparse.ArgumentParser(description='Validate two MolForge conformer smoke jobs.')
    parser.add_argument('ethanol_job', type=Path)
    parser.add_argument('acetic_acid_job', type=Path)
    args = parser.parse_args()
    print(json.dumps([
        validate(args.ethanol_job, 'CCO'),
        validate(args.acetic_acid_job, 'CC(=O)O'),
    ], indent=2))


if __name__ == '__main__':
    main()
