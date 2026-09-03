#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NomadDev — 随身开发 / 演示平台启动器
============================================
插上 U 盘，双击 launch.bat 即可：
  - 自动识别 U 盘盘符（任意电脑、任意盘符都能跑）
  - 扫描盘内「开发工具 / 本地项目 / 安装包 / 离线 AI」
  - 可视化界面一键：起本地服务器看项目 / 拉起工具 / 打开安装包
  - 环境自检：检测便携 Node/Git/JDK/Python/ADB，缺失可一键补全
  - 离线 AI：调用 Ollama 本地推理（ollama serve :11434）
  - 完整性校验：调用 Tools/integrity_check.ps1

依赖：仅 Python 3 标准库。优先用 U 盘自带 DevEnv\\python，其次系统 python。
可开源（MIT）。
"""
import os
import sys
import json
import subprocess
import threading
import webbrowser
import http.server
import socketserver
import urllib.parse
import urllib.request
from functools import partial

# ---- 路径基线 ----------------------------------------------------------
# launcher.py 位于  <USB>\Launch\launcher.py
LAUNCH_DIR = os.path.dirname(os.path.abspath(__file__))
USB_ROOT = os.path.dirname(LAUNCH_DIR)            # U 盘根
SETUP_BAT = os.path.join(USB_ROOT, "finish_setup.bat")
INTEGRITY_PS = os.path.join(LAUNCH_DIR, "..", "Tools", "integrity_check.ps1")
CONFIG_PATH = os.path.join(LAUNCH_DIR, "config.json")   # 私有配置（不进仓库）

# ---- 扫描配置 ----------------------------------------------------------
# 默认工具探测（无 config.json 时使用；config.json 的 "tools" 会覆盖）。
# 个人/私有定制请放 F:\Launch\config.json，保持本文件可直接开源。
DEFAULT_TOOL_SIGS = [
    ("7-Zip",           ["Tools/7zip/7z.exe", "Tools/7z*.exe"]),
    ("Notepad++",       ["Tools/notepad++/notepad++.exe", "Tools/npp*.exe"]),
    ("Git Bash",        ["DevEnv/git/cmd/git.exe", "DevEnv/git/bin/bash.exe"]),
    ("Node.js",         ["DevEnv/node/node.exe"]),
    ("Python",          ["DevEnv/python/python.exe"]),
    ("JDK",             ["DevEnv/jdk/bin/java.exe"]),
    ("ADB",             ["DevEnv/adb/adb.exe", "Tools/adb/adb.exe"]),
    ("Ollama 本地AI",    ["AI/ollama.exe", "AI/ollama/ollama.exe", "DevEnv/ollama/ollama.exe"]),
]


def _load_config():
    """从 config.json 读取个性化覆盖（工具清单/目录/已知项目名）。
    该文件属于私有配置，开源时保留 config.example.json 即可。"""
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as _f:
                cfg = json.load(_f)
        except Exception:
            cfg = {}
    return cfg


_CONFIG = _load_config()
TOOL_SIGS = [tuple(t) for t in _CONFIG.get("tools", DEFAULT_TOOL_SIGS)]

# 便携环境自检项：(中文名, 相对 U 盘根的可执行路径)
ENV_SIGS = [
    ("Node.js", "DevEnv/node/node.exe"),
    ("Git",     "DevEnv/git/cmd/git.exe"),
    ("JDK",     "DevEnv/jdk/bin/java.exe"),
    ("Python",  "DevEnv/python/python.exe"),
    ("ADB",     "DevEnv/adb/adb.exe"),
]

# 本地 AI 运行时（离线可用）：ollama serve 监听的地址
AI_SERVE_PORT = 11434
AI_TAGS = ("ai", "ollama")

# 项目识别：含 index.html / 已知项目名 且 不是 node_modules / .git
PROJECT_MARKERS = ["index.html", "index.htm"]
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".vs", "bin", "obj",
             "Library", "Packages", "Temp", "Logs"}

DEFAULT_INSTALLER_DIRS = ["Installers", "Apps", "SDK"]
INSTALLER_DIRS = _CONFIG.get("installer_dirs", DEFAULT_INSTALLER_DIRS)

NEW_PROCESS_GROUP = 0x00000200  # 让子进程独立运行，不被主进程关闭牵连


def _resolve(pattern):
    """Expand a pattern like 'App/*/bin/tool.exe' under the USB root
    into real paths. '*' matches any single directory level."""
    parts = pattern.split("/")
    current = [USB_ROOT]
    for part in parts:
        nxt = []
        if part == "*":
            for base in current:
                if os.path.isdir(base):
                    nxt.extend(os.path.join(base, d) for d in os.listdir(base)
                               if os.path.isdir(os.path.join(base, d)))
            current = nxt or current
            continue
        import fnmatch
        for base in current:
            if not os.path.isdir(base):
                continue
            for d in os.listdir(base):
                full = os.path.join(base, d)
                if fnmatch.fnmatch(d, part):
                    nxt.append(full)
        current = nxt
    return [c for c in current if os.path.exists(c)]


def scan_tools():
    out = []
    for name, patterns in TOOL_SIGS:
        for p in patterns:
            for h in _resolve(p):
                out.append({"name": name, "path": h, "dir": os.path.dirname(h)})
    # 去重（同一工具多匹配）
    seen, uniq = set(), []
    for t in out:
        if t["path"] in seen:
            continue
        seen.add(t["path"])
        uniq.append(t)
    return uniq


def env_status():
    """便携开发环境自检（存在且非空才算就绪，0 字节桩视为缺失）。
    Python 特殊处理：DevEnv\python 或内置 runtime\python 任一可用即算就绪。"""
    out = []
    for name, rel in ENV_SIGS:
        p = os.path.join(USB_ROOT, rel)
        ok = False
        if os.path.exists(p):
            try:
                ok = os.path.getsize(p) > 0
            except OSError:
                ok = False
        if name == "Python" and not ok:
            rp = os.path.join(USB_ROOT, "runtime", "python", "python.exe")
            if os.path.exists(rp):
                try:
                    ok = os.path.getsize(rp) > 0
                except OSError:
                    ok = False
        out.append({"name": name, "ok": ok, "path": p})
    return out


# 扫描时跳过的重目录（运行时/工具/安装包/系统/游戏构建目录），不进入其内容
PROJECT_SKIP = {"node_modules", ".git", "__pycache__", "Library", "Packages",
                "Temp", "Logs", "bin", "obj", "DevEnv", "Launch", "Installers",
                "Tools", "_old", "解释器", "Python", "Other", "Android工具(老版本)",
                "MC_Android", "Games", "MonoBleedingEdge"}


def scan_projects():
    """限深(≤2)手动遍历：找到 index.html 即记为 web 项目并停止下钻；
    命中已知项目名则记录但不下钻其内部（避免枚举 Unity 构建等大目录）。"""
    projects = []
    seen = set()
    known = _CONFIG.get("known_projects", [])

    def walk(path, depth):
        if depth > 2:
            return
        try:
            entries = list(os.scandir(path))
        except OSError:
            return
        files = [e for e in entries if e.is_file()]
        if any(e.name.lower() in PROJECT_MARKERS for e in files):
            rel = os.path.relpath(path, USB_ROOT)
            projects.append({"name": os.path.basename(path) or "根目录",
                             "path": path, "rel": rel, "type": "web"})
            seen.add(path)
            return
        low = path.lower()
        for km in known:
            if km in low and path not in seen:
                rel = os.path.relpath(path, USB_ROOT)
                projects.append({"name": os.path.basename(path), "path": path,
                                 "rel": rel, "type": "folder"})
                seen.add(path)
        if depth < 2:
            for e in entries:
                if e.is_dir() and e.name not in PROJECT_SKIP and \
                   not e.name.endswith("_Data"):
                    walk(e.path, depth + 1)

    walk(USB_ROOT, 0)
    return projects[:60]


def scan_installers():
    out = []
    for d in INSTALLER_DIRS:
        base = os.path.join(USB_ROOT, d)
        if not os.path.isdir(base):
            continue
        for dp, dirs, files in os.walk(base):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            for f in files:
                if f.lower().endswith((".exe", ".msi", ".zip", ".7z", ".msix", ".appx")):
                    fp = os.path.join(dp, f)
                    try:
                        sz = os.path.getsize(fp)
                    except OSError:
                        sz = 0
                    out.append({"name": f, "path": fp,
                                "size_mb": round(sz / 1024 / 1024, 1),
                                "dir": d})
    return out


def find_ollama():
    for pat in ["AI/ollama.exe", "AI/ollama/ollama.exe", "DevEnv/ollama/ollama.exe"]:
        hits = _resolve(pat)
        if hits:
            return hits[0]
    return None


def ai_running():
    """探测 ollama serve 是否已在监听。"""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{AI_SERVE_PORT}/api/tags",
                                    timeout=0.6) as r:
            return r.status == 200
    except Exception:
        return False


# ---- 本地服务器（拉起项目） --------------------------------------------
active_servers = {}   # port -> http.server
ai_proc = [None]        # 本地 AI 进程（ollama serve）


def start_project_server(project_path):
    """给某项目目录起一个静态服务器，返回 http://localhost:port。"""
    port = 8123
    while port < 8200:
        if port not in active_servers:
            break
        port += 1
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=project_path)
    try:
        httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    except OSError:
        return None
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    active_servers[port] = httpd
    return f"http://127.0.0.1:{port}"


def stop_server(port):
    if port in active_servers:
        srv = active_servers.pop(port)
        srv.shutdown()
        srv.server_close()
        return True
    return False


# ---- HTTP 服务 ---------------------------------------------------------
class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            try:
                with open(os.path.join(LAUNCH_DIR, "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(404, "index.html 缺失")
            return
        if parsed.path == "/api/scan":
            payload = {
                "usb": USB_ROOT,
                "env": env_status(),
                "tools": scan_tools(),
                "projects": scan_projects(),
                "installers": scan_installers(),
                "ai": {"found": find_ollama() is not None,
                       "running": ai_running(),
                       "path": find_ollama() or ""},
            }
            self._send(200, json.dumps(payload, ensure_ascii=False))
            return
        if parsed.path == "/api/ai_status":
            self._send(200, json.dumps({"running": ai_running(),
                                        "found": find_ollama() is not None}))
            return
        self._send(404, json.dumps({"error": "未找到该接口"}))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        act = parsed.path

        if act == "/api/open":
            path = q.get("path", [""])[0]
            if path and os.path.exists(path):
                try:
                    if os.name == "nt":
                        os.startfile(path)
                    else:
                        subprocess.Popen(["xdg-open", path])
                    self._send(200, json.dumps({"ok": True, "msg": "已打开"}))
                except Exception as e:
                    self._send(500, json.dumps({"error": str(e)}))
            else:
                self._send(400, json.dumps({"error": "路径无效"}))
            return

        if act == "/api/serve":
            path = q.get("path", [""])[0]
            if path and os.path.isdir(path):
                url = start_project_server(path)
                if url:
                    self._send(200, json.dumps({"url": url, "port": int(url.rsplit(":", 1)[1])}))
                else:
                    self._send(500, json.dumps({"error": "端口分配失败"}))
            else:
                self._send(400, json.dumps({"error": "路径无效"}))
            return

        if act == "/api/stop":
            port = int(q.get("port", ["0"])[0])
            self._send(200, json.dumps({"ok": stop_server(port)}))
            return

        if act == "/api/ai_start":
            exe = find_ollama()
            if not exe:
                self._send(404, json.dumps({"error": "未找到 Ollama，请把 ollama.exe 放进 U 盘 AI\\ 目录"}))
                return
            try:
                proc = subprocess.Popen([exe, "serve"], cwd=os.path.dirname(exe),
                                        creationflags=NEW_PROCESS_GROUP)
                ai_proc[0] = proc
                self._send(200, json.dumps({"url": f"http://127.0.0.1:{AI_SERVE_PORT}",
                                            "ok": True, "msg": "本地 AI 服务已启动"}))
            except Exception as e:
                self._send(500, json.dumps({"error": str(e)}))
            return

        if act == "/api/ai_stop":
            proc = ai_proc[0]
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    ai_proc[0] = None
                    self._send(200, json.dumps({"ok": True, "msg": "已停止"}))
                except Exception as e:
                    self._send(500, json.dumps({"error": str(e)}))
            else:
                ai_proc[0] = None
                self._send(200, json.dumps({"ok": True, "msg": "未在运行"}))
            return

        if act == "/api/setup":
            if os.path.exists(SETUP_BAT):
                try:
                    subprocess.Popen(["cmd", "/c", SETUP_BAT],
                                    creationflags=NEW_PROCESS_GROUP)
                    self._send(200, json.dumps({"ok": True,
                                                "msg": "已启动环境补全（finish_setup.bat）"}))
                except Exception as e:
                    self._send(500, json.dumps({"error": str(e)}))
            else:
                self._send(404, json.dumps({"error": "未找到 finish_setup.bat"}))
            return

        if act == "/api/integrity":
            ps = os.path.abspath(INTEGRITY_PS)
            if os.path.exists(ps):
                try:
                    subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy",
                                       "Bypass", "-File", ps],
                                     creationflags=NEW_PROCESS_GROUP)
                    self._send(200, json.dumps({"ok": True, "msg": "已启动完整性校验"}))
                except Exception as e:
                    self._send(500, json.dumps({"error": str(e)}))
            else:
                self._send(404, json.dumps({"error": "未找到 integrity_check.ps1"}))
            return

        self._send(404, json.dumps({"error": "未找到该接口"}))

    def log_message(self, *args):
        pass


def main():
    port = 8787
    httpd = socketserver.TCPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"[NomadDev] U盘根: {USB_ROOT}")
    print(f"[NomadDev] 打开: {url}")
    threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == "__main__":
    main()
