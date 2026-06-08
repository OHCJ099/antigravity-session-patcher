# Quick Deploy

1. 解压本压缩包到任意目录（推荐 `G:\codex-session-patcher-antigravity`）。
2. 双击 `start_antigravity_session_patcher.bat`。
3. 浏览器会自动打开 `http://127.0.0.1:47834/`。
4. 可选：双击 `install_desktop_shortcut.bat` 创建桌面快捷方式。

首次启动会自动创建 `.venv` 并安装 FastAPI 等后端依赖；前端 `dist` 已随包构建好，通常不需要 Node/npm。

Antigravity 专用能力：
- 扫描 `~/.gemini/antigravity/brain` 下的 transcript.jsonl。
- patch 时同步 `~/.gemini/antigravity/conversations/<id>.db`，确保 Antigravity UI 生效。
- Profile 模式写入当前项目 `.agent/rules/ctf_optimized.md`。
- 全局模式把 `.agent/rules/ctf_global_optimized.md` 镜像到所有已知 Antigravity 工作区。
