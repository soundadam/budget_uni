#!/usr/bin/env python
"""Build processed wide tables from official finance fact candidates.

The source candidate files are machine extracted and intentionally long-form.
This script keeps the original candidates untouched, standardizes a small set
of common metric-name variants, and writes analysis-friendly wide tables with
missing values left blank.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


PROJECT_DIR = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_DIR / "data" / "interim" / "matplotlib"))

OFFICIAL_FACTS = PROJECT_DIR / "data" / "interim" / "official_budget_tables" / "official_finance_fact_candidates.csv"
OFFICIAL_HTML_FACTS = PROJECT_DIR / "data" / "interim" / "official_html_budget_pages" / "official_html_finance_fact_candidates.csv"
OUT_DIR = PROJECT_DIR / "data" / "processed"
FIG_DEV_DIR = OUT_DIR / "figures" / "dev"
WATERMARK = "@soundadam"
GITHUB_URL = "github.com/soundadam/budget_uni_cn"

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

C9_EN = {
    "北京大学": "Peking University",
    "清华大学": "Tsinghua University",
    "浙江大学": "Zhejiang University",
    "上海交通大学": "Shanghai Jiao Tong University",
    "复旦大学": "Fudan University",
    "南京大学": "Nanjing University",
    "中国科学技术大学": "University of Science and Technology of China",
    "哈尔滨工业大学": "Harbin Institute of Technology",
    "西安交通大学": "Xi'an Jiaotong University",
}

COMPARISON_PRIORITY = [
    "budget_total",
    "income_total",
    "expense_total",
]

VALUE_COLUMNS = [
    "budget_total",
    "income_total",
    "expense_total",
    "current_year_income_total",
    "current_year_expense_total",
    "fiscal_appropriation_income",
    "general_public_budget_appropriation_income",
    "government_fund_budget_appropriation_income",
    "general_public_budget_fiscal_appropriation",
    "undertaking_income",
    "other_income",
    "non_fiscal_surplus_used",
    "carryover_from_previous_year",
    "carryover_to_next_year",
    "current_year_fiscal_appropriation_expense",
    "education_expense",
    "science_technology_expense",
    "social_security_employment_expense",
    "health_expense",
    "housing_security_expense",
    "resource_exploration_industry_information_expense",
    "energy_conservation_environmental_protection_expense",
]

PIVOT_METRICS = [
    "comparison_budget_total",
    "current_year_income_total",
    "current_year_expense_total",
    "carryover_from_previous_year",
    "carryover_to_next_year",
    "undertaking_income",
    "other_income",
    "fiscal_appropriation_income",
    "general_public_budget_appropriation_income",
    "government_fund_budget_appropriation_income",
]


def clean_metric_name(value: str) -> str:
    text = "" if pd.isna(value) else str(value)
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"^[一二三四五六七八九十]+、", "", text)
    return text.strip()


def normalized_metric_code(row: pd.Series) -> str:
    code = "" if pd.isna(row.get("metric_code")) else str(row.get("metric_code"))
    name = clean_metric_name(row.get("metric_name", ""))

    if code and code != "unmapped":
        return code

    patterns = [
        ("收支总预算", "budget_total"),
        ("部门收支总预算", "budget_total"),
        ("收入总计", "income_total"),
        ("支出总计", "expense_total"),
        ("本年收入合计", "current_year_income_total"),
        ("本年收入", "current_year_income_total"),
        ("本年支出合计", "current_year_expense_total"),
        ("本年支出", "current_year_expense_total"),
        ("财政拨款收入", "fiscal_appropriation_income"),
        ("一般公共预算拨款收入", "general_public_budget_appropriation_income"),
        ("一般公共预算财政拨款", "general_public_budget_fiscal_appropriation"),
        ("政府性基金预算拨款收入", "government_fund_budget_appropriation_income"),
        ("事业收入", "undertaking_income"),
        ("其他收入", "other_income"),
        ("使用非财政拨款结余", "non_fiscal_surplus_used"),
        ("上年结转", "carryover_from_previous_year"),
        ("结转下年", "carryover_to_next_year"),
        ("本年财政拨款支出", "current_year_fiscal_appropriation_expense"),
        ("教育支出", "education_expense"),
        ("科学技术支出", "science_technology_expense"),
        ("社会保障和就业支出", "social_security_employment_expense"),
        ("卫生健康支出", "health_expense"),
        ("住房保障支出", "housing_security_expense"),
        ("资源勘探工业信息等支出", "resource_exploration_industry_information_expense"),
        ("节能环保支出", "energy_conservation_environmental_protection_expense"),
    ]
    for pattern, normalized in patterns:
        if pattern in name:
            return normalized
    return code or "unmapped"


def read_facts() -> pd.DataFrame:
    frames = []
    pdf = pd.read_csv(OFFICIAL_FACTS)
    pdf["source_type"] = "official_pdf"
    frames.append(pdf)
    if OFFICIAL_HTML_FACTS.exists():
        html = pd.read_csv(OFFICIAL_HTML_FACTS)
        html["source_type"] = "official_html"
        frames.append(html)

    facts = pd.concat(frames, ignore_index=True)
    facts["year"] = pd.to_numeric(facts["year"], errors="coerce").astype("Int64")
    facts["amount_yi_yuan"] = pd.to_numeric(facts["amount_yi_yuan"], errors="coerce")
    facts = facts.dropna(subset=["institution_name", "year", "amount_yi_yuan"]).copy()
    facts["metric_code_normalized"] = facts.apply(normalized_metric_code, axis=1)
    facts = facts[facts["metric_code_normalized"].isin(VALUE_COLUMNS)].copy()
    facts["document_type"] = facts["document_type"].fillna("")
    facts["source_url"] = facts["source_url"].fillna("")
    facts["source_pdf"] = facts["source_pdf"].fillna("")
    facts["is_unknown_year_source"] = facts["source_pdf"].str.contains("unknown_year", na=False)
    facts["has_known_year_source"] = facts.groupby(["institution_name", "year", "document_type"])["is_unknown_year_source"].transform(
        lambda s: (~s).any()
    )
    facts = facts[~(facts["has_known_year_source"] & facts["is_unknown_year_source"])].copy()
    facts["verified"] = facts["verified"].fillna(False).astype(str)
    return facts


def pick_metric_values(facts: pd.DataFrame) -> pd.DataFrame:
    sort_cols = ["institution_name", "year", "document_type", "metric_code_normalized", "amount_yi_yuan"]
    picked = (
        facts.sort_values(sort_cols, ascending=[True, True, True, True, False])
        .groupby(["institution_name", "year", "document_type", "metric_code_normalized"], as_index=False)
        .first()
    )
    return picked


def build_wide(picked: pd.DataFrame, facts: pd.DataFrame) -> pd.DataFrame:
    values = picked.pivot_table(
        index=["institution_name", "year", "document_type"],
        columns="metric_code_normalized",
        values="amount_yi_yuan",
        aggfunc="first",
    ).reset_index()

    for column in VALUE_COLUMNS:
        if column not in values.columns:
            values[column] = pd.NA

    values["comparison_budget_total"] = pd.NA
    values["comparison_metric_code"] = ""
    for metric in COMPARISON_PRIORITY:
        mask = values["comparison_budget_total"].isna() & values[metric].notna()
        values.loc[mask, "comparison_budget_total"] = values.loc[mask, metric]
        values.loc[mask, "comparison_metric_code"] = metric

    source = (
        facts.groupby(["institution_name", "year", "document_type"], as_index=False)
        .agg(
            source_types=("source_type", lambda s: "; ".join(sorted(set(map(str, s))))),
            source_urls=("source_url", lambda s: "; ".join(sorted({str(v) for v in s if str(v)}))),
            source_pdfs=("source_pdf", lambda s: "; ".join(sorted({str(v) for v in s if str(v)}))),
            metric_codes_available=("metric_code_normalized", lambda s: "; ".join(sorted(set(map(str, s))))),
            verified_any=("verified", lambda s: any(str(v).lower() == "true" for v in s)),
        )
    )
    wide = values.merge(source, on=["institution_name", "year", "document_type"], how="left")

    ordered = (
        ["institution_name", "year", "document_type", "comparison_budget_total", "comparison_metric_code"]
        + VALUE_COLUMNS
        + ["source_types", "source_urls", "source_pdfs", "metric_codes_available", "verified_any"]
    )
    wide = wide[ordered].sort_values(["institution_name", "document_type", "year"]).reset_index(drop=True)
    return wide


def write_c9_outputs(wide: pd.DataFrame) -> None:
    c9 = wide[
        wide["institution_name"].isin(C9)
        & wide["document_type"].eq("budget")
        & wide["year"].between(2013, 2026)
    ].copy()
    c9 = c9.sort_values(["institution_name", "year"]).reset_index(drop=True)
    c9.to_csv(OUT_DIR / "c9_official_finance_fact_derived.csv", index=False, encoding="utf-8")

    for metric in PIVOT_METRICS:
        column = metric if metric in c9.columns else f"{metric}_yi_yuan"
        if column not in c9.columns:
            continue
        (
            c9.pivot_table(index="year", columns="institution_name", values=column, aggfunc="first")
            .reindex(columns=C9)
            .sort_index()
            .round(6)
            .to_csv(OUT_DIR / f"c9_official_finance_{metric}_pivot.csv", encoding="utf-8")
        )

    (
        c9.pivot_table(index="year", columns="institution_name", values="comparison_metric_code", aggfunc="first")
        .reindex(columns=C9)
        .sort_index()
        .to_csv(OUT_DIR / "c9_official_finance_comparison_metric_code_pivot.csv", encoding="utf-8")
    )

    coverage_rows = []
    for university in C9:
        group = c9[c9["institution_name"].eq(university)]
        for metric in PIVOT_METRICS:
            if metric not in group.columns:
                years = []
            else:
                years = sorted(group.loc[group[metric].notna(), "year"].astype(int).tolist())
            coverage_rows.append(
                {
                    "institution_name": university,
                    "document_type": "budget",
                    "metric": metric,
                    "available_year_count": len(years),
                    "available_years": " ".join(map(str, years)),
                    "missing_years_2013_2026": " ".join(map(str, sorted(set(range(2013, 2027)) - set(years)))),
                }
            )
    pd.DataFrame(coverage_rows).to_csv(OUT_DIR / "c9_official_finance_metric_coverage.csv", index=False, encoding="utf-8")


def set_plot_theme() -> None:
    sns.set_theme(style="whitegrid", font="DejaVu Sans")


def savefig_with_watermark(path: Path, dpi: int = 220, center_fontsize: int = 42, center_alpha: float = 0.10) -> None:
    fig = plt.gcf()
    fig.text(
        0.5,
        0.5,
        WATERMARK,
        ha="center",
        va="center",
        fontsize=center_fontsize,
        color="#334155",
        alpha=center_alpha,
        rotation=28,
        weight="bold",
    )
    fig.text(
        0.985,
        0.018,
        GITHUB_URL,
        ha="right",
        va="bottom",
        fontsize=9,
        color="#334155",
        alpha=0.5,
    )
    plt.savefig(path, dpi=dpi)


def with_plot_labels(data: pd.DataFrame) -> pd.DataFrame:
    plot_data = data.copy()
    plot_data["university_label"] = plot_data["institution_name"].map(C9_EN).fillna(plot_data["institution_name"])
    return plot_data


def c9_palette() -> dict[str, tuple[float, float, float]]:
    return dict(zip(C9_EN.values(), sns.color_palette("tab10", n_colors=len(C9))))


def plot_metric_lines(c9: pd.DataFrame, metric: str, title: str, ylabel: str, path: Path) -> None:
    plot_data = with_plot_labels(c9.dropna(subset=[metric]))
    if plot_data.empty:
        return

    set_plot_theme()
    plt.figure(figsize=(14, 7.5))
    ax = sns.lineplot(
        data=plot_data,
        x="year",
        y=metric,
        hue="university_label",
        hue_order=list(C9_EN.values()),
        palette=c9_palette(),
        marker="o",
        linewidth=1.8,
    )
    ax.set_title(title)
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel)
    ax.set_xticks(sorted(plot_data["year"].unique()))
    ax.legend(title="University", bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0, fontsize=8)
    ax.text(
        0.01,
        0.02,
        "Official PDF/HTML candidates; missing metrics are left blank.",
        transform=ax.transAxes,
        fontsize=9,
        color="#475569",
    )
    plt.tight_layout()
    savefig_with_watermark(path)
    plt.close()


def plot_current_expense_share(c9: pd.DataFrame, path: Path) -> None:
    plot_data = c9.dropna(subset=["comparison_budget_total", "current_year_expense_total"]).copy()
    if plot_data.empty:
        return

    plot_data["current_expense_share"] = plot_data["current_year_expense_total"] / plot_data["comparison_budget_total"] * 100
    plot_data = with_plot_labels(plot_data)

    set_plot_theme()
    plt.figure(figsize=(14, 7.5))
    ax = sns.lineplot(
        data=plot_data,
        x="year",
        y="current_expense_share",
        hue="university_label",
        hue_order=list(C9_EN.values()),
        palette=c9_palette(),
        marker="o",
        linewidth=1.8,
    )
    ax.set_title("C9 Current-Year Expense Share of Total Budget (Official Finance Candidates)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Current-year expense / total budget (%)")
    ax.set_xticks(sorted(plot_data["year"].unique()))
    ax.legend(title="University", bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0, fontsize=8)
    ax.text(
        0.01,
        0.02,
        "Total budget uses budget_total > income_total > expense_total priority.",
        transform=ax.transAxes,
        fontsize=9,
        color="#475569",
    )
    plt.tight_layout()
    savefig_with_watermark(path)
    plt.close()


def plot_2026_structure(c9: pd.DataFrame, path: Path) -> None:
    plot_data = c9[c9["year"].eq(2026)].copy()
    keep = ["institution_name", "comparison_budget_total", "current_year_expense_total", "carryover_to_next_year"]
    plot_data = plot_data[keep].melt(id_vars="institution_name", var_name="metric", value_name="amount_yi_yuan")
    plot_data = plot_data.dropna(subset=["amount_yi_yuan"])
    if plot_data.empty:
        return

    labels = {
        "comparison_budget_total": "Total budget",
        "current_year_expense_total": "Current-year expense",
        "carryover_to_next_year": "Carryover to next year",
    }
    plot_data["metric_label"] = plot_data["metric"].map(labels)
    plot_data["university_label"] = plot_data["institution_name"].map(C9_EN).fillna(plot_data["institution_name"])

    set_plot_theme()
    plt.figure(figsize=(15, 7.5))
    ax = sns.barplot(
        data=plot_data,
        x="university_label",
        y="amount_yi_yuan",
        hue="metric_label",
        palette=["#2563eb", "#16a34a", "#f59e0b"],
    )
    ax.set_title("C9 2026 Total Budget, Current-Year Expense, and Carryover")
    ax.set_xlabel("")
    ax.set_ylabel("Amount (100M CNY)")
    ax.tick_params(axis="x", rotation=35)
    ax.legend(title="")
    ax.text(
        0.01,
        0.96,
        "Official finance candidates; blank metrics are omitted.",
        transform=ax.transAxes,
        fontsize=9,
        color="#475569",
    )
    plt.tight_layout()
    savefig_with_watermark(path, center_fontsize=36, center_alpha=0.08)
    plt.close()


def plot_dev_figures(wide: pd.DataFrame) -> None:
    FIG_DEV_DIR.mkdir(parents=True, exist_ok=True)
    c9 = wide[
        wide["institution_name"].isin(C9)
        & wide["document_type"].eq("budget")
        & wide["year"].between(2013, 2026)
    ].copy()
    c9 = c9.sort_values(["institution_name", "year"]).reset_index(drop=True)

    plot_metric_lines(
        c9,
        "comparison_budget_total",
        "C9 Total Budget Trend by Explicit Finance Metric (Official Candidates)",
        "Total budget (100M CNY)",
        FIG_DEV_DIR / "c9_official_finance_total_budget_dev.png",
    )
    plot_metric_lines(
        c9,
        "current_year_expense_total",
        "C9 Current-Year Expense Trend (Official Finance Candidates)",
        "Current-year expense (100M CNY)",
        FIG_DEV_DIR / "c9_official_finance_current_year_expense_dev.png",
    )
    plot_metric_lines(
        c9,
        "carryover_to_next_year",
        "C9 Carryover to Next Year Trend (Official Finance Candidates)",
        "Carryover to next year (100M CNY)",
        FIG_DEV_DIR / "c9_official_finance_carryover_to_next_year_dev.png",
    )
    plot_current_expense_share(
        c9,
        FIG_DEV_DIR / "c9_official_finance_current_expense_share_dev.png",
    )
    plot_2026_structure(
        c9,
        FIG_DEV_DIR / "c9_official_finance_2026_structure_dev.png",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    facts = read_facts()
    picked = pick_metric_values(facts)
    wide = build_wide(picked, facts)

    wide.to_csv(OUT_DIR / "university_finance_fact_derived.csv", index=False, encoding="utf-8")
    write_c9_outputs(wide)
    plot_dev_figures(wide)

    print(OUT_DIR / "university_finance_fact_derived.csv")
    print(OUT_DIR / "c9_official_finance_fact_derived.csv")
    print(OUT_DIR / "c9_official_finance_metric_coverage.csv")
    print(FIG_DEV_DIR)
    print(f"rows: {len(wide)}")
    print(f"institutions: {wide['institution_name'].nunique()}")


if __name__ == "__main__":
    main()
