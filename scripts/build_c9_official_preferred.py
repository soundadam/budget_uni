#!/usr/bin/env python
"""Build a C9 budget trend with official PDF values preferred over old OCR rows."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_DIR / "data" / "interim" / "matplotlib"))

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


OFFICIAL_FACTS = PROJECT_DIR / "data" / "interim" / "official_budget_tables" / "official_finance_fact_candidates.csv"
OFFICIAL_HTML_FACTS = PROJECT_DIR / "data" / "interim" / "official_html_budget_pages" / "official_html_finance_fact_candidates.csv"
OLD_BUDGET = PROJECT_DIR / "data" / "processed" / "ministry_university_budget.csv"
OUT_DIR = PROJECT_DIR / "data" / "processed"
FIG_DIR = OUT_DIR / "figures"
WATERMARK = "@soundadam"

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

METRIC_PRIORITY = [
    "budget_total",
    "income_total",
    "expense_total",
    "current_year_expense_total",
    "current_year_income_total",
]


def c9_palette() -> dict[str, tuple[float, float, float]]:
    return dict(zip(C9, sns.color_palette("tab10", n_colors=len(C9))))


def savefig_with_watermark(path: Path, dpi: int = 220) -> None:
    fig = plt.gcf()
    fig.text(
        0.5,
        0.5,
        WATERMARK,
        ha="center",
        va="center",
        fontsize=46,
        color="#334155",
        alpha=0.12,
        rotation=28,
        weight="bold",
    )
    fig.text(
        0.985,
        0.018,
        WATERMARK,
        ha="right",
        va="bottom",
        fontsize=10,
        color="#334155",
        alpha=0.5,
    )
    plt.savefig(path, dpi=dpi)


def year_as_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def read_official_facts() -> pd.DataFrame:
    frames = [pd.read_csv(OFFICIAL_FACTS)]
    if OFFICIAL_HTML_FACTS.exists():
        html_facts = pd.read_csv(OFFICIAL_HTML_FACTS)
        html_facts["source_kind"] = "official_html"
        frames.append(html_facts)
    facts = pd.concat(frames, ignore_index=True)
    facts["source_kind"] = facts.get("source_kind", "official_pdf").fillna("official_pdf")
    return facts


def build_official_rows() -> pd.DataFrame:
    facts = read_official_facts()
    facts = facts[
        facts["institution_name"].isin(C9)
        & facts["document_type"].eq("budget")
        & facts["metric_code"].isin(METRIC_PRIORITY)
    ].copy()
    facts["year"] = year_as_int(facts["year"])
    facts["amount_yi_yuan"] = pd.to_numeric(facts["amount_yi_yuan"], errors="coerce")
    facts = facts.dropna(subset=["year", "amount_yi_yuan"])
    facts["metric_rank"] = facts["metric_code"].map({metric: i for i, metric in enumerate(METRIC_PRIORITY)})
    facts = facts.sort_values(["institution_name", "year", "metric_rank", "amount_yi_yuan"], ascending=[True, True, True, False])
    picked = facts.groupby(["institution_name", "year"], as_index=False).first()
    return pd.DataFrame(
        {
            "university": picked["institution_name"],
            "year": picked["year"].astype(int),
            "budget_yi_yuan": picked["amount_yi_yuan"],
            "source_type": picked["source_kind"],
            "metric_code": picked["metric_code"],
            "source_url": picked["source_url"],
            "notes": "official candidate; metric priority: budget_total > income_total > expense_total > current_year_expense_total > current_year_income_total",
        }
    )


def build_fallback_rows(existing_keys: set[tuple[str, int]]) -> pd.DataFrame:
    old = pd.read_csv(OLD_BUDGET)
    old = old[old["university"].isin(C9)].copy()
    old["year"] = year_as_int(old["year"])
    old["budget_yi_yuan"] = pd.to_numeric(old["budget_yi_yuan"], errors="coerce")
    old = old.dropna(subset=["year", "budget_yi_yuan"])
    old["key"] = list(zip(old["university"], old["year"].astype(int)))
    old = old[~old["key"].isin(existing_keys)]
    return pd.DataFrame(
        {
            "university": old["university"],
            "year": old["year"].astype(int),
            "budget_yi_yuan": old["budget_yi_yuan"],
            "source_type": "third_party_ocr_fallback",
            "metric_code": "legacy_budget_yi_yuan",
            "source_url": old["source_url"].fillna(""),
            "notes": old["notes"].fillna(""),
        }
    )


def plot_trend(data: pd.DataFrame, path: Path) -> None:
    sns.set_theme(style="whitegrid", font="Arial Unicode MS")
    palette = c9_palette()
    plt.figure(figsize=(14, 7.5))
    ax = sns.lineplot(
        data=data,
        x="year",
        y="budget_yi_yuan",
        hue="university",
        hue_order=C9,
        palette=palette,
        marker="o",
        linewidth=1.8,
    )

    fallback = data[data["source_type"].eq("third_party_ocr_fallback")]
    if not fallback.empty:
        sns.scatterplot(
            data=fallback,
            x="year",
            y="budget_yi_yuan",
            hue="university",
            hue_order=C9,
            palette=palette,
            marker="X",
            s=90,
            legend=False,
            ax=ax,
            edgecolor="white",
            linewidth=0.8,
        )

    ax.set_title("C9高校年度预算变化（官方优先）")
    ax.set_xlabel("年份")
    ax.set_ylabel("经费（亿元）")
    ax.set_xticks(sorted(data["year"].unique()))
    ax.legend(title="高校", bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0, fontsize=8)
    ax.text(
        0.01,
        0.02,
        "圆点/折线：官方PDF/HTML优先；X 标记：旧第三方OCR回退",
        transform=ax.transAxes,
        fontsize=9,
        color="#475569",
    )
    plt.tight_layout()
    savefig_with_watermark(path)
    plt.close()


def plot_growth(data: pd.DataFrame, path: Path) -> pd.DataFrame:
    growth = data.sort_values(["university", "year"]).copy()
    growth["growth_rate"] = growth.groupby("university")["budget_yi_yuan"].pct_change()
    growth["growth_percent"] = growth["growth_rate"] * 100
    growth = growth.dropna(subset=["growth_percent"])

    sns.set_theme(style="whitegrid", font="Arial Unicode MS")
    palette = c9_palette()
    plt.figure(figsize=(14, 7.5))
    ax = sns.lineplot(
        data=growth,
        x="year",
        y="growth_percent",
        hue="university",
        hue_order=C9,
        palette=palette,
        marker="o",
        linewidth=1.8,
    )
    fallback = growth[growth["source_type"].eq("third_party_ocr_fallback")]
    if not fallback.empty:
        sns.scatterplot(
            data=fallback,
            x="year",
            y="growth_percent",
            hue="university",
            hue_order=C9,
            palette=palette,
            marker="X",
            s=90,
            legend=False,
            ax=ax,
            edgecolor="white",
            linewidth=0.8,
        )

    ax.axhline(0, color="#475569", linewidth=1, linestyle="--")
    ax.set_title("C9高校年度预算同比增速（官方优先）")
    ax.set_xlabel("年份")
    ax.set_ylabel("同比增速（%）")
    ax.set_xticks(sorted(growth["year"].unique()))
    ax.legend(title="高校", bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0, fontsize=8)
    ax.text(
        0.01,
        0.02,
        "圆点/折线：官方PDF/HTML优先；X 标记：当年值来自旧第三方OCR回退",
        transform=ax.transAxes,
        fontsize=9,
        color="#475569",
    )
    plt.tight_layout()
    savefig_with_watermark(path)
    plt.close()
    return growth


def plot_combined(data: pd.DataFrame, growth: pd.DataFrame, path: Path) -> None:
    sns.set_theme(style="whitegrid", font="Arial Unicode MS")
    palette = c9_palette()
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(15, 11),
        sharex=True,
        gridspec_kw={"height_ratios": [1.45, 1]},
    )

    trend_ax, growth_ax = axes
    sns.lineplot(
        data=data,
        x="year",
        y="budget_yi_yuan",
        hue="university",
        hue_order=C9,
        palette=palette,
        marker="o",
        linewidth=1.8,
        ax=trend_ax,
    )
    fallback = data[data["source_type"].eq("third_party_ocr_fallback")]
    if not fallback.empty:
        sns.scatterplot(
            data=fallback,
            x="year",
            y="budget_yi_yuan",
            hue="university",
            hue_order=C9,
            palette=palette,
            marker="X",
            s=90,
            legend=False,
            ax=trend_ax,
            edgecolor="white",
            linewidth=0.8,
        )
    trend_ax.set_title("C9高校年度预算变化与同比增速（官方优先）")
    trend_ax.set_xlabel("")
    trend_ax.set_ylabel("经费（亿元）")
    trend_ax.legend(title="高校", bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0, fontsize=8)

    sns.lineplot(
        data=growth,
        x="year",
        y="growth_percent",
        hue="university",
        hue_order=C9,
        palette=palette,
        marker="o",
        linewidth=1.8,
        legend=False,
        ax=growth_ax,
    )
    growth_fallback = growth[growth["source_type"].eq("third_party_ocr_fallback")]
    if not growth_fallback.empty:
        sns.scatterplot(
            data=growth_fallback,
            x="year",
            y="growth_percent",
            hue="university",
            hue_order=C9,
            palette=palette,
            marker="X",
            s=90,
            legend=False,
            ax=growth_ax,
            edgecolor="white",
            linewidth=0.8,
        )
    growth_ax.axhline(0, color="#475569", linewidth=1, linestyle="--")
    growth_ax.set_xlabel("年份")
    growth_ax.set_ylabel("同比增速（%）")
    growth_ax.set_xticks(sorted(data["year"].unique()))
    growth_ax.text(
        0.01,
        0.03,
        "圆点/折线：官方PDF/HTML优先；X 标记：旧第三方OCR回退",
        transform=growth_ax.transAxes,
        fontsize=9,
        color="#475569",
    )

    plt.tight_layout()
    savefig_with_watermark(path)
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    official = build_official_rows()
    existing_keys = set(zip(official["university"], official["year"]))
    fallback = build_fallback_rows(existing_keys)
    combined = pd.concat([official, fallback], ignore_index=True)
    combined = combined[combined["year"].between(YEAR_MIN, YEAR_MAX)].copy()
    combined = combined.sort_values(["university", "year", "source_type"]).reset_index(drop=True)

    csv_path = OUT_DIR / "c9_budget_official_preferred.csv"
    pivot_path = OUT_DIR / "c9_budget_official_preferred_pivot.csv"
    source_pivot_path = OUT_DIR / "c9_budget_official_preferred_source_pivot.csv"
    fig_path = FIG_DIR / "c9_budget_trend_official_preferred.png"
    growth_csv_path = OUT_DIR / "c9_budget_growth_official_preferred.csv"
    growth_pivot_path = OUT_DIR / "c9_budget_growth_official_preferred_pivot.csv"
    growth_fig_path = FIG_DIR / "c9_budget_growth_official_preferred.png"
    combined_fig_path = FIG_DIR / "c9_budget_trend_growth_official_preferred.png"

    combined.to_csv(csv_path, index=False, encoding="utf-8")
    (
        combined.pivot_table(index="year", columns="university", values="budget_yi_yuan", aggfunc="first")
        .reindex(columns=C9)
        .sort_index()
        .round(2)
        .to_csv(pivot_path, encoding="utf-8")
    )
    (
        combined.pivot_table(index="year", columns="university", values="source_type", aggfunc="first")
        .reindex(columns=C9)
        .sort_index()
        .to_csv(source_pivot_path, encoding="utf-8")
    )
    plot_trend(combined, fig_path)
    growth = plot_growth(combined, growth_fig_path)
    plot_combined(combined, growth, combined_fig_path)
    growth.to_csv(growth_csv_path, index=False, encoding="utf-8")
    (
        growth.pivot_table(index="year", columns="university", values="growth_percent", aggfunc="first")
        .reindex(columns=C9)
        .sort_index()
        .round(2)
        .to_csv(growth_pivot_path, encoding="utf-8")
    )

    print(csv_path)
    print(pivot_path)
    print(source_pivot_path)
    print(fig_path)
    print(growth_csv_path)
    print(growth_pivot_path)
    print(growth_fig_path)
    print(combined_fig_path)
    print(combined.groupby(["university", "source_type"]).size().to_string())


if __name__ == "__main__":
    main()
