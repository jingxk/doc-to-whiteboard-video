#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档 → 纯文本。支持 pdf / docx / md / txt。
用法:
  python extract_doc.py <输入文件> [-o 输出.txt]
无 -o 时输出到 stdout。
注意: PDF 提取常出现「单字换行」，脚本已自动按中文习惯重组段落。
"""
import argparse
import re
import sys
from pathlib import Path


def from_pdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    parts = [(p.extract_text() or "") for p in reader.pages]
    return "\n".join(parts)


def from_docx(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


SENT_END = "。！？；…"
PUNCT_START = "，。；、：！？）」』”》"


def clean(text: str) -> str:
    """清理单字/硬换行，按中文习惯重组段落。

    PDF 提取常把每个字或标点单独成行，需要按两条规则合并：
    1. 上一行未以句末标点结尾 → 必然是被硬断开，合并
    2. 本行以标点开头（孤立的标点行）→ 合并到上一行
    例外：编号行（"1." "一、"）保持独立，避免标题与正文粘连。
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    merged = []
    for ln in lines:
        if not ln:
            merged.append("")
            continue
        if merged and merged[-1]:
            prev = merged[-1]
            is_numbering = bool(re.match(r"^([0-9]+[.、]|[一二三四五六七八九十]+[、.])", ln))
            if not is_numbering:
                if not prev.endswith(tuple(SENT_END)):
                    merged[-1] += ln
                    continue
                if ln[0] in PUNCT_START:
                    merged[-1] += ln
                    continue
        merged.append(ln)
    out = "\n".join(merged)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--output", default=None)
    args = ap.parse_args()

    src = Path(args.input).expanduser()
    if not src.exists():
        print(f"[err] 文件不存在: {src}", file=sys.stderr)
        sys.exit(1)

    ext = src.suffix.lower()
    if ext == ".pdf":
        raw = from_pdf(src)
    elif ext in (".docx", ".doc"):
        raw = from_docx(src)
    else:
        raw = src.read_text(encoding="utf-8", errors="ignore")

    text = clean(raw)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"已写出 {args.output} ({len(text)} 字)", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
