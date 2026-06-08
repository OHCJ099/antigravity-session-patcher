# Antigravity Session Patcher

Antigravity Desktop 专用版 session-patcher。基于 codex-session-patcher / Reasonix 版适配，重点支持：

- 扫描 Antigravity Desktop 会话日志：`~/.gemini/antigravity/brain/**/.system_generated/logs/transcript.jsonl`
- 清理/替换会话中的拒绝回复，移除 `thinking/reasoning` 字段
- CTF/渗透 Profile 模式：写入当前 Antigravity 工作区 `.agent/rules/ctf_optimized.md`
- CTF/渗透全局模式：把 `.agent/rules/ctf_global_optimized.md` 镜像到所有已知 Antigravity 工作区
- Web UI、桌面快捷方式、一键启动脚本

## Windows 快速使用

下载 Release 压缩包后：

1. 解压到任意目录
2. 双击 `start_antigravity_session_patcher.bat`
3. 打开 `http://127.0.0.1:47834/`

首次运行会自动创建 `.venv` 并安装后端依赖。前端 `dist` 已随包提供，通常不需要 Node.js。

## 从源码运行

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[web]"
.\.venv\Scripts\python.exe -m codex_session_patcher.cli --web --host 127.0.0.1 --port 47834
```

如果需要重构前端：

```powershell
cd web/frontend
npm install
npm run build
```

## Antigravity 适配说明

Antigravity 的规则入口不是 `.codex`，也不是 Reasonix 的 `[agent].system_prompt_file`。本项目使用 Antigravity 原生项目规则：

```md
---
trigger: always_on
description: CTF/pentest sandbox instructions managed by antigravity-session-patcher
---
```

Profile 模式只影响当前/最近识别到的工作区。全局模式会同步到所有已知工作区；如果新建了工作区，重新点一次“启用全局”即可补写 rule。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

当前验证结果：`91 passed, 25 skipped`。
