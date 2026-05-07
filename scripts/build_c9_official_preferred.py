#!/usr/bin/env python
"""Build a C9 budget trend with official PDF values preferred over old OCR rows."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_DIR / "data" / "interim" / "matplotlib"))

import matplotlib.pyplot as plt
from matplotlib.ticker import SymmetricalLogLocator
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
    return dict(zip(c9_plot_order(), sns.color_palette("tab10", n_colors=len(C9))))


def c9_plot_order() -> list[str]:
    return [C9_EN[university] for university in C9]


def with_plot_labels(data: pd.DataFrame) -> pd.DataFrame:
    plot_data = data.copy()
    plot_data["university_label"] = plot_data["university"].map(C9_EN).fillna(plot_data["university"])
    return plot_data


def set_plot_theme() -> None:
    sns.set_theme(style="whitegrid", font="DejaVu Sans")


def savefig_with_watermark(path: Path, dpi: int = 220, center_fontsize: int = 46, center_alpha: float = 0.12) -> None:
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
        WATERMARK,
        ha="right",
        va="bottom",
        fontsize=10,
        color="#334155",
        alpha=0.5,
    )
    plt.savefig(path, dpi=dpi)


def format_symlog_growth_axis(ax: plt.Axes) -> None:
    linthresh = 5
    ax.set_yscale("symlog", linthresh=linthresh, linscale=1)
    ax.minorticks_on()
    ax.yaxis.set_minor_locator(
        SymmetricalLogLocator(
            base=10,
            linthresh=linthresh,
            subs=[2, 3, 4, 5, 6, 7, 8, 9],
        )
    )
    ax.grid(which="minor", axis="y", color="#cbd5e1", linewidth=0.45, alpha=0.35)


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
    set_plot_theme()
    palette = c9_palette()
    plot_data = with_plot_labels(data)
    plt.figure(figsize=(14, 7.5))
    ax = sns.lineplot(
        data=plot_data,
        x="year",
        y="budget_yi_yuan",
        hue="university_label",
        hue_order=c9_plot_order(),
        palette=palette,
        marker="o",
        linewidth=1.8,
    )

    fallback = plot_data[plot_data["source_type"].eq("third_party_ocr_fallback")]
    if not fallback.empty:
        sns.scatterplot(
            data=fallback,
            x="year",
            y="budget_yi_yuan",
            hue="university_label",
            hue_order=c9_plot_order(),
            palette=palette,
            marker="X",
            s=90,
            legend=False,
            ax=ax,
            edgecolor="white",
            linewidth=0.8,
        )

    ax.set_title("C9 University Annual Budget Trend (Official Sources Preferred)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Budget (100M CNY)")
    ax.set_xticks(sorted(data["year"].unique()))
    ax.legend(title="University", bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0, fontsize=8)
    ax.text(
        0.01,
        0.02,
        "Lines/points prefer official PDF/HTML values; X markers indicate third-party OCR fallback.",
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

    set_plot_theme()
    palette = c9_palette()
    plot_growth_data = with_plot_labels(growth)
    plt.figure(figsize=(14, 7.5))
    ax = sns.lineplot(
        data=plot_growth_data,
        x="year",
        y="growth_percent",
        hue="university_label",
        hue_order=c9_plot_order(),
        palette=palette,
        marker="o",
        linewidth=1.8,
    )
    fallback = plot_growth_data[plot_growth_data["source_type"].eq("third_party_ocr_fallback")]
    if not fallback.empty:
        sns.scatterplot(
            data=fallback,
            x="year",
            y="growth_percent",
            hue="university_label",
            hue_order=c9_plot_order(),
            palette=palette,
            marker="X",
            s=90,
            legend=False,
            ax=ax,
            edgecolor="white",
            linewidth=0.8,
    )

    ax.axhline(0, color="#475569", linewidth=1, linestyle="--")
    ax.set_title("C9 University Budget Year-over-Year Growth (Official Sources Preferred)")
    ax.set_xlabel("Year")
    ax.set_ylabel("YoY Growth (%)")
    ax.set_xticks(sorted(growth["year"].unique()))
    ax.legend(title="University", bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0, fontsize=8)
    ax.text(
        0.01,
        0.02,
        "Lines/points prefer official PDF/HTML values; X markers indicate third-party OCR fallback.",
        transform=ax.transAxes,
        fontsize=9,
        color="#475569",
    )
    plt.tight_layout()
    savefig_with_watermark(path)
    plt.close()
    return growth


def plot_growth_symlog(growth: pd.DataFrame, path: Path) -> None:
    set_plot_theme()
    palette = c9_palette()
    plot_growth_data = with_plot_labels(growth)
    plt.figure(figsize=(14, 7.5))
    ax = sns.lineplot(
        data=plot_growth_data,
        x="year",
        y="growth_percent",
        hue="university_label",
        hue_order=c9_plot_order(),
        palette=palette,
        marker="o",
        linewidth=1.8,
    )
    fallback = plot_growth_data[plot_growth_data["source_type"].eq("third_party_ocr_fallback")]
    if not fallback.empty:
        sns.scatterplot(
            data=fallback,
            x="year",
            y="growth_percent",
            hue="university_label",
            hue_order=c9_plot_order(),
            palette=palette,
            marker="X",
            s=90,
            legend=False,
            ax=ax,
            edgecolor="white",
            linewidth=0.8,
        )

    format_symlog_growth_axis(ax)
    ax.axhline(0, color="#475569", linewidth=1, linestyle="--")
    ax.set_title("C9 University Budget YoY Growth (Symlog, Official Sources Preferred)")
    ax.set_xlabel("Year")
    ax.set_ylabel("YoY Growth (%, symlog)")
    ax.set_xticks(sorted(growth["year"].unique()))
    ax.legend(title="University", bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0, fontsize=8)
    ax.text(
        0.01,
        0.02,
        "Symlog preserves negative growth; -5% to 5% is linear; X markers indicate third-party OCR fallback.",
        transform=ax.transAxes,
        fontsize=9,
        color="#475569",
    )
    plt.tight_layout()
    savefig_with_watermark(path)
    plt.close()


def plot_combined(data: pd.DataFrame, growth: pd.DataFrame, path: Path) -> None:
    set_plot_theme()
    palette = c9_palette()
    plot_data = with_plot_labels(data)
    plot_growth_data = with_plot_labels(growth)
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(15, 11),
        sharex=True,
        gridspec_kw={"height_ratios": [1.45, 1]},
    )

    trend_ax, growth_ax = axes
    sns.lineplot(
        data=plot_data,
        x="year",
        y="budget_yi_yuan",
        hue="university_label",
        hue_order=c9_plot_order(),
        palette=palette,
        marker="o",
        linewidth=1.8,
        ax=trend_ax,
    )
    fallback = plot_data[plot_data["source_type"].eq("third_party_ocr_fallback")]
    if not fallback.empty:
        sns.scatterplot(
            data=fallback,
            x="year",
            y="budget_yi_yuan",
            hue="university_label",
            hue_order=c9_plot_order(),
            palette=palette,
            marker="X",
            s=90,
            legend=False,
            ax=trend_ax,
            edgecolor="white",
            linewidth=0.8,
        )
    trend_ax.set_title("C9 University Annual Budget Trend and Year-over-Year Growth (Official Sources Preferred)")
    trend_ax.set_xlabel("")
    trend_ax.set_ylabel("Budget (100M CNY)")
    trend_ax.legend(title="University", bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0, fontsize=8)

    sns.lineplot(
        data=plot_growth_data,
        x="year",
        y="growth_percent",
        hue="university_label",
        hue_order=c9_plot_order(),
        palette=palette,
        marker="o",
        linewidth=1.8,
        legend=False,
        ax=growth_ax,
    )
    growth_fallback = plot_growth_data[plot_growth_data["source_type"].eq("third_party_ocr_fallback")]
    if not growth_fallback.empty:
        sns.scatterplot(
            data=growth_fallback,
            x="year",
            y="growth_percent",
            hue="university_label",
            hue_order=c9_plot_order(),
            palette=palette,
            marker="X",
            s=90,
            legend=False,
            ax=growth_ax,
            edgecolor="white",
            linewidth=0.8,
        )
    growth_ax.axhline(0, color="#475569", linewidth=1, linestyle="--")
    format_symlog_growth_axis(growth_ax)
    growth_ax.set_xlabel("Year")
    growth_ax.set_ylabel("YoY Growth (%, symlog)")
    growth_ax.set_xticks(sorted(data["year"].unique()))
    growth_ax.text(
        0.01,
        0.03,
        "Symlog growth axis; X = third-party OCR fallback.",
        transform=growth_ax.transAxes,
        fontsize=9,
        color="#475569",
    )

    fig.tight_layout(rect=(0.035, 0.035, 0.88, 0.98))
    savefig_with_watermark(path, center_fontsize=38, center_alpha=0.08)
    plt.close(fig)


def build_cagr(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ordered = data.sort_values(["university", "year"])
    for university, group in ordered.groupby("university", sort=False):
        valid = group.dropna(subset=["budget_yi_yuan"]).sort_values("year")
        if len(valid) < 2:
            continue

        start = valid.iloc[0]
        end = valid.iloc[-1]
        n_years = int(end["year"] - start["year"])
        if n_years <= 0 or start["budget_yi_yuan"] <= 0:
            continue

        observed_years = sorted(valid["year"].astype(int).tolist())
        expected_years = list(range(int(start["year"]), int(end["year"]) + 1))
        missing_years = sorted(set(expected_years) - set(observed_years))
        cagr = (end["budget_yi_yuan"] / start["budget_yi_yuan"]) ** (1 / n_years) - 1
        source_counts = valid["source_type"].value_counts().sort_index()
        source_summary = "; ".join(f"{source_type}={count}" for source_type, count in source_counts.items())
        rows.append(
            {
                "university": university,
                "start_year": int(start["year"]),
                "end_year": int(end["year"]),
                "start_budget_yi_yuan": round(float(start["budget_yi_yuan"]), 6),
                "end_budget_yi_yuan": round(float(end["budget_yi_yuan"]), 6),
                "n_years": n_years,
                "observed_year_count": len(observed_years),
                "missing_years": " ".join(str(year) for year in missing_years),
                "cagr": cagr,
                "cagr_percent": cagr * 100,
                "source_coverage_notes": source_summary,
            }
        )

    return pd.DataFrame(rows).sort_values("cagr_percent", ascending=False).reset_index(drop=True)


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
    cagr_path = OUT_DIR / "c9_budget_cagr_official_preferred.csv"
    growth_fig_path = FIG_DIR / "c9_budget_growth_official_preferred.png"
    growth_symlog_fig_path = FIG_DIR / "c9_budget_growth_symlog_official_preferred.png"
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
    plot_growth_symlog(growth, growth_symlog_fig_path)
    plot_combined(combined, growth, combined_fig_path)
    growth.to_csv(growth_csv_path, index=False, encoding="utf-8")
    (
        growth.pivot_table(index="year", columns="university", values="growth_percent", aggfunc="first")
        .reindex(columns=C9)
        .sort_index()
        .round(2)
        .to_csv(growth_pivot_path, encoding="utf-8")
    )
    build_cagr(combined).round({"cagr": 6, "cagr_percent": 3}).to_csv(cagr_path, index=False, encoding="utf-8")

    print(csv_path)
    print(pivot_path)
    print(source_pivot_path)
    print(fig_path)
    print(growth_csv_path)
    print(growth_pivot_path)
    print(cagr_path)
    print(growth_fig_path)
    print(growth_symlog_fig_path)
    print(combined_fig_path)
    print(combined.groupby(["university", "source_type"]).size().to_string())


if __name__ == "__main__":
    main()
