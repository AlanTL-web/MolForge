# Development and contribution

Read [the user manual](docs/MANUAL.md) for the public workflow and
[the command reference](docs/COMMANDS.md) for supported options.

## Set up and validate

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
They do not run a full GPU docking or MD calculation. The [GitHub Actions page](https://github.com/AlanTL-web/MolForge/actions) lists CI runs.

## Change requirements

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

## Submit a change

Fork [MolForge](https://github.com/AlanTL-web/MolForge), create a branch, and submit a pull request describing the behavior changed and the checks you ran. Review `git status --short` and your diff before committing; include synthetic inputs when a reproducible example is needed.

## Build a source release

```bash
python scripts/package_release.py
```

The release uses an allowlist to exclude local environments and research results. Review the archive contents before publishing.

See [NOTICE.md](NOTICE.md) for source provenance and dependency licenses. The repository's MIT license applies to MolForge-owned source.
