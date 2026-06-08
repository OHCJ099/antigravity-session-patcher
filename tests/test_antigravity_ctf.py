# -*- coding: utf-8 -*-
import json
from pathlib import Path


def _write_antigravity_project(home: Path, workspace: Path):
    projects = home / '.gemini' / 'config' / 'projects'
    projects.mkdir(parents=True)
    (projects / 'project.json').write_text(
        json.dumps(
            {
                'id': 'project',
                'name': 'Antigravity test project',
                'projectResources': {
                    'resources': [
                        {'gitFolder': {'folderUri': workspace.as_uri()}},
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )


def test_antigravity_profile_installer_writes_project_rule(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    appdata = tmp_path / 'AppData'
    workspace = tmp_path / 'project'
    home.mkdir()
    appdata.mkdir()
    workspace.mkdir()
    _write_antigravity_project(home, workspace)
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('APPDATA', str(appdata))

    from codex_session_patcher.ctf_config.installer import AntigravityCTFInstaller
    from codex_session_patcher.ctf_config.status import ANTIGRAVITY_MARKER, check_ctf_status

    installer = AntigravityCTFInstaller()
    ok, msg = installer.install(custom_prompt='Antigravity CTF Prompt')
    assert ok, msg

    rule = Path(installer.profile_prompt_path)
    assert installer.workspace_dir == str(workspace)
    assert rule == workspace / '.agent' / 'rules' / 'ctf_optimized.md'
    text = rule.read_text(encoding='utf-8')
    assert 'trigger: always_on' in text
    assert ANTIGRAVITY_MARKER in text
    assert 'profile mode' in text
    assert 'Antigravity CTF Prompt' in text
    assert '.codex' not in text

    status = check_ctf_status()
    assert status.antigravity_profile_installed is True
    assert status.antigravity_profile_prompt_exists is True
    assert status.antigravity_profile_config_path == str(rule)

    ok, msg = installer.uninstall()
    assert ok, msg
    assert not rule.exists()
    assert check_ctf_status().antigravity_profile_installed is False


def test_antigravity_global_installer_mirrors_rules_to_known_workspaces(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    appdata = tmp_path / 'AppData'
    workspace = tmp_path / 'project'
    home.mkdir()
    appdata.mkdir()
    workspace.mkdir()
    _write_antigravity_project(home, workspace)
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('APPDATA', str(appdata))

    from codex_session_patcher.ctf_config.installer import AntigravityCTFInstaller
    from codex_session_patcher.ctf_config.status import ANTIGRAVITY_MARKER, check_ctf_status

    installer = AntigravityCTFInstaller()
    ok, msg = installer.install_global(custom_prompt='Antigravity Global Prompt')
    assert ok, msg

    manifest = Path(installer.global_config_path)
    global_rule = workspace / '.agent' / 'rules' / 'ctf_global_optimized.md'
    assert manifest.exists()
    assert global_rule.exists()
    text = global_rule.read_text(encoding='utf-8')
    assert 'trigger: always_on' in text
    assert ANTIGRAVITY_MARKER in text
    assert 'global mode' in text
    assert 'Antigravity Global Prompt' in text
    assert Path(installer.global_prompt_path).read_text(encoding='utf-8') == 'Antigravity Global Prompt'

    status = check_ctf_status()
    assert status.antigravity_global_installed is True
    assert status.antigravity_global_config_path == str(manifest)
    assert status.antigravity_global_workspace_count == 1

    ok, msg = installer.uninstall_global()
    assert ok, msg
    assert not global_rule.exists()
    assert not manifest.exists()
    assert check_ctf_status().antigravity_global_installed is False
