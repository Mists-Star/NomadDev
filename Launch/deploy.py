#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DevLauncher deploy — 按「预设/角色」快速部署便携开发环境
=========================================================
用法：
  python deploy.py --preset web --list        # 只看计划（不复制）
  python deploy.py --preset fullstack --go    # 真部署（本机有源的包复制到 U盘 DevEnv）
  python deploy.py                            # 默认 core 预设 + 预览

流程：
  1. 读 packages.json 的预设(含 who/roadmap) 与包目录
  2. 读私有 sources.json：包 id -> 本机源路径（个人文件，不进仓库）
  3. 本机有源 -> 断点续传复制到 <U盘>/DevEnv
     本机无源/联网类 -> 打印「需联网获取」指引
目标当前为 U盘(usb)。PC 工作区(target=pc --out)为后续版本。
"""
import os
import sys
import json
import shutil
import argparse

LAUNCH_DIR = os.path.dirname(os.path.abspath(__file__))
USB_ROOT = os.path.dirname(LAUNCH_DIR)
PKG_JSON = os.path.join(LAUNCH_DIR, "packages.json")
SRC_JSON = os.path.join(LAUNCH_DIR, "sources.json")   # 私有

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CHUNK = 4 * 1024 * 1024


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
    # 断点续传：目标保留 have 字节，源从 have 偏移续读
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
    done = 0
    for dp, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fn in files:
            if fn in skip_files:
                continue
            total += 1
    i = 0
    for dp, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        rel = os.path.relpath(dp, src)
        tdir = dst if rel == "." else os.path.join(dst, rel)
        for fn in files:
            if fn in skip_files:
                continue
            i += 1
            sf = os.path.join(dp, fn)
            df = os.path.join(tdir, fn)
            st = copy_resume(sf, df)
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


def main():
    ap = argparse.ArgumentParser(description="DevLauncher quick deploy")
    ap.add_argument("--preset", default="core")
    ap.add_argument("--go", action="store_true", help="actually copy (default is plan only)")
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
    print(f"  适合: {pr.get('who','')}")
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
            plan.append({"id": pid, "name": meta.get("name", pid),
                         "kind": "local", "ready": ok,
                         "src": s["src"], "dst": os.path.join(USB_ROOT, s["dest"]),
                         "skip_dirs": s.get("skip_dirs", []),
                         "skip_files": s.get("skip_files", []),
                         "size_mb": meta.get("size_mb", 0)})
        else:
            plan.append({"id": pid, "name": meta.get("name", pid),
                         "kind": "online", "ready": False,
                         "size_mb": meta.get("size_mb", 0),
                         "note": meta.get("desc", "")})

    print("\n[计划]")
    local_total = 0
    for p in plan:
        if p["kind"] == "local":
            flag = "OK" if p["ready"] else "缺源"
            print(f"  [本地 {flag}] {p['name']:22s} {p['size_mb']}MB  ->  {os.path.relpath(p['dst'], USB_ROOT)}")
            local_total += p["size_mb"]
        else:
            print(f"  [联网    ] {p['name']:22s} {p['size_mb']}MB  (本机无源，需联网获取: {p['note']})")
    print(f"\n  本地可复制合计约 {local_total}MB；联网项需额外下载。")

    if not a.go:
        print("\n(预览模式，未复制。加 --go 执行真实部署)")
        return 0

    print("\n[执行复制]")
    total_done = 0
    for p in plan:
        if p["kind"] != "local":
            print(f"  !! {p['name']}: 需联网，跳过（{p.get('note','')}）")
            continue
        if not p["ready"]:
            print(f"  !! {p['name']}: 源目录不存在，跳过: {p['src']}")
            continue
        print(f"  -> 复制 {p['name']} ...")
        n, d = copy_tree(p["src"], p["dst"], p["skip_dirs"], p["skip_files"])
        print(f"     完成: 检查 {n} 文件, 新复制/续传 {d}")
        total_done += d
    print(f"\n部署完成。总计复制/续传 {total_done} 个文件。")
    print("提示: 打开 U盘 根目录 finish_setup.bat 可全量补全；launch.bat 启动启动器。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
