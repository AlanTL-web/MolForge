"""Independent native AutoDock-GPU orchestration fork."""

from __future__ import annotations

from dataclasses import dataclass
import csv
import json
import math
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import time

from .job import create_job, descriptive_job_name, write_manifest


@dataclass(frozen=True)
class DockingParameters:
    center: tuple[float, float, float]
    size: tuple[float, float, float]
    nrun: int = 200
    heuristic_max_evaluations: int = 12_000_000
    seed: int | None = None
    rigid_macrocycle: bool = False
    auto_reduce_torsions: bool = False
    max_ligand_torsions: int = 48
    allow_bad_receptor_residues: bool = False
    choose_highest_occupancy_altloc: bool = False

    def validate(self) -> None:
        if self.nrun < 1:
            raise ValueError("AutoDock-GPU run count must be positive.")
        if self.heuristic_max_evaluations < 1:
            raise ValueError("AutoDock-GPU evaluations per run must be positive.")
        if any(value <= 0 for value in self.size):
            raise ValueError("Every docking-box dimension must be positive.")
        if any(value > 95.0 for value in self.size):
            raise ValueError(
                "Every docking-box dimension must be 95 A or smaller so AutoGrid stays below "
                "its 256-point limit. The proven cyclic-peptide default is 22.5 A."
            )
        if not 1 <= self.max_ligand_torsions <= 57:
            raise ValueError("Maximum ligand torsions must be between 1 and 57.")
        if self.auto_reduce_torsions and not self.rigid_macrocycle:
            raise ValueError(
                "Automatic torsion reduction requires the rigid-macrocycle option so the "
                "cyclic scaffold remains fixed while side-chain bonds are reduced."
            )


def _structure(path: Path, suffixes: set[str], label: str) -> Path:
    candidate = path.expanduser().resolve()
    if not candidate.is_file() or candidate.suffix.lower() not in suffixes:
        raise ValueError(f"Select an existing {label} ({', '.join(sorted(suffixes))}).")
    return candidate


def _tailor_gpf(job_dir: Path) -> None:
    """Limit AutoGrid affinity maps to atom types present in this ligand."""
    ligand_lines = (job_dir / "prepared" / "ligand.pdbqt").read_text(encoding="utf-8").splitlines()
    pdbqt_types = {line.split()[-1] for line in ligand_lines
                   if line.startswith(("ATOM", "HETATM"))}
    # Meeko represents a broken macrocycle bond with paired CGx/Gx glue
    # atoms. AutoGrid does not map glue types: CGx derives from carbon and Gx
    # is an interaction-free pseudo atom handled internally by AutoDock-GPU.
    atom_types = sorted({"C" if re.fullmatch(r"CG\d", atom_type) else atom_type
                         for atom_type in pdbqt_types if not re.fullmatch(r"G\d", atom_type)})
    if not atom_types:
        raise RuntimeError("Meeko produced a ligand PDBQT without dockable atoms.")
    gpf_path = job_dir / "prepared" / "receptor.gpf"
    lines = gpf_path.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    maps_inserted = False
    for line in lines:
        if line.startswith("ligand_types "):
            updated.append("ligand_types " + " ".join(atom_types))
        elif line.startswith("map "):
            if not maps_inserted:
                updated.extend(f"map receptor.{atom_type}.map" for atom_type in atom_types)
                maps_inserted = True
        else:
            updated.append(line)
    gpf_path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def _macrocycle_derivative_spec(job_dir: Path) -> str | None:
    lines = (job_dir / "prepared" / "ligand.pdbqt").read_text(encoding="utf-8").splitlines()
    glue_carbons = sorted({line.split()[-1] for line in lines
                           if line.startswith(("ATOM", "HETATM"))
                           and re.fullmatch(r"CG\d", line.split()[-1])})
    return f"{','.join(glue_carbons)}=C" if glue_carbons else None


def _validate_ligand_complexity(job_dir: Path) -> int:
    torsion_count = _torsion_count(job_dir)
    if torsion_count > 57:
        raise ValueError(
            f"The prepared ligand has {torsion_count} torsional degrees of freedom, but this AutoDock-GPU "
            "build supports at most 57. Use the rigid-macrocycle option, provide a more "
            "constrained conformer, or use a different method for this ligand."
        )
    return torsion_count


def _torsion_count(job_dir: Path) -> int:
    lines = (job_dir / "prepared" / "ligand.pdbqt").read_text(
        encoding="utf-8", errors="replace"
    ).splitlines()
    for line in lines:
        if line.startswith("TORSDOF"):
            try:
                return int(line.split()[1])
            except (IndexError, ValueError) as exc:
                raise RuntimeError("Meeko produced an unreadable TORSDOF record.") from exc
    return sum(line.startswith("BRANCH") for line in lines)


def _proximal_rigidification_steps(max_depth: int = 10) -> list[tuple[str, str, str]]:
    """Return cumulative ring-outward bond rules, preserving distal flexibility first."""
    return [
        ("[R]" + "-[!R]" * depth, str(depth), str(depth + 1))
        for depth in range(1, max_depth + 1)
    ]


def _with_command_arguments(command: list[str], arguments: list[str], mode: str) -> list[str]:
    """Append arguments to either a native command or its WSL shell wrapper."""
    updated = command.copy()
    if mode == "native":
        return [*updated, *arguments]
    updated[-1] += " " + " ".join(shlex.quote(value) for value in arguments)
    return updated


def _run_with_windows_startup_retry(
    command: list[str], cwd: Path, attempts: int = 3
) -> tuple[subprocess.CompletedProcess[str], int]:
    """Retry the transient Windows DLL-initialization failure 0xC0000142."""
    startup_failure_codes = {0xC0000142, -1073741502}
    result: subprocess.CompletedProcess[str] | None = None
    for attempt in range(attempts):
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
        if result.returncode not in startup_failure_codes or attempt == attempts - 1:
            return result, attempt
        time.sleep(0.75 * (attempt + 1))
    raise AssertionError("unreachable")


def _validate_docking_energy(job_dir: Path, maximum_plausible: float = 1000.0) -> float:
    """Reject collision-scale outputs that AutoDock reports with a zero exit code."""
    energies = [energy for _rank, _run, energy in _ranked_dlg_runs(job_dir, 10)]
    best = min(energies)
    if not math.isfinite(best) or best > maximum_plausible:
        raise RuntimeError(
            "AutoDock-GPU returned only collision-scale poses "
            f"(best reported energy {best:.2f} kcal/mol). The run is not a valid docking result. "
            "Review the hotspot center, ligand structure, and docking-box dimensions."
        )
    return best


def _preferred_altlocs(pdb_path: Path) -> str | None:
    """Return Meeko wanted-altloc assignments using summed PDB occupancies."""
    scores: dict[tuple[str, int], dict[str, float]] = {}
    for line in pdb_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith(("ATOM  ", "HETATM")) or len(line) < 60:
            continue
        altloc = line[16].strip()
        if not altloc:
            continue
        try:
            residue = (line[21].strip() or "_", int(line[22:26]))
            occupancy = float(line[54:60])
        except ValueError:
            continue
        scores.setdefault(residue, {}).setdefault(altloc, 0.0)
        scores[residue][altloc] += occupancy
    assignments = []
    for (chain, residue), variants in sorted(scores.items()):
        # Alphabetical tie-breaking makes equal A/B occupancy deterministic.
        selected = min(variants, key=lambda alt: (-variants[alt], alt))
        assignments.append(f"{'' if chain == '_' else chain}:{residue}={selected}")
    return ",".join(assignments) if assignments else None


def _ranked_dlg_runs(job_dir: Path, limit: int) -> list[tuple[int, int, float]]:
    """Return ``(rank, run, binding_energy)`` ordered by DLG cluster rank."""
    dlg_path = job_dir / "raw" / "docking.dlg"
    ranking: list[tuple[int, int, float]] = []
    pattern = re.compile(
        r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)"
        r"\s+.*\bRANKING\s*$"
    )
    for line in dlg_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.match(line)
        if match:
            ranking.append((int(match.group(1)), int(match.group(3)), float(match.group(4))))
    top = sorted({rank: (run, energy) for rank, run, energy in ranking}.items())[:limit]
    if not top:
        raise RuntimeError("The docking DLG contains no readable RMSD ranking table.")
    return [(rank, run, energy) for rank, (run, energy) in top]


def split_ranked_complexes(job_dir: Path, limit: int = 10) -> list[Path]:
    """Write the top DLG-ranked receptor-ligand models as individual PDBs."""
    combined_path = job_dir / "poses" / "ranked_complexes.pdb"
    top = _ranked_dlg_runs(job_dir, limit)
    selected = {run: (rank, energy) for rank, run, energy in top}
    outputs: list[Path] = []
    destination_by_run: dict[int, Path] = {}
    for run, (rank, _energy) in selected.items():
        destination = job_dir / "poses" / f"complex_rank_{rank:03d}_run_{run:03d}.pdb"
        destination_by_run[run] = destination
        outputs.append(destination)
    current = None
    handle = None
    try:
        with combined_path.open("r", encoding="utf-8", errors="replace") as source:
            for line in source:
                if line.startswith("MODEL"):
                    try:
                        current = int(line.split()[1])
                    except (IndexError, ValueError):
                        current = None
                    if current in destination_by_run:
                        rank, energy = selected[current]
                        handle = destination_by_run[current].open("w", encoding="utf-8")
                        handle.write(f"REMARK MOLFORGE DOCKING RANK {rank}\n")
                        handle.write(f"REMARK AUTODOCK-GPU RUN {current}\n")
                        handle.write(f"REMARK ESTIMATED BINDING ENERGY {energy:+.2f} KCAL/MOL\n")
                    continue
                if line.startswith("ENDMDL"):
                    if handle is not None:
                        handle.write("END\n")
                        handle.close()
                        handle = None
                    current = None
                    continue
                if handle is not None:
                    handle.write(line)
    finally:
        if handle is not None:
            handle.close()
    missing = [path for path in outputs if not path.is_file()]
    if missing:
        raise RuntimeError(f"Could not locate ranked model(s) in combined complex PDB: {missing}")
    best = job_dir / "poses" / "best_complex.pdb"
    shutil.copy2(outputs[0], best)
    return [best, *outputs]


def _sdf_property(record: str, name: str) -> str | None:
    match = re.search(rf"^>\s+<{re.escape(name)}>[^\n]*\n([^\n]*)", record, re.MULTILINE)
    return match.group(1).strip() if match else None


def _with_sdf_properties(record: str, properties: dict[str, object]) -> str:
    """Add explicit, portable SD tags before a record terminator."""
    terminator = "$$$$"
    body, separator, _tail = record.rpartition(terminator)
    if not separator:
        raise RuntimeError("Meeko produced an unterminated SDF record.")
    body = body.rstrip("\r\n") + "\n"
    tags = "".join(f">  <{name}>\n{value}\n\n" for name, value in properties.items())
    return f"{body}{tags}{terminator}\n"


def split_ranked_ligands(job_dir: Path, limit: int = 10) -> list[Path]:
    """Pair top-ranked ligand-only SDFs with complexes and record docking metadata."""
    source_path = job_dir / "poses" / "ranked_poses.sdf"
    text = source_path.read_text(encoding="utf-8", errors="replace")
    # Splitting at the SD terminator leaves the separator newline at the start
    # of every record after the first. An SDF molecule must begin immediately
    # with its title so the counts line remains line four; PyMOL otherwise
    # reports ``ReadMOLFile-Error: bad atom count``.
    records = [part.lstrip("\r\n") + "$$$$\n"
               for part in text.split("$$$$") if part.strip()]
    top = _ranked_dlg_runs(job_dir, limit)
    if any(run < 1 or run > len(records) for _rank, run, _energy in top):
        raise RuntimeError(
            f"The docking DLG references a run absent from the ligand SDF ({len(records)} records)."
        )

    receptor = "inputs/receptor.pdb"
    outputs: list[Path] = []
    summary_rows: list[dict[str, object]] = []
    for rank, run, energy in top:
        record = records[run - 1]
        meeko_data: dict[str, object] = {}
        raw_meeko = _sdf_property(record, "meeko")
        if raw_meeko:
            try:
                decoded = json.loads(raw_meeko)
                if isinstance(decoded, dict):
                    meeko_data = decoded
            except json.JSONDecodeError:
                pass
        ligand_name = f"ligand_rank_{rank:03d}_run_{run:03d}.sdf"
        complex_name = f"complex_rank_{rank:03d}_run_{run:03d}.pdb"
        destination = job_dir / "poses" / ligand_name
        properties = {
            "MOLFORGE_DOCKING_RANK": rank,
            "AUTODOCK_GPU_RUN": run,
            "AUTODOCK_GPU_BINDING_ENERGY_KCAL_MOL": f"{energy:.4f}",
            "RECEPTOR_FILE": receptor,
            "PAIRED_COMPLEX_FILE": f"poses/{complex_name}",
        }
        destination.write_text(_with_sdf_properties(record, properties), encoding="utf-8")
        outputs.append(destination)
        summary_rows.append({
            "rank": rank,
            "run": run,
            "binding_energy_kcal_mol": energy,
            "intermolecular_energy_kcal_mol": meeko_data.get("intermolecular_energy", ""),
            "internal_energy_kcal_mol": meeko_data.get("internal_energy", ""),
            "cluster_id": meeko_data.get("cluster_id", ""),
            "cluster_size": meeko_data.get("cluster_size", ""),
            "rank_in_cluster": meeko_data.get("rank_in_cluster", ""),
            "receptor_file": receptor,
            "ligand_file": f"poses/{ligand_name}",
            "complex_file": f"poses/{complex_name}",
        })

    best = job_dir / "poses" / "best_ligand.sdf"
    shutil.copy2(outputs[0], best)
    summary = job_dir / "poses" / "docking_summary.csv"
    with summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)
    return [best, summary, *outputs]


def build_commands(job_dir: Path, parameters: DockingParameters, *, mode: str,
                   wsl_distribution: str, conda_environment: str,
                   autodock_executable: str, autogrid_executable: str,
                   meeko_ligand_executable: str = "mk_prepare_ligand.py",
                   meeko_receptor_executable: str = "mk_prepare_receptor.py",
                   meeko_export_executable: str = "mk_export.py") -> list[list[str]]:
    parameters.validate()

    def tool_command(executable: str, *arguments: str) -> list[str]:
        command = [executable]
        # Linux entry points use their own shebang interpreter and active environment.
        return [*command, *arguments]

    ligand = tool_command(meeko_ligand_executable, "-i", "inputs/ligand.sdf", "-o", "prepared/ligand.pdbqt")
    if parameters.rigid_macrocycle:
        # Preserve the macrocyclic scaffold while allowing side chains and
        # linkers to optimize their contacts. Optional staged reduction is
        # applied after measuring the initial prepared TORSDOF value.
        ligand.append("--rigid_macrocycles")
    receptor = tool_command(
        meeko_receptor_executable, "--read_pdb", "inputs/receptor.pdb", "-o", "prepared/receptor",
        "-p", "-j", "-g", "--box_center", *(str(v) for v in parameters.center),
        "--box_size", *(str(v) for v in parameters.size),
    )
    if parameters.allow_bad_receptor_residues:
        receptor.append("--allow_bad_res")
    if parameters.choose_highest_occupancy_altloc:
        altlocs = _preferred_altlocs(job_dir / "inputs" / "receptor.pdb")
        if altlocs:
            receptor.extend(["--wanted_altloc", altlocs])
    # AutoGrid resolves the receptor, parameter file, and generated maps relative
    # to the GPF working directory, so this stage is executed inside prepared/.
    grid = [autogrid_executable, "-p", "receptor.gpf", "-l", "../raw/autogrid.glg"]
    dock = [autodock_executable, "--ffile", "prepared/receptor.maps.fld", "--lfile",
            "prepared/ligand.pdbqt", "--nrun", str(parameters.nrun), "--resnam", "raw/docking",
            "--gbest", "1", "--xmloutput", "1", "--dlgoutput", "1", "--clustering", "1",
            "--autostop", "1", "--heuristics", "1", "--heurmax",
            str(parameters.heuristic_max_evaluations)]
    if parameters.seed is not None:
        dock.extend(["--seed", str(parameters.seed)])
    export = tool_command(meeko_export_executable, "raw/docking.dlg", "-j", "prepared/receptor.json",
                          "-s", "poses/ranked_poses.sdf", "-p", "poses/ranked_complexes.pdb", "--all_dlg_poses")
    raw = [ligand, receptor, grid, dock, export]
    if mode == "native":
        return raw
    raise ValueError("The Linux fork supports only native execution.")


def check_runtime(*, mode: str, wsl_distribution: str, conda_environment: str,
                  autodock_executable: str, autogrid_executable: str) -> dict[str, bool]:
    names = [autodock_executable, autogrid_executable, "mk_prepare_ligand.py", "mk_prepare_receptor.py"]
    if mode != "native":
        raise ValueError("The Linux fork supports only native execution.")
    return {name: shutil.which(name) is not None or Path(name).is_file() for name in names}


def _stage_native_runtime(autodock_executable: str, job_dir: Path) -> list[Path]:
    """Copy optional source-build kernel folders and accept release binaries."""
    executable = Path(autodock_executable).expanduser().resolve()
    source_root = executable.parent.parent
    staged: list[Path] = []
    for folder_name in ("device", "common"):
        source = source_root / folder_name
        if source.is_dir():
            destination = job_dir / folder_name
            shutil.copytree(source, destination)
            staged.append(destination)
    return staged


def run(receptor_pdb: Path, ligand_sdf: Path, output_root: Path, parameters: DockingParameters, *,
        mode: str = "native", wsl_distribution: str = "", conda_environment: str = "",
        autodock_executable: str = "autodock_gpu_128wi", autogrid_executable: str = "autogrid4",
        meeko_ligand_executable: str = "mk_prepare_ligand.py",
        meeko_receptor_executable: str = "mk_prepare_receptor.py",
        meeko_export_executable: str = "mk_export.py") -> Path:
    receptor = _structure(receptor_pdb, {".pdb"}, "receptor PDB")
    ligand = _structure(ligand_sdf, {".sdf", ".sd"}, "ligand SDF")
    parameters.validate()
    job_dir, stamp = create_job(
        output_root, descriptive_job_name("autodock-gpu", receptor, ligand)
    )
    for folder in ("inputs", "prepared", "raw", "poses"):
        (job_dir / folder).mkdir()
    shutil.copy2(receptor, job_dir / "inputs" / "receptor.pdb")
    shutil.copy2(ligand, job_dir / "inputs" / "ligand.sdf")
    if mode == "native":
        _stage_native_runtime(autodock_executable, job_dir)
    commands = build_commands(job_dir, parameters, mode=mode, wsl_distribution=wsl_distribution,
                              conda_environment=conda_environment, autodock_executable=autodock_executable,
                              autogrid_executable=autogrid_executable,
                              meeko_ligand_executable=meeko_ligand_executable,
                              meeko_receptor_executable=meeko_receptor_executable,
                              meeko_export_executable=meeko_export_executable)
    (job_dir / "commands.json").write_text(json.dumps(commands, indent=2) + "\n", encoding="utf-8")
    if mode == "native":
        labels = ("Meeko ligand preparer", "Meeko receptor preparer", "AutoGrid4", "AutoDock-GPU", "Meeko result exporter")
        missing = []
        for label, command in zip(labels, commands):
            executable = command[0]
            if not Path(executable).expanduser().is_file() and shutil.which(executable) is None:
                missing.append(f"{label}: {executable}")
        if missing:
            raise ValueError(
                "Required docking executable(s) were not found:\n" + "\n".join(missing)
                + "\n\nOpen Settings and select existing files, or reinstall MolForge dependencies."
            )
    log: list[str] = []
    initial_ligand_torsions: int | None = None
    ligand_torsions: int | None = None
    torsion_reduction_rules: list[str] = []
    try:
        for index, command in enumerate(commands):
            command_cwd = job_dir / "prepared" if mode == "native" and index == 2 else job_dir
            result, startup_retries = _run_with_windows_startup_retry(command, command_cwd)
            log.extend(["$ " + subprocess.list2cmdline(command), result.stdout, result.stderr])
            if startup_retries:
                log.append(
                    f"MolForge recovered from Windows DLL initialization error 0xC0000142 "
                    f"after {startup_retries} retry/retries."
                )
            if result.returncode:
                detail = (result.stderr or result.stdout).strip()
                if len(detail) > 1800:
                    detail = detail[-1800:]
                raise RuntimeError(
                    f"Command failed with exit code {result.returncode}: {command[0]}\n\n"
                    f"{detail}\n\nFull log: {job_dir / 'autodock_gpu.log'}"
                )
            if index == 0:
                initial_ligand_torsions = _torsion_count(job_dir)
                ligand_torsions = initial_ligand_torsions
                if (
                    parameters.auto_reduce_torsions
                    and ligand_torsions > parameters.max_ligand_torsions
                ):
                    reduction_command = command.copy()
                    for smarts, first, second in _proximal_rigidification_steps():
                        arguments = [
                            "--rigidify_bonds_smarts", smarts,
                            "--rigidify_bonds_indices", first, second,
                        ]
                        reduction_command = _with_command_arguments(
                            reduction_command, arguments, mode
                        )
                        retry_result, retry_count = _run_with_windows_startup_retry(
                            reduction_command, command_cwd
                        )
                        log.extend([
                            "$ " + subprocess.list2cmdline(reduction_command),
                            retry_result.stdout,
                            retry_result.stderr,
                        ])
                        if retry_count:
                            log.append(
                                "MolForge recovered from Windows DLL initialization error "
                                f"0xC0000142 after {retry_count} retry/retries."
                            )
                        if retry_result.returncode:
                            detail = (retry_result.stderr or retry_result.stdout).strip()
                            raise RuntimeError(
                                "Automatic cyclic-ligand torsion reduction failed while applying "
                                f"{smarts}:\n\n{detail[-1800:]}"
                            )
                        ligand_torsions = _torsion_count(job_dir)
                        torsion_reduction_rules.append(smarts)
                        log.append(
                            f"Torsion reduction {smarts}: {ligand_torsions} active torsions "
                            f"(target <= {parameters.max_ligand_torsions})."
                        )
                        if ligand_torsions <= parameters.max_ligand_torsions:
                            commands[0] = reduction_command
                            break
                    if ligand_torsions > parameters.max_ligand_torsions:
                        raise ValueError(
                            f"The ligand was reduced from {initial_ligand_torsions} to "
                            f"{ligand_torsions} torsions, but the requested maximum is "
                            f"{parameters.max_ligand_torsions}. Use a higher target, a more "
                            "constrained conformer, or another docking method."
                        )
                _validate_ligand_complexity(job_dir)
                derivative_spec = _macrocycle_derivative_spec(job_dir)
                if derivative_spec:
                    commands[3].extend(["--derivtype", derivative_spec])
                (job_dir / "commands.json").write_text(
                    json.dumps(commands, indent=2) + "\n", encoding="utf-8"
                )
            if index == 1:
                _tailor_gpf(job_dir)
            if index == 3 and not (job_dir / "raw" / "docking.dlg").is_file():
                detail = (result.stdout or result.stderr).strip()
                if len(detail) > 1800:
                    detail = detail[-1800:]
                raise RuntimeError(
                    "AutoDock-GPU did not create a docking result even though its process returned zero.\n\n"
                    f"{detail}\n\nFull log: {job_dir / 'autodock_gpu.log'}"
                )
            if index == 3:
                _validate_docking_energy(job_dir)
            if index == 4:
                split_ranked_complexes(job_dir)
                split_ranked_ligands(job_dir)
    except Exception:
        (job_dir / "autodock_gpu.log").write_text("\n".join(log), encoding="utf-8")
        (job_dir / "FAILED").write_text("AutoDock-GPU workflow failed.\n", encoding="utf-8")
        raise
    (job_dir / "autodock_gpu.log").write_text("\n".join(log), encoding="utf-8")
    result_files = list((job_dir / "raw").glob("docking*")) + list((job_dir / "poses").glob("*"))
    if not result_files:
        raise RuntimeError("AutoDock-GPU returned without a docking result; inspect autodock_gpu.log.")
    write_manifest(job_dir, stamp, "autodock_gpu", {
        "receptor": str(receptor), "ligand": str(ligand), "execution_mode": mode,
        "wsl_distribution": wsl_distribution, "conda_environment": conda_environment,
        "parameters": parameters.__dict__,
        "initial_prepared_ligand_torsions": initial_ligand_torsions,
        "prepared_ligand_torsions": ligand_torsions,
        "torsion_reduction_rules": torsion_reduction_rules,
    }, {"result_files": [str(path) for path in result_files]}, job_dir / "raw")
    return job_dir
