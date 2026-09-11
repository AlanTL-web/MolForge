from dataclasses import dataclass
from pathlib import Path
import csv
import math


def write_binding_energy_average(source_csv: Path, output_csv: Path) -> Path:
    """Average successful Uni-GBSA energy rows across frames by ligand and mode."""
    with source_csv.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames or []
        if "TOTAL" not in fieldnames:
            raise RuntimeError("Uni-GBSA results do not contain a TOTAL energy column.")
        identity_fields = [name for name in ("ligandName", "mode") if name in fieldnames]
        excluded = set(identity_fields) | {"Frames", "status"}
        energy_fields = [name for name in fieldnames if name not in excluded]
        grouped: dict[tuple[str, ...], list[dict[str, str]]] = {}
        for row in reader:
            if row.get("status", "S").strip().upper() != "S":
                continue
            try:
                for name in energy_fields:
                    if not math.isfinite(float(row[name])):
                        raise ValueError('Non-finite energy')
            except (KeyError, TypeError, ValueError):
                continue
            grouped.setdefault(tuple(row.get(name, "") for name in identity_fields), []).append(row)
    if not grouped:
        raise RuntimeError("Uni-GBSA results contain no successful numeric frames to average.")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    columns = identity_fields + ["Frames_used"] + energy_fields + ["status"]
    with output_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for identity, rows in grouped.items():
            result = dict(zip(identity_fields, identity))
            result["Frames_used"] = len(rows)
            result.update({name: sum(float(row[name]) for row in rows) / len(rows)
                           for name in energy_fields})
            result["status"] = "S"
            writer.writerow(result)
    return output_csv

@dataclass(frozen=True)
class UniGBSAMDParameters:
    """Validated MD options passed to ``unigbsa-pipeline`` by configuration."""

    protein_forcefield: str = "amber03"
    ligand_forcefield: str = "gaff2"
    box_type: str = "triclinic"
    box_distance_nm: float = 0.9
    salt_concentration_molar: float = 0.15
    steps: int = 5000000
    frames: int = 1000
    threads: int = 4
    keep_intermediates: bool = True
    nvt_steps: int = 250000
    npt_steps: int = 250000

    def validate(self) -> None:
        if self.ligand_forcefield not in {"gaff", "gaff2"}:
            raise ValueError("Uni-GBSA ligand force field must be gaff or gaff2.")
        if self.box_type not in {"triclinic", "cubic", "dodecahedron", "octahedron"}:
            raise ValueError("Select a supported GROMACS box type.")
        if self.box_distance_nm <= 0 or self.salt_concentration_molar < 0:
            raise ValueError("Box distance must be positive and salt concentration cannot be negative.")
        if any(type(value) is not int or value < 1 for value in
               (self.steps, self.frames, self.threads, self.nvt_steps, self.npt_steps)):
            raise ValueError("MD steps, saved frames, and threads must be positive integers.")

STANDARD_RESIDUE_HEAVY_ATOMS = {
    "ALA": "N CA C O CB", "ARG": "N CA C O CB CG CD NE CZ NH1 NH2",
    "ASN": "N CA C O CB CG OD1 ND2", "ASP": "N CA C O CB CG OD1 OD2",
    "CYS": "N CA C O CB SG", "GLN": "N CA C O CB CG CD OE1 NE2",
    "GLU": "N CA C O CB CG CD OE1 OE2", "GLY": "N CA C O",
    "HIS": "N CA C O CB CG ND1 CD2 CE1 NE2", "ILE": "N CA C O CB CG1 CG2 CD1",
    "LEU": "N CA C O CB CG CD1 CD2", "LYS": "N CA C O CB CG CD CE NZ",
    "MET": "N CA C O CB CG SD CE", "PHE": "N CA C O CB CG CD1 CD2 CE1 CE2 CZ",
    "PRO": "N CA C O CB CG CD", "SER": "N CA C O CB OG",
    "THR": "N CA C O CB OG1 CG2",
    "TRP": "N CA C O CB CG CD1 CD2 NE1 CE2 CE3 CZ2 CZ3 CH2",
    "TYR": "N CA C O CB CG CD1 CD2 CE1 CE2 CZ OH", "VAL": "N CA C O CB CG1 CG2",
}

UNIGBSA_DEFAULT_BINDING_PROFILE = {
    "sys_name": "GBSA", "modes": "gb", "igb": "2", "indi": "4.0", "exdi": "80.0",
}

STANDARD_RESIDUE_HEAVY_ATOMS = {
    name: set(atoms.split()) for name, atoms in STANDARD_RESIDUE_HEAVY_ATOMS.items()
}

def missing_standard_residue_heavy_atoms(protein: Path) -> list[str]:
    """Report incomplete standard amino acids before GROMACS pdb2gmx fails."""
    residues: dict[tuple[str, str, str], set[str]] = {}
    for line in protein.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("ATOM  ") or len(line) < 27:
            continue
        residue_name = line[17:20].strip().upper()
        if residue_name not in STANDARD_RESIDUE_HEAVY_ATOMS:
            continue
        key = (line[21].strip() or "_", line[22:26].strip() + line[26].strip(), residue_name)
        residues.setdefault(key, set()).add(line[12:16].strip().upper())
    missing = []
    for (chain, number, residue_name), atoms in residues.items():
        absent = sorted(STANDARD_RESIDUE_HEAVY_ATOMS[residue_name] - atoms)
        if absent:
            missing.append(f"{residue_name} {chain}:{number} (missing {', '.join(absent)})")
    return missing

def write_unigbsa_pipeline_config(path: Path, parameters: UniGBSAMDParameters) -> Path:
    """Write the simulation section consumed by unigbsa-pipeline."""
    parameters.validate()
    path.write_text(
        "[simulation]\n"
        "mode = md\n"
        f"boxtype = {parameters.box_type}\n"
        f"boxsize = {parameters.box_distance_nm}\n"
        f"conc = {parameters.salt_concentration_molar}\n"
        f"nsteps = {parameters.steps}\n"
        f"eqsteps = {parameters.nvt_steps}\n"
        f"; MolForge NVT steps = {parameters.nvt_steps}; NPT steps = {parameters.npt_steps}\n"
        f"nframe = {parameters.frames}\n"
        f"proteinforcefield = {parameters.protein_forcefield}\n"
        f"ligandforcefield = {parameters.ligand_forcefield}\n"
        "ligandCharge = bcc\n\n"
        "[GBSA]\n"
        "; Profile: Uni-GBSA default.ini; entropy correction is disabled by default\n"
        + "".join(f"{key} = {value}\n" for key, value in UNIGBSA_DEFAULT_BINDING_PROFILE.items()),
        encoding="utf-8",
    )
    return path

def locate_trajectory_outputs(output_dir: Path) -> dict[str, Path]:
    """Find the canonical outputs produced by current Uni-GBSA releases."""
    patterns = {
        "trajectory": ("traj_com.xtc", "protein_ligand_md.xtc", "md.xtc"),
        "topology": ("complex.pdb", "protein_ligand_final.pdb", "md.tpr"),
        "final_structure": ("complex.pdb", "protein_ligand_final.pdb", "md.gro"),
    }
    found: dict[str, Path] = {}
    for key, names in patterns.items():
        for name in names:
            match = next((path for path in output_dir.rglob(name) if path.is_file()), None)
            if match:
                found[key] = match
                break
    return found
