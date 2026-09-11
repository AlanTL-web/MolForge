import json
from pathlib import Path

import pytest

from molforge_linux.cli import main
from molforge_linux.results import discover, resolve_job


@pytest.fixture
def jobs(tmp_path):
    root = tmp_path / 'results with spaces'
    for stamp, name, status in [('20260101T120000Z', 'sample-a', 'completed'), ('20260102T120000Z', 'sample-b', 'failed')]:
        folder = root / f'{stamp}_{name}'
        (folder / 'outputs').mkdir(parents=True)
        (folder / 'status.json').write_text(json.dumps({'status': status}))
        (folder / 'parameters.json').write_text(json.dumps({'stage': 'conformers'}))
        (folder / 'run_metadata.json').write_text(json.dumps({'task_name': name}))
        (folder / 'outputs/conformers.sdf').write_text('sample')
        (folder / 'engine.log').write_text('first\nsecond\nthird\n')
    return root


def test_list_filters_and_aliases(jobs, capsys):
    assert main(['ls', '-o', str(jobs), '--stage', 'conf', '--status', 'completed', '--json']) == 0
    entries = json.loads(capsys.readouterr().out)
    assert len(entries) == 1 and entries[0]['name'] == 'sample-a'
    assert main(['st', 'latest', '-o', str(jobs), '--json']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['status'] == 'failed'


def test_path_and_copied_job_artifacts(jobs, capsys):
    assert main(['p', 'sample-a', '-o', str(jobs), '--artifact', 'sdf']) == 0
    path = Path(capsys.readouterr().out.strip())
    assert path.is_file() and path.name == 'conformers.sdf'
    assert main(['p', str(path.parents[1])]) == 0
    assert Path(capsys.readouterr().out.strip()) == path.parents[1]


def test_ambiguous_and_missing_jobs_do_not_guess(jobs):
    for selector in ('sample', 'missing'):
        with pytest.raises(ValueError):
            resolve_job(jobs, selector)


def test_corrupt_metadata_is_reported_without_hiding_jobs(jobs):
    folder = resolve_job(jobs, 'sample-a')
    (folder / 'status.json').write_text('{broken')
    entries = discover(jobs)
    entry = next(e for e in entries if e['name'] == 'sample-a')
    assert entry['status'] == 'unknown' and entry['warnings']


def test_files_and_log_tail(jobs, capsys):
    assert main(['f', 'latest', '-o', str(jobs), '--pattern', '*.sdf', '--json']) == 0
    assert len(json.loads(capsys.readouterr().out)) == 1
    assert main(['log', 'latest', '-o', str(jobs), '--lines', '2']) == 0
    assert capsys.readouterr().out == 'second\nthird\n'
    assert main(['log', 'latest', '-o', str(jobs), '--file', '../outside.log']) == 1


def test_missing_and_ambiguous_artifacts(jobs, capsys):
    folder = resolve_job(jobs, 'sample-a')
    for name in ('one', 'two'):
        child = folder / 'outputs' / name
        child.mkdir()
        (child / 'ranked_poses.sdf').write_text('test')
    assert main(['p', str(folder), '--artifact', 'poses']) == 1
    assert 'Multiple artifacts' in capsys.readouterr().err
    assert main(['p', str(folder), '--artifact', 'energy']) == 1


def test_environment_root_and_empty_root(tmp_path, jobs, monkeypatch, capsys):
    monkeypatch.setenv('MOLFORGE_RUNS_DIR', str(jobs))
    assert main(['p']) == 0
    assert Path(capsys.readouterr().out.strip()).name.endswith('sample-b')
    assert main(['ls', '-o', str(tmp_path / 'absent'), '--json']) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert main(['p', '-o', str(tmp_path / 'absent')]) == 1


def test_short_conformer_command_and_batch_alias(tmp_path, capsys):
    config = tmp_path / 'batch.json'
    config.write_text(json.dumps({'commands': [['conf', '--smiles', 'CCO', '-n', '1', '-t', '1', '-o', str(tmp_path / 'runs')]]}))
    assert main(['batch', '--config', str(config)]) == 0
    assert main(['ls', '-o', str(tmp_path / 'runs'), '--json']) == 0
    output = capsys.readouterr().out
    assert '"stage": "conformers"' in output
