# MolForge Linux

A command-line workflow for molecular conformer generation, receptor repair,
docking, molecular dynamics, GBSA analysis, and result browsing.

**[User manual / 用户手册](docs/MANUAL.md)** · **[All commands / 指令大全](docs/COMMANDS.md)** · **[Citations / 引用](docs/CITATIONS.md)**

## Quick start

For automatic environment setup, including external scientific engines, use:

```bash
git clone https://github.com/AlanTL-web/MolForge.git
cd MolForge
bash scripts/install.sh --profile all --plan
bash scripts/install.sh --profile all --yes
```

Setup reuses the active Conda environment or creates `.molforge/envs/all`, installs
missing packages, downloads AutoDock-GPU when absent, and prints activation commands.
Choose `--profile conformers`, `dock`, `repair`, or `md` for a smaller installation.
HDOCKlite must be obtained separately; missing components cause the final checks to
fail visibly. GPU drivers and OpenCL device runtimes are supplied by the host system.
See [environment setup](docs/MANUAL.md#automatic-environment-setup) for reuse and checks.

### Minimal Python installation

Requires Linux and Python 3.10 or newer. Clone the GitHub repository, create an
isolated environment, and install the conformer-generation dependencies:

```bash
git clone https://github.com/AlanTL-web/MolForge.git
cd MolForge
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[conformers]"
molforge doctor --stage conformers
molforge conf --smiles 'CCO' -n 10 -t 2 --job-name ethanol
molforge ls
molforge st latest
molforge p latest --artifact sdf
```

`conf`, `ls`, `st`, and `p` are aliases for `conformers`, `runs`, `status`, and
`path`. Full command names remain available. Every calculation creates a new job
directory and preserves its parameters and outputs.

## Choose your help language

```bash
molforge --help --lang en
molforge conf --help --lang zh
molforge help md --lang en
molforge help --all --lang zh
export MOLFORGE_LANG=zh
```

English is the default; explicit `--lang` takes precedence over `MOLFORGE_LANG`.
中文帮助覆盖命令用途、参数、单位、默认值和示例；详细操作请阅读[合并后的用户手册](docs/MANUAL.md)。

## Find your results

```bash
molforge runs --stage conf --status completed
molforge files latest --pattern '*.sdf'
molforge path latest --artifact ranking
cd "$(molforge path latest)"
```

Use `--output-root /data/runs` or `MOLFORGE_RUNS_DIR` to browse another results root.
A selector can be `latest`, a full job ID, a unique name fragment, or a job directory.
The manual explains the working-directory behavior and how to read logs.

## Scientific scope

RDKit generates and ranks conformers. Optional engines provide AutoDock-GPU or
HDOCK docking, PDBFixer repair, and Uni-GBSA/GROMACS MD. These engines require separate
installation. Select and review ligand coordinates before MD; MolForge does not
automatically choose a scientific pose or establish sampling convergence.

Native WSL smoke tests have run on Ubuntu 24.04 with Linux RDKit, including two
large ligands. This is functional validation, not a scientific equivalence or GPU
performance claim. Full GPU docking and long MD require target-environment validation.

## Repository

Source, public documentation, tests, synthetic examples and CI are included.
Research structures, local results, virtual environments and machine settings are
excluded. See [CONTRIBUTING.md](CONTRIBUTING.md) for development and upload preparation,
[NOTICE.md](NOTICE.md) for provenance and license status, and the
[citation guide](docs/CITATIONS.md) when publishing results produced with MolForge.
