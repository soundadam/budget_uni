#!/usr/bin/env python
"""Extract finance fact candidates from registered official HTML budget pages.

This is the HTML counterpart to the official PDF pipeline. It reads
official_sources.csv, fetches rows registered as official_page + budget, and
writes long-form interim fact candidates with the same columns used by
official_finance_fact_candidates.csv.
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CSV = PROJECT_DIR / "data" / "raw" / "official_sources.csv"
DEFAULT_OUT_DIR = PROJECT_DIR / "data" / "interim" / "official_html_budget_pages"
DEFAULT_FACTS_CSV = DEFAULT_OUT_DIR / "official_html_finance_fact_candidates.csv"

OUTPUT_FIELDS = [
    "institution_name",
    "year",
    "fiscal_stage",
    "document_type",
    "table_name",
    "metric_code",
    "metric_name",
    "amount_original",
    "unit_original",
    "amount_yi_yuan",
    "source_pdf",
    "source_url",
    "extraction_method",
    "verified",
    "notes",
]

LINE_METRIC_PATTERNS = [
    ("budget_total", "部门收支总预算", r"(?:部门)?收支总预算\s*([0-9,]+(?:\.\d+)?)\s*万元"),
    ("current_year_income_total", "本年收入合计", r"本年收入合计\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("current_year_income_total", "本年收入", r"本年收入\s*([0-9,]+(?:\.\d+)?)\s*万元"),
    ("current_year_expense_total", "本年支出合计", r"本年支出合计\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("current_year_expense_total", "本年支出", r"本年支出\s*([0-9,]+(?:\.\d+)?)\s*万元"),
    ("carryover_from_previous_year", "上年结转", r"上年结转\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("carryover_to_next_year", "结转下年", r"结转下年(?:支出)?\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("income_total", "收入总计", r"收入总计\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("expense_total", "支出总计", r"支出总计\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("general_public_budget_appropriation_income", "一般公共预算拨款收入", r"一般公共预算[拨拔]款收入\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("government_fund_budget_appropriation_income", "政府性基金预算拨款收入", r"政府性基金预算[拨拔]款收入\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("undertaking_income", "事业收入", r"事业收入\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("business_income", "事业单位经营收入", r"事业单位经营收入\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("other_income", "其他收入", r"其他收入\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("education_expense", "教育支出", r"教育支出\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("science_technology_expense", "科学技术支出", r"科学技术支出\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
    ("housing_security_expense", "住房保障支出", r"住房保障支出\s*([0-9,]+(?:\.\d+)?)(?:万元)?"),
]

TABLE_METRIC_PATTERNS = [
    ("current_year_income_total", "本年收入合计"),
    ("current_year_expense_total", "本年支出合计"),
    ("carryover_from_previous_year", "上年结转"),
    ("carryover_to_next_year", "结转下年"),
    ("income_total", "收入总计"),
    ("expense_total", "支出总计"),
    ("general_public_budget_appropriation_income", "一般公共预算拨款收入"),
    ("government_fund_budget_appropriation_income", "政府性基金预算拨款收入"),
    ("undertaking_income", "事业收入"),
    ("business_income", "事业单位经营收入"),
    ("other_income", "其他收入"),
    ("education_expense", "教育支出"),
    ("science_technology_expense", "科学技术支出"),
    ("housing_security_expense", "住房保障支出"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract candidates from official HTML budget pages.")
    parser.add_argument("--source-csv", type=Path, default=DEFAULT_SOURCE_CSV)
    parser.add_argument("--out", type=Path, default=DEFAULT_FACTS_CSV)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_OUT_DIR / "raw_text")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--only-url", action="append", default=[], help="Process only this URL. Repeatable.")
    parser.add_argument("--only-university", action="append", default=[], help="Process only this university. Repeatable.")
    parser.add_argument("--only-year", action="append", default=[], help="Process only this year. Repeatable.")
    return parser.parse_args()


def read_sources(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def html_budget_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if row.get("source_level") == "official_page"
        and row.get("document_type") == "budget"
        and row.get("url", "").lower().startswith(("http://", "https://"))
    ]


def filter_rows(rows: list[dict[str, str]], args: argparse.Namespace) -> list[dict[str, str]]:
    if args.only_url:
        urls = set(args.only_url)
        rows = [row for row in rows if row.get("url") in urls]
    if args.only_university:
        universities = set(args.only_university)
        rows = [row for row in rows if row.get("university") in universities]
    if args.only_year:
        years = {str(year) for year in args.only_year}
        rows = [row for row in rows if str(row.get("year", "")).split(".")[0] in years]
    return rows


def safe_part(value: str) -> str:
    text = re.sub(r"\s+", "_", str(value or "").strip())
    text = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", text)
    return text.strip("_") or "unknown"


def source_id(row: dict[str, str]) -> str:
    netloc = urlparse(row.get("url", "")).netloc.replace(".", "_")
    return "_".join(
        [
            safe_part(row.get("university") or "unknown"),
            safe_part(str(row.get("year", "")).split(".")[0] or "unknown_year"),
            safe_part(row.get("document_type") or "document"),
            safe_part(netloc or "html"),
        ]
    )


def fetch_html(url: str, timeout: float) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) official-budget-html-extractor/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def soup_from_html(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup


def clean_text(value: str | None) -> str:
    if value is None:
        return ""
    text = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def compact_text(text: str) -> str:
    return re.sub(r"\s+", "", text.replace("\xa0", " "))


def parse_amount(value: str) -> float | None:
    text = clean_text(value).replace(",", "")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    return float(match.group()) if match else None


def amount_to_yi_yuan(amount_original: str, unit: str) -> str:
    amount = parse_amount(amount_original)
    if amount is None:
        return ""
    if unit == "万元":
        return f"{amount / 10000:.6f}"
    if unit == "亿元":
        return f"{amount:.6f}"
    return ""


def base_fact(row: dict[str, str], metric_code: str, metric_name: str, amount_original: str) -> dict[str, str]:
    return {
        "institution_name": row.get("university", ""),
        "year": str(row.get("year", "")).split(".")[0],
        "fiscal_stage": "budget",
        "document_type": row.get("document_type", ""),
        "table_name": "",
        "metric_code": metric_code,
        "metric_name": metric_name,
        "amount_original": amount_original,
        "unit_original": "万元",
        "amount_yi_yuan": amount_to_yi_yuan(amount_original, "万元"),
        "source_pdf": "",
        "source_url": row.get("url", ""),
        "extraction_method": "",
        "verified": "False",
        "notes": "auto-extracted from official HTML page; requires manual review",
    }


def text_facts(row: dict[str, str], text: str) -> list[dict[str, str]]:
    compact = compact_text(text)
    best: dict[str, dict[str, str]] = {}
    for metric_code, metric_name, pattern in LINE_METRIC_PATTERNS:
        for match in re.finditer(pattern, compact):
            fact = base_fact(row, metric_code, metric_name, match.group(1))
            fact["table_name"] = "html_text_budget_explanation"
            fact["extraction_method"] = "html_text_regex_candidate"
            fact["notes"] = "auto-extracted from official HTML text; keeps largest value per metric_code; requires manual review"
            if metric_code in best and float(best[metric_code]["amount_yi_yuan"] or 0) >= float(fact["amount_yi_yuan"] or 0):
                continue
            best[metric_code] = fact
    return list(best.values())


def table_rows(soup: BeautifulSoup) -> list[tuple[int, int, list[str]]]:
    rows: list[tuple[int, int, list[str]]] = []
    for table_index, table in enumerate(soup.find_all("table"), start=1):
        for row_index, tr in enumerate(table.find_all("tr"), start=1):
            cells = [clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["td", "th"])]
            if cells:
                rows.append((table_index, row_index, cells))
    return rows


def table_facts(row: dict[str, str], soup: BeautifulSoup) -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []
    for table_index, row_index, cells in table_rows(soup):
        for idx, cell in enumerate(cells[:-1]):
            metric = compact_text(cell)
            amount = cells[idx + 1]
            if parse_amount(amount) is None:
                continue
            for metric_code, metric_name in TABLE_METRIC_PATTERNS:
                if metric_name in metric:
                    fact = base_fact(row, metric_code, metric_name, amount)
                    fact["table_name"] = f"html_table_{table_index}_row_{row_index}"
                    fact["extraction_method"] = "html_table_cell_candidate"
                    facts.append(fact)
                    break
    return facts


def write_raw_text(path: Path, row: dict[str, str], soup: BeautifulSoup) -> str:
    text = soup.get_text("\n", strip=True)
    header = [
        f"source_url: {row.get('url', '')}",
        f"university: {row.get('university', '')}",
        f"year: {row.get('year', '')}",
        f"document_type: {row.get('document_type', '')}",
        f"title: {row.get('title', '')}",
        "",
    ]
    path.write_text("\n".join(header) + text, encoding="utf-8")
    return text


def extract_one(row: dict[str, str], args: argparse.Namespace) -> tuple[list[dict[str, str]], str]:
    html = fetch_html(row["url"], args.timeout)
    soup = soup_from_html(html)
    raw_path = args.raw_dir / f"{source_id(row)}.txt"
    text = write_raw_text(raw_path, row, soup)
    facts = text_facts(row, text)
    facts.extend(table_facts(row, soup))
    return facts, ""


def write_facts(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.raw_dir.mkdir(parents=True, exist_ok=True)

    rows = filter_rows(html_budget_rows(read_sources(args.source_csv)), args)
    all_facts: list[dict[str, str]] = []
    failures: list[str] = []
    for index, row in enumerate(rows, start=1):
        try:
            facts, _ = extract_one(row, args)
            all_facts.extend(facts)
            print(f"[{index}/{len(rows)}] {row.get('university')} {row.get('year')}: {len(facts)} facts")
        except Exception as exc:  # noqa: BLE001 - continue batch extraction across flaky disclosure sites.
            failures.append(f"{row.get('university')} {row.get('year')} {row.get('url')}: {exc}")
            print(f"[{index}/{len(rows)}] {row.get('university')} {row.get('year')}: failed: {exc}")
        if args.sleep and index < len(rows):
            time.sleep(args.sleep)

    write_facts(args.out, all_facts)
    print(f"facts: {args.out} ({len(all_facts)} rows)")
    if failures:
        failure_path = args.out.with_name(f"{args.out.stem}_failures.txt")
        failure_path.write_text("\n".join(failures) + "\n", encoding="utf-8")
        print(f"failures: {failure_path} ({len(failures)} rows)")


if __name__ == "__main__":
    main()
