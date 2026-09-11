from pathlib import Path
import runpy

import pytest

from molforge_linux.cli import main, parser
from molforge_linux.help_text import COMMANDS, ALIASES, catalog, subcommands


@pytest.mark.parametrize('command', list(COMMANDS))
@pytest.mark.parametrize('lang', ['en', 'zh'])
def test_every_command_has_descriptions_examples_and_help(command, lang, capsys):
    with pytest.raises(SystemExit) as result:
        main([ALIASES[command], '--help', '--lang', lang])
    assert result.value.code == 0
    output = capsys.readouterr().out
    assert catalog(lang)[command][0] in output
    assert ('示例' if lang == 'zh' else 'Examples:') in output
    assert 'molforge help --all' in output


def test_all_help_and_topic_do_not_require_input_files(capsys):
    assert main(['help', '--all', '--lang', 'zh']) == 0
    output = capsys.readouterr().out
    for name in COMMANDS:
        assert f'molforge {name}' in output
    assert '--nvt-steps' in output and '默认：250000' in output
    assert main(['help', 'd', '--lang', 'zh']) == 0
    output = capsys.readouterr().out
    assert '二选一' in output and '单位 Å' in output


def test_every_public_option_explains_its_purpose():
    for child in subcommands(parser()).values():
        for action in child._actions:
            assert action.help, (child.prog, action.dest)


def test_reference_matches_current_commands():
    root = Path(__file__).resolve().parents[1]
    builder = runpy.run_path(str(root / 'scripts/build_command_reference.py'))
    assert (root / 'docs/COMMANDS.md').read_text(encoding='utf-8') == builder['render']()


def test_language_environment_and_explicit_override(monkeypatch, capsys):
    monkeypatch.setenv('MOLFORGE_LANG', 'zh')
    assert main(['h', 'conf']) == 0
    assert '三维构象' in capsys.readouterr().out
    assert main(['--lang', 'en', 'h', 'conf']) == 0
    output = capsys.readouterr().out
    assert 'Generate and rank' in output
    assert '默认' not in output


def test_invalid_language_and_unknown_prefix_fail():
    for args in (['--lang', 'fr', '--help'], ['confo', '--help']):
        with pytest.raises(SystemExit) as result:
            main(args)
        assert result.value.code == 2
