#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多音字消歧：扫描旁白稿中的歧义多音字，按替换表改为无歧义写法。

背景（重要）：
  edge-tts **不支持 SSML 注音**——实测 `<phoneme alphabet="sapi" ph="...">` 会被当作
  普通文本朗读（同一句 1.44s → 4.25s）。因此唯一可靠的修音方式是**在文本层消除歧义**。

用法:
  python polyphone_fix.py <narration.json> [--apply] [--report]
默认只扫描并打印风险；加 --apply 才写回文件。

替换表位于文件顶部 REPLACEMENTS，可按项目扩展。
"""
import argparse
import json
import sys
from pathlib import Path

# ---- 替换表: (原文, 改写) ----
# 原则：保持原意，替换为「单音字或语境唯一」的写法
REPLACEMENTS = [
    # 长 zhǎng/cháng —— TTS 最常读错的一组
    ("高速增长时期", "高速发展时期"),
    ("零增长", "零增速"),
    ("负增长", "负增速"),
    ("增长", "增速"),
    ("长辈", "上一辈"),
    ("长达", "足有"),
    ("长期", "持续"),
    ("成长", "扩张"),
    ("漫长", "长久"),
    # 弹 tán/dàn
    ("高弹性", "高波动"),
    ("弹性", "波动"),
    # 为 wéi/wèi
    ("顺势而为", "顺势调整"),
    # 给 gěi/jǐ
    ("供给", "供应"),
    ("给予", "提供"),
    # 率 lǜ/shuài
    ("率先", "抢先"),
    ("率领", "带领"),
    # 参 cān/shēn/cēn
    ("参照", "参考"),
    # 重 zhòng/chóng
    ("重估", "重新评估"),
]

# ---- 扫描词表：仅列「默认读音易错」的词 ----
# 说明：还有(hái)、都是(dōu)、应该(yīng)、银行(háng)、处理(chǔ)、
# 了解(liǎo)、到处(chù) 等 TTS 默认读音正确，不列入以免噪音。
WATCH_WORDS = [
    "增长", "长辈", "长达", "长期", "成长", "漫长", "弹性",
    "供给", "给予", "率先", "率领", "参照", "重估", "顺势而为",
    "少子化", "重创", "调降", "处决", "行业", "参与", "人参",
]


def scan(segments):
    risks = []
    for s in segments:
        hits = [w for w in WATCH_WORDS if w in s["text"]]
        if hits:
            risks.append({"id": s["id"], "words": hits, "text": s["text"]})
    return risks


def apply_fix(segments):
    changes = []
    for s in segments:
        orig = s["text"]
        for a, b in REPLACEMENTS:
            if a in s["text"] and a != b:
                s["text"] = s["text"].replace(a, b)
                changes.append({"id": s["id"], "from": a, "to": b})
    return changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("narration")
    ap.add_argument("--apply", action="store_true", help="写回文件（默认只扫描）")
    args = ap.parse_args()

    p = Path(args.narration).expanduser()
    data = json.loads(p.read_text(encoding="utf-8"))
    segs = data["segments"]

    risks = scan(segs)
    print(f"=== 多音字风险扫描: {len(segs)} 段, 命中 {len(risks)} 段 ===")
    for r in risks:
        print(f"  cue{r['id']:02d} {r['words']}: {r['text'][:50]}")

    if args.apply:
        changes = apply_fix(segs)
        data["meta"]["polyphone_fixed"] = len(changes)
        data["meta"]["total_chars_actual"] = sum(len(s["text"]) for s in segs)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n=== 已替换 {len(changes)} 处 ===")
        for c in changes:
            print(f"  cue{c['id']:02d}: {c['from']} -> {c['to']}")
        remain = scan(segs)
        print(f"\n剩余风险段: {len(remain)}")
        for r in remain:
            print(f"  cue{r['id']:02d} {r['words']}")
        print(f"总字数: {data['meta']['total_chars_actual']}")
    else:
        print("\n(只读扫描，加 --apply 执行替换)")


if __name__ == "__main__":
    main()
