#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成【连续语音时间轴】：所有旁白段首尾相接铺满视频，消除段间/幕间空白。

关键设计（用户明确要求）：语音必须连续，不能出现几秒静默，否则观众只能靠画面
获取信息而画面是静态线稿。因此这里**不按幕均分**，而是按每段实际音频时长串联。

用法:
  python make_timeline.py <narration.json> --tts-dir audio/tts --out audio/timeline.json
                          [--start-offset 800] [--gap 150] [--target-ms 394000]

- start-offset: 首段起始偏移（默认 800ms，给开场留呼吸）
- gap: 段间衔接间隔（默认 150ms，人耳几乎无感，避免完全贴死）
- target-ms: 视频总时长；若语音总长超出会告警（需精简旁白或降低语速）
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def dur(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("narration")
    ap.add_argument("--tts-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--start-offset", type=int, default=800)
    ap.add_argument("--gap", type=int, default=150)
    ap.add_argument("--target-ms", type=int, default=0)
    args = ap.parse_args()

    data = json.loads(Path(args.narration).expanduser().read_text(encoding="utf-8"))
    segs = data["segments"]
    tts = Path(args.tts_dir).expanduser()

    timeline, cursor = [], args.start_offset
    missing = []
    for s in segs:
        mp3 = tts / f"cue{s['id']:02d}.mp3"
        if not mp3.exists():
            missing.append(s["id"])
            d_ms = 0
        else:
            d_ms = int(dur(mp3) * 1000)
        timeline.append({"id": s["id"], "startMs": cursor,
                         "durMs": d_ms, "endMs": cursor + d_ms})
        cursor += d_ms + args.gap

    total = timeline[-1]["endMs"] if timeline else 0
    out = Path(args.out).expanduser()
    out.write_text(json.dumps({"segments": timeline, "totalMs": total},
                              ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"时间轴: {len(timeline)} 段, 语音铺满至 {total/1000:.1f}s")
    if missing:
        print(f"[warn] 缺失音频: {missing}")
    if args.target_ms:
        delta = total - args.target_ms
        if delta > 1500:
            print(f"[warn] 语音超出视频 {delta/1000:.1f}s —— 需精简旁白或提高语速")
        elif delta < -8000:
            print(f"[warn] 语音短于视频 {abs(delta)/1000:.1f}s —— 结尾会静音，需补写旁白")
        else:
            print(f"[ok] 与视频时长匹配（差 {delta/1000:+.1f}s）")


if __name__ == "__main__":
    main()
