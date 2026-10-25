#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量生成 TTS 语音（edge-tts 微软晓晓神经网络语音）。

用法:
  python gen_tts.py <narration.json> --outdir audio/tts [--voice zh-CN-XiaoxiaoNeural]
                    [--rate +30%] [--only 3,7,12] [--force]

特性:
- 已存在且体积正常的 mp3 默认跳过（断点续跑）；--force 强制重生成
- --only 只生成指定 id（修正个别段时用，避免全量重跑）
- 实测晓晓 +30% 实际语速 ≈5.8 字/秒（比按 4.95 估算快，别过度压缩文本）
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def resolve_edge_tts():
    """定位 edge-tts：优先 PATH 上的可执行文件，否则用当前解释器 -m 调用。"""
    found = shutil.which("edge-tts")
    if found:
        return [found]
    return [sys.executable, "-m", "edge_tts"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("narration")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    ap.add_argument("--rate", default="+30%")
    ap.add_argument("--only", default=None, help="逗号分隔的 id，只生成这些段")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    data = json.loads(Path(args.narration).expanduser().read_text(encoding="utf-8"))
    segs = data["segments"]
    outdir = Path(args.outdir).expanduser()
    if not outdir.exists():
        outdir.mkdir(parents=True)

    only = None
    if args.only:
        only = {int(x) for x in args.only.split(",")}

    ok, fail = 0, []
    for s in segs:
        if only is not None and s["id"] not in only:
            continue
        mp3 = outdir / f"cue{s['id']:02d}.mp3"
        if mp3.exists() and mp3.stat().st_size > 1000 and not args.force:
            ok += 1
            continue
        r = subprocess.run(
            resolve_edge_tts() + ["--voice", args.voice, f"--rate={args.rate}",
             "--text", s["text"], "--write-media", str(mp3)],
            capture_output=True, text=True)
        if r.returncode == 0 and mp3.exists() and mp3.stat().st_size > 1000:
            ok += 1
        else:
            fail.append((s["id"], (r.stderr or "").strip()[:300]))

    total = len(only) if only else len(segs)
    print(f"生成 {ok}/{total}")
    if fail:
        print("失败:", fail)
        sys.exit(1)


if __name__ == "__main__":
    main()
