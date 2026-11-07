#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境预检：一键检查所有依赖是否就绪，避免跑到中间才发现缺东西。

用法:
  python scripts/check_env.py

输出 PASS / FAIL 逐项，任何 FAIL 退出码 1（可用于 CI）。
"""
import importlib
import shutil
import sys
from pathlib import Path

# (import_name, pip_name, required_by)
PY_DEPS = [
    ("av",        "av",            "阶段5 硬字幕烧录"),
    ("PIL",       "Pillow",        "阶段5 硬字幕烧录"),
    ("numpy",     "numpy",         "阶段2 画面渲染"),
    ("pypdf",     "pypdf",         "阶段1 解析 PDF"),
    ("docx",      "python-docx",   "阶段1 解析 DOCX"),
    ("cv2",       "opencv-python", "阶段2 内嵌白板渲染器"),
    ("edge_tts",  "edge-tts==7.3.1","阶段4 TTS 配音"),
]

BIN_DEPS = [
    ("ffmpeg",  "视频封装 / 音轨合成 / 音频转码"),
    ("ffprobe", "读取音频时长 / 质检"),
]


def check():
    print("=== doc-to-whiteboard-video 环境预检 ===\n")
    fails = 0

    print("[Python 依赖]")
    for mod, pip_name, used_by in PY_DEPS:
        try:
            m = importlib.import_module(mod)
            ver = getattr(m, "__version__", "") or getattr(m, "version", "")
            print(f"  OK   {mod:12s} {ver}")
        except ImportError:
            print(f"  FAIL {mod:12s} → pip install {pip_name}   (用途: {used_by})")
            fails += 1

    print("\n[系统二进制]")
    for bin_name, used_by in BIN_DEPS:
        p = shutil.which(bin_name)
        if p:
            print(f"  OK   {bin_name:12s} {p}")
        else:
            print(f"  FAIL {bin_name:12s} → 需在 PATH 中安装 ffmpeg   (用途: {used_by})")
            fails += 1

    # edge-tts 版本检查
    try:
        import edge_tts
        ver = getattr(edge_tts, "__version__", "")
        if ver and not ver.startswith("7.3"):
            print(f"\n[WARN] edge-tts 版本 {ver}，推荐 7.3.1（其他版本可能被微软 403）")
    except ImportError:
        pass

    # 内嵌渲染器检查（自包含，无需上游技能）
    render_dir = Path(__file__).resolve().parent / "render"
    render_ok = (
        (render_dir / "render_stream_whiteboard.py").exists()
        and (render_dir / "stream_render.py").exists()
        and (render_dir / "merge_scenes.py").exists()
    )
    hand = Path(__file__).resolve().parent.parent / "assets" / "drawing-hand.png"
    print("\n[内嵌渲染器]")
    if render_ok:
        print("  OK   scripts/render/（内嵌渲染脚本齐全）")
    else:
        print("  FAIL scripts/render/ 缺少渲染脚本")
        print("       需包含 render_stream_whiteboard.py / stream_render.py / merge_scenes.py")
        fails += 1
    if not hand.exists():
        print("  WARN assets/drawing-hand.png 不存在，白板渲染笔尖素材缺失")
    else:
        print("  OK   drawing-hand.png（无字干净版）")


    print()
    if fails:
        print(f"结论: FAIL — {fails} 项未通过，请先修复后重跑")
        sys.exit(1)
    else:
        print("结论: PASS — 环境就绪，可以开始使用")
        sys.exit(0)


if __name__ == "__main__":
    check()
