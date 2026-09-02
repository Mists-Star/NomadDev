# USB DevLauncher

A portable, offline-first **developer workspace launcher** for USB sticks (or any folder you can carry). Plug in, double-click, and get a web dashboard to run tools, preview local web projects, browse installers, and talk to a local AI — no network, no installs, Python standard library only.

[中文说明见文末](#中文说明)

## Features

- **Zero-dependency** — Python 3 standard library backend, vanilla HTML/CSS/JS frontend. No pip, no node_modules, no frameworks.
- **Portable dashboard** — scan the drive for dev tools, web projects and installers (fast, depth-limited scan).
- **One-click local servers** — serve any folder as `http://127.0.0.1:<port>` and stop it from the UI.
- **Environment self-check** — green/red status for Node / Git / JDK / Python / ADB; prompts to complete missing ones.
- **Offline AI** — starts Ollama (`ollama serve`) if present, so you can run small local models without internet.
- **Role-based quick deploy** — `deploy.py` installs a preset environment bundle (web, python-data, java/android, C/C++, full-stack, offline-AI, …) from local sources or tells you what to fetch online.
- **Privacy by design** — personal configuration lives in git-ignored files; the repo itself is generic.

## Layout

```
USB-DevLauncher/
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

> `DevEnv`, `Projects`, `Tools`, `AI` are user content, not part of this repo. Put your own portable builds there.

## Quickstart (Windows)

```bat
:: 1. fill in your environment sources, then copy portable runtimes onto the drive
copy Launch\sources.example.json Launch\sources.json
python Launch\deploy.py --preset fullstack --go

:: 2. start the launcher (it picks a working python automatically)
Launch\launch.bat
```

The dashboard opens at `http://127.0.0.1:8787`.

Or preview a deploy plan first:

```bat
python Launch\deploy.py --preset web
```

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

随身 U 盘 / 便携开发工作台启动器：插盘即用、离线优先、仅依赖 Python 标准库。

- **启动**：双击 `Launch\launch.bat`（自动挑选可用 Python），浏览器打开 `http://127.0.0.1:8787`
- **仪表盘**：识别 U 盘内开发工具 / 网页项目 / 安装包；环境自检（Node/Git/JDK/Python/ADB）；一键起本地静态服务器并可停止；检测到 Ollama 时可在页面启动/停止离线 AI
- **快速部署**：`python Launch\deploy.py --preset <web|pydata|java|cpp|fullstack|aiwork|demo|core>`，预览计划或 `--go` 真执行
- **隐私**：`config.json` / `sources.json` 等个性化配置已被 `.gitignore` 排除，本仓库只含通用代码
