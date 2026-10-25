#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
封装最终成品：带字幕视频 + 音轨 → MP4（视频轨 copy 无损，音频转 AAC）。

用法:
  python mux_final.py --video 带字幕.mp4 --audio audio/final_track.wav --out 成品.mp4
                      [--subtitle 字幕.srt]   # 可选附加软字幕轨

说明: 字幕若已烧录进画面（推荐），无需再传 --subtitle。
      附加软字幕轨仅作冗余（注意 mov_text 在部分播放器不显示）。
"""
import argparse
import subprocess
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--subtitle", default=None)
    ap.add_argument("--abitrate", default="192k")
    args = ap.parse_args()

    video = Path(args.video).expanduser()
    audio = Path(args.audio).expanduser()
    out = Path(args.out).expanduser()

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio)]
    maps = ["-map", "0:v", "-map", "1:a"]
    if args.subtitle:
        cmd += ["-i", str(Path(args.subtitle).expanduser())]
        maps += ["-map", "2:s"]
    cmd += maps + ["-c:v", "copy", "-c:a", "aac", "-b:a", args.abitrate, "-shortest"]
    if args.subtitle:
        cmd += ["-c:s", "mov_text", "-metadata:s:s:0", "language=chi"]
    cmd += [str(out)]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[err] {r.stderr.strip()[:600]}", file=sys.stderr)
        sys.exit(1)

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
         "-of", "csv=p=0", str(out)], capture_output=True, text=True)
    print(f"封装成功: {out}")
    print(f"  {probe.stdout.strip()}")


if __name__ == "__main__":
    main()
