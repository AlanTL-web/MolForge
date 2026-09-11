# Development and contribution

Read [the user manual](docs/MANUAL.md) for the public workflow and
[the command reference](docs/COMMANDS.md) for supported options.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/build_command_reference.py --check
python -m build
bash scripts/smoke_cli.sh
python scripts/package_release.py
```

Use an isolated Linux environment. The tests exercise actual RDKit conformer
generation, command parsing, result browsing, and mocked external-engine contracts.
They do not run a full GPU docking or MD calculation. CI has been configured for
Linux; its hosted status becomes available after the repository is uploaded.

Keep scientific defaults explicit. Do not accept unconverged conformers as successful
outputs or infer GPU utilization from preflight alone. Record the installed software
versions when comparing results. Updates must leave the desktop source independent.

Add descriptions to both help catalogs when introducing a public option. Run
`python scripts/build_command_reference.py` to regenerate the bilingual reference.
Use explicit aliases; ambiguous command prefixes are intentionally rejected.

The release script uses an allowlist and rejects symlinks. It includes source,
public docs, tests, shell examples, and CI files. It excludes virtual environments,
test results, private ligands, logs, build directories, and the one-time upstream
extraction script. Local scientific results remain on disk and are ignored by Git.

## Upload preparation

The local Git repository has no configured remote and no automatically created commit.
Review `git status --short` and `git diff --cached` before committing. Create your
GitHub repository, then add its real URL as the remote and push when ready. No remote
repository has been created or uploaded by this preparation.

See [NOTICE.md](NOTICE.md) for source provenance and dependency license information.
The repository's MIT LICENSE applies to MolForge Linux source owned by the project
author.
