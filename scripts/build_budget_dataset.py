#!/usr/bin/env python
"""Build interim and processed budget CSV files from OCR outputs."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from process_strip_ocr import compute_global_coords, group_into_rows, process_2017, process_2022, write_csv


PROJECT_DIR = Path(__file__).resolve().parents[1]
OCR_DIR = PROJECT_DIR / "data" / "interim" / "ocr"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
FINAL_CSV = PROCESSED_DIR / "ministry_university_budget.csv"
FINAL_ACCOUNTS_CSV = PROCESSED_DIR / "ministry_university_final_accounts.csv"
FINANCIAL_TABLE_CSV = PROCESSED_DIR / "ministry_university_financial_table.csv"
REPORT_MD = PROCESSED_DIR / "extraction_report.md"

FIELDNAMES = [
    "year",
    "rank",
    "university",
    "budget_original",
    "budget_unit",
    "budget_yi_yuan",
    "source_image",
    "source_url",
    "extraction_method",
    "verified",
    "notes",
]

FINANCIAL_FIELDNAMES = [
    "year",
    "rank",
    "university",
    "annual_budget_yi_yuan",
    "current_year_income_yi_yuan",
    "income_total_yi_yuan",
    "annual_income_total_yi_yuan",
    "annual_expenditure_total_yi_yuan",
    "prior_year_budget_yi_yuan",
    "change_yi_yuan",
    "change_ratio",
    "fiscal_appropriation_income_yi_yuan",
    "fiscal_appropriation_ratio",
    "department",
    "province",
    "source_image",
    "source_url",
    "extraction_method",
    "verified",
    "notes",
]

BUDGET_VALUE_INDEX = {
    2023: 1,  # 2023 图为“本年收入/收入总计”，预算趋势应取“收入总计”。
}

FINANCIAL_PROFILES = {
    2017: ("strip", "2017_budget", "paddleocr_strip", "budget_income_expenditure"),
    2018: ("strip", "2018_budget", "paddleocr_strip", "budget_income_expenditure"),
    2019: ("ocr", None, "paddleocr_row", "budget_fiscal"),
    2020: ("strip", "2020_budget", "paddleocr_strip", "budget_prior_change"),
    2021: ("ocr", None, "paddleocr_row", "budget_change_ratio"),
    2022: ("strip", "2022", "paddleocr_strip", "budget_current_income_dept"),
    2023: ("strip", "2023_budget", "paddleocr_strip", "current_income_total"),
    2024: ("ocr", None, "paddleocr_row", "budget_prior_change_ratio"),
    2025: ("ocr", None, "paddleocr_row", "budget_current_income_prior"),
    2026: ("ocr", None, "paddleocr_row", "budget_current_income_prior"),
}

VALUE_OVERRIDES = {
    (2018, "同济大学"): {
        "annual_budget": 134.21,
        "annual_income_total": 109.75,
        "annual_expenditure_total": 107.21,
        "notes": "OCR漏识别预算总经费134.21; 已按原图补入",
    },
}

TABLE_2016 = [
    (1, "清华大学", 182.17, 139.03, 142.17),
    (2, "浙江大学", 154.28, 106.66, 85.36),
    (3, "北京大学", 153.11, 118.86, 120.25),
    (4, "上海交通大学", 118.03, 90.25, 91.03),
    (5, "复旦大学", 78.80, 46.82, 50.55),
    (6, "武汉大学", 78.23, 51.16, 59.68),
    (7, "山东大学", 77.28, 62.45, 63.62),
    (8, "中山大学", 73.96, 73.96, 73.96),
    (9, "华中科技大学", 70.47, 50.84, 54.43),
    (10, "天津大学", 70.31, 54.07, 59.86),
    (11, "四川大学", 63.25, 45.65, 48.25),
    (12, "同济大学", 60.07, 40.85, 44.00),
    (13, "南京大学", 57.02, 32.18, 38.24),
    (14, "西安交通大学", 56.37, 40.63, 40.88),
    (15, "厦门大学", 55.79, 45.67, 48.29),
    (16, "北京师范大学", 53.67, 35.72, 53.67),
    (17, "吉林大学", 52.19, 50.62, 52.19),
    (18, "南开大学", 51.81, 45.72, 45.81),
    (19, "华南理工大学", 51.79, 37.00, 37.29),
    (20, "东南大学", 51.20, 32.82, 33.20),
    (21, "中南大学", 50.12, 38.89, 40.12),
    (22, "大连理工大学", 45.02, 30.29, 32.76),
    (23, "中国人民大学", 43.55, 33.78, 37.84),
    (24, "华东师范大学", 42.35, 33.08, 34.02),
    (25, "武汉理工大学", 41.51, 31.60, 31.61),
    (26, "东北大学", 40.54, 29.52, 30.03),
    (27, "重庆大学", 39.60, 36.10, 36.10),
    (28, "电子科技大学", 37.71, 25.71, 26.21),
    (29, "北京交通大学", 37.07, 23.53, 28.64),
    (30, "中国地质大学（武汉）", 34.62, 27.24, 28.92),
    (31, "中国矿业大学", 33.46, 19.39, 25.24),
    (32, "中国石油大学（华东）", 33.11, 21.38, 21.51),
    (33, "北京科技大学", 33.00, 21.76, 23.30),
    (34, "中国石油大学（北京）", 32.67, 14.91, 16.45),
    (35, "兰州大学", 32.43, 25.98, 26.03),
    (36, "西南大学", 32.39, 31.60, 32.39),
    (37, "湖南大学", 32.03, 23.55, 25.03),
    (38, "西南交通大学", 30.64, 28.82, 30.64),
    (39, "北京化工大学", 30.07, 23.49, 24.02),
    (40, "西北农林科技大学", 29.73, 23.36, 24.57),
    (41, "河海大学", 28.88, 19.99, 21.08),
    (42, "西安电子科技大学", 28.28, 20.86, 20.72),
    (43, "南京农业大学", 27.46, 19.00, 22.97),
    (44, "华中农业大学", 27.05, 18.81, 21.60),
    (45, "华北电力大学", 27.00, 19.67, 19.49),
    (46, "合肥工业大学", 26.63, 19.52, 20.60),
    (47, "长安大学", 26.53, 19.61, 19.61),
    (48, "中国海洋大学", 24.74, 19.45, 24.74),
    (49, "华中师范大学", 24.45, 20.00, 23.95),
    (50, "江南大学", 23.22, 18.27, 20.72),
    (51, "北京邮电大学", 22.55, 19.75, 22.55),
    (52, "东北师范大学", 22.36, 19.39, 19.62),
    (53, "中国地质大学（北京）", 20.85, 11.88, 13.45),
    (54, "中南财经政法大学", 20.16, 13.79, 19.46),
    (55, "东华大学", 19.58, 15.90, 15.90),
    (56, "陕西师范大学", 17.41, 16.13, 16.17),
    (57, "对外经济贸易大学", 16.07, 11.91, 15.47),
    (58, "北京林业大学", 15.67, 15.57, 14.87),
    (59, "东北林业大学", 14.84, 12.83, 12.88),
    (60, "北京中医药大学", 14.52, 8.57, 11.96),
    (61, "中国药科大学", 14.12, 11.02, 11.02),
    (62, "上海财经大学", 13.16, 11.38, 12.28),
    (63, "中国矿业大学（北京）", 12.31, 7.36, 7.76),
    (64, "中国传媒大学", 11.92, 11.08, 11.03),
    (65, "中央财经大学", 11.36, 10.56, 10.60),
    (66, "北京外国语大学", 10.18, 9.95, 10.01),
    (67, "北京语言大学", 10.15, 7.60, 9.83),
    (68, "中国政法大学", 9.91, 9.77, 9.91),
    (69, "上海外国语大学", 9.02, 8.74, 8.86),
    (70, "中央音乐学院", 4.20, 3.96, 4.20),
    (71, "中央戏剧学院", 3.05, 2.47, 3.05),
]

SOURCE_URLS = {
    2016: "",
    2017: "https://www.edu.cn/ke_yan_yu_fa_zhan/gao_xiao_cheng_guo/gao_xiao_zi_xun/201808/t20180813_1620842.shtml",
    2018: "https://www.antpedia.com/news/99/n-2161799.html",
    2019: "https://www.sohu.com/a/311077070_503494",
    2020: "https://www.eol.cn/shuju/uni/202108/t20210805_2143174.shtml",
    2021: "https://m.mp.oeeee.com/a/BAAFRD000020210414468623.html",
    2023: "https://cacsc.com.cn/2024/2023年教育部直属高校预算汇总.html?utm_source=chatgpt.com",
    2024: "https://zhuanlan.zhihu.com/p/693822580",
    2025: "https://news.qq.com/rain/a/20250418A08R7100",
    2026: "",
}

SOURCE_IMAGES = {
    2016: "2016.jpg",
    2017: "2017.png",
    2018: "2018.jpeg",
    2019: "2019.jpg",
    2020: "2020预算.jpg",
    2021: "2021.png",
    2022: "2022.jpg",
    2023: "2023.webp",
    2024: "2024.png",
    2025: "2025.webp",
    2026: "2026.png",
}

MIIT_UNIS = {
    "哈尔滨工业大学",
    "北京航空航天大学",
    "北京理工大学",
    "西北工业大学",
    "南京航空航天大学",
    "南京理工大学",
    "哈尔滨工程大学",
}
CAS_UNIS = {"中国科学技术大学", "中国科学院大学"}
EXCLUDE_UNIS = MIIT_UNIS | CAS_UNIS


def parse_ocr_rows(year: int, y_tolerance: float = 20) -> list[list[str]]:
    path = OCR_DIR / f"{year}_paddleocr.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    entries: list[dict] = []
    for page in data["raw_result"]:
        if not page:
            continue
        for block in page:
            if not block:
                continue
            bbox = block[0]
            text, confidence = block[1]
            entries.append({"bbox": bbox, "text": text, "confidence": confidence})
    entries.sort(key=lambda e: e["bbox"][0][1])

    rows: list[list[dict]] = []
    current: list[dict] = []
    current_y: float | None = None
    for entry in entries:
        y = entry["bbox"][0][1]
        if current_y is None or abs(y - current_y) <= y_tolerance:
            current.append(entry)
            current_y = y if current_y is None else current_y
        else:
            current.sort(key=lambda e: e["bbox"][0][0])
            rows.append(current)
            current = [entry]
            current_y = y
    if current:
        current.sort(key=lambda e: e["bbox"][0][0])
        rows.append(current)
    return [[e["text"].strip() for e in row if e["text"].strip()] for row in rows]


def parse_strip_rows(key: str, y_tolerance: float = 18) -> list[list[str]]:
    path = OCR_DIR / "crops" / f"{key}_strip_ocr.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = group_into_rows(compute_global_coords(raw), y_tolerance=y_tolerance)
    return [[e["text"].strip() for e in row if e["text"].strip()] for row in rows]


def normalize_name(text: str) -> str:
    text = text.strip()
    text = text.replace(" ", "")
    text = text.replace("(", "（").replace(")", "）")
    text = text.replace("°", "").replace("家", "")
    text = text.replace("董庆大学", "重庆大学")
    text = text.replace("青华大学", "清华大学")
    text = text.replace("华南理工大字", "华南理工大学")
    text = text.replace("中国矿业业大学", "中国矿业大学")
    text = text.replace("华中农业业大学", "华中农业大学")
    text = re.sub(r"^[wW.]+", "", text)
    text = re.sub(r"[h°念m。)]+$", "", text)
    return text


def split_rank_name(cell: str) -> tuple[int | None, str | None]:
    clean = cell.strip().replace("#", "").replace("S", "5")
    match = re.match(r"^(\d{1,3})\s*(.+)$", clean)
    if not match:
        return None, None
    rank = int(match.group(1))
    name = normalize_name(match.group(2))
    if is_university_name(name):
        return rank, name
    return None, None


def is_university_name(text: str) -> bool:
    return any(token in text for token in ("大学", "学院", "学校"))


def extract_name(cells: list[str]) -> str | None:
    normalized = [normalize_name(c) for c in cells]
    for i, cell in enumerate(normalized):
        rank, embedded_name = split_rank_name(cell)
        if embedded_name:
            return embedded_name
        if cell == "中国矿业" and i + 1 < len(normalized) and normalized[i + 1] == "业大学":
            return "中国矿业大学"
        if cell == "华中农业" and i + 1 < len(normalized) and normalized[i + 1] == "业大学":
            return "华中农业大学"
        if cell in {"中国科学院"}:
            continue
        if is_university_name(cell):
            return cell
    return None


def smooth_rank(rank: int | None, last_rank: int, notes: str) -> tuple[int | None, str]:
    if rank is None or last_rank <= 0:
        return rank, notes
    if rank > last_rank + 5 or rank < last_rank - 3:
        fixed = last_rank + 1
        note = f"rank OCR疑似为{rank}，按行序校正为{fixed}"
        notes = (notes + "; " if notes else "") + note
        return fixed, notes
    return rank, notes


def extract_rank(cells: list[str], fallback: int | None) -> int | None:
    for cell in cells:
        rank, _ = split_rank_name(cell)
        if rank is not None and 1 <= rank <= 120:
            return rank
        clean = cell.strip().replace("#", "").replace("S", "5")
        if clean.isdigit() and 1 <= int(clean) <= 120:
            return int(clean)
    return fallback


def parse_number_token(text: str) -> float | None:
    clean = text.strip()
    clean = clean.replace("，", ".").replace("．", ".").replace(" ", "")
    clean = clean.replace("W", "").replace("w", "").replace("小", "")
    clean = clean.replace("L", "1").replace("l", "1")
    clean = clean.replace("'", ".").replace("。", "")
    match = re.search(r"-?\d+(?:\.\d+)?", clean)
    if not match:
        return None
    token = match.group()
    try:
        value = float(token)
    except ValueError:
        return None
    if "." not in token and value >= 1000:
        value = value / 100
        if value > 250:
            value = value / 10
    return round(value, 2)


def cells_after_name(cells: list[str], name: str) -> list[str]:
    normalized_name = normalize_name(name)
    normalized = [normalize_name(c) for c in cells]
    for i, cell in enumerate(normalized):
        _, embedded_name = split_rank_name(cell)
        if embedded_name == normalized_name:
            return cells[i + 1 :]
        if cell == normalized_name:
            return cells[i + 1 :]
        if (
            normalized_name == "中国矿业大学"
            and cell == "中国矿业"
            and i + 1 < len(normalized)
            and normalized[i + 1] == "业大学"
        ):
            return cells[i + 2 :]
        if (
            normalized_name == "华中农业大学"
            and cell == "华中农业"
            and i + 1 < len(normalized)
            and normalized[i + 1] == "业大学"
        ):
            return cells[i + 2 :]
    return cells


def numeric_values(cells: list[str]) -> list[float]:
    values: list[float] = []
    for cell in cells:
        value = parse_number_token(cell)
        if value is not None:
            values.append(value)
    return values


def first_budget_value(cells: list[str], rank: int | None) -> tuple[float | None, str]:
    values = numeric_values(cells)
    candidates = [v for v in values if v > 1 and (rank is None or abs(v - rank) > 1e-9)]
    candidates = [v for v in candidates if v < 500]
    if not candidates:
        return None, "未识别到预算金额"
    return candidates[0], ""


def nth_budget_value(cells: list[str], rank: int | None, index: int = 0) -> tuple[float | None, str]:
    values = numeric_values(cells)
    candidates = [v for v in values if v > 1 and (rank is None or abs(v - rank) > 1e-9)]
    candidates = [v for v in candidates if v < 500]
    if len(candidates) <= index:
        return None, "未识别到预算金额"
    return candidates[index], ""


def make_row(year: int, rank: int | None, name: str, budget: float, method: str, notes: str = "") -> dict:
    return {
        "year": year,
        "rank": rank,
        "university": normalize_name(name),
        "budget_original": f"{budget:.2f}亿元",
        "budget_unit": "亿元",
        "budget_yi_yuan": f"{budget:.2f}",
        "source_image": SOURCE_IMAGES[year],
        "source_url": SOURCE_URLS.get(year, ""),
        "extraction_method": method,
        "verified": False,
        "notes": notes,
    }


def make_financial_row(
    year: int,
    rank: int | None,
    name: str,
    annual_budget: float | str = "",
    current_year_income: float | str = "",
    income_total: float | str = "",
    annual_income_total: float | str = "",
    annual_expenditure_total: float | str = "",
    prior_year_budget: float | str = "",
    change: float | str = "",
    change_ratio: str = "",
    fiscal_appropriation_income: float | str = "",
    fiscal_appropriation_ratio: str = "",
    department: str = "",
    province: str = "",
    method: str = "paddleocr_row",
    verified: bool = False,
    notes: str = "",
) -> dict:
    def fmt(value: float | str) -> str:
        return f"{value:.2f}" if isinstance(value, float) else value

    return {
        "year": year,
        "rank": rank,
        "university": normalize_name(name),
        "annual_budget_yi_yuan": fmt(annual_budget),
        "current_year_income_yi_yuan": fmt(current_year_income),
        "income_total_yi_yuan": fmt(income_total),
        "annual_income_total_yi_yuan": fmt(annual_income_total),
        "annual_expenditure_total_yi_yuan": fmt(annual_expenditure_total),
        "prior_year_budget_yi_yuan": fmt(prior_year_budget),
        "change_yi_yuan": fmt(change),
        "change_ratio": change_ratio,
        "fiscal_appropriation_income_yi_yuan": fmt(fiscal_appropriation_income),
        "fiscal_appropriation_ratio": fiscal_appropriation_ratio,
        "department": department,
        "province": province,
        "source_image": SOURCE_IMAGES[year],
        "source_url": SOURCE_URLS.get(year, ""),
        "extraction_method": method,
        "verified": verified,
        "notes": notes,
    }


def process_2016_financial_table() -> list[dict]:
    return [
        make_financial_row(
            2016,
            rank,
            name,
            annual_budget,
            annual_income_total=annual_income_total,
            annual_expenditure_total=annual_expenditure_total,
            method="manual_from_source_image",
            notes="2016原表含年度预算数、年度收入合计、年度支出合计; 主表budget_yi_yuan取年度预算数",
        )
        for rank, name, annual_budget, annual_income_total, annual_expenditure_total in TABLE_2016
    ]


def process_2016_budget_rows() -> list[dict]:
    rows = []
    for rank, name, annual_budget, annual_income_total, _ in TABLE_2016:
        note = ""
        if name == "北京交通大学":
            note = f"已区分2016年度预算数与年度收入合计; 收入合计为{annual_income_total:.2f}亿元"
        rows.append(make_row(2016, rank, name, annual_budget, "manual_from_source_image", note))
    return rows


def budget_rows_to_financial_rows(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        out.append(
            make_financial_row(
                int(row["year"]),
                int(row["rank"]) if str(row.get("rank", "")).strip() else None,
                str(row["university"]),
                float(row["budget_yi_yuan"]),
                method=str(row["extraction_method"]),
                verified=str(row["verified"]) == "True",
                notes="当前原图只抽取年度预算列; 收入/支出列为空"
                + (f"; {row['notes']}" if str(row.get("notes", "")).strip() else ""),
            )
        )
    return out


def ratio_value(cells: list[str]) -> str:
    for cell in cells:
        if "%" in cell:
            return cell.strip().replace(" ", "")
    return ""


def text_value(cells: list[str], keywords: tuple[str, ...]) -> str:
    for cell in cells:
        clean = cell.strip()
        if any(keyword in clean for keyword in keywords):
            return clean
    return ""


def make_financial_from_cells(
    year: int,
    rank: int | None,
    name: str,
    values: list[float],
    cells: list[str],
    profile: str,
    method: str,
    notes: str = "",
) -> dict:
    kwargs: dict[str, float | str] = {}
    if profile == "budget_income_expenditure":
        kwargs["annual_budget"] = values[0] if len(values) > 0 else ""
        kwargs["annual_income_total"] = values[1] if len(values) > 1 else ""
        kwargs["annual_expenditure_total"] = values[2] if len(values) > 2 else ""
    elif profile == "budget_fiscal":
        kwargs["annual_budget"] = values[0] if len(values) > 0 else ""
        kwargs["fiscal_appropriation_income"] = values[1] if len(values) > 1 else ""
        kwargs["fiscal_appropriation_ratio"] = ratio_value(cells)
    elif profile == "budget_prior_change":
        kwargs["annual_budget"] = values[0] if len(values) > 0 else ""
        kwargs["prior_year_budget"] = values[1] if len(values) > 1 else ""
        kwargs["change"] = values[2] if len(values) > 2 else ""
    elif profile == "budget_change_ratio":
        kwargs["annual_budget"] = values[0] if len(values) > 0 else ""
        kwargs["change"] = values[1] if len(values) > 1 else ""
        kwargs["change_ratio"] = ratio_value(cells)
    elif profile == "budget_current_income_dept":
        kwargs["annual_budget"] = values[0] if len(values) > 0 else ""
        kwargs["current_year_income"] = values[1] if len(values) > 1 else ""
        kwargs["department"] = text_value(cells, ("教育部", "工业和信息化部", "中国科学院", "国家民委", "交通运输部"))
        kwargs["province"] = text_value(cells, ("省", "市", "自治区"))
    elif profile == "current_income_total":
        kwargs["current_year_income"] = values[0] if len(values) > 0 else ""
        kwargs["income_total"] = values[1] if len(values) > 1 else ""
        kwargs["annual_budget"] = values[1] if len(values) > 1 else ""
    elif profile == "budget_prior_change_ratio":
        kwargs["annual_budget"] = values[0] if len(values) > 0 else ""
        kwargs["prior_year_budget"] = values[1] if len(values) > 1 else ""
        kwargs["change"] = values[2] if len(values) > 2 else ""
        kwargs["change_ratio"] = ratio_value(cells)
    elif profile == "budget_current_income_prior":
        kwargs["annual_budget"] = values[0] if len(values) > 0 else ""
        kwargs["current_year_income"] = values[1] if len(values) > 1 else ""
        kwargs["prior_year_budget"] = values[2] if len(values) > 2 else ""

    override = VALUE_OVERRIDES.get((year, normalize_name(name)))
    if override:
        notes = (notes + "; " if notes else "") + str(override.get("notes", ""))
        kwargs.update({k: v for k, v in override.items() if k != "notes"})

    return make_financial_row(year, rank, name, method=method, notes=notes, **kwargs)


def financial_rows_from_ocr(year: int) -> list[dict]:
    mode, key, method, profile = FINANCIAL_PROFILES[year]
    rows = parse_strip_rows(str(key)) if mode == "strip" else parse_ocr_rows(year)
    results: list[dict] = []
    last_rank = 0
    for cells in rows:
        joined = "".join(cells)
        if any(word in joined for word in ("预算汇总", "预算经费", "排名学校", "收入总预算", "序号", "数据说明", "教育部、工信部、中国科学院", "直属高校", "大学名称", "部门预算")):
            continue
        if any(word in joined for word in ("微信公", "www.cing", "vww.cingt", "青塔", "cingta.com")):
            cells = [c for c in cells if not any(noise in c for noise in ("微信", "www", "vww", "cingt", "青塔"))]
        name = extract_name(cells)
        if not name:
            continue
        if year in {2025, 2026} and name in EXCLUDE_UNIS:
            continue
        if year == 2022:
            dept = text_value(cells, ("教育部", "工业和信息化部", "中国科学院", "国家民委", "交通运输部"))
            if dept and "教育部" not in dept:
                continue
            if name in EXCLUDE_UNIS:
                continue

        rank = extract_rank(cells, last_rank + 1 if last_rank else 1)
        rank, rank_note = smooth_rank(rank, last_rank, "")
        values = numeric_values(cells_after_name(cells, name))
        if not values:
            continue
        row = make_financial_from_cells(year, rank, name, values, cells, profile, str(method), rank_note)
        results.append(row)
        if rank:
            last_rank = max(last_rank, rank)
    return dedupe(results)


def build_financial_rows(by_year: dict[int, list[dict]]) -> list[dict]:
    rows = process_2016_financial_table()
    for year in sorted(by_year):
        if year == 2016:
            continue
        if year in FINANCIAL_PROFILES:
            allowed = {(int(r["year"]), normalize_name(str(r["university"]))) for r in by_year[year]}
            extracted = [
                r
                for r in financial_rows_from_ocr(year)
                if (int(r["year"]), normalize_name(str(r["university"]))) in allowed
            ]
            present = {(int(r["year"]), normalize_name(str(r["university"]))) for r in extracted}
            missing_budget_rows = [
                r
                for r in by_year[year]
                if (int(r["year"]), normalize_name(str(r["university"]))) not in present
            ]
            rows.extend(extracted)
            rows.extend(budget_rows_to_financial_rows(missing_budget_rows))
        else:
            rows.extend(budget_rows_to_financial_rows(by_year[year]))
    return rows


def rows_to_budget_results(
    rows: list[list[str]],
    year: int,
    method: str,
    extra_note: str = "",
    smooth: bool = True,
    budget_value_index: int = 0,
) -> list[dict]:
    results: list[dict] = []
    last_rank = 0
    pending_2021_music = False

    for cells in rows:
        joined = "".join(cells)
        if any(word in joined for word in ("预算汇总", "预算经费", "排名学校", "收入总预算", "序号", "数据说明", "教育部、工信部、中国科学院", "直属高校", "大学名称", "部门预算")):
            continue

        if any(word in joined for word in ("微信公", "www.cing", "vww.cingt", "青塔", "cingta.com")):
            cells = [c for c in cells if not any(noise in c for noise in ("微信", "www", "vww", "cingt", "青塔"))]
            joined = "".join(cells)
        if year == 2021 and "中央音乐学院" in joined and "中央美术学院" in joined:
            results.append(make_row(year, 73, "中央美术学院", 8.99, "paddleocr_row", "OCR行内混入中央音乐学院; 按上下文拆分"))
            pending_2021_music = True
            last_rank = 73
            continue
        if year == 2021 and pending_2021_music:
            amount, note = first_budget_value(cells, 74)
            if amount:
                results.append(make_row(year, 74, "中央音乐学院", amount, "paddleocr_row", "OCR上一行混排; 按上下文拆分"))
                last_rank = 74
            pending_2021_music = False
            continue

        name = extract_name(cells)
        if not name:
            continue
        if year in {2025, 2026} and name in EXCLUDE_UNIS:
            continue

        rank = extract_rank(cells, last_rank + 1 if last_rank else 1)
        rank_note = ""
        if smooth:
            rank, rank_note = smooth_rank(rank, last_rank, "")
        amount, note = nth_budget_value(cells_after_name(cells, name), rank, budget_value_index)
        if amount is None:
            continue
        if (year, normalize_name(name)) in VALUE_OVERRIDES and "annual_budget" in VALUE_OVERRIDES[(year, normalize_name(name))]:
            override = VALUE_OVERRIDES[(year, normalize_name(name))]
            amount = float(override["annual_budget"])
            note = (note + "; " if note else "") + str(override.get("notes", ""))
        if rank_note:
            note = (note + "; " if note else "") + rank_note

        if year in {2025, 2026} and amount < 80 and rank and rank <= 25:
            note = (note + "; " if note else "") + "高排名金额偏低，疑似OCR缺位，需人工复核"
        if amount < 3 and rank and rank <= 70:
            note = (note + "; " if note else "") + "金额异常偏低，疑似OCR缺位，需人工复核"
        if extra_note:
            note = (note + "; " if note else "") + extra_note
        results.append(make_row(year, rank, name, amount, method, note))
        if rank:
            last_rank = max(last_rank, rank)
    return dedupe(results)


def simple_year_rows(year: int, extra_note: str = "") -> list[dict]:
    return rows_to_budget_results(
        parse_ocr_rows(year),
        year,
        "paddleocr_row",
        extra_note,
        budget_value_index=BUDGET_VALUE_INDEX.get(year, 0),
    )


def strip_year_rows(year: int, key: str, extra_note: str = "") -> list[dict]:
    return rows_to_budget_results(
        parse_strip_rows(key),
        year,
        "paddleocr_strip",
        extra_note,
        budget_value_index=BUDGET_VALUE_INDEX.get(year, 0),
    )


def process_2019() -> list[dict]:
    rows = parse_ocr_rows(2019)
    results: list[dict] = []
    last_rank = 0
    pending_name: str | None = None
    for cells in rows:
        joined = "".join(cells)
        if any(word in joined for word in ("预算经费", "预算总经费", "财政拨款", "占比")):
            continue

        name = extract_name(cells)
        rank = extract_rank(cells, last_rank + 1 if last_rank else 1)
        rank, rank_note = smooth_rank(rank, last_rank, "")
        values = numeric_values(cells)
        if name and not any(1 < v < 250 and (rank is None or abs(v - rank) > 1e-9) for v in values):
            pending_name = name
            continue
        if pending_name and not name:
            name = pending_name
            pending_name = None
        if not name:
            continue
        amount, note = first_budget_value(cells_after_name(cells, name), rank)
        if amount is None:
            continue
        if rank_note:
            note = (note + "; " if note else "") + rank_note
        results.append(make_row(2019, rank, name, amount, "paddleocr_row", note))
        if rank:
            last_rank = max(last_rank, rank)
    return dedupe(results)


def dedupe(rows: list[dict]) -> list[dict]:
    seen: set[tuple[int, str]] = set()
    out: list[dict] = []
    for row in rows:
        key = (int(row["year"]), row["university"])
        if key in seen:
            row["notes"] = (str(row["notes"]) + "; 重复项已跳过").strip("; ")
            continue
        seen.add(key)
        out.append(row)
    return out


def write_year(year: int, rows: list[dict]) -> None:
    write_csv(rows, OCR_DIR / f"{year}_extracted.csv")


def write_financial_table(rows: list[dict]) -> None:
    with FINANCIAL_TABLE_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FINANCIAL_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def build_report(by_year: dict[int, list[dict]], final_rows: list[dict]) -> None:
    lines = ["# OCR 抽取校验报告", ""]
    lines.append("## 每年记录数")
    lines.append("")
    lines.append("| 年份 | 记录数 | 备注 |")
    lines.append("| --- | ---: | --- |")
    for year in sorted(by_year):
        note = ""
        if year == 2018 and len(by_year[year]) <= 20:
            note = "预算图只含约 10 所高校"
        lines.append(f"| {year} | {len(by_year[year])} | {note} |")

    lines.extend(["", "## 口径修正/确认", ""])
    lines.append("| 年份 | 主表取值 | 明细表保留 |")
    lines.append("| --- | --- | --- |")
    lines.append("| 2016 | 2016年度预算数 | 年度收入合计、年度支出合计 |")
    lines.append("| 2017 | 预算总数 | 收入合计、支出合计 |")
    lines.append("| 2018 | 预算总经费 | 收入合计、支出合计；同济大学预算总经费按原图补入134.21 |")
    lines.append("| 2019 | 预算总经费 | 财政拨款收入、占比 |")
    lines.append("| 2020 | 2020年度部门预算 | 2019年度部门预算、两年变化 |")
    lines.append("| 2021 | 收入总预算 | 比去年增加、增长率 |")
    lines.append("| 2022 | 预算总收入 | 本年度收入、主管部门、所在省市 |")
    lines.append("| 2023 | 收入总计 | 本年收入；此前第一列“本年收入”不再作为预算趋势值 |")
    lines.append("| 2024 | 2024年预算 | 2023年预算、增减情况、增减比 |")
    lines.append("| 2025/2026 | 当年预算 | 当年本年收入、上一年预算 |")

    review_terms = ("疑似", "异常", "OCR", "拆分", "需人工")
    suspicious = [
        r
        for rows in by_year.values()
        for r in rows
        if any(term in str(r.get("notes", "")) for term in review_terms)
    ]
    lines.extend(["", "## 疑似需复核行", ""])
    if suspicious:
        lines.append("| 年份 | 排名 | 高校 | 金额 | 备注 |")
        lines.append("| --- | ---: | --- | ---: | --- |")
        for row in suspicious:
            lines.append(
                f"| {row['year']} | {row['rank']} | {row['university']} | "
                f"{row['budget_yi_yuan']} | {row['notes']} |"
            )
    else:
        lines.append("暂无。")

    lines.extend(["", "## 最终主表", ""])
    lines.append(f"- 文件：`{FINAL_CSV.relative_to(PROJECT_DIR)}`")
    lines.append(f"- 行数：{len(final_rows)}")
    lines.append(f"- 全字段明细：`{FINANCIAL_TABLE_CSV.relative_to(PROJECT_DIR)}`")
    lines.append(f"- 决算另存：`{FINAL_ACCOUNTS_CSV.relative_to(PROJECT_DIR)}`")
    lines.append("- 当前趋势分析表 `budget_yi_yuan` 只取年度预算；多列原表的其他字段保存在全字段明细表。")
    lines.append("- `verified` 均为 `False`，需要人工复核后再改为 `True`。")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    rows_2022 = process_2022()
    by_year: dict[int, list[dict]] = {
        2016: process_2016_budget_rows(),
        2017: strip_year_rows(2017, "2017_budget"),
        2018: strip_year_rows(2018, "2018_budget"),
        2019: process_2019(),
        2020: strip_year_rows(2020, "2020_budget"),
        2021: simple_year_rows(2021),
        2022: rows_2022,
        2023: strip_year_rows(2023, "2023_budget"),
        2024: simple_year_rows(2024),
        2025: simple_year_rows(2025, "原图含教育部、工信部、中科院; 已按名称排除工信部/中科院高校"),
        2026: simple_year_rows(2026, "原图含教育部、工信部、中科院; 已按名称排除工信部/中科院高校"),
    }

    for year, rows in by_year.items():
        write_year(year, rows)

    final_rows: list[dict] = []
    for year in sorted(by_year):
        final_rows.extend(by_year[year])
    final_rows.sort(key=lambda r: (int(r["year"]), int(r["rank"]) if r["rank"] else 999, r["university"]))
    write_csv(final_rows, FINAL_CSV)
    financial_rows = build_financial_rows(by_year)
    financial_rows.sort(key=lambda r: (int(r["year"]), int(r["rank"]) if r["rank"] else 999, r["university"]))
    write_financial_table(financial_rows)
    final_accounts_rows = process_2017()
    write_csv(final_accounts_rows, FINAL_ACCOUNTS_CSV)
    build_report(by_year, final_rows)

    for year in sorted(by_year):
        print(f"{year}: {len(by_year[year])}")
    print(f"final: {len(final_rows)} -> {FINAL_CSV}")
    print(f"report: {REPORT_MD}")


if __name__ == "__main__":
    main()
