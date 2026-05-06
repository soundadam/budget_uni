#!/usr/bin/env python
"""Normalize downloaded official PDF metadata using extracted PDF text."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CSV = PROJECT_DIR / "data" / "raw" / "official_sources.csv"
DEFAULT_INVENTORY = PROJECT_DIR / "data" / "interim" / "official_budget_tables" / "official_pdf_processing_inventory.csv"

SOURCE_FIELDS = [
    "university",
    "year",
    "document_type",
    "title",
    "url",
    "source_site",
    "source_level",
    "discovered_at",
    "notes",
]

FINANCE_DOC_TYPES = {
    "budget",
    "final_account",
    "ministry_budget",
    "ministry_final_account",
    "institute_budget",
    "institute_final_account",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize official PDF rows from extracted text.")
    parser.add_argument("--source-csv", type=Path, default=DEFAULT_SOURCE_CSV)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_sources(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SOURCE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def local_filename_from_notes(notes: str) -> str:
    match = re.search(r"本地文件\s*([A-Za-z0-9_.-]+\.pdf)", notes or "")
    return match.group(1) if match else ""


def compact_text(path: str) -> str:
    if not path:
        return ""
    text_path = Path(path)
    if not text_path.exists():
        return ""
    text = text_path.read_text(encoding="utf-8", errors="ignore")
    return re.sub(r"\s+", "", text)


def infer_year(text: str, row: dict[str, str]) -> str:
    for pattern in (r"(20\d{2})年度?部门预算", r"(20\d{2})年部门预算", r"(20\d{2})年度?部门决算", r"(20\d{2})年部门决算"):
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    match = re.search(r"(20\d{2})", f"{row.get('title', '')} {row.get('url', '')}")
    return match.group(1) if match else str(row.get("year", "")).split(".")[0]


def infer_doc_type(text: str, row: dict[str, str]) -> str:
    university = row.get("university", "")
    base_type = row.get("document_type", "")
    if "部门决算" in text:
        if university == "教育部":
            return "ministry_final_account"
        if university.startswith("中国科学院") and university != "中国科学院":
            return "institute_final_account"
        return "final_account"
    if "部门预算" in text or "预算公开" in text:
        if university == "教育部" or university == "中国科学院":
            return "ministry_budget"
        if university.startswith("中国科学院") and university != "中国科学院":
            return "institute_budget"
        return "budget"
    return base_type


def normalized_title(row: dict[str, str], year: str, doc_type: str) -> str:
    university = row.get("university", "")
    if doc_type.endswith("final_account"):
        return f"{university}{year}年度部门决算" if year else row.get("title", "")
    if doc_type.endswith("budget") or doc_type == "budget":
        return f"{university}{year}年度部门预算" if year else row.get("title", "")
    return row.get("title", "")


def append_note(notes: str, extra: str) -> str:
    if extra in notes:
        return notes
    return f"{notes}；{extra}" if notes else extra


def main() -> None:
    args = parse_args()
    rows = read_csv(args.source_csv)
    inventory = read_csv(args.inventory) if args.inventory.exists() else []
    by_filename: dict[str, dict[str, str]] = {}
    for item in inventory:
        local_pdf = Path(item.get("local_pdf", "")).name
        if local_pdf:
            by_filename[local_pdf] = item

    kept_rows: list[dict[str, str]] = []
    removed = 0
    normalized = 0

    for row in rows:
        if row.get("source_level") != "official_pdf":
            kept_rows.append(row)
            continue

        filename = local_filename_from_notes(row.get("notes", ""))
        inventory_row = by_filename.get(filename, {})
        text = compact_text(inventory_row.get("text_path", ""))
        old_doc_type = row.get("document_type", "")
        new_doc_type = infer_doc_type(text, row)
        new_year = infer_year(text, row)

        if old_doc_type == "finance_document" and new_doc_type == "finance_document":
            removed += 1
            continue

        if new_doc_type != old_doc_type or new_year != str(row.get("year", "")).split(".")[0]:
            row["document_type"] = new_doc_type
            row["year"] = new_year
            row["title"] = normalized_title(row, new_year, new_doc_type)
            row["notes"] = append_note(row.get("notes", ""), "已根据PDF文本规范化年份和预算/决算口径")
            normalized += 1

        if row.get("document_type") not in FINANCE_DOC_TYPES:
            removed += 1
            continue
        kept_rows.append(row)

    write_sources(args.source_csv, kept_rows)
    print(f"normalized official PDF rows: {normalized}")
    print(f"removed non-finance PDF rows: {removed}")
    print(f"remaining rows: {len(kept_rows)}")


if __name__ == "__main__":
    main()
