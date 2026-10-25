#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音轨合成：TTS 语音按时间轴 adelay 对齐 → apad 补齐 → BGM 循环低音量混音。

用法:
  python build_audio.py --tts-dir audio/tts --timeline audio/timeline.json
                        --bgm <bgm.wav> --total-ms 394000
                        --voice-out audio/voice_track.wav --out audio/final_track.wav
                        [--bgm-volume 0.08]

踩坑提醒（勿改回旧写法）：
1. amix 输出后不能直接链 apad，必须拆成两条 filter：
   `...amix=...[voice];[voice]apad=whole_dur=394.000[voice2]`
2. 不补齐的话 amix 默认 duration=longest 会截断在最后一段语音结束处，
   导致音轨比视频短几秒（本次曾短 8.3s）
3. BGM 用 -stream_loop -1 循环 + atrim 截断，amix duration=first 以语音轨为准
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[err] {r.stderr.strip()[:600]}", file=sys.stderr)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tts-dir", required=True)
    ap.add_argument("--timeline", required=True)
    ap.add_argument("--bgm", required=True)
    ap.add_argument("--total-ms", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--voice-out", default=None,
                    help="中间产物纯语音轨路径，默认 <out目录>/voice_track.wav")
    ap.add_argument("--bgm-volume", type=float, default=0.08)
    args = ap.parse_args()

    tts = Path(args.tts_dir).expanduser()
    tl = json.loads(Path(args.timeline).expanduser().read_text(encoding="utf-8"))["segments"]
    out = Path(args.out).expanduser()
    voice_out = Path(args.voice_out).expanduser() if args.voice_out else out.parent / "voice_track.wav"
    total_s = args.total_ms / 1000.0

    # ---- 1. mp3 → wav（统一 44.1kHz 立体声）----
    wavs = []
    for seg in tl:
        sid = seg["id"]
        mp3 = tts / f"cue{sid:02d}.mp3"
        wav = tts / f"cue{sid:02d}.wav"
        if not wav.exists():
            if not mp3.exists():
                print(f"[err] 缺音频 cue{sid:02d}", file=sys.stderr)
                sys.exit(1)
            r = run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3),
                     "-ar", "44100", "-ac", "2", str(wav)])
            if r.returncode != 0:
                sys.exit(1)
        wavs.append(wav)
    print(f"wav 就绪: {len(wavs)}/{len(tl)}")

    # ---- 2. adelay + amix + apad ----
    n = len(wavs)
    filters = [f"[{i}:a]adelay={tl[i]['startMs']}|{tl[i]['startMs']}[v{i}]" for i in range(n)]
    filters.append(f"{''.join(f'[v{i}]' for i in range(n))}amix=inputs={n}:normalize=0[voice]")
    filters.append(f"[voice]apad=whole_dur={total_s:.3f}[voice2]")

    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for w in wavs:
        cmd += ["-i", str(w)]
    cmd += ["-filter_complex", ";".join(filters),
            "-map", "[voice2]", "-t", f"{total_s:.3f}", str(voice_out)]
    print("== 合成语音轨 ==")
    if run(cmd).returncode != 0 or not voice_out.exists():
        sys.exit(1)
    print(f"语音轨: {voice_out.name} ({voice_out.stat().st_size//1024}KB)")

    # ---- 3. BGM 循环混音 ----
    print("== 混入 BGM ==")
    cmd2 = ["ffmpeg", "-y", "-loglevel", "error",
            "-i", str(voice_out),
            "-stream_loop", "-1", "-i", str(Path(args.bgm).expanduser()),
            "-filter_complex",
            f"[1:a]volume={args.bgm_volume},atrim=0:{total_s:.3f},asetpts=N/SR/TB[bgm];"
            f"[0:a][bgm]amix=inputs=2:duration=first:normalize=0[aout]",
            "-map", "[aout]", "-ar", "44100", "-ac", "2", str(out)]
    if run(cmd2).returncode != 0 or not out.exists():
        sys.exit(1)
    print(f"最终音轨: {out} ({out.stat().st_size//1024}KB)")


if __name__ == "__main__":
    main()
