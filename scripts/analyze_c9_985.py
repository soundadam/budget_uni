#!/usr/bin/env python
"""Extract C9/985 budget subsets and plot budget changes."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_DIR / "data" / "interim" / "matplotlib"))

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


DATA_PATH = PROJECT_DIR / "data" / "processed" / "ministry_university_budget.csv"
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

C9_PLOT_ORDER = [university for university in C9 if university not in {"中国科学技术大学", "哈尔滨工业大学"}]
C9_PALETTE = dict(zip(C9_PLOT_ORDER, sns.color_palette("tab10", n_colors=len(C9_PLOT_ORDER))))

PROJECT_985 = [
    "北京大学", "清华大学", "中国人民大学", "北京师范大学", "北京航空航天大学", "北京理工大学",
    "中国农业大学", "中央民族大学", "南开大学", "天津大学", "大连理工大学", "东北大学",
    "吉林大学", "哈尔滨工业大学", "复旦大学", "同济大学", "上海交通大学", "华东师范大学",
    "南京大学", "东南大学", "浙江大学", "中国科学技术大学", "厦门大学", "山东大学",
    "中国海洋大学", "武汉大学", "华中科技大学", "湖南大学", "中南大学", "国防科技大学",
    "中山大学", "华南理工大学", "四川大学", "电子科技大学", "重庆大学", "西安交通大学",
    "西北工业大学", "西北农林科技大学", "兰州大学",
]


def savefig_with_watermark(path: Path, dpi: int = 200) -> None:
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


def plot_line(
    data: pd.DataFrame,
    title: str,
    path: Path,
    figsize: tuple[int, int],
    hue_order: list[str] | None = None,
    palette: dict[str, tuple[float, float, float]] | None = None,
    legend_cols: int = 1,
) -> None:
    plt.figure(figsize=figsize)
    ax = sns.lineplot(
        data=data,
        x="year",
        y="budget_yi_yuan",
        hue="university",
        hue_order=hue_order,
        palette=palette,
        marker="o",
        linewidth=1.8,
    )
    ax.set_title(title)
    ax.set_xlabel("年份")
    ax.set_ylabel("经费（亿元）")
    ax.set_xticks(sorted(data["year"].unique()))
    ax.legend(
        title="高校",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        borderaxespad=0,
        ncol=legend_cols,
        fontsize=8,
    )
    plt.tight_layout()
    savefig_with_watermark(path)
    plt.close()


def plot_growth(
    data: pd.DataFrame,
    path: Path,
    hue_order: list[str] | None = None,
    palette: dict[str, tuple[float, float, float]] | None = None,
) -> pd.DataFrame:
    growth = data.sort_values(["university", "year"]).copy()
    growth["growth_rate"] = growth.groupby("university")["budget_yi_yuan"].pct_change()
    growth["growth_percent"] = growth["growth_rate"] * 100
    growth = growth.dropna(subset=["growth_percent"])

    plt.figure(figsize=(13, 7))
    ax = sns.lineplot(
        data=growth,
        x="year",
        y="growth_percent",
        hue="university",
        hue_order=hue_order,
        palette=palette,
        marker="o",
        linewidth=1.8,
    )
    ax.axhline(0, color="#475569", linewidth=1, linestyle="--")
    ax.set_title("C9高校年度预算同比增速")
    ax.set_xlabel("年份")
    ax.set_ylabel("同比增速（%）")
    ax.set_xticks(sorted(growth["year"].unique()))
    ax.legend(title="高校", bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0, fontsize=8)
    plt.tight_layout()
    savefig_with_watermark(path)
    plt.close()
    return growth


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    (PROJECT_DIR / "data" / "interim" / "matplotlib").mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_PATH)
    df["budget_yi_yuan"] = pd.to_numeric(df["budget_yi_yuan"], errors="coerce")

    c9 = df[df["university"].isin(C9)].copy()
    c9["group"] = "C9"
    c9_missing = sorted(set(C9) - set(c9["university"]))
    c9.to_csv(OUT_DIR / "c9_budget.csv", index=False, encoding="utf-8")

    project_985 = df[df["university"].isin(PROJECT_985)].copy()
    project_985["group"] = "985"
    missing_985 = sorted(set(PROJECT_985) - set(project_985["university"]))
    project_985.to_csv(OUT_DIR / "project_985_budget.csv", index=False, encoding="utf-8")

    sns.set_theme(style="whitegrid", font="Arial Unicode MS")
    c9_plot_order = [university for university in C9_PLOT_ORDER if university in set(c9["university"])]
    c9_palette = {university: C9_PALETTE[university] for university in c9_plot_order}
    fig_path = FIG_DIR / "c9_budget_trend.png"
    plot_line(c9, "C9高校年度预算变化", fig_path, (13, 7), hue_order=c9_plot_order, palette=c9_palette)

    c9_growth_fig_path = FIG_DIR / "c9_budget_growth_rate.png"
    c9_growth = plot_growth(c9, c9_growth_fig_path, hue_order=c9_plot_order, palette=c9_palette)
    c9_growth.to_csv(OUT_DIR / "c9_budget_growth_rate.csv", index=False, encoding="utf-8")
    (
        c9_growth.pivot_table(index="year", columns="university", values="growth_percent", aggfunc="first")
        .sort_index()
        .round(2)
        .to_csv(OUT_DIR / "c9_budget_growth_rate_pivot.csv", encoding="utf-8")
    )

    summary = (
        c9.pivot_table(index="year", columns="university", values="budget_yi_yuan", aggfunc="first")
        .sort_index()
        .round(2)
    )
    summary.to_csv(OUT_DIR / "c9_budget_pivot.csv", encoding="utf-8")

    project_985_summary = (
        project_985.pivot_table(index="university", columns="year", values="budget_yi_yuan", aggfunc="first")
        .reindex(PROJECT_985)
        .dropna(how="all")
        .round(2)
    )
    project_985_summary.to_csv(OUT_DIR / "project_985_budget_pivot.csv", encoding="utf-8")

    plt.figure(figsize=(12, 14))
    ax = sns.heatmap(project_985_summary, cmap="YlGnBu", linewidths=0.35, linecolor="#e5e7eb")
    ax.set_title("985高校年度预算热力图")
    ax.set_xlabel("年份")
    ax.set_ylabel("高校")
    plt.tight_layout()
    project_985_heatmap_path = FIG_DIR / "project_985_budget_heatmap.png"
    savefig_with_watermark(project_985_heatmap_path)
    plt.close()

    counts = c9.groupby("university").size().sort_index()
    count_lines = ["| 高校 | 记录数 |", "| --- | ---: |"]
    count_lines.extend(f"| {university} | {count} |" for university, count in counts.items())

    notes = [
        "# C9 与 985 提取说明",
        "",
        f"- C9 明细：`{(OUT_DIR / 'c9_budget.csv').relative_to(PROJECT_DIR)}`",
        f"- C9 透视表：`{(OUT_DIR / 'c9_budget_pivot.csv').relative_to(PROJECT_DIR)}`",
        f"- C9 折线图：`{fig_path.relative_to(PROJECT_DIR)}`",
        f"- C9 增速明细：`{(OUT_DIR / 'c9_budget_growth_rate.csv').relative_to(PROJECT_DIR)}`",
        f"- C9 增速透视表：`{(OUT_DIR / 'c9_budget_growth_rate_pivot.csv').relative_to(PROJECT_DIR)}`",
        f"- C9 增速图：`{c9_growth_fig_path.relative_to(PROJECT_DIR)}`",
        f"- 985 明细：`{(OUT_DIR / 'project_985_budget.csv').relative_to(PROJECT_DIR)}`",
        f"- 985 透视表：`{(OUT_DIR / 'project_985_budget_pivot.csv').relative_to(PROJECT_DIR)}`",
        f"- 985 热力图：`{project_985_heatmap_path.relative_to(PROJECT_DIR)}`",
        "- 985 折线 trend 图线条过密，当前先不作为默认产物生成。",
        "",
        "## 口径提醒",
        "",
        "- 当前主表来自教育部直属高校预算抽取，budget_yi_yuan 只取年度预算列。",
        "- 2016 原图同时含年度预算、年度收入合计、年度支出合计，收入/支出另存于 ministry_university_financial_table.csv。",
        "- 2017 决算图已单独保存为 ministry_university_final_accounts.csv，未进入预算主表。",
        "- 2020、2023 决算口径未进入主表。",
        "- 2025/2026 原图含教育部、工信部、中国科学院，主表已按名称排除工信部/中科院高校。",
        "- 因此 C9 中中国科学技术大学、哈尔滨工业大学目前不在主表中。",
        "",
        "## 缺失名单",
        "",
        "C9 缺失：" + ("、".join(c9_missing) if c9_missing else "无"),
        "",
        "985 缺失：" + ("、".join(missing_985) if missing_985 else "无"),
        "",
        "## C9 记录数",
        "",
        "\n".join(count_lines),
    ]
    (OUT_DIR / "c9_985_summary.md").write_text("\n".join(notes) + "\n", encoding="utf-8")

    print(f"C9 rows: {len(c9)}")
    print(f"985 rows: {len(project_985)}")
    print(f"C9 missing: {', '.join(c9_missing) if c9_missing else 'none'}")
    print(f"985 missing: {', '.join(missing_985) if missing_985 else 'none'}")
    print(fig_path)
    print(c9_growth_fig_path)
    print(project_985_heatmap_path)


if __name__ == "__main__":
    main()
