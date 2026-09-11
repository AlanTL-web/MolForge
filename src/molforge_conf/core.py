"""Core conformer-generation and MMFF-ranking workflow."""

from __future__ import annotations

import csv
import json
from contextlib import contextmanager
import math
from pathlib import Path
import shutil
import subprocess

from rdkit import Chem, rdBase
from rdkit.Chem import AllChem, rdMolDescriptors
from .sampling import sample, select_diverse


RANKING_FIELDS = (
    "Subset_rank",
    "Energy_rank",
    "Conformer_ID",
    "MMFF_energy_kcal_mol",
    "Delta_MMFF_energy_kcal_mol",
    "MMFF_converged",
    "Partial_charge_method",
    "Partial_charge_implementation",
)


@contextmanager
def _sdf_writer(path: Path, mol: Chem.Mol):
    """Create an SDF writer compatible with PyMOL's V2000 reader when possible."""
    # V2000 uses three-character atom and bond count fields and supports values
    # through 999. PyMOL releases that do not understand V3000 report its
    # placeholder ``0  0`` count line as "bad atom count", so only switch when
    # the molecule genuinely exceeds V2000's capacity.
    # Python opens Unicode paths correctly on Windows; RDKit's native filename
    # overload may interpret them using the system code page.
    with path.open('w', encoding='utf-8', newline='') as stream:
        with Chem.SDWriter(stream) as writer:
            if mol.GetNumAtoms() > 999 or mol.GetNumBonds() > 999:
                writer.SetForceV3000(True)
            yield writer


def _calculate_gasteiger_charges(mol: Chem.Mol) -> tuple[float, ...]:
    """Calculate one topology-based Gasteiger charge per atom."""
    try:
        AllChem.ComputeGasteigerCharges(mol, throwOnParamFailure=True)
    except Exception as exc:
        raise RuntimeError(f"Gasteiger partial-charge calculation failed: {exc}") from exc

    charges = []
    for atom in mol.GetAtoms():
        try:
            charge = float(atom.GetProp("_GasteigerCharge"))
        except (KeyError, ValueError) as exc:
            raise RuntimeError(
                f"Missing Gasteiger charge for atom index {atom.GetIdx()}."
            ) from exc
        if not math.isfinite(charge):
            raise RuntimeError(
                f"Non-finite Gasteiger charge for atom index {atom.GetIdx()}."
            )
        charges.append(charge)
    return tuple(charges)


def _make_record(
    mol: Chem.Mol,
    conf_id: int,
    energy_rank: int,
    status: int,
    energy: float,
    lowest_energy: float,
    charges: tuple[float, ...],
    *,
    subset_rank: int | None = None,
) -> Chem.Mol:
    record = Chem.Mol(mol)
    record.SetProp("_Name", f"conformer_{energy_rank}")
    record.SetProp("Conformer_ID", str(conf_id))
    record.SetProp("MMFF_energy", f"{energy:.6f}")
    record.SetProp("Delta_MMFF_energy", f"{energy - lowest_energy:.6f}")
    record.SetProp("MMFF_converged", str(status == 0))
    record.SetProp("MMFF_variant", "MMFF94s")
    record.SetProp("Embedding_method", "ETKDGv3")
    record.SetProp("Energy_comparison_scope", "Conformers of the same molecular species only")
    record.SetProp("Energy_rank", str(energy_rank))
    record.SetProp("Partial_charge_method", "Gasteiger")
    record.SetProp("Partial_charge_implementation", "RDKit")
    record.SetProp("Partial_charge_atom_order", "RDKit atom index, zero-based")
    record.SetProp(
        "Gasteiger_partial_charges",
        " ".join(f"{charge:.8f}" for charge in charges),
    )
    if subset_rank is not None:
        record.SetProp("Top_10_percent", "True")
        record.SetProp("Top_subset_rank", str(subset_rank))
    return record


def _write_sdf(
    path: Path,
    mol: Chem.Mol,
    rows: list[tuple[int, int, int, float]],
    lowest_energy: float,
    charges: tuple[float, ...],
    *,
    top_subset: bool,
) -> None:
    with _sdf_writer(path, mol) as writer:
        for subset_rank, (energy_rank, conf_id, status, energy) in enumerate(rows, start=1):
            record = _make_record(
                mol,
                conf_id,
                energy_rank,
                status,
                energy,
                lowest_energy,
                charges,
                subset_rank=subset_rank if top_subset else None,
            )
            writer.write(record, confId=conf_id)


def _write_ranking_csv(
    path: Path,
    rows: list[tuple[int, int, int, float]],
    lowest_energy: float,
    *,
    top_subset: bool,
) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=RANKING_FIELDS)
        writer.writeheader()
        for subset_rank, (energy_rank, conf_id, status, energy) in enumerate(rows, start=1):
            writer.writerow({
                "Subset_rank": subset_rank if top_subset else "",
                "Energy_rank": energy_rank,
                "Conformer_ID": conf_id,
                "MMFF_energy_kcal_mol": f"{energy:.6f}",
                "Delta_MMFF_energy_kcal_mol": f"{energy - lowest_energy:.6f}",
                "MMFF_converged": status == 0,
                "Partial_charge_method": "Gasteiger",
                "Partial_charge_implementation": "RDKit",
            })


def _write_multimodel_pdb(
    path: Path,
    mol: Chem.Mol,
    rows: list[tuple[int, int, int, float]],
    charges: tuple[float, ...],
) -> None:
    """Write top conformers as PDB MODEL records with charge REMARK records."""
    with path.open("w", newline="\n", encoding="ascii") as pdb_file:
        for model_number, (energy_rank, conf_id, status, energy) in enumerate(rows, start=1):
            pdb_file.write(f"MODEL     {model_number:4d}\n")
            pdb_file.write(
                "REMARK 900 ENERGY_RANK "
                f"{energy_rank} MMFF94S_KCAL_MOL {energy:.6f} "
                f"CONVERGED {status == 0}\n"
            )
            pdb_file.write("REMARK 950 PARTIAL_CHARGE_METHOD GASTEIGER\n")
            pdb_file.write("REMARK 950 PARTIAL_CHARGE_IMPLEMENTATION RDKIT\n")
            for atom_serial, charge in enumerate(charges, start=1):
                pdb_file.write(
                    f"REMARK 951 ATOM_SERIAL {atom_serial:5d} CHARGE {charge: .8f}\n"
                )

            pdb_block = Chem.MolToPDBBlock(mol, confId=conf_id)
            for line in pdb_block.splitlines():
                if line.startswith("MODEL") or line.startswith("ENDMDL") or line == "END":
                    continue
                pdb_file.write(f"{line}\n")
            pdb_file.write("ENDMDL\n")
        pdb_file.write("END\n")


def _convert_to_pdbqt(obabel_path: str, sdf_path: Path, pdbqt_path: Path) -> None:
    try:
        subprocess.run(
            [
                obabel_path,
                str(sdf_path),
                "-O",
                str(pdbqt_path),
                "--partialcharge",
                "gasteiger",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        details = exc.stderr.strip() or exc.stdout.strip() or "No details provided."
        raise RuntimeError(f"Open Babel PDBQT conversion failed: {details}") from exc
    if not pdbqt_path.is_file() or pdbqt_path.stat().st_size == 0:
        raise RuntimeError("Open Babel did not produce a non-empty PDBQT file.")


def _write_single_pdb(
    path: Path,
    mol: Chem.Mol,
    row: tuple[int, int, int, float],
    charges: tuple[float, ...],
    subset_rank: int,
) -> None:
    energy_rank, conf_id, status, energy = row
    with path.open("w", newline="\n", encoding="ascii") as pdb_file:
        pdb_file.write(f"REMARK 900 TOP_SUBSET_RANK {subset_rank}\n")
        pdb_file.write(
            "REMARK 900 ENERGY_RANK "
            f"{energy_rank} MMFF94S_KCAL_MOL {energy:.6f} "
            f"CONVERGED {status == 0}\n"
        )
        pdb_file.write("REMARK 950 PARTIAL_CHARGE_METHOD GASTEIGER\n")
        pdb_file.write("REMARK 950 PARTIAL_CHARGE_IMPLEMENTATION RDKIT\n")
        for atom_serial, charge in enumerate(charges, start=1):
            pdb_file.write(
                f"REMARK 951 ATOM_SERIAL {atom_serial:5d} CHARGE {charge: .8f}\n"
            )

        pdb_block = Chem.MolToPDBBlock(mol, confId=conf_id)
        for line in pdb_block.splitlines():
            if line.startswith("MODEL") or line.startswith("ENDMDL") or line == "END":
                continue
            pdb_file.write(f"{line}\n")
        pdb_file.write("END\n")


def _write_individual_top_conformers(
    folder: Path,
    mol: Chem.Mol,
    rows: list[tuple[int, int, int, float]],
    lowest_energy: float,
    charges: tuple[float, ...],
    obabel_path: str | None,
) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for existing_path in folder.iterdir():
        if (
            existing_path.is_file()
            and existing_path.name.startswith("subset_")
            and existing_path.suffix.lower() in {".sdf", ".pdb", ".pdbqt"}
        ):
            existing_path.unlink()

    for subset_rank, row in enumerate(rows, start=1):
        energy_rank, conf_id, status, energy = row
        file_stem = (
            f"subset_{subset_rank:03d}_energy_rank_{energy_rank:03d}_conf_{conf_id}"
        )
        sdf_path = folder / f"{file_stem}.sdf"
        pdb_path = folder / f"{file_stem}.pdb"

        record = _make_record(
            mol,
            conf_id,
            energy_rank,
            status,
            energy,
            lowest_energy,
            charges,
            subset_rank=subset_rank,
        )
        with _sdf_writer(sdf_path, record) as writer:
            writer.write(record, confId=conf_id)
        _write_single_pdb(pdb_path, mol, row, charges, subset_rank)

        if obabel_path is not None:
            _convert_to_pdbqt(obabel_path, sdf_path, folder / f"{file_stem}.pdbqt")


def _select_top_ten_percent(
    ranked_rows: list[tuple[int, int, int, float]],
) -> list[tuple[int, int, int, float]]:
    """Select ceil(10%) strictly by ascending MMFF energy."""
    top_count = max(1, math.ceil(len(ranked_rows) * 0.10))
    return ranked_rows[:top_count]


def generate_rank_conformers(
    smiles: str,
    num_confs: int,
    output_folder: str | Path,
    *,
    seed: int = -1,
    prune_rms_thresh: float = 0.5,
    max_iters: int = 5000,
    sampling_rounds: int = 3,
    embedding_attempts: int = 100,
    sampling_scheme: str = "Standard",
    threads: int = 4,
    write_pdbqt: bool = False,
    obabel_executable: str = "obabel",
) -> tuple[Path, Path, int, int]:
    """Generate, optimize, rank, and export general molecular conformers.

    The complete ensemble is written to ``conformers.sdf`` and
    ``conformer_ranking.csv``. The best ceil(10%) are also written separately to
    ``top_10_percent.sdf``, ``top_10_percent.pdb``, and a subset ranking CSV.
    Each selected conformer is also written separately under
    ``top_10_percent_conformers``.
    PDB partial charges are stored in REMARK records because standard PDB has no
    dedicated partial-charge field. Set ``write_pdbqt=True`` to additionally
    create full and top-subset PDBQT files with Open Babel.

    Returns ``(sdf_path, csv_path, retained_conformer_count, converged_count)``.
    """
    if type(threads) is not int or threads < 1:
        raise ValueError('threads must be a positive integer.')
    if not smiles.strip():
        raise ValueError("A SMILES string is required.")
    if num_confs < 1:
        raise ValueError("num_confs must be a positive integer.")
    if max_iters < 1:
        raise ValueError("max_iters must be a positive integer.")
    if type(sampling_rounds) is not int or not 1 <= sampling_rounds <= 10:
        raise ValueError("Sampling rounds must be an integer from 1 to 10.")
    if type(embedding_attempts) is not int or not 1 <= embedding_attempts <= 10000:
        raise ValueError("Embedding attempts must be an integer from 1 to 10000.")
    if sampling_scheme not in {"Standard", "High torsion"}:
        raise ValueError("Sampling scheme must be Standard or High torsion.")
    if not math.isfinite(prune_rms_thresh) or prune_rms_thresh < 0:
        raise ValueError("Pruning RMS threshold must be finite and non-negative.")

    output_folder = Path(output_folder)
    if not output_folder.is_dir():
        raise ValueError(f"Output folder does not exist: {output_folder}")

    obabel_path = None
    if write_pdbqt:
        obabel_path = shutil.which(obabel_executable)
        if obabel_path is None:
            raise RuntimeError(
                "PDBQT export requires Open Babel. Install it so that 'obabel' "
                "is on PATH, or pass obabel_executable with its full path."
            )

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError("Could not build a molecule from the supplied SMILES.")
    Chem.SanitizeMol(mol)
    if len(Chem.GetMolFrags(mol)) != 1:
        raise ValueError("Select one connected molecular species; separate counterions or mixtures explicitly.")
    mol_h = Chem.AddHs(mol)
    if not AllChem.MMFFHasAllMoleculeParams(mol_h):
        raise RuntimeError("MMFF parameters are unavailable; cannot optimize conformers.")

    rotatable_bonds = rdMolDescriptors.CalcNumRotatableBonds(mol, strict=True)
    high_torsion = sampling_scheme == "High torsion"
    effective_rounds = sampling_rounds
    effective_attempts = embedding_attempts
    effective_rms = prune_rms_thresh

    def report_progress(reports):
        (output_folder / 'sampling_progress.json').write_text(json.dumps({
            'completed_rounds': len(reports), 'requested_rounds': effective_rounds,
            'rounds': reports}, indent=2) + '\n', encoding='utf-8')
    mol_h, candidates, sampling_reports = sample(
        mol_h, num_confs, seed, effective_rms, max_iters, effective_rounds,
        effective_attempts, report_progress, random_coordinates_only=high_torsion, threads=threads)
    chosen, duplicates = select_diverse(mol_h, candidates, effective_rms, num_confs)
    (output_folder / "sampling_diagnostics.json").write_text(json.dumps({
        "rounds": sampling_reports, "candidate_count": len(candidates),
        "candidates": [{"id": identity, "status": status,
                        "energy": energy if math.isfinite(energy) else None}
                       for identity, status, energy in candidates],
        "retained": len(chosen), "duplicates_rejected_before_limit": duplicates,
    }, indent=2) + "\n", encoding="utf-8")
    if not chosen:
        raise RuntimeError("No converged conformers survived. Inspect sampling_diagnostics.json; increase sampling or optimization limits.")
    ranked_rows = [
        (energy_rank, conf_id, status, energy)
        for energy_rank, (conf_id, status, energy) in enumerate(chosen, start=1)
    ]
    top_rows = _select_top_ten_percent(ranked_rows)
    lowest_energy = ranked_rows[0][3]
    charges = _calculate_gasteiger_charges(mol_h)

    sdf_path = output_folder / "conformers.sdf"
    csv_path = output_folder / "conformer_ranking.csv"
    top_sdf_path = output_folder / "top_10_percent.sdf"
    top_csv_path = output_folder / "top_10_percent_ranking.csv"
    top_pdb_path = output_folder / "top_10_percent.pdb"

    _write_sdf(sdf_path, mol_h, ranked_rows, lowest_energy, charges, top_subset=False)
    _write_ranking_csv(csv_path, ranked_rows, lowest_energy, top_subset=False)
    _write_sdf(top_sdf_path, mol_h, top_rows, lowest_energy, charges, top_subset=True)
    _write_ranking_csv(top_csv_path, top_rows, lowest_energy, top_subset=True)
    _write_multimodel_pdb(top_pdb_path, mol_h, top_rows, charges)
    _write_individual_top_conformers(
        output_folder / "top_10_percent_conformers",
        mol_h,
        top_rows,
        lowest_energy,
        charges,
        obabel_path,
    )

    if write_pdbqt:
        _convert_to_pdbqt(
            obabel_path,
            sdf_path,
            output_folder / "conformers.pdbqt",
        )
        _convert_to_pdbqt(
            obabel_path,
            top_sdf_path,
            output_folder / "top_10_percent.pdbqt",
        )

    converged_count = sum(status == 0 for _, _, status, _ in ranked_rows)
    metadata = {
        "input_smiles": smiles,
        "canonical_isomeric_smiles": Chem.MolToSmiles(mol, isomericSmiles=True),
        "rdkit_version": rdBase.rdkitVersion,
        "embedding_method": "ETKDGv3",
        "embedding_parameters": sampling_reports[0]["embedding_parameters"],
        "resolved_embedding_parameters": sampling_reports[0]["resolved_embedding_parameters"],
        "sampling_scheme": sampling_scheme, "rotatable_bonds_strict": rotatable_bonds,
        "scheme_recommendation": "High torsion" if rotatable_bonds >= 25 else "Standard",
        "requested_sampling_rounds": sampling_rounds, "sampling_rounds": effective_rounds,
        "requested_embedding_attempts": embedding_attempts,
        "embedding_attempts": effective_attempts, "sampling_reports": sampling_reports,
        "candidate_count": len(candidates),
        "excluded_unconverged_or_invalid": sum(s != 0 or not math.isfinite(e) for _, s, e in candidates),
        "requested_rmsd_threshold": prune_rms_thresh,
        "post_optimization_rmsd_threshold": effective_rms,
        "diversity_symmetry_max_matches": 256,
        "mmff_variant": "MMFF94s", "mmff_max_iters": max_iters,
        "requested_conformers": num_confs, "retained_conformers": len(ranked_rows),
        "converged_conformers": converged_count,
        "energy_units": "kcal/mol",
        "energy_comparison_scope": "Conformers of the same molecular species only",
        "warnings": (["Some candidates failed convergence; excluded from ranked exports."]
                     if any(s != 0 or not math.isfinite(e) for _, s, e in candidates) else [])
                     + (["Fewer diverse converged conformers than requested were retained."] if len(chosen) < num_confs else [])
                     + ["Finite sampling does not establish global-minimum convergence."],
    }
    (output_folder / "conformer_protocol.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return sdf_path, csv_path, len(ranked_rows), converged_count
