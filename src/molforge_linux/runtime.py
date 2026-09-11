"""Native, non-interactive Linux execution and job provenance."""
from contextlib import contextmanager
from dataclasses import asdict
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys

from molforge_core.job import create_job, sha256, write_manifest


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, default=str) + '\n', encoding='utf-8')


def executable(value):
    found = shutil.which(str(Path(value).expanduser()))
    if not found:
        raise ValueError(f'Executable not found or not executable: {value}. Activate the correct environment or set PATH.')
    return str(Path(found).absolute())


def evidence():
    versions = {}
    for name in ('molforge-linux', 'rdkit', 'meeko', 'unigbsa', 'pdbfixer', 'openmm'):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    if versions['rdkit'] is None:
        try:
            from rdkit import rdBase
            versions['rdkit'] = rdBase.rdkitVersion
        except ImportError:
            pass
    return {'platform': platform.platform(), 'python': sys.version, 'executable': sys.executable,
            'versions': versions, 'CUDA_VISIBLE_DEVICES': os.getenv('CUDA_VISIBLE_DEVICES'),
            'SLURM_JOB_ID': os.getenv('SLURM_JOB_ID')}


@contextmanager
def job(root, name, parameters, inputs=None):
    folder, stamp = create_job(Path(root).expanduser().resolve(), name)
    (folder / 'inputs').mkdir()
    (folder / 'outputs').mkdir()
    dump(folder / 'status.json', {'status': 'running'})
    dump(folder / 'environment.json', evidence())
    dump(folder / 'parameters.json', parameters)
    print(f'Job: {folder}', file=sys.stderr, flush=True)
    try:
        copied = {}
        for name, source in (inputs or {}).items():
            source = Path(source).expanduser().resolve(strict=True)
            target = folder / 'inputs' / name
            shutil.copy2(source, target)
            copied[name] = {'source': str(source), 'sha256': sha256(target)}
        dump(folder / 'inputs.json', copied)
        yield folder
        write_manifest(folder, stamp, name, json.loads(json.dumps(parameters, default=str)), {}, folder / 'outputs')
        dump(folder / 'status.json', {'status': 'completed'})
    except BaseException as exc:
        dump(folder / 'status.json', {'status': 'interrupted' if isinstance(exc, KeyboardInterrupt) else 'failed',
                                     'error': f'{type(exc).__name__}: {exc}'})
        (folder / 'FAILED.txt').write_text(f'{type(exc).__name__}: {exc}\n', encoding='utf-8')
        raise


def run(command, folder, label, *, env=None, stdin=None, cwd=None):
    history = folder / 'commands.json'
    commands = json.loads(history.read_text()) if history.exists() else []
    commands.append({'argv': command, 'cwd': str(cwd or folder), 'stdin': stdin,
                     'environment_overrides': env or {}})
    dump(history, commands)
    log = folder / f'{label}.log'
    with log.open('w', encoding='utf-8') as stream:
        stream.write('$ ' + shlex.join(command) + '\n')
        stream.flush()
        completed = subprocess.run(command, cwd=cwd or folder,
                                   env={**os.environ, **(env or {})}, input=stdin,
                                   text=True, stdout=stream, stderr=subprocess.STDOUT)
    if completed.returncode:
        raise RuntimeError(f'{label} exited {completed.returncode}; see {log}')
    return log


def md_preflight(accelerator):
    gmx = executable('gmx')
    executable('unigbsa-pipeline')
    env = {'CUDA_VISIBLE_DEVICES': ''} if accelerator == 'cpu' else {}
    check = subprocess.run([gmx, '--version'], capture_output=True, text=True,
                           env={**os.environ, **env}, timeout=30, check=True)
    version = check.stdout + check.stderr
    result = {'gmx': gmx, 'version': version, 'accelerator': accelerator,
              'gpu_usage_verified': False, 'environment_overrides': env}
    if accelerator == 'gpu':
        if not re.search(r'GPU support\s*:\s*CUDA', version, re.I):
            raise RuntimeError('GPU mode requires GROMACS reporting GPU support: CUDA.')
        if os.getenv('CUDA_VISIBLE_DEVICES') in ('', '-1'):
            raise RuntimeError('CUDA_VISIBLE_DEVICES hides the allocated GPU.')
        gpu = subprocess.run([executable('nvidia-smi'), '-L'], capture_output=True,
                             text=True, timeout=30, check=True)
        if not re.search(r'GPU\s+\d+:', gpu.stdout):
            raise RuntimeError('No NVIDIA GPU is visible.')
        result['nvidia_smi'] = gpu.stdout
    return result
