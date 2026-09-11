"""Exercise the actual shell entry point without downloading scientific packages."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != 'linux', reason='Native Linux installer')
SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/install.sh'


def invoke(*args, env=None):
    return subprocess.run(['bash', str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True, env=env, timeout=20)


def test_plan_does_not_create_prefix(tmp_path):
    prefix = tmp_path / 'environment with spaces'
    result = invoke('--profile', 'all', '--prefix', prefix, '--plan')
    assert result.returncode == 0, result.stderr
    assert 'gromacs' in result.stdout and 'ambertools' in result.stdout
    assert 'AutoDock-GPU' in result.stdout and 'HDOCK' in result.stdout
    assert not prefix.exists()


def test_invalid_profile_rejected_before_install(tmp_path):
    result = invoke('--profile', 'anything', '--prefix', tmp_path / 'env', '--yes')
    assert result.returncode == 2
    assert not (tmp_path / 'env').exists()


def test_missing_environment_fails_check(tmp_path):
    result = invoke('--prefix', tmp_path / 'missing', '--check')
    assert result.returncode != 0
    assert 'Environment missing' in result.stdout


def test_ready_environment_skips_package_manager(tmp_path):
    prefix = tmp_path / 'existing env'
    (prefix / 'bin').mkdir(parents=True)
    python = prefix / 'bin/python'
    python.write_text('#!/bin/sh\nexit 0\n')
    python.chmod(0o755)
    result = invoke('--prefix', prefix, '--yes')
    assert result.returncode == 0, result.stderr
    assert 'no downloads required' in result.stdout
    assert not (prefix / 'conda-meta').exists()


def test_check_reports_failed_stage(tmp_path):
    prefix = tmp_path / 'bad env'
    (prefix / 'bin').mkdir(parents=True)
    python = prefix / 'bin/python'
    python.write_text('#!/bin/sh\nexit 1\n')
    python.chmod(0o755)
    result = invoke('--prefix', prefix, '--profile', 'all', '--check')
    assert result.returncode != 0


def test_active_conda_prefix_is_selected(tmp_path):
    env = {**os.environ, 'CONDA_PREFIX': str(tmp_path / 'active')}
    result = invoke('--plan', env=env)
    assert result.returncode == 0
    assert str(tmp_path / 'active') in result.stdout


def test_partial_venv_is_preserved(tmp_path):
    prefix = tmp_path / 'venv'
    prefix.mkdir()
    marker = prefix / 'keep.txt'
    marker.write_text('user data')
    result = invoke('--prefix', prefix, '--yes')
    assert result.returncode != 0
    assert 'not a conda environment' in result.stderr
    assert marker.read_text() == 'user data'
