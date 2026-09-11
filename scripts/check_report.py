#!/usr/bin/env python3
"""Validate a DeepRead report without printing the body to the terminal."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# ASCII labels only. Do not print Chinese to the terminal.
REQUIRED_CHECKS = [
    ("title", "# 论文阅读"),
    ("metadata", "## 论文基本信息"),
    ("english_title", "- **英文原名**："),
    ("stage1", "# 阶段一：关键章节翻译"),
    ("abstract", "## Abstract"),
    ("introduction", "## Introduction"),
    ("conclusion", "## Conclusion / Summary"),
    ("stage2", "# 阶段二：逐 RQ 讲解"),
    ("rq_list", "## RQ 列表"),
    ("method", "### 原文方法"),
    ("results", "### 原文实验 / 结果"),
    ("ai_summary", "### AI 总结"),
    ("stage3", "# 阶段三：翻译并总结 related work"),
    ("stage4", "# 阶段四：吸收总结"),
    ("q1", "## 问题 1："),
    ("q2", "## 问题 2："),
    ("q3", "## 问题 3："),
]


def safe_paper_name(title: str) -> str:
    title = title.replace("\u2018", "").replace("\u2019", "").replace("\u201b", "")
    title = title.replace("'", "").replace("`", "")
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title)
    title = re.sub(r"\s+", " ", title).strip(" .")
    return title[:120] or "paper"


def check_report(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"MISSING file {path}", file=sys.stderr)
        print("[DeepRead_REPORT_INCOMPLETE]")
        return 3
    except UnicodeDecodeError:
        print("MISSING utf-8 decoding failed", file=sys.stderr)
        print("[DeepRead_REPORT_INCOMPLETE]")
        return 4

    missing = 0
    for label, needle in REQUIRED_CHECKS:
        if needle in text:
            print(f"OK {label}")
        else:
            print(f"MISSING {label}")
            missing += 1

    if missing:
        print("[DeepRead_REPORT_INCOMPLETE]")
        return 1
    print("[DeepRead_REPORT_READY]")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check DeepRead report headings with ASCII-only status lines."
    )
    parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to outputs/<name>_DeepRead.md",
    )
    parser.add_argument(
        "--suggest-name",
        help="Print a filesystem-safe paper name and exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.suggest_name:
        print(safe_paper_name(args.suggest_name))
        return 0
    if not args.report_path:
        print("Report path required unless --suggest-name is used.", file=sys.stderr)
        return 2
    return check_report(Path(args.report_path).expanduser())


if __name__ == "__main__":
    raise SystemExit(main())