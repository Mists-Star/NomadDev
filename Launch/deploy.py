#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NomadDev deploy — 按「预设/角色」快速部署便携开发环境
=========================================================
用法：
  python deploy.py --preset web                      # 预览计划
  python deploy.py --preset fullstack --go           # 部署：本机有源就复制
  python deploy.py --preset fullstack --go --online  # 部署：缺的包自动联网下载
  python deploy.py --preset aiwork --go --online     # 离线 AI 预设（需联网取 ollama）

流程：
  1. 读 packages.json 的预设(who/roadmap)与包目录
  2. 本地源(sources.json, 私有)有 -> 断点续传复制到 <根>/DevEnv
  3. 无本地源但有下载规格 -> --online 时从镜像下载便携包并解压进 DevEnv
  4. 两者都没有 -> 打印手动获取指引
目标当前为 U盘(usb)。PC 工作区(target=pc --out)为后续版本。
"""
import os
import sys
import json
import shutil
import zipfile
import argparse
import urllib.request

LAUNCH_DIR = os.path.dirname(os.path.abspath(__file__))
USB_ROOT = os.path.dirname(LAUNCH_DIR)
PKG_JSON = os.path.join(LAUNCH_DIR, "packages.json")
SRC_JSON = os.path.join(LAUNCH_DIR, "sources.json")   # 私有
DL_DIR = os.path.join(LAUNCH_DIR, "_dl")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CHUNK = 4 * 1024 * 1024
UA = {"User-Agent": "NomadDev-deploy/0.2 (+portable workspace)"}

# 核心便携包的镜像下载规格（与 finish_setup.bat 同源，优先国内镜像）
DOWNLOADS = {
    "python": dict(dest="DevEnv/python", check="DevEnv/python/python.exe",
                   urls=["https://mirrors.huaweicloud.com/python/3.13.12/python-3.13.12-embed-amd64.zip",
                         "https://www.python.org/ftp/python/3.13.12/python-3.13.12-embed-amd64.zip"]),
    "node": dict(dest="DevEnv/node", check="DevEnv/node/node.exe",
                 urls=["https://registry.npmmirror.com/-/binary/node/v22.22.2/node-v22.22.2-win-x64.zip",
                       "https://nodejs.org/dist/v22.22.2/node-v22.22.2-win-x64.zip"]),
    "git": dict(dest="DevEnv/git", check="DevEnv/git/cmd/git.exe",
                urls=["https://github.com/git-for-windows/git/releases/download/v2.46.0.windows.1/MinGit-2.46.0-64-bit.zip"]),
    "jdk": dict(dest="DevEnv/jdk", check="DevEnv/jdk/bin/java.exe",
                urls=["https://api.adoptium.net/v3/binary/latest/17/ga/windows/x64/jdk/hotspot/normal/eclipse"]),
    "adb": dict(dest="DevEnv/adb", check="DevEnv/adb/adb.exe",
                urls=["https://dl.google.com/android/repository/platform-tools-latest-windows.zip"]),
}


def copy_resume(sf, df):
    """跳过大小一致；否则从已存在部分续传；损坏/空则重拷。"""
    need = os.path.getsize(sf)
    have = os.path.getsize(df) if os.path.exists(df) else 0
    if have == need:
        return "skip"
    ddir = os.path.dirname(df)
    if not os.path.isdir(ddir):
        os.makedirs(ddir, exist_ok=True)
    if have == 0 or have > need:
        with open(sf, "rb") as r, open(df, "wb") as w:
            shutil.copyfileobj(r, w, CHUNK)
        return "copy"
    with open(sf, "rb") as r, open(df, "r+b") as w:
        r.seek(have)
        w.seek(0, os.SEEK_END)
        while True:
            b = r.read(CHUNK)
            if not b:
                break
            w.write(b)
    return "resume"


def copy_tree(src, dst, skip_dirs=(), skip_files=()):
    total = 0
    for dp, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        total += len([f for f in files if f not in skip_files])
    i = done = 0
    for dp, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        rel = os.path.relpath(dp, src)
        tdir = dst if rel == "." else os.path.join(dst, rel)
        for fn in files:
            if fn in skip_files:
                continue
            i += 1
            st = copy_resume(os.path.join(dp, fn), os.path.join(tdir, fn))
            if st != "skip":
                done += 1
            if i % 25 == 0:
                print(f"    [{i}/{total}] {os.path.basename(tdir)}/{fn}")
    return total, done


def load_json(p):
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("!! 无法解析", p, "->", e)
        return {}


def already_good(rel_check):
    p = os.path.join(USB_ROOT, rel_check)
    return os.path.exists(p) and os.path.getsize(p) > 0


def download(urls, dest_zip):
    for u in urls:
        try:
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                total = int(r.headers.get("Content-Length") or 0)
                got = 0
                with open(dest_zip, "wb") as f:
                    while True:
                        b = r.read(1 << 16)
                        if not b:
                            break
                        f.write(b)
                        got += len(b)
                if total and got < total * 0.9:
                    raise IOError("download incomplete")
            print(f"      [OK] {got / 1048576:.1f} MB  <- {u}")
            return True
        except Exception as e:
            print(f"      [!] {u}\n          {e.__class__.__name__}: {e}")
    return False


def extract_zip(zip_path, dest, pkg):
    """解压到 DevEnv/<pkg>，自动展平 zip 顶层单目录（node/jdk/adb/git 都是这种）。"""
    tmp = os.path.join(DL_DIR, "x_" + pkg)
    if os.path.isdir(tmp):
        shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        firsts = {n.split("/", 1)[0] for n in names}
        root = next(iter(firsts)) if len(firsts) == 1 else None
        z.extractall(tmp)
    src = os.path.join(tmp, root) if root else tmp
    os.makedirs(dest, exist_ok=True)
    for child in os.listdir(src):
        shutil.move(os.path.join(src, child), os.path.join(dest, child))
    shutil.rmtree(tmp, ignore_errors=True)
    return root


def fetch_one(pid, meta):
    spec = DOWNLOADS[pid]
    dest = os.path.join(USB_ROOT, spec["dest"])
    if already_good(spec["check"]):
        print(f"  [已装] {meta.get('name', pid)} 已就绪，跳过下载")
        return True
    os.makedirs(DL_DIR, exist_ok=True)
    zpath = os.path.join(DL_DIR, pid + ".zip")
    print(f"  -> 下载 {meta.get('name', pid)} ...")
    if not download(spec["urls"], zpath):
        print(f"  [FAIL] {pid} 下载失败。可手动下载后解压到 {spec['dest']}。")
        return False
    try:
        root = extract_zip(zpath, dest, pid)
        print(f"      [OK] 已解压到 {spec['dest']}" + (f" (展平 {root})" if root else ""))
        if already_good(spec["check"]):
            print("      [OK] 校验通过")
            return True
        print(f"      [!!] 解压后未在 {spec['check']} 找到可执行文件，请人工检查")
        return False
    except Exception as e:
        print(f"  [FAIL] 解压失败: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description="NomadDev quick deploy")
    ap.add_argument("--preset", default="core")
    ap.add_argument("--go", action="store_true", help="actually deploy (default: plan only)")
    ap.add_argument("--online", action="store_true", help="download missing packages from mirrors")
    ap.add_argument("--target", default="usb", choices=["usb", "pc"])
    ap.add_argument("--out", default="", help="PC target directory (not implemented yet)")
    a = ap.parse_args()

    pkg = load_json(PKG_JSON)
    sources = load_json(SRC_JSON)
    presets = {p["id"]: p for p in pkg.get("presets", [])}
    catalog = {p["id"]: p for p in pkg.get("packages", [])}

    if a.preset not in presets:
        print("未知预设:", a.preset)
        print("可选:", ", ".join(presets))
        return 1
    pr = presets[a.preset]

    if a.target == "pc":
        print("[i] PC 工作区部署尚未实现（v0 仅支持 --target usb）。")
        return 0

    print("=" * 62)
    print(f"  预设: {pr['name']}   ({a.preset})")
    print(f"  适合: {pr.get('who', '')}")
    print("-" * 62)
    print("  搭建路线:")
    for k, step in enumerate(pr.get("roadmap", []), 1):
        print(f"    {k}. {step}")
    print("=" * 62)

    plan = []
    for pid in pr.get("pkgs", []):
        meta = catalog.get(pid, {})
        if pid in sources:
            s = sources[pid]
            ok = os.path.isdir(s["src"])
            plan.append({"id": pid, "name": meta.get("name", pid), "kind": "local",
                         "ready": ok, "src": s["src"],
                         "dst": os.path.join(USB_ROOT, s["dest"]),
                         "skip_dirs": s.get("skip_dirs", []),
                         "skip_files": s.get("skip_files", []),
                         "size_mb": meta.get("size_mb", 0)})
        elif pid in DOWNLOADS:
            plan.append({"id": pid, "name": meta.get("name", pid), "kind": "dl",
                         "ready": already_good(DOWNLOADS[pid]["check"]),
                         "size_mb": meta.get("size_mb", 0)})
        else:
            plan.append({"id": pid, "name": meta.get("name", pid), "kind": "online",
                         "ready": False, "size_mb": meta.get("size_mb", 0),
                         "note": meta.get("desc", "")})

    print("\n[计划]")
    for p in plan:
        if p["kind"] == "local":
            flag = "OK" if p["ready"] else "缺源"
            print(f"  [本地 {flag}] {p['name']:20s} {p['size_mb']}MB  ->  {os.path.relpath(p['dst'], USB_ROOT)}")
        elif p["kind"] == "dl":
            flag = "已装" if p["ready"] else "可自动下载(--online)"
            print(f"  [联网     ] {p['name']:20s} {p['size_mb']}MB  ({flag})")
        else:
            print(f"  [手取     ] {p['name']:20s} {p['size_mb']}MB  ({p['note']})")

    if not a.go:
        print("\n(预览模式，未执行。加 --go 部署；联网项需再加 --online)")
        return 0

    print("\n[执行]")
    total_done = 0
    for p in plan:
        name = p["name"]
        if p["kind"] == "local":
            if not p["ready"]:
                if p["id"] in DOWNLOADS and a.online:
                    ok = fetch_one(p["id"], catalog.get(p["id"], {}))
                    if ok:
                        total_done += 1
                else:
                    print(f"  !! {name}: 本地源缺失({p['src']})" + ("，尝试联网失败/未启用 --online" if p['id'] in DOWNLOADS else ""))
                continue
            print(f"  -> 复制 {name} ...")
            n, d = copy_tree(p["src"], p["dst"], p["skip_dirs"], p["skip_files"])
            print(f"     完成: 检查 {n} 文件, 新复制/续传 {d}")
            total_done += d
        elif p["kind"] == "dl":
            if p["ready"]:
                print(f"  [已装] {name} 已就绪，跳过")
            elif a.online:
                ok = fetch_one(p["id"], catalog.get(p["id"], {}))
                if ok:
                    total_done += 1
            else:
                print(f"  !! {name}: 本机无源，需 --online 联网下载（当前未启用）")
        else:
            print(f"  !! {name}: 需手动获取（暂无自动下载源）: {p.get('note', '')}")
    print(f"\n部署完成。剩余缺项可用 finish_setup.bat（全量/联网）补齐；launch.bat 启动启动器。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
