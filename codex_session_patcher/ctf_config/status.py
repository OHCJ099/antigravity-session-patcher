# -*- coding: utf-8 -*-
"""
CTF 配置状态检查
"""

import os
import re
import json
import urllib.parse
from dataclasses import dataclass
from typing import List, Optional

CTF_MARKER = 'managed-by: codex-session-patcher:ctf'


def expand_user_path(path: str) -> str:
    """跨平台展开 ~。

    Windows 的 os.path.expanduser 通常优先 USERPROFILE，忽略测试/脚本临时设置的
    HOME。上游测试和不少跨平台部署脚本会通过 HOME 重定向配置根目录，因此这里
    显式优先 HOME，避免 Codex/Claude/OpenCode 配置误写到真实用户目录。
    """
    if path == "~":
        return os.environ.get("HOME") or os.path.expanduser(path)
    if path.startswith("~/") or path.startswith("~\\"):
        home = os.environ.get("HOME")
        if home:
            return os.path.normpath(os.path.join(home, path[2:]))
    return os.path.normpath(os.path.expanduser(path))


DEFAULT_CLAUDE_CTF_WORKSPACE = expand_user_path("~/.claude-ctf-workspace")
DEFAULT_OPENCODE_CTF_WORKSPACE = expand_user_path("~/.opencode-ctf-workspace")


GLOBAL_MARKER = '# __csp_ctf_global__'
DEFAULT_CODEX_PROMPT_FILE = "ctf_optimized.md"
ANTIGRAVITY_MARKER = '<!-- __agsp_ctf__ -->'
ANTIGRAVITY_PROFILE_RULE_FILE = "ctf_optimized.md"
ANTIGRAVITY_GLOBAL_RULE_FILE = "ctf_global_optimized.md"


def default_antigravity_dir() -> str:
    return os.path.join(expand_user_path("~"), ".gemini", "antigravity")


def default_antigravity_global_config() -> str:
    # Antigravity 没有可直接注入的 [agent].system_prompt_file 全局 TOML。
    # 本工具的“全局模式”使用 manifest 记录已写入的各工作区 always_on rule。
    return os.path.join(default_antigravity_dir(), "prompts", "ctf_global_manifest.json")


def default_antigravity_prompt_path() -> str:
    return os.path.join(default_antigravity_dir(), "prompts", DEFAULT_CODEX_PROMPT_FILE)


def _uri_to_path(uri_or_path: str) -> Optional[str]:
    """把 file:///... URI 或普通路径转为本机路径。"""
    if not uri_or_path:
        return None
    value = str(uri_or_path)
    if value.startswith("file://"):
        parsed = urllib.parse.urlparse(value)
        path = urllib.parse.unquote(parsed.path or "")
        # Windows file:///g%3A/foo 会被解析成 /g:/foo
        if re.match(r"^/[a-zA-Z]:/", path):
            path = path[1:]
        return os.path.normpath(path)
    return os.path.normpath(value)


def _existing_dir(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    path = os.path.normpath(path)
    return path if os.path.isdir(path) else None


def _dedupe_paths(paths: List[str]) -> List[str]:
    result = []
    seen = set()
    for path in paths:
        if not path:
            continue
        norm = os.path.normpath(path)
        key = os.path.normcase(os.path.abspath(norm))
        if key in seen:
            continue
        seen.add(key)
        result.append(norm)
    return result


def _antigravity_project_workspaces() -> List[str]:
    """读取 ~/.gemini/config/projects/*.json 中记录的 Antigravity 项目目录。"""
    projects_dir = os.path.join(expand_user_path("~"), ".gemini", "config", "projects")
    paths: List[str] = []
    if not os.path.isdir(projects_dir):
        return paths
    try:
        project_files = [
            os.path.join(projects_dir, name)
            for name in os.listdir(projects_dir)
            if name.endswith(".json") and name != "outside-of-project.json"
        ]
    except OSError:
        return paths
    project_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    for project_file in project_files:
        try:
            with open(project_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            resources = data.get("projectResources", {}).get("resources", [])
            for resource in resources:
                git_folder = resource.get("gitFolder") or {}
                folder = _uri_to_path(git_folder.get("folderUri") or git_folder.get("folderPath") or "")
                existing = _existing_dir(folder)
                if existing:
                    paths.append(existing)
        except Exception:
            continue
    return _dedupe_paths(paths)


def _antigravity_workspace_storage_paths() -> List[str]:
    """读取 %APPDATA%/antigravity/User/workspaceStorage 的最近工作区记录。"""
    appdata = os.environ.get("APPDATA", os.path.join(expand_user_path("~"), "AppData", "Roaming"))
    storage_root = os.path.join(appdata, "antigravity", "User", "workspaceStorage")
    paths: List[str] = []
    if not os.path.isdir(storage_root):
        return paths
    workspace_jsons = []
    for root, _, files in os.walk(storage_root):
        if "workspace.json" in files:
            workspace_jsons.append(os.path.join(root, "workspace.json"))
    workspace_jsons.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    for workspace_json in workspace_jsons:
        try:
            with open(workspace_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            folder = _uri_to_path(data.get("folder") or data.get("workspace") or "")
            existing = _existing_dir(folder)
            if existing:
                paths.append(existing)
        except Exception:
            continue
    return _dedupe_paths(paths)


def detect_antigravity_profile_workspace() -> Optional[str]:
    """识别最近 Antigravity 项目工作区。

    Antigravity 的可加载规则位于项目内 `.agent/rules/*.md`，所以 Profile
    模式必须写入真实项目目录，而不是创建独立 bat/工作区。
    """
    candidates = _antigravity_project_workspaces() + _antigravity_workspace_storage_paths()
    # 本机测试工作区兜底；只有目录真实存在才使用。
    candidates.extend([
        os.path.join("G:\\", "测试工作区", "Antigravity_workspace"),
        os.path.join("G:\\", "%E6%B5%8B%E8%AF%95%E5%B7%A5%E4%BD%9C%E5%8C%BA", "Antigravity_workspace"),
    ])
    for workspace in _dedupe_paths(candidates):
        if os.path.isdir(workspace):
            return workspace
    return None


def default_antigravity_profile_workspace() -> str:
    return detect_antigravity_profile_workspace() or os.path.join(
        expand_user_path("~"),
        "antigravity-ctf-workspace",
    )


def antigravity_profile_prompt_path_for_workspace(workspace: str) -> str:
    return os.path.join(workspace, ".agent", "rules", ANTIGRAVITY_PROFILE_RULE_FILE)


def antigravity_global_prompt_path_for_workspace(workspace: str) -> str:
    return os.path.join(workspace, ".agent", "rules", ANTIGRAVITY_GLOBAL_RULE_FILE)


def detect_antigravity_global_workspaces() -> List[str]:
    """返回全局模式要写入 always_on rule 的所有已知 Antigravity 工作区。"""
    candidates = _antigravity_project_workspaces() + _antigravity_workspace_storage_paths()
    detected = detect_antigravity_profile_workspace()
    if detected:
        candidates.insert(0, detected)
    return _dedupe_paths([p for p in candidates if os.path.isdir(p)])


@dataclass
class CTFStatus:
    """CTF 配置状态"""
    # Codex
    installed: bool = False
    config_exists: bool = False
    prompt_exists: bool = False
    profile_available: bool = False
    global_installed: bool = False
    injection_mode: str = "none"
    global_injection_mode: str = "none"
    config_path: Optional[str] = None
    prompt_path: Optional[str] = None
    # Claude Code
    claude_installed: bool = False
    claude_workspace_exists: bool = False
    claude_prompt_exists: bool = False
    claude_workspace_path: Optional[str] = None
    claude_prompt_path: Optional[str] = None
    # OpenCode
    opencode_installed: bool = False
    opencode_workspace_exists: bool = False
    opencode_prompt_exists: bool = False
    opencode_workspace_path: Optional[str] = None
    opencode_prompt_path: Optional[str] = None
    # Antigravity Desktop
    antigravity_profile_installed: bool = False
    antigravity_profile_workspace_exists: bool = False
    antigravity_profile_prompt_exists: bool = False
    antigravity_profile_workspace_path: Optional[str] = None
    antigravity_profile_config_path: Optional[str] = None
    antigravity_profile_prompt_path: Optional[str] = None
    antigravity_profile_launcher_path: Optional[str] = None
    antigravity_global_installed: bool = False
    antigravity_global_config_exists: bool = False
    antigravity_global_config_path: Optional[str] = None
    antigravity_global_prompt_path: Optional[str] = None
    antigravity_global_injection_mode: str = "none"
    antigravity_global_workspace_count: int = 0


def _top_level_lines(content: str) -> List[str]:
    """返回第一个 TOML section 前的顶层行。"""
    lines = content.splitlines()
    section_start = len(lines)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('[') and not stripped.startswith('#'):
            section_start = index
            break
    return lines[:section_start]


def _has_top_level_key(content: str, key: str) -> bool:
    """检查未注释的顶层 key。"""
    pattern = re.compile(rf'^\s*{re.escape(key)}\s*=')
    return any(pattern.match(line) for line in _top_level_lines(content))


def _get_top_level_string_value(content: str, key: str) -> Optional[str]:
    """读取未注释的顶层字符串值。"""
    pattern = re.compile(rf'^\s*{re.escape(key)}\s*=\s*"([^"]+)"')
    for line in _top_level_lines(content):
        match = pattern.match(line)
        if match:
            return match.group(1)
    return None


def _default_codex_prompt_path(codex_dir: str) -> str:
    return os.path.join(codex_dir, "prompts", DEFAULT_CODEX_PROMPT_FILE)


def _managed_global_block(content: str) -> str:
    """返回全局模式标记后的受管理顶层配置块。"""
    marker_index = content.find(GLOBAL_MARKER)
    if marker_index < 0:
        return ""

    block_lines = []
    for line in content[marker_index:].splitlines():
        stripped = line.strip()
        if block_lines and stripped.startswith('[') and not stripped.startswith('#'):
            break
        block_lines.append(line)
    return "\n".join(block_lines)


def check_ctf_status() -> CTFStatus:
    """
    检查 CTF 配置的安装状态（Codex + Claude Code）

    Returns:
        CTFStatus: 配置状态信息
    """
    # ── Codex 检查 ──
    codex_dir = expand_user_path("~/.codex")
    base_config_path = os.path.join(codex_dir, "config.toml")
    profile_config_path = os.path.join(codex_dir, "ctf.config.toml")

    status = CTFStatus(
        config_path=profile_config_path,
        prompt_path=None,
    )

    if os.path.exists(profile_config_path):
        try:
            with open(profile_config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            status.config_exists = True
            if _has_top_level_key(content, "developer_instructions"):
                status.profile_available = True
                status.prompt_exists = True
                status.injection_mode = "append"
                default_prompt_path = _default_codex_prompt_path(codex_dir)
                if os.path.exists(default_prompt_path):
                    status.prompt_path = default_prompt_path
            else:
                prompt_path = _get_top_level_string_value(content, "model_instructions_file")
                if prompt_path:
                    status.profile_available = True
                    status.injection_mode = "replace"
                    status.prompt_path = expand_user_path(prompt_path)
        except Exception:
            pass

    if os.path.exists(base_config_path):
        try:
            with open(base_config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if GLOBAL_MARKER in content:
                    status.global_installed = True
                    managed_content = _managed_global_block(content)
                    if _has_top_level_key(managed_content, "developer_instructions"):
                        status.global_injection_mode = "append"
                    elif _has_top_level_key(managed_content, "model_instructions_file"):
                        status.global_injection_mode = "replace"
        except Exception:
            pass

    if status.prompt_path and os.path.exists(status.prompt_path):
        status.prompt_exists = True

    status.installed = status.config_exists and status.prompt_exists and status.profile_available

    # ── Claude Code 检查 ──
    workspace_path = DEFAULT_CLAUDE_CTF_WORKSPACE
    claude_prompt_path = os.path.join(workspace_path, ".claude", "CLAUDE.md")

    status.claude_workspace_path = workspace_path
    status.claude_prompt_path = claude_prompt_path
    status.claude_workspace_exists = os.path.isdir(workspace_path)

    if os.path.exists(claude_prompt_path):
        try:
            with open(claude_prompt_path, 'r', encoding='utf-8') as f:
                content = f.read(500)  # 只需读开头
                if CTF_MARKER in content:
                    status.claude_prompt_exists = True
        except Exception:
            pass

    status.claude_installed = status.claude_workspace_exists and status.claude_prompt_exists

    # ── OpenCode 检查 ──
    opencode_workspace = DEFAULT_OPENCODE_CTF_WORKSPACE
    opencode_agents_path = os.path.join(opencode_workspace, "AGENTS.md")

    status.opencode_workspace_path = opencode_workspace
    status.opencode_prompt_path = opencode_agents_path
    status.opencode_workspace_exists = os.path.isdir(opencode_workspace)

    if os.path.exists(opencode_agents_path):
        try:
            with open(opencode_agents_path, 'r', encoding='utf-8') as f:
                content = f.read(500)
                if CTF_MARKER in content:
                    status.opencode_prompt_exists = True
        except Exception:
            pass

    status.opencode_installed = status.opencode_workspace_exists and status.opencode_prompt_exists

    # ── Antigravity Desktop 检查 ──
    antigravity_workspace = default_antigravity_profile_workspace()
    antigravity_profile_rule = antigravity_profile_prompt_path_for_workspace(antigravity_workspace)
    antigravity_global_manifest = default_antigravity_global_config()
    antigravity_global_prompt = default_antigravity_prompt_path()

    status.antigravity_profile_workspace_path = antigravity_workspace
    status.antigravity_profile_config_path = antigravity_profile_rule
    status.antigravity_profile_prompt_path = antigravity_profile_rule
    status.antigravity_profile_launcher_path = None
    status.antigravity_profile_workspace_exists = os.path.isdir(antigravity_workspace)
    status.antigravity_profile_prompt_exists = os.path.exists(antigravity_profile_rule)
    if os.path.exists(antigravity_profile_rule):
        try:
            with open(antigravity_profile_rule, 'r', encoding='utf-8') as f:
                content = f.read()
                status.antigravity_profile_installed = (
                    ANTIGRAVITY_MARKER in content and "profile mode" in content
                )
        except Exception:
            pass

    status.antigravity_global_config_path = antigravity_global_manifest
    status.antigravity_global_prompt_path = antigravity_global_prompt
    status.antigravity_global_config_exists = os.path.exists(antigravity_global_manifest)
    if os.path.exists(antigravity_global_manifest):
        try:
            with open(antigravity_global_manifest, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            rule_paths = manifest.get("rule_paths", [])
            active_rule_paths = []
            for rule_path in rule_paths:
                if not os.path.exists(rule_path):
                    continue
                try:
                    with open(rule_path, "r", encoding="utf-8") as rf:
                        rule_content = rf.read()
                    if ANTIGRAVITY_MARKER in rule_content and "global mode" in rule_content:
                        active_rule_paths.append(rule_path)
                except Exception:
                    continue
            status.antigravity_global_workspace_count = len(active_rule_paths)
            if active_rule_paths:
                status.antigravity_global_installed = True
                status.antigravity_global_injection_mode = "always_on_rule"
        except Exception:
            pass

    return status
