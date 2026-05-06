#!/usr/bin/env python
"""Extract text and table candidates from official university budget PDFs.

This script is intentionally offline: pass a local PDF that was already
downloaded from an official page or index. It keeps source metadata beside the
raw extraction so later cleaning can preserve budget/final-account口径.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from urllib.parse import urlparse


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CSV = PROJECT_DIR / "data" / "raw" / "official_sources.csv"
DEFAULT_OUT_DIR = PROJECT_DIR / "data" / "interim" / "official_pdf_text"
DEFAULT_TABLES_DIR = PROJECT_DIR / "data" / "interim" / "official_budget_tables"

KEYWORDS = [
    "收支预算总表",
    "收入预算表",
    "支出预算表",
    "财政拨款",
    "收入总计",
    "本年收入",
    "事业收入",
    "其他收入",
    "上年结转",
    "支出合计",
    "结转下年",
    "部门预算",
    "部门决算",
    "决算",
    "预算",
]

META_FIELDS = [
    "source_pdf",
    "source_url",
    "university",
    "year",
    "document_type",
    "title",
    "source_site",
    "source_level",
    "unit_hint",
    "extraction_method",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract full text and raw table candidates from a local official budget PDF."
    )
    parser.add_argument("pdf", type=Path, help="Local PDF path. HTTP URLs are metadata only; download separately.")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, type=Path, help="Text output directory.")
    parser.add_argument("--tables-dir", default=DEFAULT_TABLES_DIR, type=Path, help="Table/line candidate output directory.")
    parser.add_argument("--source-csv", default=DEFAULT_SOURCE_CSV, type=Path, help="official_sources.csv path.")
    parser.add_argument("--source-url", default="", help="Official page or PDF URL used to match source metadata.")
    parser.add_argument("--university", default="", help="Override or help match the university name.")
    parser.add_argument("--year", default="", help="Override or help match the document year.")
    parser.add_argument("--document-type", default="", help="Override or help match budget/final_account/etc.")
    parser.add_argument("--prefix", default="", help="Output filename prefix. Defaults to PDF stem.")
    return parser.parse_args()


def require_local_pdf(path: Path) -> Path:
    raw = str(path)
    if urlparse(raw).scheme in {"http", "https"}:
        raise SystemExit(
            "This script does not download PDFs. Download the URL first, then pass the local PDF path "
            "and keep the original URL in --source-url."
        )
    pdf = path.expanduser().resolve()
    if not pdf.exists():
        raise SystemExit(f"PDF not found: {pdf}")
    if pdf.suffix.lower() != ".pdf":
        raise SystemExit(f"Expected a .pdf file: {pdf}")
    return pdf


def load_source_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def is_match(row: dict[str, str], *, source_url: str, university: str, year: str, document_type: str) -> bool:
    if source_url and row.get("url") == source_url:
        return True
    checks = []
    if university:
        checks.append(row.get("university") == university)
    if year:
        checks.append(row.get("year") == year)
    if document_type:
        checks.append(row.get("document_type") == document_type)
    return bool(checks) and all(checks)


def build_metadata(args: argparse.Namespace, pdf: Path) -> dict[str, str]:
    rows = load_source_rows(args.source_csv)
    matched = None
    for row in rows:
        if is_match(
            row,
            source_url=args.source_url,
            university=args.university,
            year=str(args.year),
            document_type=args.document_type,
        ):
            matched = row
            break

    meta = {
        "source_pdf": str(pdf),
        "source_url": args.source_url,
        "university": args.university,
        "year": str(args.year),
        "document_type": args.document_type,
        "title": "",
        "source_site": "",
        "source_level": "",
        "unit_hint": "",
        "extraction_method": "pymupdf",
    }
    if matched:
        meta.update(
            {
                "source_url": args.source_url or matched.get("url", ""),
                "university": args.university or matched.get("university", ""),
                "year": str(args.year) or matched.get("year", ""),
                "document_type": args.document_type or matched.get("document_type", ""),
                "title": matched.get("title", ""),
                "source_site": matched.get("source_site", ""),
                "source_level": matched.get("source_level", ""),
            }
        )
    return meta


def clean_cell(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def detect_unit(text: str) -> str:
    if "单位：万元" in text or "单位:万元" in text:
        return "万元"
    if "单位：亿元" in text or "单位:亿元" in text:
        return "亿元"
    if "万元" in text:
        return "万元"
    if "亿元" in text:
        return "亿元"
    return ""


def number_candidates(text: str) -> str:
    values = re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?%?", text)
    return "|".join(values)


def extract_pdf(pdf: Path) -> tuple[list[dict[str, object]], list[dict[str, str]], str]:
    try:
        import fitz
    except ImportError as exc:
        raise SystemExit(
            "PyMuPDF is not importable. Activate dev env first:\n"
            "source /Users/adam/.venvs/dev/.venv/bin/activate"
        ) from exc

    text_pages: list[str] = []
    table_rows: list[dict[str, object]] = []
    line_candidates: list[dict[str, str]] = []

    with fitz.open(pdf) as doc:
        for page_index, page in enumerate(doc, start=1):
            page_text = page.get_text("text")
            text_pages.append(f"\n\n===== page {page_index} =====\n{page_text}")
            unit_hint = detect_unit(page_text)

            for line_no, line in enumerate(page_text.splitlines(), start=1):
                line = re.sub(r"\s+", " ", line).strip()
                if not line:
                    continue
                if any(keyword in line for keyword in KEYWORDS) or number_candidates(line):
                    line_candidates.append(
                        {
                            "page": str(page_index),
                            "line_no": str(line_no),
                            "unit_hint": unit_hint,
                            "raw_text": line,
                            "number_candidates": number_candidates(line),
                            "keyword_hits": "|".join(k for k in KEYWORDS if k in line),
                        }
                    )

            if not hasattr(page, "find_tables"):
                continue
            tables = page.find_tables()
            for table_index, table in enumerate(tables.tables, start=1):
                for row_index, row in enumerate(table.extract(), start=1):
                    cells = [clean_cell(cell) for cell in row]
                    table_rows.append(
                        {
                            "page": page_index,
                            "table_index": table_index,
                            "row_index": row_index,
                            "unit_hint": unit_hint,
                            "cells": cells,
                        }
                    )

    return table_rows, line_candidates, "".join(text_pages).lstrip()


def write_table_candidates(path: Path, rows: list[dict[str, object]], meta: dict[str, str]) -> None:
    max_cols = max((len(row["cells"]) for row in rows), default=0)
    fieldnames = META_FIELDS + ["page", "table_index", "row_index"] + [f"col_{i:02d}" for i in range(max_cols)]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            cells = row["cells"]
            out = {field: meta.get(field, "") for field in META_FIELDS}
            out["unit_hint"] = row.get("unit_hint") or meta.get("unit_hint", "")
            out.update(
                {
                    "page": row["page"],
                    "table_index": row["table_index"],
                    "row_index": row["row_index"],
                }
            )
            out.update({f"col_{i:02d}": cells[i] if i < len(cells) else "" for i in range(max_cols)})
            writer.writerow(out)


def write_line_candidates(path: Path, rows: list[dict[str, str]], meta: dict[str, str]) -> None:
    fieldnames = META_FIELDS + ["page", "line_no", "raw_text", "number_candidates", "keyword_hits"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = {field: meta.get(field, "") for field in META_FIELDS}
            out["unit_hint"] = row.get("unit_hint") or meta.get("unit_hint", "")
            out.update(row)
            writer.writerow(out)


def main() -> None:
    args = parse_args()
    pdf = require_local_pdf(args.pdf)
    out_dir = args.out_dir.resolve()
    tables_dir = args.tables_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    prefix = args.prefix or pdf.stem
    meta = build_metadata(args, pdf)
    table_rows, line_candidates, text = extract_pdf(pdf)

    text_path = out_dir / f"{prefix}.txt"
    tables_path = tables_dir / f"{prefix}_tables.csv"
    lines_path = tables_dir / f"{prefix}_line_candidates.csv"

    text_path.write_text(text, encoding="utf-8")
    write_table_candidates(tables_path, table_rows, meta)
    write_line_candidates(lines_path, line_candidates, meta)

    print(f"text: {text_path}")
    print(f"tables: {tables_path} ({len(table_rows)} rows)")
    print(f"line_candidates: {lines_path} ({len(line_candidates)} rows)")


if __name__ == "__main__":
    main()
