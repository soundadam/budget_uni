#!/usr/bin/env python
"""Report official budget/final-account source coverage by institution and year."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SOURCE_CSV = PROJECT_DIR / "data" / "raw" / "official_sources.csv"
INVENTORY_CSV = PROJECT_DIR / "data" / "interim" / "official_budget_tables" / "official_pdf_processing_inventory.csv"
OUT_DIR = PROJECT_DIR / "data" / "processed"

C9 = [
    "北京大学",
    "清华大学",
    "浙江大学",
    "上海交通大学",
    "复旦大学",
    "南京大学",
    "中国科学技术大学",
    "哈尔滨工业大学",
    "西安交通大学",
]

YEAR_MIN = 2013
YEAR_MAX = 2026
DOCUMENT_TYPES = ["budget", "final_account"]
OFFICIAL_SOURCE_LEVELS = {"official_pdf", "official_page"}


def year_as_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def compact_years(years: list[int]) -> str:
    if not years:
        return ""
    ranges: list[str] = []
    start = prev = years[0]
    for year in years[1:]:
        if year == prev + 1:
            prev = year
            continue
        ranges.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = year
    ranges.append(str(start) if start == prev else f"{start}-{prev}")
    return "、".join(ranges)


def source_coverage(source: pd.DataFrame, universities: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    years = list(range(YEAR_MIN, YEAR_MAX + 1))
    source = source.copy()
    source["year_int"] = year_as_int(source["year"])
    source = source[source["source_level"].isin(OFFICIAL_SOURCE_LEVELS)]
    for university in universities:
        for document_type in DOCUMENT_TYPES:
            subset = source[
                source["university"].eq(university)
                & source["document_type"].eq(document_type)
                & source["year_int"].notna()
            ]
            have = sorted(set(subset["year_int"].astype(int)) & set(years))
            missing = [year for year in years if year not in have]
            rows.append(
                {
                    "university": university,
                    "document_type": document_type,
                    "years_have": compact_years(have),
                    "years_missing": compact_years(missing),
                    "coverage_count": len(have),
                    "coverage_total": len(years),
                }
            )
    return pd.DataFrame(rows)


def extraction_coverage(inventory_path: Path, universities: list[str]) -> pd.DataFrame:
    if not inventory_path.exists():
        return pd.DataFrame()
    inventory = pd.read_csv(inventory_path)
    inventory["year_int"] = year_as_int(inventory["year"])
    inventory["fact_rows"] = pd.to_numeric(inventory["fact_rows"], errors="coerce").fillna(0).astype(int)
    inventory = inventory[
        inventory["institution_name"].isin(universities)
        & inventory["document_type"].isin(DOCUMENT_TYPES)
        & inventory["year_int"].notna()
    ].copy()
    if inventory.empty:
        return pd.DataFrame()
    return (
        inventory.groupby(["institution_name", "document_type", "year_int"], as_index=False)
        .agg(pdf_count=("pdf_id", "count"), fact_rows=("fact_rows", "sum"))
        .rename(columns={"institution_name": "university", "year_int": "year"})
        .sort_values(["university", "document_type", "year"])
    )


def write_markdown(path: Path, coverage: pd.DataFrame, extraction: pd.DataFrame) -> None:
    budget = coverage[coverage["document_type"].eq("budget")].copy()
    final_account = coverage[coverage["document_type"].eq("final_account")].copy()
    lines = [
        "# C9 Official Source Coverage",
        "",
        f"范围：{YEAR_MIN}-{YEAR_MAX}。覆盖仅统计 `official_pdf` 和 `official_page`，预算和决算分开统计。",
        "",
        "## 预算缺口",
        "",
        budget.to_markdown(index=False),
        "",
        "## 决算缺口",
        "",
        final_account.to_markdown(index=False),
        "",
        "## 抽取状态",
        "",
    ]
    if extraction.empty:
        lines.append("当前没有可用的 PDF inventory。")
    else:
        lines.append(extraction.to_markdown(index=False))
    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- 后续抓取必须同时查找 `budget` 和 `final_account`，不要只补预算。",
            "- `official_page` 代表官方 HTML 正文页；`official_pdf` 代表本地已有 PDF 或可下载 PDF。",
            "- 抽取候选仍需人工核对表名和指标口径，尤其要区分预算、决算、收入总计、本年收入、本年支出、财政拨款等名目。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source = pd.read_csv(SOURCE_CSV)
    coverage = source_coverage(source, C9)
    extraction = extraction_coverage(INVENTORY_CSV, C9)
    coverage_path = OUT_DIR / "c9_official_source_coverage_2013_2026.csv"
    extraction_path = OUT_DIR / "c9_official_extraction_coverage_2013_2026.csv"
    report_path = OUT_DIR / "c9_official_source_coverage_2013_2026.md"
    coverage.to_csv(coverage_path, index=False, encoding="utf-8")
    extraction.to_csv(extraction_path, index=False, encoding="utf-8")
    write_markdown(report_path, coverage, extraction)
    print(coverage_path)
    print(extraction_path)
    print(report_path)
    print(coverage.to_string(index=False))


if __name__ == "__main__":
    main()
