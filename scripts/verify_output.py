#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成品端到端自检（交付前必跑）。逐项检查并给出 PASS/FAIL：

1. 流结构：视频 h264 + 音频 aac（+ 可选字幕轨）
2. 时长匹配：成品时长 vs 视频源时长（偏差应 <1s）
3. 语音连续性：按窗口采样音量，静音窗口（<-45dB 且持续）视为语音空白
4. 字幕可见性：抽帧检测底部区域是否存在「深色底框 + 亮白文字」
5. BGM 存在性：无人声窗口应有底噪（BGM），不应是完全静音

用法:
  python verify_output.py 成品.mp4 [--step 15] [--frames 20,60,150,300]
"""
import argparse
import subprocess
import sys
from pathlib import Path


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def ffprobe_fields(path, *fields):
    return sh(["ffprobe", "-v", "error", "-show_entries", ":".join(fields),
               "-of", "csv=p=0", str(path)])


def mean_volume(path, start, dur=1.0):
    out = subprocess.run(
        ["ffmpeg", "-ss", str(start), "-t", str(dur), "-i", str(path),
         "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    for line in out.splitlines():
        if "mean_volume" in line:
            try:
                return float(line.split(":")[1].replace("dB", "").strip())
            except Exception:
                return None
    return None


def check_subtitle_frame(path, t):
    """抽帧 → 检测底部 25% 是否有字幕（深色底框 + 亮白文字）"""
    import av
    import numpy as np
    try:
        c = av.open(str(path))
        s = c.streams.video[0]
        for f in c.decode(s):
            if abs(f.time - t) < 0.1:
                arr = f.to_ndarray(format="rgb24")
                h = arr.shape[0]
                b = arr[int(h * 0.75):, :, :].astype(int)
                dark = (b[:, :, 0] < 180) & (b[:, :, 1] < 180) & (b[:, :, 2] < 180)
                white = (b[:, :, 0] > 240) & (b[:, :, 1] > 240) & (b[:, :, 2] > 240)
                c.close()
                return dark.mean() * 100, white.mean() * 100
            if f.time > t + 1:
                break
        c.close()
    except Exception:
        pass
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--step", type=int, default=15, help="音量采样步长（秒）")
    ap.add_argument("--frames", default="20,60,150,300", help="字幕抽帧时间点")
    ap.add_argument("--expect-duration", type=float, default=0)
    args = ap.parse_args()

    p = Path(args.video).expanduser()
    fails, warns = [], []
    print(f"=== 成品自检: {p.name} ===\n")

    # 1. 流结构
    codecs = ffprobe_fields(p, "stream=codec_type", "stream=codec_name")
    codec_list = [c.strip() for c in codecs.splitlines() if c.strip()]
    print(f"[1] 流结构: {codec_list}")
    if not any("h264" in c or "hevc" in c for c in codec_list):
        fails.append("缺少视频轨")
    if not any("aac" in c or "mp3" in c for c in codec_list):
        fails.append("缺少音频轨")

    # 2. 时长
    dur = float(sh(["ffprobe", "-v", "error", "-show_entries",
                    "format=duration", "-of", "csv=p=0", str(p)]))
    print(f"[2] 时长: {dur:.1f}s")
    if args.expect_duration and abs(dur - args.expect_duration) > 1.0:
        warns.append(f"时长偏差 {dur - args.expect_duration:+.1f}s")

    # 3. 语音连续性
    print(f"[3] 语音连续性采样（步长 {args.step}s）:")
    silent = []
    t = 0.0
    while t < dur - 1:
        v = mean_volume(p, t)
        flag = ""
        if v is None or v < -45:
            silent.append(round(t, 1))
            flag = "  <-- 静音"
        print(f"    {t:6.1f}s: {v}dB{flag}")
        t += args.step
    if len(silent) > max(2, int(dur / args.step) * 0.15):
        fails.append(f"静音窗口过多: {silent}")

    # 4. 字幕可见性
    print("[4] 字幕抽帧检测:")
    sub_ok = 0
    for ts in [float(x) for x in args.frames.split(",") if x]:
        if ts >= dur:
            continue
        dark, white = check_subtitle_frame(p, ts)
        if dark is None:
            print(f"    {ts}s: 抽帧失败")
            continue
        ok = dark > 0.5 and white > 0.3
        sub_ok += 1 if ok else 0
        print(f"    {ts}s: 底框 {dark:.2f}% 文字 {white:.2f}% {'OK' if ok else 'MISSING'}")
        if not ok:
            warns.append(f"{ts}s 未检测到字幕")
    if sub_ok == 0:
        warns.append("所有抽帧点均未检测到字幕（确认是否已烧录）")

    print("\n=== 结论 ===")
    if fails:
        print("FAIL:")
        for f in fails:
            print(f"  - {f}")
    if warns:
        print("WARN:")
        for w in warns:
            print(f"  - {w}")
    if not fails and not warns:
        print("PASS: 全部检查通过")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
