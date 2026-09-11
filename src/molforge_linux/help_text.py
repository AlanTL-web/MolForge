"""User-facing command descriptions shared by terminal help and the reference manual."""
from .i18n import ALIASES, COMMANDS_EN, OPTIONS_EN

COMMANDS = {
    'help': ('查看帮助与指令大全', '无需准备输入文件或安装计算引擎。', 'molforge help\nmolforge help md\nmolforge help --all'),
    'doctor': ('检查运行环境', '在计算前检查所选阶段需要的软件。检查通过后再提交正式任务。', 'molforge doctor --stage conformers\nmolforge doctor --stage md --accelerator gpu'),
    'status': ('查看任务状态和结果位置', '使用运行结束时打印的任务目录，查看完成、失败或运行中状态。', 'molforge status ./runs/你的任务目录'),
    'run': ('按配置文件批量运行', '按顺序运行 JSON 中的命令，遇到失败即停止。所有输入文件须事先准备好。', 'molforge run --config examples/conformers.json --dry-run\nmolforge run --config examples/conformers.json'),
    'conformers': ('从 SMILES 生成三维构象', '对构象进行优化和排序。SMILES 可直接输入，也可从单行文本文件读取。结果保存在 outputs/conformers.sdf 和 outputs/conformer_ranking.csv。', "molforge conformers --smiles 'CCO' --num-confs 10 --threads 2\nmolforge conformers --smiles-file ./SMILES.txt --sampling-scheme 'High torsion' --sampling-rounds 2"),
    'select': ('从 SDF 中选取一个构象或姿势', '按文件中的记录序号选取，序号从 1 开始。输出 outputs/selected_ligand.sdf。', 'molforge select --sdf ./ensemble.sdf --record 1'),
    'repair': ('修复受体缺失原子', '输入受体 PDB，补齐缺失原子并加入 pH 7 氢。不会重建缺失的残基或环区。使用结果前请检查修复报告。', 'molforge repair --receptor ./receptor.pdb'),
    'dock': ('运行 AutoDock-GPU 对接', '需要受体 PDB、一个已选取的配体 SDF 记录以及结合位点。中心坐标与位点残基二选一；盒子尺寸必填。', 'molforge dock --receptor ./receptor.pdb --ligand ./ligand.sdf --center 10 20 30 --size 22.5 22.5 22.5\nmolforge dock --receptor ./receptor.pdb --ligand ./ligand.sdf --site-residues A:195,A:203-206 --size 22.5 22.5 22.5 --rigid-macrocycle'),
    'md': ('运行分子动力学与 GBSA 分析', '使用受体和已审阅的配体姿势，两者须在同一坐标系。结果包含逐帧能量与平均能量 CSV。', 'molforge md --receptor ./receptor.pdb --ligand ./reviewed_pose.sdf --accelerator cpu --threads 4\nmolforge md --receptor ./receptor.pdb --ligand ./reviewed_pose.sdf --accelerator gpu --nvt-steps 250000 --npt-steps 250000 --steps 5000000'),
    'convert': ('将轨迹转换为多模型 PDB', '需要原子数和顺序匹配的拓扑与轨迹。输出 outputs/trajectory_animation.pdb，去除常见水和离子残基。', 'molforge convert --topology ./md.tpr --trajectory ./md.xtc'),
    'hdock': ('运行本地 HDOCK 对接', '需要受体 PDB、适合宏分子对接的配体 PDB，以及本地 HDOCKlite。输出排名后的复合物 PDB。', 'molforge hdock --receptor ./receptor.pdb --ligand ./peptide.pdb --models 100'),
}

OPTIONS = {
    'help': '显示帮助并退出',
    'version': '显示安装版本并退出',
    'topic': '要查询的命令名称；省略时显示命令列表',
    'all': '显示所有命令的完整参数和示例',
    'output_root': '任务保存目录；每次运行自动创建独立子目录',
    'job_name': '任务名称；留空时按计算类型自动命名',
    'receptor': '受体 PDB 文件路径（必填）',
    'ligand': '配体文件路径（必填）',
    'smiles': '一个分子的 SMILES 字符串；与 --smiles-file 二选一，建议用单引号包围',
    'smiles_file': '仅含一个非空 SMILES 行的 UTF-8 文本文件；与 --smiles 二选一，适合长 SMILES',
    'num_confs': '希望保留的构象数，正整数；去重后实际数量可能更少',
    'seed': '随机种子；指定相同值有助于重复采样',
    'threads': 'CPU 线程数，正整数；不应超过分配的 CPU 数',
    'prune_rms_thresh': '重原子 RMSD 去重阈值，单位 Å；增大可提高构象间差异',
    'max_iters': '每个构象的初次能量最小化迭代上限；未收敛候选可再尝试一次',
    'sampling_rounds': '采样轮数，1–10；更多轮次需要更长时间',
    'embedding_attempts': '每轮三维嵌入的尝试预算，正整数',
    'sampling_scheme': 'Standard 为常规采样；High torsion 每轮均使用随机坐标，适合高柔性分子',
    'sdf': '包含多个构象或姿势的 SDF 文件（必填）',
    'record': '要选取的文件记录序号，从 1 开始；不是 conf_id（必填）',
    'center': '结合位点中心 X Y Z，单位 Å；与 --site-residues 二选一',
    'site_residues': '用受体残基计算中心，如 A:195,A:203-206；与 --center 二选一',
    'size': '盒子 X Y Z 三个尺寸，单位 Å，每维须大于 0 且不超过 95（必填）',
    'nrun': '独立对接搜索次数，正整数',
    'heuristic_max_evaluations': '每次搜索的启发式评估次数上限，正整数',
    'rigid_macrocycle': '保持大环骨架刚性，同时允许可用的侧链扭转',
    'auto_reduce_torsions': '超过目标扭转数时逐步固定侧链键；必须同时设置 --rigid-macrocycle',
    'max_ligand_torsions': '自动减少扭转时的目标上限，1–57；需启用 --auto-reduce-torsions',
    'allow_bad_receptor_residues': '允许 Meeko 跳过无法处理的受体残基；可能改变受体组成，请谨慎使用',
    'choose_highest_occupancy_altloc': '对替代构象选择总占有率最高的标识；使用前请检查受体',
    'autodock': 'AutoDock-GPU 可执行文件名或绝对路径',
    'autogrid': 'AutoGrid4 可执行文件名或绝对路径',
    'protein_forcefield': '蛋白力场名称；必须由当前 GROMACS/Uni-GBSA 环境支持',
    'ligand_forcefield': '配体力场：gaff 或 gaff2',
    'box_type': '溶剂盒形状：triclinic、cubic、dodecahedron 或 octahedron',
    'box_distance_nm': '溶质到盒边的距离，单位 nm，须大于 0',
    'salt_concentration_molar': '盐浓度，单位 mol/L，须大于或等于 0',
    'nvt_steps': 'NVT 平衡步数，正整数',
    'npt_steps': 'NPT 平衡步数，正整数',
    'steps': '生产模拟步数，正整数；时长还取决于引擎的时间步长',
    'frames': '要求保存的帧数，正整数且不超过生产步数',
    'accelerator': 'auto 沿用环境；cpu 隐藏 CUDA 设备；gpu 要求 CUDA 构建和可见 NVIDIA GPU',
    'topology': '与轨迹匹配的 TPR、PDB 或 GRO 文件（必填）',
    'trajectory': 'XTC 或 TRR 轨迹文件（必填）',
    'hdock': '本地 HDOCK 可执行文件名或绝对路径',
    'createpl': 'HDOCK createpl 可执行文件名或绝对路径',
    'models': '要导出的 HDOCK 模型数，正整数',
    'check_stage': '要检查的计算阶段（必填）',
    'job': '运行时打印的完整任务目录（必填）',
    'config': 'JSON 批处理配置文件路径（必填）',
    'dry_run': '仅检查配置格式、命令语法和输入是否存在，不执行计算',
}

COMMANDS.update({
    'runs': ('浏览已保存任务', '按时间倒序列出任务，可按阶段和状态筛选。', 'molforge runs\nmolforge ls --stage conf --status completed'),
    'path': ('获取任务或结果路径', '只打印路径，方便 cd 和 Shell 变量使用。多个匹配结果时要求明确选择。', 'molforge path latest\ncd "$(molforge p latest)"\nmolforge p latest --artifact sdf'),
    'files': ('浏览输出文件', '列出输出和日志的相对路径，包括嵌套的对接结果。', "molforge files latest\nmolforge f latest --pattern '*.sdf'"),
    'logs': ('读取日志末尾', '有多个日志时需指定相对路径。只读取最后 N 行。', 'molforge logs latest --file unigbsa_pipeline.log --lines 50'),
})
COMMANDS['status'] = ('查看任务状态和结果位置', '支持 latest、任务 ID、唯一名称片段或完整任务目录。记录的 running 不代表进程仍存活。', 'molforge status latest\nmolforge st latest --json')
OPTIONS.update({
    'lang': '帮助语言 en 或 zh，优先于 MOLFORGE_LANG',
    'job': 'latest、任务 ID、唯一名称片段或已有任务目录',
    'json': '输出机器可读的 JSON', 'limit': '最多显示的任务数，正整数',
    'filter_stage': '仅显示此计算阶段，支持命令简称', 'filter_status': '仅显示此记录状态',
    'artifact': '结果类别：job、outputs、sdf、ranking、protocol、poses、energy、trajectory',
    'pattern': '按相对路径通配符筛选，如 *.sdf', 'log_file': '任务内的日志相对路径，仅有一个日志时可省略',
    'lines': '读取日志最后多少行，正整数',
})


def catalog(lang):
    if lang == 'zh':
        return COMMANDS
    return {name: (*COMMANDS_EN[name], entry[2]) for name, entry in COMMANDS.items()}


def decorate(parser, subparsers, lang='en'):
    """Keep descriptions and defaults attached to actual argparse options."""
    options = OPTIONS if lang == 'zh' else OPTIONS_EN
    for action in parser._actions:
        if action.dest in options:
            action.help = options[action.dest]
    for name, child in subparsers.choices.items():
        if name not in COMMANDS:
            continue
        title, detail, examples = catalog(lang)[name]
        child.description = title + '\n\n' + detail
        child.epilog = ('示例：\n' if lang == 'zh' else 'Examples:\n') + examples + '\n\nmolforge help --all'
        child.epilog += ('\n简称：' if lang == 'zh' else '\nAlias: ') + ALIASES[name]
        child._positionals.title = '位置参数' if lang == 'zh' else 'positional arguments'
        child._optionals.title = '选项' if lang == 'zh' else 'options'
        for action in child._actions:
            if action.dest in options:
                action.help = options[action.dest]
            if action.dest == 'ligand':
                action.help = ({'dock': '单记录配体 SDF 文件（必填）；可先用 molforge select 选取',
                               'md': '已审阅的配体姿势，支持 SDF/MOL/MOL2/PDB（必填）',
                               'hdock': '适合宏分子对接的配体 PDB 文件（必填）'} if lang == 'zh' else {
                               'dock': 'One ligand SDF record; use select to extract a record',
                               'md': 'Reviewed ligand pose: SDF, MOL, MOL2 or PDB',
                               'hdock': 'Ligand PDB suitable for macromolecular docking'})[name]
            if not action.required and action.option_strings and action.dest not in {'help', 'all', 'lang'}:
                value = action.default
                if value is False:
                    label = '关闭；添加此开关以启用' if lang == 'zh' else 'off; add flag to enable'
                elif value is None:
                    label = '不指定' if lang == 'zh' else 'not specified'
                elif value == '':
                    label = '自动命名' if lang == 'zh' else 'automatic'
                else:
                    label = str(value)
                action.help += f'（默认：{label}）' if lang == 'zh' else f' (default: {label})'


def subcommands(parser):
    import argparse
    return {name: child for name, child in next(a.choices for a in parser._actions if isinstance(a, argparse._SubParsersAction)).items() if name in COMMANDS}


def full_help(parser):
    return parser.format_help() + '\n' + '\n'.join(
        '=' * 72 + '\n' + child.format_help() for child in subcommands(parser).values())
