#!/usr/bin/env python
"""Process all registered official PDFs into text, table, and fact candidates."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote, urlparse

from official_pdf_extract import (
    DEFAULT_OUT_DIR,
    DEFAULT_SOURCE_CSV,
    DEFAULT_TABLES_DIR,
    build_metadata,
    extract_pdf,
    write_line_candidates,
    write_table_candidates,
)
from official_tables_to_fact import OUTPUT_FIELDS, convert


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PDF_DIR = PROJECT_DIR / "data" / "raw" / "official" / "pdfs"
DEFAULT_REPORT_DIR = PROJECT_DIR / "data" / "interim" / "official_budget_tables"

INVENTORY_FIELDS = [
    "pdf_id",
    "institution_name",
    "year",
    "document_type",
    "title",
    "source_url",
    "source_site",
    "source_level",
    "local_pdf",
    "text_path",
    "tables_path",
    "lines_path",
    "facts_path",
    "table_rows",
    "line_candidate_rows",
    "fact_rows",
    "status",
    "notes",
]

FIELD_CATALOG_FIELDS = [
    "pdf_id",
    "institution_name",
    "year",
    "document_type",
    "metric_code",
    "metric_name",
    "unit_original",
    "amount_yi_yuan",
    "source_url",
    "source_pdf",
    "verified",
    "notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process all local official PDFs registered in official_sources.csv.")
    parser.add_argument("--source-csv", type=Path, default=DEFAULT_SOURCE_CSV)
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    parser.add_argument("--text-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--tables-dir", type=Path, default=DEFAULT_TABLES_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    return parser.parse_args()


def read_sources(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pdf_url_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if row.get("url", "").lower().split("?")[0].endswith(".pdf")]


def safe_part(value: str) -> str:
    text = re.sub(r"\s+", "_", str(value or "").strip())
    text = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", text)
    return text.strip("_") or "unknown"


def pdf_id_from_row(row: dict[str, str], fallback_pdf: Path | None = None) -> str:
    parts = [
        safe_part(row.get("university") or "unknown"),
        safe_part(row.get("year") or "unknown_year"),
        safe_part(row.get("document_type") or "document"),
    ]
    if fallback_pdf is not None:
        parts.append(safe_part(fallback_pdf.stem))
    return "_".join(parts)


def basename_from_url(url: str) -> str:
    path = unquote(urlparse(url).path)
    return Path(path).name


def find_local_pdf(row: dict[str, str], pdfs: list[Path], used: set[Path]) -> Path | None:
    url_basename = basename_from_url(row.get("url", ""))
    for pdf in pdfs:
        if pdf.name == url_basename:
            used.add(pdf)
            return pdf

    year = str(row.get("year", "")).split(".")[0]
    doc_type = str(row.get("document_type", ""))
    scored: list[tuple[int, Path]] = []
    for pdf in pdfs:
        if pdf in used:
            continue
        score = 0
        stem = pdf.stem.lower()
        if year and year in stem:
            score += 2
        if doc_type and doc_type.lower() in stem:
            score += 1
        if row.get("university") == "北京理工大学" and "bit" in stem:
            score += 3
        if score:
            scored.append((score, pdf))
    if scored:
        scored.sort(reverse=True)
        used.add(scored[0][1])
        return scored[0][1]
    return None


def row_to_namespace(row: dict[str, str], pdf: Path, source_csv: Path) -> SimpleNamespace:
    year = str(row.get("year", "")).split(".")[0]
    return SimpleNamespace(
        pdf=pdf,
        out_dir=DEFAULT_OUT_DIR,
        tables_dir=DEFAULT_TABLES_DIR,
        source_csv=source_csv,
        source_url=row.get("url", ""),
        university=row.get("university", ""),
        year=year,
        document_type=row.get("document_type", ""),
        prefix="",
    )


def process_one(row: dict[str, str], pdf: Path, args: argparse.Namespace) -> dict[str, str]:
    pdf_id = pdf_id_from_row(row, pdf)
    meta_args = row_to_namespace(row, pdf, args.source_csv)
    meta = build_metadata(meta_args, pdf)
    table_rows, line_candidates, text = extract_pdf(pdf)

    text_path = args.text_dir / f"{pdf_id}.txt"
    tables_path = args.tables_dir / f"{pdf_id}_tables.csv"
    lines_path = args.tables_dir / f"{pdf_id}_line_candidates.csv"
    facts_path = args.tables_dir / f"{pdf_id}_facts.csv"

    text_path.write_text(text, encoding="utf-8")
    write_table_candidates(tables_path, table_rows, meta)
    write_line_candidates(lines_path, line_candidates, meta)

    fact_rows = convert(tables_path)
    with facts_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(fact_rows)

    return {
        "pdf_id": pdf_id,
        "institution_name": meta.get("university", ""),
        "year": meta.get("year", ""),
        "document_type": meta.get("document_type", ""),
        "title": meta.get("title", ""),
        "source_url": meta.get("source_url", ""),
        "source_site": meta.get("source_site", ""),
        "source_level": meta.get("source_level", ""),
        "local_pdf": str(pdf),
        "text_path": str(text_path),
        "tables_path": str(tables_path),
        "lines_path": str(lines_path),
        "facts_path": str(facts_path),
        "table_rows": str(len(table_rows)),
        "line_candidate_rows": str(len(line_candidates)),
        "fact_rows": str(len(fact_rows)),
        "status": "processed",
        "notes": "auto processed; facts require manual metric/table review before processed use",
    }


def write_inventory(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=INVENTORY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_combined_facts(path: Path, fact_paths: list[Path]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for fact_path in fact_paths:
            with fact_path.open(newline="", encoding="utf-8") as f_in:
                reader = csv.DictReader(f_in)
                writer.writerows(reader)


def write_field_catalog(path: Path, fact_paths: list[Path]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=FIELD_CATALOG_FIELDS)
        writer.writeheader()
        for fact_path in fact_paths:
            pdf_id = fact_path.stem.removesuffix("_facts")
            with fact_path.open(newline="", encoding="utf-8") as f_in:
                for row in csv.DictReader(f_in):
                    writer.writerow(
                        {
                            "pdf_id": pdf_id,
                            "institution_name": row.get("institution_name", ""),
                            "year": row.get("year", ""),
                            "document_type": row.get("document_type", ""),
                            "metric_code": row.get("metric_code", ""),
                            "metric_name": row.get("metric_name", ""),
                            "unit_original": row.get("unit_original", ""),
                            "amount_yi_yuan": row.get("amount_yi_yuan", ""),
                            "source_url": row.get("source_url", ""),
                            "source_pdf": row.get("source_pdf", ""),
                            "verified": row.get("verified", ""),
                            "notes": row.get("notes", ""),
                        }
                    )


def main() -> None:
    args = parse_args()
    args.text_dir.mkdir(parents=True, exist_ok=True)
    args.tables_dir.mkdir(parents=True, exist_ok=True)
    args.report_dir.mkdir(parents=True, exist_ok=True)

    sources = read_sources(args.source_csv)
    pdfs = sorted(args.pdf_dir.glob("*.pdf"))
    used: set[Path] = set()
    inventory_rows: list[dict[str, str]] = []

    for row in pdf_url_rows(sources):
        pdf = find_local_pdf(row, pdfs, used)
        if pdf is None:
            inventory_rows.append(
                {
                    "pdf_id": pdf_id_from_row(row),
                    "institution_name": row.get("university", ""),
                    "year": str(row.get("year", "")).split(".")[0],
                    "document_type": row.get("document_type", ""),
                    "title": row.get("title", ""),
                    "source_url": row.get("url", ""),
                    "source_site": row.get("source_site", ""),
                    "source_level": row.get("source_level", ""),
                    "local_pdf": "",
                    "text_path": "",
                    "tables_path": "",
                    "lines_path": "",
                    "facts_path": "",
                    "table_rows": "0",
                    "line_candidate_rows": "0",
                    "fact_rows": "0",
                    "status": "missing_local_pdf",
                    "notes": "registered PDF URL has not been downloaded yet",
                }
            )
            continue
        inventory_rows.append(process_one(row, pdf, args))

    for pdf in pdfs:
        if pdf in used:
            continue
        row = {
            "university": "",
            "year": "",
            "document_type": "",
            "title": "",
            "url": "",
            "source_site": "",
            "source_level": "local_pdf_unregistered",
        }
        inventory_rows.append(process_one(row, pdf, args))

    fact_paths = [Path(row["facts_path"]) for row in inventory_rows if row.get("facts_path")]
    inventory_path = args.report_dir / "official_pdf_processing_inventory.csv"
    combined_facts_path = args.report_dir / "official_finance_fact_candidates.csv"
    field_catalog_path = args.report_dir / "official_pdf_field_catalog.csv"

    write_inventory(inventory_path, inventory_rows)
    write_combined_facts(combined_facts_path, fact_paths)
    write_field_catalog(field_catalog_path, fact_paths)

    print(f"inventory: {inventory_path} ({len(inventory_rows)} PDFs)")
    print(f"combined_facts: {combined_facts_path}")
    print(f"field_catalog: {field_catalog_path}")


if __name__ == "__main__":
    main()
