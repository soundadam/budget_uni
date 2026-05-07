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
    KEYWORDS,
    build_metadata,
    extract_pdf,
    number_candidates,
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

LINE_METRIC_PATTERNS = [
    ("budget_total", "收支总预算", r"收支总预算\s*([0-9,]+(?:\.\d+)?)\s*万元"),
    ("current_year_income_total", "本年收入合计", r"本年收入合计\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("current_year_income_total", "本年收入", r"本年收入\s*([0-9,]+(?:\.\d+)?)\s*万元"),
    ("non_fiscal_surplus_used", "使用非财政拨款结余", r"使用非财政[拨拔]款结余\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("carryover_from_previous_year", "上年结转", r"上年结转\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("current_year_expense_total", "本年支出合计", r"本年支出合计\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("current_year_expense_total", "本年支出", r"本年支出(?:预算)?\s*([0-9,]+(?:\.\d+)?)\s*万元"),
    ("carryover_to_next_year", "结转下年", r"结转下年\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("income_total", "收入总计", r"收入总计\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("expense_total", "支出总计", r"支出总计\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    (
        "general_public_budget_appropriation_income",
        "一般公共预算拨款收入",
        r"一般公共预算[拨拔]款收入\s*([0-9,]+(?:\.\d+)?)(?:万元)?",
    ),
    (
        "government_fund_budget_appropriation_income",
        "政府性基金预算拨款收入",
        r"政府性基金预算[拨拔]款收入\s*([0-9,]+(?:\.\d+)?)(?:万元)?",
    ),
    ("undertaking_income", "事业收入", r"事业收入\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("other_income", "其他收入", r"其他收入\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    (
        "current_year_fiscal_appropriation_expense",
        "本年财政拨款支出",
        r"本年财政拨款支出\s*([0-9,]+(?:\.\d+)?)\s*万元",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process all local official PDFs registered in official_sources.csv.")
    parser.add_argument("--source-csv", type=Path, default=DEFAULT_SOURCE_CSV)
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    parser.add_argument("--text-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--tables-dir", type=Path, default=DEFAULT_TABLES_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--ocr-empty-pdfs", action="store_true", help="Run PaddleOCR when PyMuPDF finds no text/tables.")
    parser.add_argument(
        "--include-unregistered-pdfs",
        action="store_true",
        help="Also process local PDFs that are not registered as official finance PDFs in the source CSV.",
    )
    parser.add_argument(
        "--reuse-existing-outputs",
        action="store_true",
        help="Reuse existing per-PDF text/table/fact CSVs when a non-empty facts file already exists.",
    )
    parser.add_argument("--only-university", action="append", default=[], help="Process only rows for this university. Repeatable.")
    parser.add_argument("--only-document-type", action="append", default=[], help="Process only rows for this document type. Repeatable.")
    parser.add_argument("--only-year", action="append", default=[], help="Process only rows for this year. Repeatable.")
    return parser.parse_args()


def read_sources(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pdf_url_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    finance_doc_types = {
        "budget",
        "final_account",
        "ministry_budget",
        "ministry_final_account",
        "institute_budget",
        "institute_final_account",
    }
    return [
        row
        for row in rows
        if row.get("source_level") == "official_pdf"
        and row.get("document_type") in finance_doc_types
        and row.get("url", "").lower().split("?")[0].endswith(".pdf")
    ]


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


def local_filename_from_notes(notes: str) -> str:
    match = re.search(r"本地文件\s*([A-Za-z0-9_.\-/\u4e00-\u9fff]+\.pdf)", notes or "")
    return match.group(1) if match else ""


def find_local_pdf(row: dict[str, str], pdfs: list[Path], used: set[Path]) -> Path | None:
    noted_filename = local_filename_from_notes(row.get("notes", ""))
    if noted_filename:
        noted_path = Path(noted_filename)
        for pdf in pdfs:
            try:
                relative_pdf = pdf.relative_to(DEFAULT_PDF_DIR)
            except ValueError:
                relative_pdf = pdf
            if pdf.name == noted_filename or relative_pdf == noted_path:
                used.add(pdf)
                return pdf

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


def amount_text_to_yi_yuan(value: str) -> str:
    amount = float(value.replace(",", ""))
    return f"{amount / 10000:.6f}"


def compact_pdf_text(text: str) -> str:
    compact = re.sub(r"=====page\d+=====", "", text.replace(" ", ""))
    return re.sub(r"\s+", "", compact)


def has_meaningful_text(text: str) -> bool:
    return bool(compact_pdf_text(text))


def line_facts_from_text(meta: dict[str, str], pdf: Path, text: str) -> list[dict[str, str]]:
    compact = compact_pdf_text(text)
    best_rows: dict[str, dict[str, str]] = {}
    for metric_code, metric_name, pattern in LINE_METRIC_PATTERNS:
        for match in re.finditer(pattern, compact):
            amount_original = match.group(1)
            amount_yi_yuan = amount_text_to_yi_yuan(amount_original)
            if metric_code in best_rows and float(best_rows[metric_code]["amount_yi_yuan"]) >= float(amount_yi_yuan):
                continue
            best_rows[metric_code] = {
                "institution_name": meta.get("university", ""),
                "year": meta.get("year", ""),
                "fiscal_stage": "budget" if meta.get("document_type") == "budget" else "",
                "document_type": meta.get("document_type", ""),
                "table_name": "text_budget_explanation",
                "metric_code": metric_code,
                "metric_name": metric_name,
                "amount_original": amount_original,
                "unit_original": "万元",
                "amount_yi_yuan": amount_yi_yuan,
                "source_pdf": str(pdf),
                "source_url": meta.get("source_url", ""),
                "extraction_method": "pymupdf_text_regex_candidate",
                "verified": "False",
                "notes": "auto-converted from official PDF text; keeps largest value per metric_code; requires manual review",
            }
    return list(best_rows.values())


def line_candidates_from_text(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    page = 0
    line_no = 0
    for raw_line in text.splitlines():
        if raw_line.startswith("===== page "):
            page_match = re.search(r"page\s+(\d+)", raw_line)
            page = int(page_match.group(1)) if page_match else page + 1
            line_no = 0
            continue
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        line_no += 1
        if any(keyword in line for keyword in KEYWORDS) or number_candidates(line):
            rows.append(
                {
                    "page": str(page),
                    "line_no": str(line_no),
                    "unit_hint": "万元" if "万元" in line else "",
                    "raw_text": line,
                    "number_candidates": number_candidates(line),
                    "keyword_hits": "|".join(k for k in KEYWORDS if k in line),
                }
            )
    return rows


def csv_data_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as f:
        return max(sum(1 for _ in f) - 1, 0)


def ocr_pdf_text(pdf: Path) -> str:
    try:
        import fitz
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise SystemExit("OCR fallback needs PyMuPDF and PaddleOCR in the dev environment.") from exc

    ocr = PaddleOCR(lang="ch", show_log=False)
    pages: list[str] = []
    with fitz.open(pdf) as doc:
        for page_index, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image_path = DEFAULT_OUT_DIR / "_ocr_tmp_page.png"
            pix.save(image_path)
            result = ocr.ocr(str(image_path), cls=True)
            texts: list[str] = []
            for block in result or []:
                for item in block or []:
                    if len(item) >= 2:
                        texts.append(str(item[1][0]))
            pages.append(f"\n\n===== page {page_index} =====\n" + "\n".join(texts))
            image_path.unlink(missing_ok=True)
    return "".join(pages).lstrip()


def process_one(row: dict[str, str], pdf: Path, args: argparse.Namespace) -> dict[str, str]:
    pdf_id = pdf_id_from_row(row, pdf)
    meta_args = row_to_namespace(row, pdf, args.source_csv)
    meta = build_metadata(meta_args, pdf)

    text_path = args.text_dir / f"{pdf_id}.txt"
    tables_path = args.tables_dir / f"{pdf_id}_tables.csv"
    lines_path = args.tables_dir / f"{pdf_id}_line_candidates.csv"
    facts_path = args.tables_dir / f"{pdf_id}_facts.csv"

    existing_fact_rows = csv_data_rows(facts_path)
    if args.reuse_existing_outputs and existing_fact_rows:
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
            "table_rows": str(csv_data_rows(tables_path)),
            "line_candidate_rows": str(csv_data_rows(lines_path)),
            "fact_rows": str(existing_fact_rows),
            "status": "reused_existing_outputs",
            "notes": "reused existing per-PDF outputs; facts still require manual metric/table review",
        }

    table_rows, line_candidates, text = extract_pdf(pdf)
    if args.ocr_empty_pdfs and not table_rows and not line_candidates and not has_meaningful_text(text):
        text = ocr_pdf_text(pdf)
        line_candidates = line_candidates_from_text(text)

    text_path.write_text(text, encoding="utf-8")
    write_table_candidates(tables_path, table_rows, meta)
    write_line_candidates(lines_path, line_candidates, meta)

    fact_rows = convert(tables_path)
    if not fact_rows:
        fact_rows = line_facts_from_text(meta, pdf, text)
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
    pdfs = sorted(args.pdf_dir.rglob("*.pdf"))
    used: set[Path] = set()
    inventory_rows: list[dict[str, str]] = []

    rows_to_process = pdf_url_rows(sources)
    if args.only_university:
        rows_to_process = [row for row in rows_to_process if row.get("university") in set(args.only_university)]
    if args.only_document_type:
        rows_to_process = [row for row in rows_to_process if row.get("document_type") in set(args.only_document_type)]
    if args.only_year:
        years = {str(year) for year in args.only_year}
        rows_to_process = [row for row in rows_to_process if str(row.get("year", "")).split(".")[0] in years]

    for row in rows_to_process:
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

    if args.include_unregistered_pdfs:
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
