# MolForge Linux

MolForge is a Linux command-line workflow for ligand conformer generation, receptor repair, molecular docking, molecular dynamics and MM/GBSA analysis. It connects RDKit, Meeko, AutoDock-GPU, PDBFixer and Uni-GBSA/GROMACS, and saves each calculation in its own job directory. It runs in Linux shells, WSL and server batch jobs.

[Installation](#installation) · [Usage](#usage) · [All commands](docs/COMMANDS.md) · [User manual / 用户手册](docs/MANUAL.md) · [Citations](docs/CITATIONS.md)

## Help

```bash
molforge --help                    # List commands
molforge dock --help               # Show docking options and defaults
molforge help --all | less         # Read every command's help
molforge help --all --lang zh      # 中文指令大全
bash scripts/install.sh --help     # Environment installer options
```

English is the default. Add `--lang zh` to a command or set `export MOLFORGE_LANG=zh` for Chinese help. Report reproducible problems through [GitHub Issues](https://github.com/AlanTL-web/MolForge/issues), including the command, software versions and relevant error log.

## Installation

### Linux / WSL

Clone the repository and install the profile needed for your calculation:

```bash
git clone https://github.com/AlanTL-web/MolForge.git
cd MolForge
bash scripts/install.sh --profile conformers --plan
bash scripts/install.sh --profile conformers --yes
```

Follow the activation command printed by the installer, then check the environment:

```bash
molforge doctor --stage conformers
molforge --help
```

The installer checks the selected environment first and installs missing components. It uses the active Conda environment, or creates `.molforge/envs/PROFILE`; use `--prefix /data/envs/molforge` to choose a location. It finds Conda/Mamba or downloads micromamba automatically. A working environment is reused without downloads; resolving an incomplete Conda environment may update its packages.

| Profile | Software installed | Use |
|---|---|---|
| `conformers` | RDKit | Generate and select ligand conformers |
| `dock` | RDKit, Meeko, gemmi, AutoGrid, AutoDock-GPU | Ligand docking |
| `repair` | PDBFixer, OpenMM | Receptor repair |
| `md` | GROMACS, AmberTools, ACPYPE, gmx_MMPBSA, Open Babel, MPI, Uni-GBSA, lickit | MD and MM/GBSA |
| `all` | All profiles above; also checks for HDOCK | Complete workflow |

To install docking or MD dependencies, or inspect an existing environment:

```bash
bash scripts/install.sh --profile dock --yes
bash scripts/install.sh --profile md --prefix /data/envs/molforge-md --yes
bash scripts/install.sh --profile md --prefix /data/envs/molforge-md --check
```

GPU drivers and CUDA/OpenCL device runtimes must be available on the host. The GROMACS package is not guaranteed to support CUDA; check it on the compute node with `molforge doctor --stage md --accelerator gpu`. HDOCK's `hdock` and `createpl` executables must be obtained separately and placed on `PATH`; the `all` profile fails its final check if they are missing. See [environment setup](docs/MANUAL.md#automatic-environment-setup) for backend selection and existing environments.

In WSL, run these commands inside Linux. Windows paths such as `D:\data\ligand.sdf` become `/mnt/d/data/ligand.sdf`.

### Python-only installation

For conformer generation with Python 3.10 or newer, run from the cloned repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[conformers]"
molforge doctor --stage conformers
```

`.[conformers]` installs MolForge and its RDKit extra from the current directory. It does not install AutoDock-GPU, GROMACS or other external engines. Use the installer profiles above for those dependencies.

## Usage

Set an absolute results directory so that results remain easy to find after changing directories:

```bash
export MOLFORGE_RUNS_DIR="$HOME/molforge-runs"
```

### Generate conformers

Generate a small ethanol ensemble:

```bash
molforge conformers --smiles 'CCO' --num-confs 10 --threads 2 --job-name ethanol
molforge path latest --artifact sdf
molforge path latest --artifact ranking
```

For a large ligand, supply a UTF-8 text file containing one SMILES on one nonempty line:

```bash
molforge conformers --smiles-file ./SMILES.txt --num-confs 2 --threads 2 \
  --sampling-scheme 'High torsion' --sampling-rounds 2 \
  --embedding-attempts 20 --max-iters 2000 --seed 2026
```

This small run checks the workflow. Retained conformers may be fewer than requested because of convergence and diversity filtering; inspect the ranking and sampling diagnostics before increasing the sampling budget.

### Select a conformer and repair a receptor

Extract one SDF record, preserving its coordinates, and repair missing receptor atoms:

```bash
molforge select --sdf ./ensemble.sdf --record 1
molforge path latest --artifact sdf
molforge repair --receptor ./receptor.pdb
```

`--record` is a one-based file record number. Repair adds missing atoms and pH 7 hydrogens; it does not rebuild missing residues or loops. Review the repaired structure before docking.

### Dock a ligand

Dock a single-record ligand SDF into a receptor binding site:

```bash
molforge dock --receptor ./receptor.pdb --ligand ./selected_ligand.sdf \
  --center 10 20 30 --size 22.5 22.5 22.5 --nrun 200
```

Replace the example coordinates with your site center. Center and box dimensions are in Å. Alternatively, use `--site-residues 'A:195,A:203-206'` in place of `--center`.

### Keep a macrocycle rigid and reduce rotatable bonds

Preserve the input ring conformation and reduce active side-chain torsions to a target ceiling:

```bash
molforge dock --receptor ./receptor.pdb --ligand ./selected_ligand.sdf \
  --center 10 20 30 --size 22.5 22.5 22.5 \
  --rigid-macrocycle --auto-reduce-torsions --max-ligand-torsions 48
```

`--rigid-macrocycle` fixes the ring scaffold. `--auto-reduce-torsions` progressively freezes side-chain bonds from rings outward until the ceiling is reached, or fails if it cannot reach it. This reduces docking flexibility; it is not torsional-energy minimization. Both options are off by default.

### Run local HDOCK

Dock suitable macromolecular PDB inputs using separately installed HDOCKlite:

```bash
molforge hdock --receptor ./receptor.pdb --ligand ./peptide.pdb --models 100
```

### Run MD and MM/GBSA

Use a reviewed ligand pose and receptor in the same coordinate system:

```bash
molforge doctor --stage md --accelerator gpu
molforge md --receptor ./receptor.pdb --ligand ./reviewed_pose.sdf \
  --threads 4 --accelerator gpu --nvt-steps 250000 --npt-steps 250000 \
  --steps 5000000 --frames 1000
molforge path latest --artifact energy
```

Use `--accelerator cpu` for CPU execution. Simulation duration depends on the engine timestep; step counts alone do not define a duration. MM/GBSA output is an endpoint energy estimate. See [MD settings and interpretation](docs/MANUAL.md#md-and-trajectory-conversion).

### Convert a trajectory

```bash
molforge convert --topology ./md.tpr --trajectory ./md.xtc
```

Topology and trajectory must have matching atom order. Outputs include a system PDB, animation PDB and filtering report.

### Find results and logs

```bash
molforge runs --status completed
molforge status latest
molforge files latest --pattern '*.sdf'
molforge path latest --artifact poses
molforge logs latest --lines 50
```

`latest` selects the newest job, which may have failed. Use a full job ID from `molforge runs` to select a particular result. Keep the full job directory, including inputs, parameters, environment records and logs.

### Batch jobs and Slurm

```bash
molforge run --config examples/conformers.json --dry-run
molforge run --config examples/conformers.json
sbatch scripts/slurm-md.sh /data/receptor.pdb /data/reviewed_pose.sdf /scratch/results
```

Batch commands run sequentially and stop on failure. Adapt the Slurm script's account, partition and environment to your cluster before submission.

## All options

The [complete command reference](docs/COMMANDS.md) lists every CLI option, requirement and default in English and Chinese. The [user manual](docs/MANUAL.md) covers installation details, output selection, scientific settings and troubleshooting.

## Citation

Cite MolForge using [CITATION.cff](CITATION.cff) and cite the scientific packages used in your calculation. The [citation guide](docs/CITATIONS.md) groups the upstream references by workflow stage and explains version-specific citations.

## Validation and license

Native conformer smoke tests have run in WSL Ubuntu 24.04, including two large ligands. Full GPU docking and long MD require validation in the target environment. Small smoke tests do not establish scientific convergence.

MolForge-owned source is distributed under the [MIT License](LICENSE). Dependencies retain their own licenses; see [software notices](NOTICE.md). Development and release instructions are in [CONTRIBUTING.md](CONTRIBUTING.md).
