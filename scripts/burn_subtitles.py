#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
硬字幕烧录：PyAV 逐帧解码 + PIL 绘制 + 重编码。

为什么不用 ffmpeg subtitles 滤镜：
  homebrew ffmpeg (8.1.1) 未编译 libass/freetype，`subtitles` / `drawtext` 滤镜不可用。
  mov_text 软字幕虽然能封装，但很多播放器（含 QuickTime 默认）不显示 → "没有字幕"。
  因此本脚本用 PyAV + PIL 把字幕真正画进画面（burned-in）。

用法:
  python burn_subtitles.py --src 无音轨.mp4 --narration audio/narration.json
                           --timeline audio/timeline.json --out 带字幕.mp4
                           [--font-size 34] [--max-chars 26] [--bitrate 8000000]

字幕规范（经 caption-access-desk 质检验证，等级 A）:
- 每条 6–26 字，渲染 1 行（绝不整段堆砌，本次曾出现 83 字堆 6 行占屏 38%）
- 停留 0.83–7s（短句按字数占比分配显示时长，过短会闪烁）
- 相邻字幕留 ≥100ms 间隔（≥2 帧@60fps），避免切换生硬
- 字号约为画面高度的 4–5%（1080×720 用 34px）

踩坑提醒：
  写入帧务必 `nf.pts = None` 让编码器自动分配。复用源帧 pts 会因时间基不同
  导致输出帧率错乱（本次曾输出 0.234fps / duration 102651s）。
"""
import argparse
import json
import re
import sys
from fractions import Fraction
from pathlib import Path

import av
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"
DEFAULT_MIN_CHARS = 6


def split_clauses(text, max_chars=26, min_chars=DEFAULT_MIN_CHARS):
    """按标点断句，贪心合并，使每条落在 [min_chars, max_chars]"""
    parts = re.split(r'([，。；、：！？])', text)
    units = []
    for i in range(0, len(parts), 2):
        seg = parts[i]
        punct = parts[i + 1] if i + 1 < len(parts) else ""
        if seg or punct:
            units.append(seg + punct)
    clauses, cur = [], ""
    for u in units:
        if not cur:
            cur = u
        elif len(cur) < min_chars:
            cur += u
        elif len(cur) + len(u) <= max_chars:
            cur += u
        else:
            clauses.append(cur)
            cur = u
    if cur:
        clauses.append(cur)
    result = []
    for c in clauses:
        while len(c) > max_chars:
            result.append(c[:max_chars])
            c = c[max_chars:]
        if c:
            result.append(c)
    if len(result) > 1 and len(result[-1]) < min_chars:
        if len(result[-2]) + len(result[-1]) <= max_chars:
            result[-2] += result[-1]
            result.pop()
    return result


def build_subs(narration, timeline, max_chars, min_chars):
    subs = []
    for seg in timeline:
        n = next((x for x in narration if x["id"] == seg["id"]), None)
        if n is None:
            continue
        clauses = split_clauses(n["text"], max_chars, min_chars)
        total_chars = sum(len(c) for c in clauses) or 1
        seg_ms = seg["endMs"] - seg["startMs"]
        cursor = seg["startMs"]
        for c in clauses:
            dur_ms = int(seg_ms * len(c) / total_chars)
            subs.append({"text": c, "start": cursor,
                         "end": max(cursor + 200, cursor + dur_ms - 100)})
            cursor += dur_ms
    return subs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--narration", required=True)
    ap.add_argument("--timeline", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--font-size", type=int, default=34)
    ap.add_argument("--max-chars", type=int, default=26)
    ap.add_argument("--min-chars", type=int, default=DEFAULT_MIN_CHARS)
    ap.add_argument("--bitrate", type=int, default=8000000)
    ap.add_argument("--font", default=FONT_PATH)
    args = ap.parse_args()

    narration = json.loads(Path(args.narration).expanduser().read_text(encoding="utf-8"))["segments"]
    timeline = json.loads(Path(args.timeline).expanduser().read_text(encoding="utf-8"))["segments"]
    src, out = Path(args.src).expanduser(), Path(args.out).expanduser()

    subs = build_subs(narration, timeline, args.max_chars, args.min_chars)
    durs = [(s["end"] - s["start"]) / 1000 for s in subs]
    chars = [len(s["text"]) for s in subs]
    gaps = [(subs[i + 1]["start"] - subs[i]["end"]) / 1000 for i in range(len(subs) - 1)]

    print(f"字幕条数: {len(subs)}")
    print(f"字数 {min(chars)}-{max(chars)} | 停留 {min(durs):.1f}-{max(durs):.1f}s")
    bad_short = sum(1 for d in durs if d < 0.83)
    bad_long = sum(1 for d in durs if d > 7)
    bad_char = sum(1 for c in chars if c > args.max_chars)
    bad_gap = sum(1 for g in gaps if g < 0.083)
    print(f"自检不合格: 停留<0.83s {bad_short} | >7s {bad_long} | "
          f"超{args.max_chars}字 {bad_char} | 间隔<2帧 {bad_gap}")
    if bad_short or bad_long or bad_char:
        print("[warn] 存在不达标项，建议调整 --max-chars / --min-chars", file=sys.stderr)

    font = ImageFont.truetype(args.font, args.font_size)
    line_h = args.font_size + 10
    padding = 12
    bottom_margin = 70

    def render(img, text):
        base = img.convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        w, h = img.size
        max_w = int(w * 0.84)
        lines, cur = [], ""
        for ch in text:
            if d.textlength(cur + ch, font=font) > max_w:
                lines.append(cur)
                cur = ch
            else:
                cur += ch
        if cur:
            lines.append(cur)
        lines = lines[:2]
        total_h = len(lines) * line_h + padding * 2
        top = h - total_h - bottom_margin
        for i, line in enumerate(lines):
            lw = d.textlength(line, font=font)
            lx = (w - lw) / 2
            ly = top + padding + i * line_h
            d.rounded_rectangle([lx - 8, ly - 4, lx + lw + 8, ly + args.font_size + 6],
                                radius=8, fill=(0, 0, 0, 160))
            d.text((lx, ly), line, font=font, fill=(255, 255, 255, 255))
        return Image.alpha_composite(base, overlay).convert("RGB")

    container = av.open(str(src))
    stream = container.streams.video[0]
    w, h = stream.width, stream.height
    fps = float(stream.average_rate)
    print(f"视频: {w}x{h} @ {fps:.2f}fps")

    out_c = av.open(str(out), mode="w")
    out_stream = out_c.add_stream("h264", rate=Fraction(int(round(fps * 1000)), 1000))
    out_stream.width, out_stream.height = w, h
    out_stream.pix_fmt = "yuv420p"
    out_stream.bit_rate = args.bitrate

    fi = 0
    for frame in container.decode(stream):
        t_ms = frame.time * 1000
        cur_text = None
        for s in subs:
            if s["start"] <= t_ms <= s["end"]:
                cur_text = s["text"]
                break
        img = frame.to_image()
        if cur_text:
            img = render(img, cur_text)
        nf = av.VideoFrame.from_image(img)
        nf.pts = None  # 关键：让编码器自动分配，勿复用源 pts
        for packet in out_stream.encode(nf):
            out_c.mux(packet)
        fi += 1
        if fi % 5000 == 0:
            print(f"  已处理 {fi} 帧")

    for packet in out_stream.encode():
        out_c.mux(packet)
    out_c.close()
    print(f"完成: {out} ({out.stat().st_size/1024/1024:.1f}MB, {fi} 帧)")


if __name__ == "__main__":
    main()
