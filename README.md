# NomadDev · 游牧开发

A **portable, offline-first developer workspace launcher**. It follows you between machines: run your dev tools, preview local web projects, and talk to a local AI from **any USB drive or any folder** — no installs, no network required. Python standard library only.

[中文说明见文末](#中文说明)

## Why "Nomad"?

Your dev environment travels with you instead of living on one machine — like a nomad's camp, packed up and set up anywhere.

## Features

- **Zero-dependency** — Python 3 standard library backend, vanilla HTML/CSS/JS frontend. No pip, no node_modules, no frameworks.
- **Portable dashboard** — fast depth-limited scan of dev tools, web projects and installers on the drive/folder.
- **One-click local servers** — serve any folder as `http://127.0.0.1:<port>` and stop it from the UI.
- **Environment self-check** — green/red status for Node / Git / JDK / Python / ADB; prompts to complete missing ones.
- **Offline AI** — starts Ollama (`ollama serve`) if present, for small local models without internet.
- **Role-based quick deploy** — `deploy.py` installs a preset environment bundle (web, python-data, java/android, C/C++, full-stack, offline-AI, …) from local sources or tells you what to fetch online.
- **Runs on USB *and* plain folders / PC workspaces** — not tied to any device.
- **Privacy by design** — personal configuration lives in git-ignored files; this repo itself is generic.

## Layout

```
NomadDev/
├── Launch/                  # the launcher app
│   ├── launcher.py          # backend (stdlib only)
│   ├── index.html           # dashboard (terminal-styled)
│   ├── launch.bat           # start on Windows
│   ├── deploy.py            # preset quick-deploy CLI
│   ├── packages.json        # optional package catalog + presets
│   ├── config.example.json  # copy to config.json to customize
│   └── sources.example.json # copy to sources.json to map your local envs
├── DevEnv/                  # portable runtimes (git, node, python, jdk, …) — your own copies
├── Projects/                # your web projects (served from the UI)
├── Tools/                   # extra portable tools
└── AI/                      # ollama.exe + models
```

> `Launch` is just the conventional folder name; the app locates the workspace root as its parent. You may rename it.

## Quickstart (Windows)

```bat
:: 1. (optional) map your local environment sources, then copy them on
copy Launch\sources.example.json Launch\sources.json
python Launch\deploy.py --preset fullstack --go

:: 2. start the launcher (auto-detects a working Python 3)
Launch\launch.bat
```

The dashboard opens at `http://127.0.0.1:8787`.

Preview a deploy plan first:

```bat
python Launch\deploy.py --preset web
```

No local environment to copy? Put the drive on any internet PC and run the setup
bootstrap (finish_setup.bat in the full package) which downloads portable builds.

## Customization

Personal/private overrides never belong in this repo. Keep them in local files:

- `Launch/config.json` — tool signatures, installer dirs, known project names (see `config.example.json`).
- `Launch/sources.json` — map catalog package ids to local source folders (see `sources.example.json`).

Both are git-ignored.

## Offline AI

Put `ollama.exe` into `AI\`, then in the dashboard click **start** under the Offline AI card; Ollama listens on `127.0.0.1:11434`. Pull a small model once while online (e.g. `ollama pull qwen2.5:0.5b`) and it works offline afterwards.

## License

MIT — see [LICENSE](LICENSE). Third-party tool names belong to their respective owners; this project does not bundle them.

---

## 中文说明

**NomadDev · 游牧开发** —— 随身、离线优先的开发工作台启动器。把你的开发环境装进 U 盘或任意文件夹，插到哪台机器都能用：起工具、预览网页项目、跑本地 AI，无需安装、不污染目标机器，仅依赖 Python 标准库。

- **启动**：双击 `Launch\launch.bat`（自动深度探测可用 Python），浏览器打开 `http://127.0.0.1:8787`
- **仪表盘**（终端配色）：识别开发工具 / 网页项目 / 安装包；环境自检（Node/Git/JDK/Python/ADB）；一键起停本地静态服务器；检测到 Ollama 可在页面启停离线 AI
- **快速部署**：`python Launch\deploy.py --preset <web|pydata|java|cpp|fullstack|aiwork|demo|core>`，预览计划或 `--go` 真执行
- **隐私**：`config.json` / `sources.json` 等个性化配置已被 `.gitignore` 排除，本仓库只含通用代码
