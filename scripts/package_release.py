"""Create a portable source tarball with Linux script permissions."""
import hashlib
from pathlib import Path
import tarfile
import re

root = Path(__file__).resolve().parents[1]
version = re.search(r'^version = "([0-9.]+)"', (root / 'pyproject.toml').read_text(), re.M).group(1)
target = root.parent / f'MolForge_Linux_{version}.tar.gz'
excluded = {'__pycache__', '.pytest_cache', '.venv', 'build', 'dist', 'runs'}
public_files = {'README.md', 'CONTRIBUTING.md', 'NOTICE.md', 'pyproject.toml',
                'SOURCE_PROVENANCE.json', '.gitignore', '.gitattributes', 'MANIFEST.in'}
public_dirs = {'src', 'tests', 'docs', 'examples', '.github'}
public_scripts = {'install.sh', 'slurm-md.sh', 'package_release.py', 'build_command_reference.py',
                  'validate_conformer_smoke.py', 'smoke_cli.sh'}
with tarfile.open(target, 'w:gz', format=tarfile.PAX_FORMAT) as archive:
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if not (relative.as_posix() in public_files or relative.parts[0] in public_dirs
                or relative.parts[0] == 'scripts' and len(relative.parts) == 2 and path.name in public_scripts):
            continue
        if path.is_symlink():
            raise ValueError(f'Release source must not contain symlinks: {relative}')
        if any(part in excluded or part.endswith('.egg-info') for part in relative.parts):
            continue
        if not path.is_file() or path.suffix == '.pyc':
            continue
        info = archive.gettarinfo(str(path), arcname=str(Path(root.name) / relative))
        info.mode = 0o755 if path.suffix == '.sh' else 0o644
        info.uid = info.gid = 0
        info.uname = info.gname = ''
        with path.open('rb') as stream:
            archive.addfile(info, stream)
digest = hashlib.sha256(target.read_bytes()).hexdigest()
target.with_suffix(target.suffix + '.sha256').write_text(f'{digest}  {target.name}\n', encoding='ascii')
print(target)
print(digest)
