# Command reference / 指令大全

[Home](../README.md) · [User manual / 用户手册](MANUAL.md)

Find a command below, copy its example, and consult the option table for requirements and defaults.

[English](#english) · [中文](#中文) · [Installer options](MANUAL.md#automatic-environment-setup)

```bash
molforge --lang en --help
molforge conf --help --lang zh
molforge help --all --lang en
export MOLFORGE_LANG=zh
```

An explicit `--lang` overrides `MOLFORGE_LANG`; the default language is English. Command abbreviations are fixed aliases, not arbitrary prefixes.

显式 `--lang` 优先于环境变量，默认语言为英文。简称为固定别名，不支持任意前缀。

| Command / 命令 | Alias / 简称 | English | 中文 |
|---|---|---|---|
| [help](#help-h) | `h` | Browse command help | 查看帮助与指令大全 |
| [doctor](#doctor-dr) | `dr` | Check the active environment | 检查运行环境 |
| [status](#status-st) | `st` | Inspect a result | 查看任务状态和结果位置 |
| [run](#run-batch) | `batch` | Run a batch configuration | 按配置文件批量运行 |
| [conformers](#conformers-conf) | `conf` | Generate and rank 3D conformers | 从 SMILES 生成三维构象 |
| [select](#select-sel) | `sel` | Select one SDF record | 从 SDF 中选取一个构象或姿势 |
| [repair](#repair-rep) | `rep` | Repair missing receptor atoms | 修复受体缺失原子 |
| [dock](#dock-d) | `d` | Run AutoDock-GPU docking | 运行 AutoDock-GPU 对接 |
| [md](#md-sim) | `sim` | Run MD and GBSA analysis | 运行分子动力学与 GBSA 分析 |
| [convert](#convert-conv) | `conv` | Convert a trajectory to PDB | 将轨迹转换为多模型 PDB |
| [hdock](#hdock-hd) | `hd` | Run local HDOCK docking | 运行本地 HDOCK 对接 |
| [runs](#runs-ls) | `ls` | List saved jobs | 浏览已保存任务 |
| [path](#path-p) | `p` | Print a job or artifact path | 获取任务或结果路径 |
| [files](#files-f) | `f` | List output files | 浏览输出文件 |
| [logs](#logs-log) | `log` | Read a log tail | 读取日志末尾 |

## English

### help (h)

Browse command help. Choose a command or print the full reference.

```bash
molforge help
molforge help md
molforge help --all
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | Show help and exit |
| `--lang` | optional / 可选 | Help language: en or zh; overrides MOLFORGE_LANG; `en`, `zh` |
| `topic` | optional / 可选 | Command or alias to look up; omit for the overview; `help`, `doctor`, `status`, `run`, `conformers`, `select`, `repair`, `dock`, `md`, `convert`, `hdock`, `runs`, `path`, `files`, `logs` |
| `--all` | optional / 可选 | Show every command with all options and examples |

### doctor (dr)

Check the active environment. Check required software before submitting calculations.

```bash
molforge doctor --stage conformers
molforge doctor --stage md --accelerator gpu
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | Show help and exit |
| `--lang` | optional / 可选 | Help language: en or zh; overrides MOLFORGE_LANG; `en`, `zh` |
| `--stage` | required / 必填 | Calculation stage to check; `conformers`, `dock`, `md`, `repair`, `convert`, `hdock` |
| `--accelerator` | optional / 可选 | auto: inherit environment; cpu: hide CUDA; gpu: require CUDA build and visible NVIDIA GPU (default: auto); `auto`, `cpu`, `gpu` |
| `--autodock` | optional / 可选 | AutoDock-GPU executable name or absolute path (default: autodock_gpu_128wi) |
| `--autogrid` | optional / 可选 | AutoGrid4 executable name or absolute path (default: autogrid4) |

### status (st)

Inspect a result. Accepts latest, a job ID, a unique name fragment, or a job directory. Running is a recorded state, not a process liveness check.

```bash
molforge status latest
molforge st latest --json
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | Show help and exit |
| `--lang` | optional / 可选 | Help language: en or zh; overrides MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | Root directory for jobs (default: runs) |
| `job` | optional / 可选 | latest, job ID, unique name fragment, or an existing job directory |
| `--json` | optional / 可选 | Output machine-readable JSON (default: off; add flag to enable) |

### runs (ls)

List saved jobs. Show immediate job directories, newest first. Use --stage or --status to filter.

```bash
molforge runs
molforge ls --stage conf --status completed
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | Show help and exit |
| `--lang` | optional / 可选 | Help language: en or zh; overrides MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | Root directory for jobs (default: runs) |
| `--json` | optional / 可选 | Output machine-readable JSON (default: off; add flag to enable) |
| `--limit` | optional / 可选 | Maximum jobs to display, positive integer (default: 20) |
| `--stage` | optional / 可选 | Only show this calculation stage (aliases accepted) (default: not specified); `conformers`, `select`, `dock`, `repair`, `md`, `convert`, `hdock` |
| `--status` | optional / 可选 | Only show this recorded state (default: not specified); `completed`, `failed`, `interrupted`, `running`, `unknown` |

### path (p)

Print a job or artifact path. Prints only a path, suitable for cd or shell variables. Multiple artifact matches require explicit selection.

```bash
molforge path latest
cd "$(molforge p latest)"
molforge p latest --artifact sdf
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | Show help and exit |
| `--lang` | optional / 可选 | Help language: en or zh; overrides MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | Root directory for jobs (default: runs) |
| `job` | optional / 可选 | latest, job ID, unique name fragment, or an existing job directory |
| `--artifact` | optional / 可选 | Artifact key: job, outputs, sdf, ranking, protocol, poses, energy, trajectory (default: job); `job`, `outputs`, `sdf`, `ranking`, `protocol`, `poses`, `energy`, `trajectory` |

### files (f)

List output files. Lists outputs and logs relative to the selected job, including nested docking results.

```bash
molforge files latest
molforge f latest --pattern '*.sdf'
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | Show help and exit |
| `--lang` | optional / 可选 | Help language: en or zh; overrides MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | Root directory for jobs (default: runs) |
| `job` | optional / 可选 | latest, job ID, unique name fragment, or an existing job directory |
| `--json` | optional / 可选 | Output machine-readable JSON (default: off; add flag to enable) |
| `--pattern` | optional / 可选 | Match relative file paths with a glob, e.g. *.sdf (default: *) |

### logs (log)

Read a log tail. Select a relative log path when several logs exist. Reads the last N lines without loading the whole log.

```bash
molforge logs latest --file unigbsa_pipeline.log --lines 50
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | Show help and exit |
| `--lang` | optional / 可选 | Help language: en or zh; overrides MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | Root directory for jobs (default: runs) |
| `job` | optional / 可选 | latest, job ID, unique name fragment, or an existing job directory |
| `--file` | optional / 可选 | Relative log file within the job; omit only when exactly one exists (default: not specified) |
| `--lines` | optional / 可选 | Number of trailing lines, positive integer (default: 50) |

### run (batch)

Run a batch configuration. Run JSON argument arrays sequentially, stopping at the first error. All input files must already exist.

```bash
molforge run --config examples/conformers.json --dry-run
molforge run --config examples/conformers.json
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | Show help and exit |
| `--lang` | optional / 可选 | Help language: en or zh; overrides MOLFORGE_LANG; `en`, `zh` |
| `--config` | required / 必填 | JSON batch configuration file |
| `--dry-run` | optional / 可选 | Validate syntax and input existence without computing (default: off; add flag to enable) |

### conformers (conf)

Generate and rank 3D conformers. Read one SMILES string or file. Writes outputs/conformers.sdf and conformer_ranking.csv.

```bash
molforge conformers --smiles 'CCO' --num-confs 10 --threads 2
molforge conformers --smiles-file ./SMILES.txt --sampling-scheme 'High torsion' --sampling-rounds 2
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | Show help and exit |
| `--lang` | optional / 可选 | Help language: en or zh; overrides MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | Root directory for jobs (default: runs) |
| `--job-name` | optional / 可选 | Readable task name; empty means automatic naming (default: automatic) |
| `--smiles` | one of group / 组内二选一 | One SMILES string; choose either --smiles or --smiles-file (default: not specified) |
| `-f, --smiles-file` | one of group / 组内二选一 | UTF-8 file with one nonempty SMILES line; choose either --smiles or --smiles-file (default: not specified) |
| `-n, --num-confs` | optional / 可选 | Requested retained conformers, positive integer; filtering may retain fewer (default: 100) |
| `--seed` | optional / 可选 | Random seed for reproducible sampling (default: 2026) |
| `-t, --threads` | optional / 可选 | CPU threads, positive integer; stay within your allocation (default: 4) |
| `--prune-rms-thresh` | optional / 可选 | Heavy-atom RMSD diversity threshold in Angstrom (default: 0.5) |
| `--max-iters` | optional / 可选 | Initial MMFF minimization iteration limit; unconverged candidates may receive one extra budget (default: 5000) |
| `--sampling-rounds` | optional / 可选 | Sampling rounds, 1-10 (default: 3) |
| `--embedding-attempts` | optional / 可选 | Positive embedding attempt budget (default: 100) |
| `--sampling-scheme` | optional / 可选 | Standard sampling or random-coordinate High torsion sampling (default: Standard); `Standard`, `High torsion` |

### select (sel)

Select one SDF record. Record numbers start at 1. Writes outputs/selected_ligand.sdf with the original coordinates.

```bash
molforge select --sdf ./ensemble.sdf --record 1
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | Show help and exit |
| `--lang` | optional / 可选 | Help language: en or zh; overrides MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | Root directory for jobs (default: runs) |
| `--job-name` | optional / 可选 | Readable task name; empty means automatic naming (default: automatic) |
| `--sdf` | required / 必填 | SDF containing conformers or poses |
| `--record` | required / 必填 | One-based file record number, not the conf_id property |

### dock (d)

Run AutoDock-GPU docking. Requires receptor PDB, one ligand SDF record and a box. Choose either center coordinates or site residues.

```bash
molforge dock --receptor ./receptor.pdb --ligand ./ligand.sdf --center 10 20 30 --size 22.5 22.5 22.5
molforge dock --receptor ./receptor.pdb --ligand ./ligand.sdf --site-residues A:195,A:203-206 --size 22.5 22.5 22.5 --rigid-macrocycle
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | Show help and exit |
| `--lang` | optional / 可选 | Help language: en or zh; overrides MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | Root directory for jobs (default: runs) |
| `--job-name` | optional / 可选 | Readable task name; empty means automatic naming (default: automatic) |
| `-r, --receptor` | required / 必填 | Receptor PDB file |
| `-l, --ligand` | required / 必填 | One ligand SDF record; use select to extract a record |
| `--center` | one of group / 组内二选一 | Box center X Y Z in Angstrom; mutually exclusive with --site-residues (default: not specified) |
| `--site-residues` | one of group / 组内二选一 | Residues used to calculate the center, e.g. A:195,A:203-206 (default: not specified) |
| `--size` | required / 必填 | Box dimensions X Y Z in Angstrom; each must be >0 and <=95 |
| `--nrun` | optional / 可选 | Positive number of docking searches (default: 200) |
| `--heuristic-max-evaluations` | optional / 可选 | Positive evaluation ceiling per search (default: 12000000) |
| `--seed` | optional / 可选 | Random seed for reproducible sampling (default: not specified) |
| `--rigid-macrocycle` | optional / 可选 | Keep the macrocycle scaffold rigid while allowing available side-chain torsions (default: off; add flag to enable) |
| `--auto-reduce-torsions` | optional / 可选 | Reduce excess side-chain torsions; requires --rigid-macrocycle (default: off; add flag to enable) |
| `--max-ligand-torsions` | optional / 可选 | Target torsion ceiling (1-57) when automatic reduction is enabled (default: 48) |
| `--allow-bad-receptor-residues` | optional / 可选 | Allow Meeko to skip unprocessable residues; review changes to receptor composition (default: off; add flag to enable) |
| `--choose-highest-occupancy-altloc` | optional / 可选 | Select alternate locations by highest summed occupancy (default: off; add flag to enable) |
| `--autodock` | optional / 可选 | AutoDock-GPU executable name or absolute path (default: autodock_gpu_128wi) |
| `--autogrid` | optional / 可选 | AutoGrid4 executable name or absolute path (default: autogrid4) |

### repair (rep)

Repair missing receptor atoms. Add missing atoms and pH 7 hydrogens. Missing residues and loops are not rebuilt. Review the repair report.

```bash
molforge repair --receptor ./receptor.pdb
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | Show help and exit |
| `--lang` | optional / 可选 | Help language: en or zh; overrides MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | Root directory for jobs (default: runs) |
| `--job-name` | optional / 可选 | Readable task name; empty means automatic naming (default: automatic) |
| `-r, --receptor` | required / 必填 | Receptor PDB file |

### md (sim)

Run MD and GBSA analysis. Provide a reviewed receptor and ligand pose in the same coordinate system. Produces per-frame and average energy CSVs.

```bash
molforge md --receptor ./receptor.pdb --ligand ./reviewed_pose.sdf --accelerator cpu --threads 4
molforge md --receptor ./receptor.pdb --ligand ./reviewed_pose.sdf --accelerator gpu --nvt-steps 250000 --npt-steps 250000 --steps 5000000
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | Show help and exit |
| `--lang` | optional / 可选 | Help language: en or zh; overrides MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | Root directory for jobs (default: runs) |
| `--job-name` | optional / 可选 | Readable task name; empty means automatic naming (default: automatic) |
| `-r, --receptor` | required / 必填 | Receptor PDB file |
| `-l, --ligand` | required / 必填 | Reviewed ligand pose: SDF, MOL, MOL2 or PDB |
| `--protein-forcefield` | optional / 可选 | Protein force field supported by the installed MD environment (default: amber03) |
| `--ligand-forcefield` | optional / 可选 | Ligand force field: gaff or gaff2 (default: gaff2) |
| `--box-type` | optional / 可选 | Solvent box: triclinic, cubic, dodecahedron or octahedron (default: triclinic) |
| `--box-distance-nm` | optional / 可选 | Positive distance from solute to box edge in nm (default: 0.9) |
| `--salt-concentration-molar` | optional / 可选 | Nonnegative salt concentration in mol/L (default: 0.15) |
| `--steps` | optional / 可选 | Production steps; duration also depends on the engine timestep (default: 5000000) |
| `--frames` | optional / 可选 | Positive saved frame count, no greater than production steps (default: 1000) |
| `-t, --threads` | optional / 可选 | CPU threads, positive integer; stay within your allocation (default: 4) |
| `--nvt-steps` | optional / 可选 | Positive number of NVT equilibration steps (default: 250000) |
| `--npt-steps` | optional / 可选 | Positive number of NPT equilibration steps (default: 250000) |
| `--accelerator` | optional / 可选 | auto: inherit environment; cpu: hide CUDA; gpu: require CUDA build and visible NVIDIA GPU (default: auto); `auto`, `gpu`, `cpu` |

### convert (conv)

Convert a trajectory to PDB. Topology and trajectory must match. Writes outputs/trajectory_animation.pdb, excluding common water and ion residues.

```bash
molforge convert --topology ./md.tpr --trajectory ./md.xtc
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | Show help and exit |
| `--lang` | optional / 可选 | Help language: en or zh; overrides MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | Root directory for jobs (default: runs) |
| `--job-name` | optional / 可选 | Readable task name; empty means automatic naming (default: automatic) |
| `--topology` | required / 必填 | Matching TPR, PDB or GRO topology |
| `--trajectory` | required / 必填 | XTC or TRR trajectory |

### hdock (hd)

Run local HDOCK docking. Requires suitable receptor and peptide PDB inputs plus local HDOCKlite executables.

```bash
molforge hdock --receptor ./receptor.pdb --ligand ./peptide.pdb --models 100
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | Show help and exit |
| `--lang` | optional / 可选 | Help language: en or zh; overrides MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | Root directory for jobs (default: runs) |
| `--job-name` | optional / 可选 | Readable task name; empty means automatic naming (default: automatic) |
| `-r, --receptor` | required / 必填 | Receptor PDB file |
| `-l, --ligand` | required / 必填 | Ligand PDB suitable for macromolecular docking |
| `--hdock` | optional / 可选 | HDOCK executable name or absolute path (default: hdock) |
| `--createpl` | optional / 可选 | HDOCK createpl executable name or absolute path (default: createpl) |
| `--models` | optional / 可选 | Positive number of HDOCK models to export (default: 100) |


## 中文

### help (h)

查看帮助与指令大全. 无需准备输入文件或安装计算引擎。

```bash
molforge help
molforge help md
molforge help --all
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | 显示帮助并退出 |
| `--lang` | optional / 可选 | 帮助语言 en 或 zh，优先于 MOLFORGE_LANG; `en`, `zh` |
| `topic` | optional / 可选 | 要查询的命令名称；省略时显示命令列表; `help`, `doctor`, `status`, `run`, `conformers`, `select`, `repair`, `dock`, `md`, `convert`, `hdock`, `runs`, `path`, `files`, `logs` |
| `--all` | optional / 可选 | 显示所有命令的完整参数和示例 |

### doctor (dr)

检查运行环境. 在计算前检查所选阶段需要的软件。检查通过后再提交正式任务。

```bash
molforge doctor --stage conformers
molforge doctor --stage md --accelerator gpu
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | 显示帮助并退出 |
| `--lang` | optional / 可选 | 帮助语言 en 或 zh，优先于 MOLFORGE_LANG; `en`, `zh` |
| `--stage` | required / 必填 | 要检查的计算阶段（必填）; `conformers`, `dock`, `md`, `repair`, `convert`, `hdock` |
| `--accelerator` | optional / 可选 | auto 沿用环境；cpu 隐藏 CUDA 设备；gpu 要求 CUDA 构建和可见 NVIDIA GPU（默认：auto）; `auto`, `cpu`, `gpu` |
| `--autodock` | optional / 可选 | AutoDock-GPU 可执行文件名或绝对路径（默认：autodock_gpu_128wi） |
| `--autogrid` | optional / 可选 | AutoGrid4 可执行文件名或绝对路径（默认：autogrid4） |

### status (st)

查看任务状态和结果位置. 支持 latest、任务 ID、唯一名称片段或完整任务目录。记录的 running 不代表进程仍存活。

```bash
molforge status latest
molforge st latest --json
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | 显示帮助并退出 |
| `--lang` | optional / 可选 | 帮助语言 en 或 zh，优先于 MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | 任务保存目录；每次运行自动创建独立子目录（默认：runs） |
| `job` | optional / 可选 | latest、任务 ID、唯一名称片段或已有任务目录 |
| `--json` | optional / 可选 | 输出机器可读的 JSON（默认：关闭；添加此开关以启用） |

### runs (ls)

浏览已保存任务. 按时间倒序列出任务，可按阶段和状态筛选。

```bash
molforge runs
molforge ls --stage conf --status completed
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | 显示帮助并退出 |
| `--lang` | optional / 可选 | 帮助语言 en 或 zh，优先于 MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | 任务保存目录；每次运行自动创建独立子目录（默认：runs） |
| `--json` | optional / 可选 | 输出机器可读的 JSON（默认：关闭；添加此开关以启用） |
| `--limit` | optional / 可选 | 最多显示的任务数，正整数（默认：20） |
| `--stage` | optional / 可选 | 仅显示此计算阶段，支持命令简称（默认：不指定）; `conformers`, `select`, `dock`, `repair`, `md`, `convert`, `hdock` |
| `--status` | optional / 可选 | 仅显示此记录状态（默认：不指定）; `completed`, `failed`, `interrupted`, `running`, `unknown` |

### path (p)

获取任务或结果路径. 只打印路径，方便 cd 和 Shell 变量使用。多个匹配结果时要求明确选择。

```bash
molforge path latest
cd "$(molforge p latest)"
molforge p latest --artifact sdf
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | 显示帮助并退出 |
| `--lang` | optional / 可选 | 帮助语言 en 或 zh，优先于 MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | 任务保存目录；每次运行自动创建独立子目录（默认：runs） |
| `job` | optional / 可选 | latest、任务 ID、唯一名称片段或已有任务目录 |
| `--artifact` | optional / 可选 | 结果类别：job、outputs、sdf、ranking、protocol、poses、energy、trajectory（默认：job）; `job`, `outputs`, `sdf`, `ranking`, `protocol`, `poses`, `energy`, `trajectory` |

### files (f)

浏览输出文件. 列出输出和日志的相对路径，包括嵌套的对接结果。

```bash
molforge files latest
molforge f latest --pattern '*.sdf'
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | 显示帮助并退出 |
| `--lang` | optional / 可选 | 帮助语言 en 或 zh，优先于 MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | 任务保存目录；每次运行自动创建独立子目录（默认：runs） |
| `job` | optional / 可选 | latest、任务 ID、唯一名称片段或已有任务目录 |
| `--json` | optional / 可选 | 输出机器可读的 JSON（默认：关闭；添加此开关以启用） |
| `--pattern` | optional / 可选 | 按相对路径通配符筛选，如 *.sdf（默认：*） |

### logs (log)

读取日志末尾. 有多个日志时需指定相对路径。只读取最后 N 行。

```bash
molforge logs latest --file unigbsa_pipeline.log --lines 50
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | 显示帮助并退出 |
| `--lang` | optional / 可选 | 帮助语言 en 或 zh，优先于 MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | 任务保存目录；每次运行自动创建独立子目录（默认：runs） |
| `job` | optional / 可选 | latest、任务 ID、唯一名称片段或已有任务目录 |
| `--file` | optional / 可选 | 任务内的日志相对路径，仅有一个日志时可省略（默认：不指定） |
| `--lines` | optional / 可选 | 读取日志最后多少行，正整数（默认：50） |

### run (batch)

按配置文件批量运行. 按顺序运行 JSON 中的命令，遇到失败即停止。所有输入文件须事先准备好。

```bash
molforge run --config examples/conformers.json --dry-run
molforge run --config examples/conformers.json
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | 显示帮助并退出 |
| `--lang` | optional / 可选 | 帮助语言 en 或 zh，优先于 MOLFORGE_LANG; `en`, `zh` |
| `--config` | required / 必填 | JSON 批处理配置文件路径（必填） |
| `--dry-run` | optional / 可选 | 仅检查配置格式、命令语法和输入是否存在，不执行计算（默认：关闭；添加此开关以启用） |

### conformers (conf)

从 SMILES 生成三维构象. 对构象进行优化和排序。SMILES 可直接输入，也可从单行文本文件读取。结果保存在 outputs/conformers.sdf 和 outputs/conformer_ranking.csv。

```bash
molforge conformers --smiles 'CCO' --num-confs 10 --threads 2
molforge conformers --smiles-file ./SMILES.txt --sampling-scheme 'High torsion' --sampling-rounds 2
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | 显示帮助并退出 |
| `--lang` | optional / 可选 | 帮助语言 en 或 zh，优先于 MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | 任务保存目录；每次运行自动创建独立子目录（默认：runs） |
| `--job-name` | optional / 可选 | 任务名称；留空时按计算类型自动命名（默认：自动命名） |
| `--smiles` | one of group / 组内二选一 | 一个分子的 SMILES 字符串；与 --smiles-file 二选一，建议用单引号包围（默认：不指定） |
| `-f, --smiles-file` | one of group / 组内二选一 | 仅含一个非空 SMILES 行的 UTF-8 文本文件；与 --smiles 二选一，适合长 SMILES（默认：不指定） |
| `-n, --num-confs` | optional / 可选 | 希望保留的构象数，正整数；去重后实际数量可能更少（默认：100） |
| `--seed` | optional / 可选 | 随机种子；指定相同值有助于重复采样（默认：2026） |
| `-t, --threads` | optional / 可选 | CPU 线程数，正整数；不应超过分配的 CPU 数（默认：4） |
| `--prune-rms-thresh` | optional / 可选 | 重原子 RMSD 去重阈值，单位 Å；增大可提高构象间差异（默认：0.5） |
| `--max-iters` | optional / 可选 | 每个构象的初次能量最小化迭代上限；未收敛候选可再尝试一次（默认：5000） |
| `--sampling-rounds` | optional / 可选 | 采样轮数，1–10；更多轮次需要更长时间（默认：3） |
| `--embedding-attempts` | optional / 可选 | 每轮三维嵌入的尝试预算，正整数（默认：100） |
| `--sampling-scheme` | optional / 可选 | Standard 为常规采样；High torsion 每轮均使用随机坐标，适合高柔性分子（默认：Standard）; `Standard`, `High torsion` |

### select (sel)

从 SDF 中选取一个构象或姿势. 按文件中的记录序号选取，序号从 1 开始。输出 outputs/selected_ligand.sdf。

```bash
molforge select --sdf ./ensemble.sdf --record 1
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | 显示帮助并退出 |
| `--lang` | optional / 可选 | 帮助语言 en 或 zh，优先于 MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | 任务保存目录；每次运行自动创建独立子目录（默认：runs） |
| `--job-name` | optional / 可选 | 任务名称；留空时按计算类型自动命名（默认：自动命名） |
| `--sdf` | required / 必填 | 包含多个构象或姿势的 SDF 文件（必填） |
| `--record` | required / 必填 | 要选取的文件记录序号，从 1 开始；不是 conf_id（必填） |

### dock (d)

运行 AutoDock-GPU 对接. 需要受体 PDB、一个已选取的配体 SDF 记录以及结合位点。中心坐标与位点残基二选一；盒子尺寸必填。

```bash
molforge dock --receptor ./receptor.pdb --ligand ./ligand.sdf --center 10 20 30 --size 22.5 22.5 22.5
molforge dock --receptor ./receptor.pdb --ligand ./ligand.sdf --site-residues A:195,A:203-206 --size 22.5 22.5 22.5 --rigid-macrocycle
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | 显示帮助并退出 |
| `--lang` | optional / 可选 | 帮助语言 en 或 zh，优先于 MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | 任务保存目录；每次运行自动创建独立子目录（默认：runs） |
| `--job-name` | optional / 可选 | 任务名称；留空时按计算类型自动命名（默认：自动命名） |
| `-r, --receptor` | required / 必填 | 受体 PDB 文件路径（必填） |
| `-l, --ligand` | required / 必填 | 单记录配体 SDF 文件（必填）；可先用 molforge select 选取 |
| `--center` | one of group / 组内二选一 | 结合位点中心 X Y Z，单位 Å；与 --site-residues 二选一（默认：不指定） |
| `--site-residues` | one of group / 组内二选一 | 用受体残基计算中心，如 A:195,A:203-206；与 --center 二选一（默认：不指定） |
| `--size` | required / 必填 | 盒子 X Y Z 三个尺寸，单位 Å，每维须大于 0 且不超过 95（必填） |
| `--nrun` | optional / 可选 | 独立对接搜索次数，正整数（默认：200） |
| `--heuristic-max-evaluations` | optional / 可选 | 每次搜索的启发式评估次数上限，正整数（默认：12000000） |
| `--seed` | optional / 可选 | 随机种子；指定相同值有助于重复采样（默认：不指定） |
| `--rigid-macrocycle` | optional / 可选 | 保持大环骨架刚性，同时允许可用的侧链扭转（默认：关闭；添加此开关以启用） |
| `--auto-reduce-torsions` | optional / 可选 | 超过目标扭转数时逐步固定侧链键；必须同时设置 --rigid-macrocycle（默认：关闭；添加此开关以启用） |
| `--max-ligand-torsions` | optional / 可选 | 自动减少扭转时的目标上限，1–57；需启用 --auto-reduce-torsions（默认：48） |
| `--allow-bad-receptor-residues` | optional / 可选 | 允许 Meeko 跳过无法处理的受体残基；可能改变受体组成，请谨慎使用（默认：关闭；添加此开关以启用） |
| `--choose-highest-occupancy-altloc` | optional / 可选 | 对替代构象选择总占有率最高的标识；使用前请检查受体（默认：关闭；添加此开关以启用） |
| `--autodock` | optional / 可选 | AutoDock-GPU 可执行文件名或绝对路径（默认：autodock_gpu_128wi） |
| `--autogrid` | optional / 可选 | AutoGrid4 可执行文件名或绝对路径（默认：autogrid4） |

### repair (rep)

修复受体缺失原子. 输入受体 PDB，补齐缺失原子并加入 pH 7 氢。不会重建缺失的残基或环区。使用结果前请检查修复报告。

```bash
molforge repair --receptor ./receptor.pdb
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | 显示帮助并退出 |
| `--lang` | optional / 可选 | 帮助语言 en 或 zh，优先于 MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | 任务保存目录；每次运行自动创建独立子目录（默认：runs） |
| `--job-name` | optional / 可选 | 任务名称；留空时按计算类型自动命名（默认：自动命名） |
| `-r, --receptor` | required / 必填 | 受体 PDB 文件路径（必填） |

### md (sim)

运行分子动力学与 GBSA 分析. 使用受体和已审阅的配体姿势，两者须在同一坐标系。结果包含逐帧能量与平均能量 CSV。

```bash
molforge md --receptor ./receptor.pdb --ligand ./reviewed_pose.sdf --accelerator cpu --threads 4
molforge md --receptor ./receptor.pdb --ligand ./reviewed_pose.sdf --accelerator gpu --nvt-steps 250000 --npt-steps 250000 --steps 5000000
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | 显示帮助并退出 |
| `--lang` | optional / 可选 | 帮助语言 en 或 zh，优先于 MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | 任务保存目录；每次运行自动创建独立子目录（默认：runs） |
| `--job-name` | optional / 可选 | 任务名称；留空时按计算类型自动命名（默认：自动命名） |
| `-r, --receptor` | required / 必填 | 受体 PDB 文件路径（必填） |
| `-l, --ligand` | required / 必填 | 已审阅的配体姿势，支持 SDF/MOL/MOL2/PDB（必填） |
| `--protein-forcefield` | optional / 可选 | 蛋白力场名称；必须由当前 GROMACS/Uni-GBSA 环境支持（默认：amber03） |
| `--ligand-forcefield` | optional / 可选 | 配体力场：gaff 或 gaff2（默认：gaff2） |
| `--box-type` | optional / 可选 | 溶剂盒形状：triclinic、cubic、dodecahedron 或 octahedron（默认：triclinic） |
| `--box-distance-nm` | optional / 可选 | 溶质到盒边的距离，单位 nm，须大于 0（默认：0.9） |
| `--salt-concentration-molar` | optional / 可选 | 盐浓度，单位 mol/L，须大于或等于 0（默认：0.15） |
| `--steps` | optional / 可选 | 生产模拟步数，正整数；时长还取决于引擎的时间步长（默认：5000000） |
| `--frames` | optional / 可选 | 要求保存的帧数，正整数且不超过生产步数（默认：1000） |
| `-t, --threads` | optional / 可选 | CPU 线程数，正整数；不应超过分配的 CPU 数（默认：4） |
| `--nvt-steps` | optional / 可选 | NVT 平衡步数，正整数（默认：250000） |
| `--npt-steps` | optional / 可选 | NPT 平衡步数，正整数（默认：250000） |
| `--accelerator` | optional / 可选 | auto 沿用环境；cpu 隐藏 CUDA 设备；gpu 要求 CUDA 构建和可见 NVIDIA GPU（默认：auto）; `auto`, `gpu`, `cpu` |

### convert (conv)

将轨迹转换为多模型 PDB. 需要原子数和顺序匹配的拓扑与轨迹。输出 outputs/trajectory_animation.pdb，去除常见水和离子残基。

```bash
molforge convert --topology ./md.tpr --trajectory ./md.xtc
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | 显示帮助并退出 |
| `--lang` | optional / 可选 | 帮助语言 en 或 zh，优先于 MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | 任务保存目录；每次运行自动创建独立子目录（默认：runs） |
| `--job-name` | optional / 可选 | 任务名称；留空时按计算类型自动命名（默认：自动命名） |
| `--topology` | required / 必填 | 与轨迹匹配的 TPR、PDB 或 GRO 文件（必填） |
| `--trajectory` | required / 必填 | XTC 或 TRR 轨迹文件（必填） |

### hdock (hd)

运行本地 HDOCK 对接. 需要受体 PDB、适合宏分子对接的配体 PDB，以及本地 HDOCKlite。输出排名后的复合物 PDB。

```bash
molforge hdock --receptor ./receptor.pdb --ligand ./peptide.pdb --models 100
```

| Option / 参数 | Requirement / 要求 | Description / 说明 |
|---|---|---|
| `-h, --help` | optional / 可选 | 显示帮助并退出 |
| `--lang` | optional / 可选 | 帮助语言 en 或 zh，优先于 MOLFORGE_LANG; `en`, `zh` |
| `-o, --output-root` | optional / 可选 | 任务保存目录；每次运行自动创建独立子目录（默认：runs） |
| `--job-name` | optional / 可选 | 任务名称；留空时按计算类型自动命名（默认：自动命名） |
| `-r, --receptor` | required / 必填 | 受体 PDB 文件路径（必填） |
| `-l, --ligand` | required / 必填 | 适合宏分子对接的配体 PDB 文件（必填） |
| `--hdock` | optional / 可选 | 本地 HDOCK 可执行文件名或绝对路径（默认：hdock） |
| `--createpl` | optional / 可选 | HDOCK createpl 可执行文件名或绝对路径（默认：createpl） |
| `--models` | optional / 可选 | 要导出的 HDOCK 模型数，正整数（默认：100） |
