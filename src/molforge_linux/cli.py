"""Public CLI; help and configuration validation need no molecular packages."""
import argparse
from contextlib import redirect_stdout
from dataclasses import fields
import json
import os
from pathlib import Path
import sys

from molforge_core.md_config import UniGBSAMDParameters
from .runtime import dump, evidence, executable, md_preflight
from .help_text import COMMANDS, ALIASES, catalog, decorate, full_help, subcommands

REVERSE_ALIASES = {value: key for key, value in ALIASES.items()}


def canonical(value):
    return REVERSE_ALIASES.get(value, value)


def positive(value):
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError('Must be a positive integer.')
    return result


class HelpParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('formatter_class', argparse.RawTextHelpFormatter)
        kwargs.setdefault('allow_abbrev', False)
        super().__init__(*args, **kwargs)


def input_file(value):
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f'Input file does not exist: {path}')
    return path


def parser(lang='en'):
    p = HelpParser(prog='molforge', description='MolForge — Linux 分子计算命令行工具\n构象生成 · 受体修复 · 分子对接 · 分子动力学 · 轨迹转换',
        epilog="首次运行：molforge conformers --smiles 'CCO' --num-confs 10\n单条命令帮助：molforge md --help 或 molforge help md\n完整指令大全：molforge help --all\n版本查询：molforge --version")
    if lang == 'en':
        p.description = 'MolForge — Linux molecular workflow CLI\nConformers, docking, molecular dynamics and result browsing'
        p.epilog = "Start: molforge conf --smiles 'CCO' -n 10\nHelp: molforge help md --lang en\nFull reference: molforge help --all\nLanguage: --lang en|zh or MOLFORGE_LANG"
    p._positionals.title = '位置参数' if lang == 'zh' else 'positional arguments'
    p._optionals.title = '选项' if lang == 'zh' else 'options'
    p.add_argument('--version', action='version', version='molforge-linux 1.1.0')
    p.add_argument('--lang', choices=['en', 'zh'], default=lang)
    sub = p.add_subparsers(dest='stage', required=True)
    def add(name):
        child = sub.add_parser(name, aliases=[ALIASES[name]], help=catalog(lang)[name][0])
        child.set_defaults(stage=name)
        child.add_argument('--lang', choices=['en', 'zh'], default=argparse.SUPPRESS)
        return child

    helper = add('help')
    helper.add_argument('topic', nargs='?', type=canonical, choices=list(COMMANDS))
    helper.add_argument('--all', action='store_true')
    doctor = add('doctor')
    doctor.add_argument('--stage', dest='check_stage', choices=['conformers', 'dock', 'md', 'repair', 'convert', 'hdock'], required=True)
    doctor.add_argument('--accelerator', choices=['auto', 'cpu', 'gpu'], default='auto')
    doctor.add_argument('--autodock', default='autodock_gpu_128wi')
    doctor.add_argument('--autogrid', default='autogrid4')
    for name in ('status', 'runs', 'path', 'files', 'logs'):
        nav = add(name)
        nav.add_argument('-o', '--output-root', type=Path, default=Path(os.getenv('MOLFORGE_RUNS_DIR', 'runs')))
        if name != 'runs':
            nav.add_argument('job', nargs='?', default='latest')
        if name in ('status', 'runs', 'files'):
            nav.add_argument('--json', action='store_true')
        if name == 'runs':
            nav.add_argument('--limit', type=positive, default=20)
            nav.add_argument('--stage', dest='filter_stage', type=canonical, choices=['conformers', 'select', 'dock', 'repair', 'md', 'convert', 'hdock'])
            nav.add_argument('--status', dest='filter_status', choices=['completed', 'failed', 'interrupted', 'running', 'unknown'])
        if name == 'path':
            nav.add_argument('--artifact', choices=['job', 'outputs', 'sdf', 'ranking', 'protocol', 'poses', 'energy', 'trajectory'], default='job')
        if name == 'files':
            nav.add_argument('--pattern', default='*')
        if name == 'logs':
            nav.add_argument('--file', dest='log_file')
            nav.add_argument('--lines', type=positive, default=50)
    batch = add('run')
    batch.add_argument('--config', type=input_file, required=True)
    batch.add_argument('--dry-run', action='store_true', help='Validate syntax without running calculations')
    for name in ('conformers', 'select', 'dock', 'repair', 'md', 'convert', 'hdock'):
        s = add(name)
        s.add_argument('-o', '--output-root', type=Path, default=Path(os.getenv('MOLFORGE_RUNS_DIR', 'runs')))
        s.add_argument('--job-name', default='')
        if name in ('dock', 'repair', 'md', 'hdock'):
            s.add_argument('-r', '--receptor', type=input_file, required=True)
        if name in ('dock', 'md', 'hdock'):
            s.add_argument('-l', '--ligand', type=input_file, required=True)
        if name == 'conformers':
            smiles_source = s.add_mutually_exclusive_group(required=True)
            smiles_source.add_argument('--smiles')
            smiles_source.add_argument('-f', '--smiles-file', type=input_file)
            s.add_argument('-n', '--num-confs', type=int, default=100)
            s.add_argument('--seed', type=int, default=2026)
            s.add_argument('-t', '--threads', type=int, default=4)
            s.add_argument('--prune-rms-thresh', type=float, default=0.5)
            s.add_argument('--max-iters', type=int, default=5000)
            s.add_argument('--sampling-rounds', type=int, default=3)
            s.add_argument('--embedding-attempts', type=int, default=100)
            s.add_argument('--sampling-scheme', choices=['Standard', 'High torsion'], default='Standard')
        elif name == 'select':
            s.add_argument('--sdf', type=input_file, required=True)
            s.add_argument('--record', type=int, required=True, help='One-based record number explicitly selected by the user')
        elif name == 'dock':
            center = s.add_mutually_exclusive_group(required=True)
            center.add_argument('--center', nargs=3, type=float)
            center.add_argument('--site-residues', help='Example: A:195,A:203-206')
            s.add_argument('--size', nargs=3, type=float, required=True, help='Box dimensions in Angstrom')
            s.add_argument('--nrun', type=int, default=200)
            s.add_argument('--heuristic-max-evaluations', type=int, default=12000000)
            s.add_argument('--seed', type=int)
            s.add_argument('--rigid-macrocycle', action='store_true')
            s.add_argument('--auto-reduce-torsions', action='store_true')
            s.add_argument('--max-ligand-torsions', type=int, default=48)
            s.add_argument('--allow-bad-receptor-residues', action='store_true')
            s.add_argument('--choose-highest-occupancy-altloc', action='store_true')
            s.add_argument('--autodock', default='autodock_gpu_128wi')
            s.add_argument('--autogrid', default='autogrid4')
        elif name == 'md':
            for field in fields(UniGBSAMDParameters):
                if field.name == 'keep_intermediates':
                    s.set_defaults(keep_intermediates=True)
                    continue
                flags = ['-t', '--threads'] if field.name == 'threads' else ['--' + field.name.replace('_', '-')]
                s.add_argument(*flags, type=type(field.default), default=field.default)
            s.add_argument('--accelerator', choices=['auto', 'gpu', 'cpu'], default='auto')
        elif name == 'convert':
            s.add_argument('--topology', type=input_file, required=True)
            s.add_argument('--trajectory', type=input_file, required=True)
        elif name == 'hdock':
            s.add_argument('--hdock', default='hdock')
            s.add_argument('--createpl', default='createpl')
            s.add_argument('--models', type=int, default=100)
    decorate(p, sub, lang)
    return p


def doctor(args):
    result = evidence()
    if args.check_stage == 'md':
        result['runtime'] = md_preflight(args.accelerator)
        import importlib
        importlib.import_module('unigbsa.simulation.mdrun')
    else:
        import importlib
        modules = {'conformers': ['rdkit.Chem.AllChem'], 'dock': ['rdkit', 'meeko'],
                   'repair': ['pdbfixer', 'openmm'], 'convert': [], 'hdock': []}[args.check_stage]
        for module in modules:
            importlib.import_module(module)
        names = {'dock': [args.autodock, args.autogrid, 'mk_prepare_ligand.py', 'mk_prepare_receptor.py', 'mk_export.py'],
                 'convert': ['gmx'], 'hdock': ['hdock', 'createpl']}.get(args.check_stage, [])
        result['tools'] = {name: executable(name) for name in names}
    print(json.dumps(result, indent=2))


def execute(args):
    if args.stage == 'help':
        p = parser(args.lang)
        if args.all and args.topic:
            raise ValueError('Choose help COMMAND or help --all, not both.')
        print(full_help(p) if args.all else subcommands(p)[args.topic].format_help() if args.topic else p.format_help())
        return
    if args.stage == 'doctor':
        return doctor(args)
    if args.stage in {'status', 'runs', 'path', 'files', 'logs'}:
        from .results import navigate
        return navigate(args)
    if args.stage == 'run':
        config = json.loads(args.config.read_text(encoding='utf-8'))
        if not isinstance(config, dict) or set(config) != {'commands'}:
            raise ValueError('Config must contain exactly one key: commands.')
        commands = config['commands']
        if not isinstance(commands, list) or not commands:
            raise ValueError('commands must be a nonempty list of argument arrays.')
        parsed = []
        for command in commands:
            if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
                raise ValueError('Each command must be a nonempty array of strings, not a shell string.')
            if canonical(command[0]) not in ('conformers', 'select', 'dock', 'repair', 'md', 'convert', 'hdock'):
                raise ValueError('Only calculation stages are allowed in run configurations.')
            parsed.append(parser(args.lang).parse_args(command))
        if args.dry_run:
            print(json.dumps([vars(x) for x in parsed], indent=2, default=str))
        else:
            for stage in parsed:
                execute(stage)
        return
    from . import stages
    with redirect_stdout(sys.stderr):
        folder = getattr(stages, args.stage)(args)
    print(folder, flush=True)


def main(argv=None):
    try:
        # Select language before argparse's immediate --help action, wherever the flag occurs.
        probe = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
        probe.add_argument('--lang', choices=['en', 'zh'], default=os.getenv('MOLFORGE_LANG', 'en'))
        language, _ = probe.parse_known_args(argv)
        if language.lang not in {'en', 'zh'}:
            probe.error('MOLFORGE_LANG must be en or zh')
        execute(parser(language.lang).parse_args(argv))
        return 0
    except KeyboardInterrupt:
        print('Interrupted; inspect the job directory before restarting.', file=sys.stderr)
        return 130
    except (Exception,) as exc:
        print(f'molforge: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
