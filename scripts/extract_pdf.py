#!/usr/bin/env python3
"""Extract the complete text of a PDF while preserving page boundaries."""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


MIN_VALID_CHARS = 100
GLUED_SPACE_RATIO = 0.05
METADATA_FIELDS = {
    "title": ("/Title", "Title", "title"),
    "author": ("/Author", "Author", "author"),
    "subject": ("/Subject", "Subject", "subject"),
    "creator": ("/Creator", "Creator", "creator"),
    "producer": ("/Producer", "Producer", "producer"),
    "creation_date": ("/CreationDate", "CreationDate", "creation_date"),
}
PDFPLUMBER_ATTEMPTS: tuple[dict[str, float], ...] = (
    {"x_tolerance": 1, "y_tolerance": 3},
    {"x_tolerance": 2, "y_tolerance": 3},
    {"x_tolerance": 3, "y_tolerance": 3},
    {},
)


class ExtractionError(RuntimeError):
    """Raised when no installed extractor can read the PDF."""


def module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\x00", "").strip()


def latin_letter_count(text: str) -> int:
    return sum(ch.isascii() and ch.isalpha() for ch in text)


def space_count(text: str) -> int:
    return sum(ch.isspace() for ch in text)


def latin_space_ratio(text: str) -> float:
    letters = latin_letter_count(text)
    if letters == 0:
        return 0.0
    return space_count(text) / letters


def is_latin_heavy(text: str) -> bool:
    return latin_letter_count(text) >= 200


def spacing_score(text: str) -> float:
    """Prefer readable English spacing without rewarding huge layout gaps."""
    letters = latin_letter_count(text)
    if letters < 50:
        return float(len(text))
    ratio = latin_space_ratio(text)
    if ratio < GLUED_SPACE_RATIO:
        return ratio
    return min(ratio, 0.30) + min(len(text), 8000) / 200000.0


def spacing_quality(pages: list[str]) -> str:
    joined = "\n".join(pages)
    if not is_latin_heavy(joined):
        return "n/a"
    if latin_space_ratio(joined) < GLUED_SPACE_RATIO:
        return "latin-glued"
    return "ok"


def extract_page_text(page: Any) -> str:
    candidates: list[str] = []
    for kwargs in PDFPLUMBER_ATTEMPTS:
        try:
            raw = page.extract_text(**kwargs) if kwargs else page.extract_text()
        except TypeError:
            raw = page.extract_text()
        text = clean_text(raw or "")
        if text:
            candidates.append(text)
    if not candidates:
        return ""
    if any(is_latin_heavy(text) for text in candidates):
        return max(candidates, key=spacing_score)
    return max(candidates, key=len)


def normalize_metadata(raw_metadata: Any) -> dict[str, str]:
    if not raw_metadata:
        return {}

    normalized: dict[str, str] = {}
    for output_name, candidates in METADATA_FIELDS.items():
        for candidate in candidates:
            try:
                value = raw_metadata.get(candidate)
            except AttributeError:
                value = None
            if value:
                normalized[output_name] = re.sub(r"\s+", " ", clean_text(value))
                break
    return normalized


def extract_with_pdfplumber(pdf_path: Path) -> tuple[list[str], dict[str, str]]:
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            pages.append(extract_page_text(page))
        metadata = normalize_metadata(pdf.metadata)
    return pages, metadata


def extract_with_pypdf(pdf_path: Path) -> tuple[list[str], dict[str, str]]:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    if reader.is_encrypted:
        raise ExtractionError("The PDF is encrypted and no password was provided.")

    pages = [clean_text(page.extract_text() or "") for page in reader.pages]
    return pages, normalize_metadata(reader.metadata)


def extractor_order(requested: str, file_size_mb: float) -> list[str]:
    if requested != "auto":
        return [requested]
    if file_size_mb < 10:
        return ["pdfplumber", "pypdf"]
    return ["pypdf", "pdfplumber"]


def unavailable_message(extractor: str) -> str:
    return (
        f"{extractor} is not installed. Run "
        '"python -m pip install -r requirements.txt" from the skill directory.'
    )


def extract_pdf(
    pdf_path: Path, requested_extractor: str
) -> tuple[str, list[str], dict[str, str]]:
    file_size_mb = pdf_path.stat().st_size / 1024 / 1024
    failures: list[str] = []

    for extractor in extractor_order(requested_extractor, file_size_mb):
        module_name = "pdfplumber" if extractor == "pdfplumber" else "pypdf"
        if not module_available(module_name):
            failures.append(unavailable_message(extractor))
            continue

        try:
            if extractor == "pdfplumber":
                pages, metadata = extract_with_pdfplumber(pdf_path)
            else:
                pages, metadata = extract_with_pypdf(pdf_path)
        except Exception as exc:  # Extractor-specific failures are expected.
            failures.append(f"{extractor}: {exc}")
            continue

        extracted_chars = sum(len(page) for page in pages)
        if extracted_chars < MIN_VALID_CHARS:
            failures.append(
                f"{extractor}: only {extracted_chars} characters were extracted; "
                "the PDF may be scanned or image-only."
            )
            continue

        return extractor, pages, metadata

    details = "\n".join(f"- {failure}" for failure in failures)
    raise ExtractionError(
        "No PDF extractor produced usable text. The file may be encrypted, "
        f"scanned, or malformed.\n{details}"
    )


def safe_stem(pdf_path: Path) -> str:
    stem = pdf_path.stem
    for mark in ("'", "‘", "’", "‛", "`"):
        stem = stem.replace(mark, "")
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", stem)
    stem = re.sub(r"\s+", " ", stem).strip(" .")
    return stem[:160] or "paper"


def resolve_output_path(pdf_path: Path, output_arg: str | None) -> Path:
    if not output_arg:
        return pdf_path.with_name(f"{safe_stem(pdf_path)}.extracted.md")

    output_path = Path(output_arg).expanduser()
    if output_path.exists() and output_path.is_dir():
        return output_path / f"{safe_stem(pdf_path)}.extracted.md"
    if not output_path.suffix:
        return output_path / f"{safe_stem(pdf_path)}.extracted.md"
    return output_path


def render_markdown(
    pdf_path: Path,
    extractor: str,
    pages: list[str],
    metadata: dict[str, str],
) -> str:
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    quality = spacing_quality(pages)
    lines = [
        "# PDF 提取文本",
        "",
        f"- 来源文件：`{pdf_path.resolve()}`",
        f"- 页数：{len(pages)}",
        f"- 提取器：`{extractor}`",
        f"- 提取时间：`{generated_at}`",
        f"- 空格质量：`{quality}`",
    ]

    if metadata:
        lines.extend(["", "## PDF 元数据提示", ""])
        for key, value in metadata.items():
            lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "> 以下内容是 PDF 的完整可提取文本，仅保留页码边界；"
            "论文发布日期、期刊、作者单位等信息需结合正文核对。",
            "",
            "---",
            "",
        ]
    )

    for page_number, page_text in enumerate(pages, start=1):
        lines.extend(
            [
                f"## Page {page_number}",
                "",
                page_text or "[本页未提取到文字]",
                "",
                "---",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract complete PDF text with page boundaries for DeepRead."
    )
    parser.add_argument("pdf_path", help="Path to the source PDF.")
    parser.add_argument(
        "-o",
        "--output",
        help=(
            "Output Markdown file or directory. Defaults to "
            "<pdf-name>.extracted.md beside the PDF."
        ),
    )
    parser.add_argument(
        "--extractor",
        choices=("auto", "pdfplumber", "pypdf"),
        default="auto",
        help="PDF extractor to use. Defaults to automatic selection.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pdf_path = Path(args.pdf_path).expanduser()

    if not pdf_path.is_file():
        print(f"PDF not found: {pdf_path}", file=sys.stderr)
        return 2
    if pdf_path.suffix.lower() != ".pdf":
        print(f"Not a PDF file: {pdf_path}", file=sys.stderr)
        return 2

    try:
        extractor, pages, metadata = extract_pdf(pdf_path, args.extractor)
    except ExtractionError as exc:
        print(str(exc), file=sys.stderr)
        return 4

    output_path = resolve_output_path(pdf_path, args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_markdown(pdf_path, extractor, pages, metadata),
        encoding="utf-8",
    )

    quality = spacing_quality(pages)
    if quality == "latin-glued":
        print(
            f"[DeepRead_PDF_SPACING_WARN] {output_path.resolve()}",
            file=sys.stderr,
        )
    print(f"[DeepRead_PDF_READY] {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())