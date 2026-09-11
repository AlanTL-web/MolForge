"""Linux adapters around the independently copied molecular core."""
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys

from molforge_core import md_config
from molforge_core.solvent import filter_pdb_solvent, HIDDEN_RESIDUES
from .runtime import dump, executable, job, md_preflight, run


def conformers(args):
    from molforge_conf.core import generate_rank_conformers
    if args.smiles_file:
        lines = [line.strip() for line in args.smiles_file.read_text(encoding='utf-8-sig').splitlines()
                 if line.strip()]
        if len(lines) != 1:
            raise ValueError('--smiles-file must contain exactly one nonempty SMILES line.')
        smiles = lines[0]
    else:
        smiles = args.smiles
    options = {key: getattr(args, key) for key in ('seed', 'prune_rms_thresh', 'max_iters',
                'sampling_rounds', 'embedding_attempts', 'sampling_scheme', 'threads')}
    source = {'smiles_source.txt': args.smiles_file} if args.smiles_file else None
    with job(args.output_root, args.job_name or 'conformers', vars(args), source) as folder:
        (folder / 'inputs/smiles.txt').write_text(smiles + '\n', encoding='utf-8')
        generate_rank_conformers(smiles, args.num_confs, folder / 'outputs', **options)
    return folder


def dock(args):
    from molforge_core import autodock_gpu as core
    from molforge_core.hotspot import calculate_center
    center = args.center
    if args.site_residues:
        center, _, _ = calculate_center(args.receptor, args.site_residues)
    if not all(math.isfinite(x) for x in (*center, *args.size)):
        raise ValueError('Docking box coordinates and sizes must be finite.')
    parameters = core.DockingParameters(tuple(center), tuple(args.size), nrun=args.nrun,
        heuristic_max_evaluations=args.heuristic_max_evaluations, seed=args.seed,
        rigid_macrocycle=args.rigid_macrocycle, auto_reduce_torsions=args.auto_reduce_torsions,
        max_ligand_torsions=args.max_ligand_torsions,
        allow_bad_receptor_residues=args.allow_bad_receptor_residues,
        choose_highest_occupancy_altloc=args.choose_highest_occupancy_altloc)
    parameters.validate()
    from rdkit import Chem
    molecules = list(Chem.SDMolSupplier(str(args.ligand), removeHs=False))
    if len(molecules) != 1 or molecules[0] is None:
        raise ValueError('Docking requires one reviewed, chemically complete SDF record; use select first.')
    with job(args.output_root, args.job_name or 'dock', vars(args),
             {'receptor.pdb': args.receptor, 'ligand.sdf': args.ligand}) as folder:
        result = core.run(folder / 'inputs/receptor.pdb', folder / 'inputs/ligand.sdf', folder / 'outputs', parameters,
            mode='native', wsl_distribution='', conda_environment='',
            autodock_executable=executable(args.autodock), autogrid_executable=executable(args.autogrid),
            meeko_ligand_executable=executable('mk_prepare_ligand.py'),
            meeko_receptor_executable=executable('mk_prepare_receptor.py'),
            meeko_export_executable=executable('mk_export.py'))
        dump(folder / 'result.json', {'docking_job': str(result)})
    return folder


def select(args):
    from rdkit import Chem
    records = list(Chem.SDMolSupplier(str(args.sdf), removeHs=False))
    if not 1 <= args.record <= len(records) or records[args.record-1] is None:
        raise ValueError('Record must be a valid one-based SDF record number.')
    with job(args.output_root, args.job_name or 'select', vars(args), {'ensemble.sdf': args.sdf}) as folder:
        with Chem.SDWriter(str(folder / 'outputs/selected_ligand.sdf')) as writer:
            writer.write(records[args.record-1])
    return folder


def repair(args):
    with job(args.output_root, args.job_name or 'repair', vars(args), {'receptor.pdb': args.receptor}) as folder:
        output = folder / 'outputs/receptor_repaired.pdb'
        run([sys.executable, '-m', 'molforge_core.pdbfixer_repair', str(folder / 'inputs/receptor.pdb'),
             str(output), str(folder / 'outputs/repair_report.json')], folder, 'repair')
        missing = md_config.missing_standard_residue_heavy_atoms(output)
        if missing:
            raise RuntimeError('Repaired receptor still has missing atoms: ' + '; '.join(missing))
    return folder


def md(args):
    if args.receptor.suffix.lower() != '.pdb' or args.ligand.suffix.lower() not in {'.sdf', '.mol', '.mol2', '.pdb'}:
        raise ValueError('MD requires receptor PDB and ligand SDF/MOL/MOL2/PDB.')
    parameters = md_config.UniGBSAMDParameters(**{
        key: getattr(args, key) for key in md_config.UniGBSAMDParameters.__dataclass_fields__})
    parameters.validate()
    if not math.isfinite(parameters.box_distance_nm) or not math.isfinite(parameters.salt_concentration_molar):
        raise ValueError('Box distance and salt concentration must be finite.')
    if parameters.frames > parameters.steps:
        raise ValueError('frames cannot exceed production steps.')
    missing = md_config.missing_standard_residue_heavy_atoms(args.receptor)
    if missing:
        raise ValueError('Receptor has missing atoms; run repair and review its report: ' + '; '.join(missing))
    with job(args.output_root, args.job_name or 'md', vars(args),
             {'receptor.pdb': args.receptor, 'ligand' + args.ligand.suffix: args.ligand}) as folder:
        preflight = md_preflight(args.accelerator)
        dump(folder / 'runtime_preflight.json', preflight)
        config = md_config.write_unigbsa_pipeline_config(folder / 'inputs/unigbsa.ini', parameters)
        output = folder / 'outputs/unigbsa_results.csv'
        command = [sys.executable, '-m', 'molforge_core.unigbsa_runner', str(parameters.nvt_steps),
                   str(parameters.npt_steps), 'unigbsa-pipeline', '-i', str(folder / 'inputs/receptor.pdb'),
                   '-l', str(folder / ('inputs/ligand' + args.ligand.suffix)), '-c', str(config),
                   '-o', str(output), '-nt', str(parameters.threads), '-validate', '--verbose']
        run(command, folder, 'unigbsa_pipeline', env=preflight['environment_overrides'])
        md_config.write_binding_energy_average(output, folder / 'outputs/unigbsa_results_average.csv')
        dump(folder / 'trajectory_paths.json', md_config.locate_trajectory_outputs(folder))
    return folder


def convert(args):
    if args.topology.suffix.lower() not in {'.tpr', '.pdb', '.gro'} or args.trajectory.suffix.lower() not in {'.xtc', '.trr'}:
        raise ValueError('Conversion requires TPR/PDB/GRO topology and XTC/TRR trajectory.')
    with job(args.output_root, args.job_name or 'convert', vars(args)) as folder:
        # Hash large trajectories without duplicating them; conversion never writes the sources.
        from molforge_core.job import sha256
        dump(folder / 'inputs.json', {str(p): {'sha256': sha256(p)} for p in (args.topology, args.trajectory)})
        raw = folder / 'outputs/system.pdb'
        command = [executable('gmx'), 'trjconv', '-s', str(args.topology), '-f', str(args.trajectory), '-o', str(raw)]
        selection = '0\n'
        if args.topology.suffix.lower() == '.tpr':
            command += ['-pbc', 'mol', '-center']
            selection = '0\n0\n'
        run(command, folder, 'conversion', stdin=selection)
        report = filter_pdb_solvent(raw, folder / 'outputs/trajectory_animation.pdb')
        report['excluded_residue_names'] = sorted(HIDDEN_RESIDUES)
        dump(folder / 'outputs/conversion.json', report)
    return folder


def hdock(args):
    from molforge_core.hdock import run as core_run
    with job(args.output_root, args.job_name or 'hdock', vars(args),
             {'receptor.pdb': args.receptor, 'ligand.pdb': args.ligand}) as folder:
        core_run(folder / 'inputs/receptor.pdb', folder / 'inputs/ligand.pdb', folder / 'outputs',
                 hdock_executable=executable(args.hdock), createpl_executable=executable(args.createpl),
                 number_of_models=args.models)
    return folder
