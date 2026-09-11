"""Generate one bilingual reference directly from the CLI parser."""
import argparse
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'src'))
from molforge_linux.cli import parser
from molforge_linux.help_text import ALIASES, catalog, subcommands


def render():
    lines = ['# Command reference / 指令大全', '',
             '[Home](../README.md) · [User manual / 用户手册](MANUAL.md)', '',
             'Find a command below, copy its example, and consult the option table for requirements and defaults.', '',
             '[English](#english) · [中文](#中文) · [Installer options](MANUAL.md#automatic-environment-setup)', '',
             '```bash', 'molforge --lang en --help', 'molforge conf --help --lang zh',
             'molforge help --all --lang en', 'export MOLFORGE_LANG=zh', '```', '',
             'An explicit `--lang` overrides `MOLFORGE_LANG`; the default language is English. '
             'Command abbreviations are fixed aliases, not arbitrary prefixes.', '',
             '显式 `--lang` 优先于环境变量，默认语言为英文。简称为固定别名，不支持任意前缀。', '',
             '| Command / 命令 | Alias / 简称 | English | 中文 |', '|---|---|---|---|']
    for name in catalog('en'):
        lines.append(f'| [{name}](#{name}-{ALIASES[name]}) | `{ALIASES[name]}` | {catalog("en")[name][0]} | {catalog("zh")[name][0]} |')
    for lang in ('en', 'zh'):
        lines += ['', '## English' if lang == 'en' else '## 中文', '']
        # Generated defaults must not embed a developer's local results directory.
        with patch.dict('os.environ', {'MOLFORGE_RUNS_DIR': 'runs'}):
            children = subcommands(parser(lang))
        for name, child in children.items():
            title, detail, examples = catalog(lang)[name]
            lines += [f'### {name} ({ALIASES[name]})', '', f'{title}. {detail}', '', '```bash', examples, '```', '',
                      '| Option / 参数 | Requirement / 要求 | Description / 说明 |', '|---|---|---|']
            grouped = {a.dest for g in child._mutually_exclusive_groups if g.required for a in g._group_actions}
            for action in child._actions:
                requirement = 'one of group / 组内二选一' if action.dest in grouped else 'required / 必填' if action.required else 'optional / 可选'
                label = ', '.join(action.option_strings) or action.dest
                description = action.help
                if action.choices:
                    description += '; ' + ', '.join(f'`{c}`' for c in action.choices)
                lines.append(f'| `{label}` | {requirement} | {description.replace("|", "/")} |')
            lines += ['']
    return '\n'.join(lines)


if __name__ == '__main__':
    check = '--check' in sys.argv
    path = ROOT / 'docs/COMMANDS.md'
    expected = render()
    if check:
        if not path.is_file() or path.read_text(encoding='utf-8') != expected:
            raise SystemExit('Command reference is stale. Run scripts/build_command_reference.py.')
        print('Command reference is current.')
    else:
        path.write_text(expected, encoding='utf-8', newline='\n')
