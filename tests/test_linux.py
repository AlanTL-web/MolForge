import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from molforge_linux.cli import main, parser
from molforge_linux.runtime import evidence, job, md_preflight, run
from molforge_core.autodock_gpu import DockingParameters, build_commands
from molforge_core.md_config import UniGBSAMDParameters, write_unigbsa_pipeline_config
from molforge_core.unigbsa_runner import equilibration_steps


def test_cli_conformer_chemistry_and_selection(tmp_path):
    from rdkit import Chem
    assert main(['conformers', '--smiles', 'C[C@H](O)C(=O)O', '--num-confs', '3',
                 '--threads', '1', '--output-root', str(tmp_path)]) == 0
    folder = next(tmp_path.iterdir())
    assert json.loads((folder / 'status.json').read_text())['status'] == 'completed'
    sdf = folder / 'outputs/conformers.sdf'
    molecules = list(Chem.SDMolSupplier(str(sdf), removeHs=False))
    expected = Chem.MolToSmiles(Chem.MolFromSmiles('C[C@H](O)C(=O)O'))
    assert all(Chem.MolToSmiles(Chem.RemoveHs(m)) == expected for m in molecules)
    protocol = json.loads((folder / 'outputs/sampling_progress.json').read_text())
    assert protocol['rounds'][0]['embedding_parameters']['numThreads'] == 1
    assert main(['select', '--sdf', str(sdf), '--record', '1', '--output-root', str(tmp_path / 'selected')]) == 0
    result = next((tmp_path / 'selected').glob('*/outputs/selected_ligand.sdf'))
    assert len(list(Chem.SDMolSupplier(str(result)))) == 1


def test_cli_reads_one_long_smiles_from_file(tmp_path):
    from rdkit import Chem
    source = tmp_path / 'SMILES.txt'
    source.write_text('CC(=O)O\n', encoding='utf-8')
    assert main(['conformers', '--smiles-file', str(source), '--num-confs', '2',
                 '--threads', '1', '--output-root', str(tmp_path / 'runs')]) == 0
    folder = next((tmp_path / 'runs').iterdir())
    molecule = next(iter(Chem.SDMolSupplier(str(folder / 'outputs/conformers.sdf'))))
    assert Chem.MolToSmiles(molecule) == 'CC(=O)O'
    assert (folder / 'inputs/smiles_source.txt').read_text() == 'CC(=O)O\n'


def test_smiles_file_rejects_multiple_records(tmp_path):
    source = tmp_path / 'SMILES.txt'
    source.write_text('CCO\nCCN\n', encoding='utf-8')
    assert main(['conformers', '--smiles-file', str(source), '--num-confs', '1',
                 '--output-root', str(tmp_path / 'runs')]) == 1


def test_sampling_records_only_parameters_supported_by_installed_rdkit(tmp_path, monkeypatch):
    from rdkit import Chem
    from molforge_conf import sampling
    real = sampling.AllChem.ETKDGv3

    class OlderParameters:
        def __init__(self):
            self._delegate = real()
        def __getattr__(self, name):
            if name == 'useMacrocycle14config':
                raise AttributeError(name)
            return getattr(self._delegate, name)
        def __setattr__(self, name, value):
            if name == '_delegate':
                object.__setattr__(self, name, value)
            else:
                setattr(self._delegate, name, value)

    real_embed = sampling.AllChem.EmbedMultipleConfs
    monkeypatch.setattr(sampling.AllChem, 'ETKDGv3', OlderParameters)
    monkeypatch.setattr(sampling.AllChem, 'EmbedMultipleConfs',
                        lambda mol, numConfs, params: real_embed(mol, numConfs=numConfs,
                                                                params=params._delegate))
    molecule = Chem.AddHs(Chem.MolFromSmiles('CCO'))
    _, _, reports = sampling.sample(molecule, 1, 1, 0.5, 50, 1, threads=1)
    assert 'useMacrocycle14config' not in reports[0]['embedding_parameters']


def test_native_commands_preserve_spaced_executables(tmp_path):
    commands = build_commands(tmp_path, DockingParameters((1, 2, 3), (22.5, 22.5, 22.5)),
        mode='native', wsl_distribution='', conda_environment='',
        autodock_executable='/opt/docking tools/autodock', autogrid_executable='/opt/grid tools/autogrid',
        meeko_ligand_executable='/opt/meeko tools/mk_prepare_ligand.py')
    assert commands[0][0] == '/opt/meeko tools/mk_prepare_ligand.py'
    assert commands[3][0] == '/opt/docking tools/autodock'
    assert not any('wsl' in part for command in commands for part in command)


def test_failure_preserves_inputs_and_log(tmp_path):
    source = tmp_path / 'original.txt'
    source.write_text('unaltered')
    with pytest.raises(RuntimeError):
        with job(tmp_path / 'runs', 'failure', {}, {'original.txt': source}) as folder:
            run([sys.executable, '-c', 'print("failure evidence"); raise SystemExit(7)'], folder, 'engine')
    assert source.read_text() == 'unaltered'
    assert (folder / 'inputs/original.txt').read_text() == 'unaltered'
    assert 'failure evidence' in (folder / 'engine.log').read_text()
    assert json.loads((folder / 'status.json').read_text())['status'] == 'failed'
    assert not (folder / 'manifest.json').exists()


def test_md_gpu_preflight_and_cpu_environment(monkeypatch):
    from molforge_linux import runtime
    monkeypatch.setattr(runtime, 'executable', lambda x: x)
    seen = []
    def fake(cmd, **kwargs):
        seen.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, 'GPU support: disabled', '')
    monkeypatch.setattr(runtime.subprocess, 'run', fake)
    with pytest.raises(RuntimeError, match='CUDA'):
        md_preflight('gpu')
    result = md_preflight('cpu')
    assert result['environment_overrides'] == {'CUDA_VISIBLE_DEVICES': ''}
    assert seen[-1][1]['env']['CUDA_VISIBLE_DEVICES'] == ''
    assert result['gpu_usage_verified'] is False


def test_unequal_equilibration_and_profile(tmp_path):
    class Engine:
        def gmx_nvt(self, nsteps=1): return nsteps
        def gmx_npt(self, nsteps=1): return nsteps
    with equilibration_steps(Engine, 100, 200):
        assert Engine().gmx_nvt(nsteps=9) == 100
        assert Engine().gmx_npt() == 200
    assert Engine().gmx_nvt() == 1
    path = write_unigbsa_pipeline_config(tmp_path / 'config.ini', UniGBSAMDParameters())
    assert 'ligandCharge = bcc' in path.read_text()
    assert 'igb = 2' in path.read_text()


def test_batch_rejects_shell_and_recursion(tmp_path):
    config = tmp_path / 'bad.json'
    for commands in (['echo unsafe'], [['run', '--config', str(config)]], []):
        config.write_text(json.dumps({'commands': commands}))
        assert main(['run', '--config', str(config)]) == 1


def test_batch_dry_run_creates_no_jobs(tmp_path):
    config = tmp_path / 'run.json'
    output = tmp_path / 'runs'
    config.write_text(json.dumps({'commands': [['conformers', '--smiles', 'CCO', '--output-root', str(output)]]}))
    assert main(['run', '--config', str(config), '--dry-run']) == 0
    assert not output.exists()


def test_md_dispatch_native_and_independent_steps(tmp_path, monkeypatch):
    from molforge_linux import stages
    receptor = tmp_path / 'r.pdb'
    receptor.write_text('END\n')
    ligand = tmp_path / 'l.sdf'
    ligand.write_text('test input')
    monkeypatch.setattr(stages, 'md_preflight', lambda x: {'environment_overrides': {'CUDA_VISIBLE_DEVICES': ''}})
    seen = []
    def fake(command, folder, label, **kwargs):
        seen.append(command)
        (folder / 'outputs/unigbsa_results.csv').write_text('ligandName,mode,Frames,TOTAL,status\nL,gb,1,-2,S\n')
    monkeypatch.setattr(stages, 'run', fake)
    assert main(['md', '--receptor', str(receptor), '--ligand', str(ligand), '--nvt-steps', '20',
                 '--npt-steps', '30', '--output-root', str(tmp_path / 'runs')]) == 0
    assert seen[0][1:6] == ['-m', 'molforge_core.unigbsa_runner', '20', '30', 'unigbsa-pipeline']
    assert all('wsl' not in item for item in seen[0])


def test_conversion_preserves_sources_and_filters_solvent(tmp_path, monkeypatch):
    from molforge_linux import stages
    topology = tmp_path / 'md.tpr'
    trajectory = tmp_path / 'md.xtc'
    topology.write_bytes(b'topology')
    trajectory.write_bytes(b'trajectory')
    seen = []
    monkeypatch.setattr(stages, 'executable', lambda x: x)
    def fake(command, folder, label, **kwargs):
        seen.append(kwargs['stdin'])
        (folder / 'outputs/system.pdb').write_text(
            'MODEL        1\n'
            'ATOM      1  CA  ALA A   1       1.000   2.000   3.000  1.00  0.00           C\n'
            'HETATM    2  O   HOH B   2       1.000   2.000   3.000  1.00  0.00           O\nENDMDL\n')
    monkeypatch.setattr(stages, 'run', fake)
    assert main(['convert', '--topology', str(topology), '--trajectory', str(trajectory),
                 '--output-root', str(tmp_path / 'runs')]) == 0
    result = next((tmp_path / 'runs').glob('*/outputs/trajectory_animation.pdb'))
    assert 'ALA' in result.read_text() and 'HOH' not in result.read_text()
    assert seen == ['0\n0\n']
    assert trajectory.read_bytes() == b'trajectory'


def test_average_excludes_nan_and_failed_rows(tmp_path):
    from molforge_core.md_config import write_binding_energy_average
    source = tmp_path / 'frames.csv'
    source.write_text('ligandName,mode,Frames,TOTAL,status\nL,gb,1,-2,S\nL,gb,2,nan,S\nL,gb,3,-8,F\n')
    output = write_binding_energy_average(source, tmp_path / 'average.csv')
    assert 'L,gb,1,-2.0,S' in output.read_text()


def test_environment_reports_rdkit_version_without_distribution_metadata(monkeypatch):
    from importlib import metadata
    from rdkit import rdBase
    real_version = metadata.version

    def version(name):
        if name == 'rdkit':
            raise metadata.PackageNotFoundError(name)
        return real_version(name)

    monkeypatch.setattr(metadata, 'version', version)
    assert evidence()['versions']['rdkit'] == rdBase.rdkitVersion
