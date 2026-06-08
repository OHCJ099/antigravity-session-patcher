# Antigravity Session Patcher

Antigravity Desktop 适配版会话清理器 / CTF 提示词注入器。

## 一键启动

双击：`start_antigravity_session_patcher.bat`

首次启动会自动创建 `.venv` 并安装 Web 后端依赖；前端已预构建到 `web/frontend/dist`，正常情况下不需要 Node.js。

默认地址：<http://127.0.0.1:47834>

## Antigravity 适配点

- 会话扫描：`%USERPROFILE%\.gemini\antigravity\brain\*\.system_generated\logs\transcript.jsonl`
- 助手消息识别：`source=MODEL` + `type=PLANNER_RESPONSE`
- 用户消息识别：`source=USER_EXPLICIT` + `type=USER_INPUT`
- Profile CTF/渗透模式：写入当前/最近 Antigravity 项目的 `.agent/rules/ctf_optimized.md`
- 全局模式：Antigravity 无单一全局 TOML，本工具会把 `trigger: always_on` rule 镜像到所有已知 Antigravity 工作区，并在 `~/.gemini/antigravity/prompts/ctf_global_manifest.json` 记录受管理路径

## 注意

全局模式只会覆盖“已知/已打开过”的 Antigravity 工作区。新建或切换到新的工作区后，重新点击“启用全局”即可补写 rule。
