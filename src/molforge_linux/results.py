"""Read-only result discovery, including older task folders and nested engine outputs."""
from collections import deque
import fnmatch
import json
from pathlib import Path


def read_object(path):
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding='utf-8-sig'))
        return value if isinstance(value, dict) else {'_error': f'Expected an object: {path.name}'}
    except (OSError, ValueError) as exc:
        return {'_error': f'{path.name}: {exc}'}


def is_job(path):
    return path.is_dir() and any((path / name).is_file() for name in
                                ('status.json', 'manifest.json', 'run_metadata.json'))


def describe(path):
    path = path.resolve()
    state, meta, params, manifest = [read_object(path / name) for name in
        ('status.json', 'run_metadata.json', 'parameters.json', 'manifest.json')]
    status = state.get('status', manifest.get('status', 'unknown'))
    if state.get('_error'):
        status = 'unknown'
    elif not state and any((path / name).exists() for name in ('FAILED', 'FAILED.txt')):
        status = 'failed'
    return {'id': path.name, 'name': meta.get('task_name', path.name),
            'stage': params.get('stage', meta.get('operation', manifest.get('node', 'unknown'))),
            'status': status, 'path': str(path), 'outputs': str(path / 'outputs'),
            'error': state.get('error'),
            'warnings': [v['_error'] for v in (state, meta, params, manifest) if '_error' in v]}


def discover(root):
    root = Path(root).expanduser().resolve()
    if not root.exists():
        return []
    if not root.is_dir():
        raise ValueError(f'Not a results directory: {root}')
    return [describe(path) for path in sorted(root.iterdir(), key=lambda p: p.name, reverse=True)
            if not path.is_symlink() and is_job(path)]


def resolve_job(root, selector):
    selector = str(selector)
    direct = Path(selector).expanduser()
    if selector != 'latest' and is_job(direct):
        return direct.resolve()
    entries = discover(root)
    if not entries:
        raise ValueError(f'No jobs found in {Path(root).expanduser().resolve()}. Set --output-root or MOLFORGE_RUNS_DIR.')
    if selector == 'latest':
        return Path(entries[0]['path'])
    exact = [entry for entry in entries if entry['id'] == selector]
    matches = exact or [entry for entry in entries if selector.casefold() in entry['id'].casefold()
                       or selector.casefold() in str(entry['name']).casefold()]
    if len(matches) != 1:
        detail = '\n'.join(entry['id'] for entry in matches)
        raise ValueError(f"{'Ambiguous job' if matches else 'Job not found'}: {selector}. "
                         f'Use a full ID or path.\n{detail}')
    return Path(matches[0]['path'])


def safe_files(folder):
    return [p for p in sorted(folder.rglob('*')) if p.is_file() and not p.is_symlink()
            and p.resolve().is_relative_to(folder.resolve())]


ARTIFACTS = {
    'sdf': ['outputs/conformers.sdf', 'outputs/selected_ligand.sdf'],
    'ranking': ['outputs/conformer_ranking.csv'], 'protocol': ['outputs/conformer_protocol.json'],
    'energy': ['outputs/unigbsa_results_average.csv'],
    'poses': ['ranked_poses.sdf', 'top_models.pdb'],
    'trajectory': ['outputs/trajectory_animation.pdb', 'traj_com.xtc', 'protein_ligand_md.xtc', 'md.xtc'],
}


def artifact_path(folder, kind):
    if kind == 'job':
        return folder
    if kind == 'outputs':
        if not (folder / 'outputs').is_dir():
            raise ValueError('This job has no outputs directory. Use molforge files to inspect it.')
        return folder / 'outputs'
    for name in ARTIFACTS[kind]:
        if '/' in name:
            candidate = folder / name
            matches = [candidate] if candidate.is_file() else []
        else:
            matches = [p for p in safe_files(folder) if p.name == name]
        matches = [p for p in matches if p.resolve().is_relative_to(folder.resolve()) and not p.is_symlink()]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError('Multiple artifacts; select a path from molforge files:\n' +
                             '\n'.join(str(p.relative_to(folder)) for p in matches))
    raise ValueError(f'No {kind} artifact in this job. Use molforge files to inspect available results.')


def navigate(args):
    root = args.output_root
    if args.stage == 'runs':
        entries = [entry for entry in discover(root)
                   if (not args.filter_stage or entry['stage'] == args.filter_stage)
                   and (not args.filter_status or entry['status'] == args.filter_status)][:args.limit]
        if args.json:
            print(json.dumps(entries, ensure_ascii=False, indent=2))
        elif not entries:
            print('没有匹配的任务。' if args.lang == 'zh' else 'No matching jobs.')
        else:
            print('状态 | 阶段 | 任务 ID' if args.lang == 'zh' else 'STATUS | STAGE | JOB ID')
            for entry in entries:
                print(f"{entry['status']} | {entry['stage']} | {entry['id']}")
        return
    folder = resolve_job(root, args.job)
    if args.stage == 'path':
        print(artifact_path(folder, args.artifact))
    elif args.stage == 'status':
        entry = describe(folder)
        entry['artifacts'] = {}
        for key in ARTIFACTS:
            try:
                entry['artifacts'][key] = str(artifact_path(folder, key))
            except ValueError:
                pass
        if args.json:
            print(json.dumps(entry, ensure_ascii=False, indent=2))
        else:
            labels = ('任务', '状态', '阶段', '目录', '结果') if args.lang == 'zh' else ('Job', 'Status', 'Stage', 'Path', 'Results')
            for label, key in zip(labels[:4], ('name', 'status', 'stage', 'path')):
                print(f'{label}: {entry[key]}')
            for key, path in entry['artifacts'].items():
                print(f'{labels[4]} [{key}]: {path}')
            for warning in entry['warnings']:
                print(f'Warning: {warning}')
            if entry['error']:
                print(f"Error: {entry['error']}")
    elif args.stage == 'files':
        entries = [{'path': str(p.relative_to(folder)), 'bytes': p.stat().st_size}
                   for p in safe_files(folder) if fnmatch.fnmatchcase(p.relative_to(folder).as_posix(), args.pattern)]
        if args.json:
            print(json.dumps(entries, ensure_ascii=False, indent=2))
        else:
            for entry in entries:
                print(f"{entry['bytes']:>12}  {entry['path']}")
    else:
        logs = [p for p in safe_files(folder) if p.suffix == '.log' or p.name in {'FAILED', 'FAILED.txt'}]
        if args.log_file:
            selected = (folder / args.log_file).resolve()
            if not selected.is_relative_to(folder) or selected not in logs:
                raise ValueError('Choose a log file inside this job, listed by molforge files.')
        elif len(logs) == 1:
            selected = logs[0]
        else:
            raise ValueError('Specify --file; available logs:\n' + '\n'.join(str(p.relative_to(folder)) for p in logs))
        with selected.open(encoding='utf-8', errors='replace') as stream:
            print(''.join(deque(stream, maxlen=args.lines)), end='')
