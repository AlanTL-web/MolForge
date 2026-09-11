"""Local HDOCKlite runner for receptor-peptide PDB docking."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

from .job import create_job, write_manifest


def _input_pdb(path: Path, label: str) -> Path:
    candidate = path.expanduser().resolve()
    if not candidate.is_file():
        raise ValueError(f"{label} does not exist: {candidate}")
    if candidate.suffix.lower() != ".pdb":
        raise ValueError(f"HDOCK requires {label} in PDB format: {candidate}")
    if not any(line.startswith(("ATOM  ", "HETATM")) for line in candidate.read_text(encoding="utf-8", errors="replace").splitlines()):
        raise ValueError(f"{label} contains no ATOM or HETATM coordinates: {candidate}")
    return candidate


def _executable(value: str | Path, label: str) -> str:
    requested = str(value).strip()
    if not requested:
        raise ValueError(f"Configure the {label} executable under Settings.")
    path = Path(requested).expanduser()
    if path.is_file():
        return str(path.resolve())
    found = shutil.which(requested)
    if found:
        return found
    raise ValueError(f"{label} executable was not found: {requested}")


def inspect_ligand_pdb(path: Path) -> dict[str, object]:
    """Report whether a PDB looks residue-aware enough for HDOCK review."""
    ligand = _input_pdb(path, "Ligand")
    residues: set[tuple[str, str, str]] = set()
    atom_records = 0
    hetero_records = 0
    for line in ligand.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith(("ATOM  ", "HETATM")) or len(line) < 27:
            continue
        atom_records += 1
        hetero_records += int(line.startswith("HETATM"))
        residues.add((line[21].strip(), line[22:26].strip(), line[17:20].strip()))
    residue_names = sorted({item[2] for item in residues})
    generic_names = {"", "LIG", "MOL", "UNL", "UNK"}
    generic = bool(residue_names) and all(name in generic_names for name in residue_names)
    return {
        "atom_records": atom_records,
        "hetero_records": hetero_records,
        "residue_count": len(residues),
        "residue_names": residue_names,
        "generic_single_component": generic and len(residues) <= 1,
    }


def run(
    receptor_pdb: Path,
    ligand_pdb: Path,
    output_root: Path,
    *,
    hdock_executable: str | Path,
    createpl_executable: str | Path,
    job_name: str = "hdock",
    number_of_models: int = 100,
) -> Path:
    """Run HDOCKlite and create ranked receptor-ligand PDB models."""
    receptor = _input_pdb(receptor_pdb, "Receptor")
    ligand = _input_pdb(ligand_pdb, "Ligand")
    if number_of_models < 1:
        raise ValueError("The requested number of HDOCK models must be positive.")
    hdock_bin = _executable(hdock_executable, "HDOCK")
    createpl_bin = _executable(createpl_executable, "createpl")

    job_dir, stamp = create_job(output_root, job_name)
    outputs = job_dir / "outputs"
    outputs.mkdir()
    raw_output = outputs / "Hdock.out"
    models_output = outputs / "top_models.pdb"
    commands = [
        [hdock_bin, str(receptor), str(ligand), "-out", str(raw_output)],
        [createpl_bin, str(raw_output), str(models_output), "-nmax", str(number_of_models), "-complex", "-models"],
    ]
    (job_dir / "commands.json").write_text(json.dumps(commands, indent=2) + "\n", encoding="utf-8")

    log_parts: list[str] = []
    for command in commands:
        result = subprocess.run(command, cwd=outputs, capture_output=True, text=True)
        log_parts.extend(["$ " + subprocess.list2cmdline(command), result.stdout, result.stderr])
        if result.returncode:
            log_path = job_dir / "hdock.log"
            log_path.write_text("\n".join(log_parts), encoding="utf-8")
            (job_dir / "FAILED").write_text(f"HDOCK command failed with exit code {result.returncode}.\n", encoding="utf-8")
            raise RuntimeError(f"HDOCK failed with exit code {result.returncode}; see {log_path}")
    (job_dir / "hdock.log").write_text("\n".join(log_parts), encoding="utf-8")
    if not raw_output.is_file() or not models_output.is_file():
        raise RuntimeError(f"HDOCK completed without expected outputs; see {job_dir / 'hdock.log'}")

    ligand_report = inspect_ligand_pdb(ligand)
    write_manifest(
        job_dir,
        stamp,
        "hdock",
        {
            "receptor_pdb": str(receptor),
            "ligand_pdb": str(ligand),
            "number_of_models": number_of_models,
            "ligand_structure_report": ligand_report,
        },
        {"models": str(models_output), "generic_ligand_warning": ligand_report["generic_single_component"]},
        outputs,
    )
    return job_dir
