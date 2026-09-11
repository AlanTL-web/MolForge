# User manual / 用户手册

[Home / 首页](../README.md) · [Complete command reference / 指令大全](COMMANDS.md) · [Citations / 引用](CITATIONS.md)

This manual combines installation, everyday commands, result navigation, batch jobs,
Slurm, troubleshooting and validation notes. The command reference contains every
option in both English and Chinese.

## Install

Clone the GitHub repository and create a Linux environment:

```bash
git clone https://github.com/AlanTL-web/MolForge.git
cd MolForge
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[conformers]"
molforge doctor --stage conformers
```

If Git is unavailable, download the source archive from GitHub, unpack it, enter the
unpacked directory, and start at `python3 -m venv .venv`. Do not run installation
commands from a parent directory because `.[conformers]` refers to the current checkout.

On subsequent logins, activate the same environment. If Ubuntu lacks venv, install
`python3-venv`. An alternative used in native WSL validation is Ubuntu's
`python3-rdkit` with a venv created using `--system-site-packages`; then install
MolForge with `python -m pip install --no-deps .`. This lets that venv read the
distribution RDKit without downloading a separate wheel.

From Windows, first enter Linux using `wsl -d Ubuntu-24.04`. A Windows path such as
`D:\data\SMILES.txt` is normally `/mnt/d/data/SMILES.txt` inside WSL. On a remote Linux
server, use the actual server paths instead.

| Stage | Required software | Check |
|---|---|---|
| conformers / select | RDKit | `molforge dr --stage conformers` |
| dock | RDKit, Meeko, gemmi, AutoGrid4, AutoDock-GPU | `molforge dr --stage dock` |
| repair | PDBFixer, OpenMM | `molforge dr --stage repair` |
| md | Uni-GBSA, GROMACS, AmberTools and the installed Uni-GBSA analysis dependencies | `molforge dr --stage md` |
| convert | GROMACS, available as gmx | `molforge dr --stage convert` |
| hdock | local hdock and createpl | `molforge dr --stage hdock` |

`pip install '.[dock]'` installs Python docking dependencies, not the docking engines.
Use your server's established MD environment and install MolForge there as well.
Meeko scripts must be executable on PATH and use the intended Python environment.
Use `--autodock /path/to/binary --autogrid /path/to/autogrid4` for custom engine paths.
MD and conversion find `gmx` on PATH; load the corresponding server module first.

## Help, language and short commands

```bash
molforge --lang en --help
molforge conf --help --lang zh
molforge help conf --lang en
molforge help --all --lang zh | less
export MOLFORGE_LANG=zh
```

Both positions of `--lang` work, including after `--help`. Explicit language wins
over the environment, and English is used otherwise. Scientific parameter values
such as `High torsion` remain unchanged in either language. Help text and navigation
labels are translated; underlying engine errors may still be English.

| Full command | Alias | Full command | Alias |
|---|---|---|---|
| conformers | conf | select | sel |
| repair | rep | dock | d |
| hdock | hd | md | sim |
| convert | conv | doctor | dr |
| run | batch | help | h |
| runs | ls | status | st |
| path | p | files | f |
| logs | log | | |

Short options include `-o` output root, `-n` conformer count, `-t` CPU threads,
`-f` SMILES file, `-r` receptor and `-l` ligand where those inputs apply. Arbitrary
prefix abbreviations are rejected to avoid ambiguous scientific settings.

## First conformer calculation

```bash
export MOLFORGE_RUNS_DIR="$HOME/molforge-runs"
molforge conf --smiles 'CCO' -n 10 -t 2 --job-name ethanol
molforge st latest
molforge p latest --artifact sdf
molforge p latest --artifact ranking
```

The SDF contains retained 3D conformers; the ranking CSV contains MMFF94s energies.
The protocol and sampling diagnostics describe the actual settings and convergence.
Filtering may retain fewer than requested. Energies should only be compared within
the same molecular species.

For long SMILES, use a UTF-8 file containing exactly one nonempty line:

```bash
molforge conf -f ./SMILES.txt -n 2 -t 2 --seed 2026 \
  --sampling-scheme 'High torsion' --sampling-rounds 2 \
  --embedding-attempts 20 --max-iters 2000 --prune-rms-thresh 1.0
```

This is a small pipeline check. In prior native Linux checks of two very large
ligands, 200, 500 and 1000 MMFF iterations failed to converge the first ligand;
2000 succeeded for both. It is not a universal minimum or a production recommendation.
Unconverged candidates can receive one additional minimization budget before exclusion.

## Find, inspect and enter results

```bash
molforge ls
molforge ls --stage conf --status completed --limit 10
molforge st latest
molforge st ethanol
molforge f latest --pattern '*.sdf'
molforge p latest --artifact protocol
molforge st latest --json
```

The results root is selected by `-o/--output-root`, then `MOLFORGE_RUNS_DIR`, then
`./runs`. `latest` means the newest immediate job directory by its timestamped ID;
it can be failed or still running. Use `runs --status completed` to find successful
jobs, then pass the chosen full ID. Name fragments must match only one job; otherwise
the command lists candidates and fails instead of guessing.

```bash
cd "$(molforge p latest)"
```

Set an absolute `MOLFORGE_RUNS_DIR` before changing directory, or continue to pass
`-o /absolute/results/root`. Otherwise `./runs` follows your new working directory.
The command prints a path; it cannot change the parent shell's directory itself.

You can also store a path:

```bash
job=$(molforge p latest)
echo "$job"
molforge st "$job"
```

`job=...` assigns a variable; `"$job"` reads its value; `echo job` prints the literal
word. There must be no spaces around `=`. Quoting preserves paths with spaces.
You never need to rerun a calculation just to recover its directory.

Artifact keys are `job`, `outputs`, `sdf`, `ranking`, `protocol`, `poses`, `energy`
and `trajectory`. Paths are discovered from the actual job contents, so copied jobs
do not depend on the original machine's paths. If several files match, use `files`
to choose one explicitly. Discovery is read-only and does not follow file symlinks.

## Select, repair and dock

Review the SDF before choosing a one-based file record (not its conf_id property):

```bash
molforge sel --sdf ./ensemble.sdf --record 1 --job-name selected-ligand
molforge p latest --artifact sdf
molforge rep -r ./receptor.pdb
```

Selection keeps the record's coordinates. Repair outputs `receptor_repaired.pdb`
and `repair_report.json`; it adds missing atoms and pH 7 hydrogens but does not
rebuild missing residues or loops. Review the repaired structure before using it.

```bash
molforge d -r ./receptor.pdb -l ./selected_ligand.sdf \
  --center 10 20 30 --size 22.5 22.5 22.5 --nrun 200
molforge p latest --artifact poses
molforge f latest --pattern '*.pdb'
```

Replace all example file paths and center coordinates with your inputs. Center and
size are in Angstrom; box dimensions must be >0 and <=95. You may replace `--center`
with `--site-residues 'A:195,A:203-206'`. Only one center method is allowed.
`--rigid-macrocycle` fixes the ring scaffold. `--auto-reduce-torsions` additionally
reduces side-chain torsions and requires that flag; both are off unless requested.

Local HDOCK accepts suitable macromolecular PDB inputs:

```bash
molforge hd -r ./receptor.pdb -l ./peptide.pdb --models 100
```

Generic single-residue UNL PDB files are not established HDOCK inputs. This package
does not submit structures to remote HDOCK or HighFold3 services.

## MD and trajectory conversion

Use a reviewed ligand pose and matching receptor in the same coordinate system:

```bash
molforge dr --stage md --accelerator gpu
molforge sim -r ./receptor.pdb -l ./reviewed_pose.sdf -t 4 \
  --accelerator gpu --nvt-steps 250000 --npt-steps 250000 \
  --steps 5000000 --frames 1000
molforge p latest --artifact energy
molforge log latest --file unigbsa_pipeline.log --lines 50
molforge conv --topology ./md.tpr --trajectory ./md.xtc
```

Defaults are Amber03/GAFF2, BCC ligand charge, triclinic box with 0.9 nm distance,
0.15 mol/L salt, and GB/igb=2/internal dielectric 4/external dielectric 80.
The intended analysis excludes entropy correction; check the installed engine's
generated settings. Integrator, timestep and restraints come from its templates.
Steps alone do not specify a fixed duration. TOTAL is an endpoint energy estimate,
not complete Gibbs free energy. `Frames_used` reports successful numeric frames
included in each ligand/mode average. Intermediate files are retained.

`gpu` preflight requires CUDA support and visible NVIDIA hardware; actual utilization
must be checked in engine logs. `cpu` hides CUDA devices. `auto` preserves the
environment. No mode automatically aligns the receptor and ligand or proves convergence.

Conversion requires matching topology/trajectory atom order. TPR applies molecular
periodic-boundary processing and System-group centering; PDB/GRO does not. Outputs
include full-system `system.pdb`, filtered `trajectory_animation.pdb` and a filtering
report. Large input trajectories are read and hashed without copying them.

## Batch and Slurm

```bash
molforge batch --config examples/conformers.json --dry-run
molforge batch --config examples/conformers.json
```

JSON contains one `commands` array of argument arrays. Full names and aliases work.
Tasks run sequentially and stop on the first failure. Inputs must exist before
starting, and relative paths refer to the current working directory. Shell variables,
pipes and automatic references to newly generated jobs are not evaluated.

```bash
sbatch scripts/slurm-md.sh /data/receptor.pdb /data/reviewed_pose.sdf /scratch/results
```

Adapt account, partition, time and environment activation to the cluster. The sample
requests one GPU and four CPU threads. It preserves GPU allocation and passes the
allocated CPU count to MD. For CPU jobs, remove the GPU resource request and change
both accelerator arguments to cpu. Do not launch duplicate MolForge processes with
multiple MPI ranks for a single job.

## Troubleshooting and files to keep

| Symptom | Action |
|---|---|
| molforge not found | Activate the installation environment; try `python -m molforge_linux --help` |
| Missing package or engine | Run doctor for that stage; install into the same environment or correct PATH |
| No converged conformers | Inspect sampling_diagnostics.json; explicitly increase minimization/sampling budget |
| Too few conformers | Check convergence and diversity filtering; fewer retained records can be expected |
| No jobs found | Set the correct output root; absolute paths remain valid after changing directories |
| Ambiguous result name | Use the full ID from `molforge ls` |
| No log / several logs | Use `molforge f JOB --pattern '*.log'` and select `--file` |
| GPU check fails | Check node allocation and CUDA GROMACS build; CPU mode is available |
| Interrupted job still says running | Check the scheduler/process; saved state alone does not prove liveness |
| Chinese text garbled | Use a UTF-8 terminal, or choose `--lang en` |

Keep the entire job directory: inputs, outputs, parameters, environment, logs and
manifest. External trajectories need separate archiving. No automatic checkpoint
resume or cleanup is provided; rerunning starts a new task. Exit codes: 0 success,
1 runtime error, 2 syntax error, 130 caught Ctrl+C. Engine logs may be buffered during
long docking steps. `logs` prints a snapshot; use `tail -f` on the real path to follow.

## 中文快速操作

本手册已合并安装、运行、结果管理、批处理和故障排查。所有参数的中文解释见
[指令大全的中文部分](COMMANDS.md#中文)。

```bash
git clone https://github.com/AlanTL-web/MolForge.git
cd MolForge
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[conformers]"
export MOLFORGE_LANG=zh
export MOLFORGE_RUNS_DIR="$HOME/molforge-runs"
molforge conf --help
molforge conf --smiles 'CCO' -n 10 -t 2 --job-name ethanol
molforge ls
molforge st latest
molforge p latest --artifact sdf
```

`--lang en` 或 `--lang zh` 可以放在命令前后，甚至放在 `--help` 后。显式选择优先于
`MOLFORGE_LANG`，默认英文。语言只影响帮助和导航文字，科学参数值不变。

长 SMILES 使用 `-f ./SMILES.txt`（文件只允许一个非空行），避免引号问题。常用简称为
`conf` 构象、`sel` 选择、`rep` 修复、`d` 对接、`sim` MD、`conv` 转换、`dr` 环境检查、
`ls` 任务列表、`st` 状态、`p` 路径、`f` 文件、`log` 日志。完整命令名继续有效。

结果目录由 `-o`、`MOLFORGE_RUNS_DIR`、当前目录下 `runs` 依次决定。`latest` 是最新任务，
并不保证成功；用 `molforge ls --status completed` 找到成功任务的 ID 后再选择。
也可传入唯一名称片段或绝对任务路径。多个匹配时会要求明确选择，不会猜测。

```bash
molforge f latest --pattern '*.sdf'
molforge p latest --artifact ranking
cd "$(molforge p latest)"
```

切换目录前建议设置绝对结果根目录。`job=$(命令)` 把输出保存为变量，`"$job"` 读取值，
`echo job` 只打印单词 job。无需为了找回路径重新计算。

对接前选择单记录 SDF；受体修复后检查报告；MD 必须使用与受体坐标匹配的已审阅姿势。
冒烟测试只验证软件流程，少量构象和短时间 MD 不代表科学收敛。缺少引擎时运行对应的
`doctor` 检查。失败后保留目录和日志；本版不自动断点续跑。详尽科学默认值和所有命令示例
均保存在同一份[双语指令大全](COMMANDS.md)。

发表使用本流程所得结果时，请按[引用指南](CITATIONS.md)记录实际软件版本，并引用此次
运行真正使用的科学软件。MolForge 不会自动安装或打包外部对接与分子动力学引擎。
