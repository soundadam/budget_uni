#!/usr/bin/env python
"""Process strip-based OCR JSON into organized table rows and CSV files.

Handles 2017 (决算, 5 columns) and 2022 (全国, 6 columns with 主管部门 filter).
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
CROPS_DIR = PROJECT_DIR / "data" / "interim" / "ocr" / "crops"
OCR_DIR = PROJECT_DIR / "data" / "interim" / "ocr"
IMAGES_DIR = PROJECT_DIR / "data" / "raw" / "images"
OUT_DIR = OCR_DIR

# Strip height in original image pixels (before 3x resize)
STRIP_HEIGHT = 600

# 工信部 universities to exclude
MIIT_UNIS = {
    "哈尔滨工业大学", "北京航空航天大学", "北京理工大学",
    "西北工业大学", "南京航空航天大学", "南京理工大学", "哈尔滨工程大学",
}

# 中科院 universities to exclude
CAS_UNIS = {"中国科学技术大学", "中国科学院大学"}


def compute_global_coords(entries: list[dict]) -> list[dict]:
    """Add global_y (original image coords) to each OCR entry."""
    for e in entries:
        strip = e["strip"]
        # Strip 0 starts at y=0, strip N at y=N*STRIP_HEIGHT in original coords
        # OCR bbox coords are in the 3x-resized strip, so divide by 3 for original
        # Then add strip offset
        offset = strip * STRIP_HEIGHT
        # Use center y for grouping
        top_y_raw = e["bbox"][0][1]
        bot_y_raw = e["bbox"][2][1]
        center_y_raw = (top_y_raw + bot_y_raw) / 2
        # Convert to original image coordinates
        e["global_y"] = center_y_raw / 3 + offset
        # Also compute center x in original coords
        left_x = e["bbox"][0][0]
        right_x = e["bbox"][1][0]
        e["global_x"] = (left_x + right_x) / 2 / 3
    return entries


def group_into_rows(entries: list[dict], y_tolerance: float = 15) -> list[list[dict]]:
    """Group entries into rows by y-coordinate proximity."""
    if not entries:
        return []
    # Sort by global_y
    sorted_entries = sorted(entries, key=lambda e: e["global_y"])
    rows = []
    current_row = [sorted_entries[0]]
    for e in sorted_entries[1:]:
        if abs(e["global_y"] - current_row[0]["global_y"]) <= y_tolerance:
            current_row.append(e)
        else:
            # Sort row entries by x position
            current_row.sort(key=lambda e: e["global_x"])
            rows.append(current_row)
            current_row = [e]
    # Don't forget last row
    current_row.sort(key=lambda e: e["global_x"])
    rows.append(current_row)
    return rows


def extract_number(text: str) -> float | None:
    """Extract a numeric value from OCR text, handling common OCR errors."""
    # Clean up common OCR artifacts
    text = text.strip()
    # Replace Chinese decimal point variants
    text = text.replace("．", ".").replace("，", ".")
    # Try to find a number pattern
    m = re.search(r'[\d]+\.?[\d]*', text)
    if m:
        try:
            return float(m.group())
        except ValueError:
            return None
    return None


def process_2017():
    """Process 2017 strip OCR data into CSV rows."""
    raw = json.loads((CROPS_DIR / "2017_strip_ocr.json").read_text(encoding="utf-8"))
    entries = compute_global_coords(raw)

    # Filter out watermark/noise entries
    noise_words = {"微信", "微信公众号", "WW", "公众", "订阅", "分享", "更多"}
    entries = [e for e in entries if e["text"].strip() not in noise_words
               and not e["text"].strip().startswith("微信")]

    rows = group_into_rows(entries, y_tolerance=18)

    # 2017 columns: 排名, 学校名称, 总经费, 年度收入, 年度支出
    # Title row: "教育部直属高校2017年度决算经费（单位：亿元）"
    # Header row: 排名, 学校名称, 总经费, 年度收入, 年度支出

    # Find header row and data rows
    header_row_idx = None
    data_rows = []

    for i, row in enumerate(rows):
        texts = [e["text"] for e in row]
        # Check if this is the header row
        if "排名" in texts or "学校名称" in texts:
            header_row_idx = i
            continue
        # Check if this looks like a data row (starts with a number = rank)
        if texts and extract_number(texts[0]) is not None and extract_number(texts[0]) <= 76:
            data_rows.append(row)
        # Some rows might not have a rank number but have university name + budget
        elif texts and any(kw in texts[0] for kw in ["大学", "学院", "师范"]):
            data_rows.append(row)

    # For 2017: 决算数据, columns are rank, university, total_budget, annual_income, annual_expenditure
    # The budget_unit is 亿元

    results = []
    for row in data_rows:
        texts = [e["text"].strip() for e in row]
        # Fix known OCR errors
        texts = [t.replace("北京师范大与", "北京师范大学") for t in texts]

        # Try to identify columns by position
        # Typically: rank (x~30-80), university (x~100-250), budget1 (x~260-350), budget2, budget3
        rank_val = None
        uni_name = None
        budget_val = None

        # Find rank (first numeric value that's small)
        for t in texts:
            n = extract_number(t)
            if n is not None and n <= 76 and n == int(n):
                rank_val = int(n)
                break

        # Find university name (contains 大学 or 学院 or 师范 etc.)
        uni_keywords = ["大学", "学院", "师范"]
        for t in texts:
            if any(kw in t for kw in uni_keywords):
                uni_name = t
                break

        # Find budget value (largest numeric, usually the 总经费 column)
        numbers = [(extract_number(t), t) for t in texts]
        budget_candidates = [(n, t) for n, t in numbers if n is not None and n > 1 and n < 300]
        if budget_candidates:
            # Take the first budget candidate that isn't the rank
            for n, t in budget_candidates:
                if rank_val is None or n != rank_val:
                    budget_val = n
                    break

        rank_fixes = {"清华大学": 1, "北京大学": 2, "上海财经大学": 62}
        if uni_name in rank_fixes:
            rank_val = rank_fixes[uni_name]
        if uni_name:
            uni_name = uni_name.replace(" (北京)", "（北京）").replace("(北京)", "（北京）")

        if uni_name and budget_val:
            results.append({
                "year": 2017,
                "rank": rank_val,
                "university": uni_name,
                "budget_original": f"{budget_val}亿元",
                "budget_unit": "亿元",
                "budget_yi_yuan": budget_val,
                "source_image": "2017决算.jpg",
                "source_url": "https://www.edu.cn/ke_yan_yu_fa_zhan/gao_xiao_cheng_guo/gao_xiao_zi_xun/201808/t20180813_1620842.shtml",
                "extraction_method": "paddleocr_strip",
                "verified": False,
                "notes": "决算口径(非预算); 总经费=决算经费总额",
            })

    return results


def process_2022():
    """Process 2022 strip OCR data into CSV rows, filtering to 教育部 only."""
    raw = json.loads((CROPS_DIR / "2022_strip_ocr.json").read_text(encoding="utf-8"))
    entries = compute_global_coords(raw)

    # Filter out watermark/noise
    noise_words = {"微信", "微信公众号", "WW", "公众", "订阅", "分享", "更多"}
    entries = [e for e in entries if e["text"].strip() not in noise_words
               and not e["text"].strip().startswith("微信")]

    rows = group_into_rows(entries, y_tolerance=20)

    # 2022 columns: 序号, 学校名称, 预算(总收入), 本年度收入, 主管部门, 所在省市
    # Title row: "全国高校2022年预算经费汇总"
    # Header row has: 序号, 学校名称, etc.

    data_rows = []
    for row in rows:
        texts = [e["text"].strip() for e in row]
        # Data rows start with a rank number
        if texts and extract_number(texts[0]) is not None and extract_number(texts[0]) >= 1:
            data_rows.append(row)

    results = []
    for row in data_rows:
        texts = [e["text"].strip() for e in row]
        # Fix OCR errors
        texts = [t.replace("展龙江省", "黑龙江省") for t in texts]

        # Identify columns
        rank_val = extract_number(texts[0])
        if rank_val is None:
            continue

        # Find university name. Some rows put campus markers before the base name,
        # e.g. ["50", "(华东)", "中国石油大学", ...].
        uni_name = None
        uni_keywords = ["大学", "学院", "师范"]
        for idx, t in enumerate(texts):
            if any(kw in t for kw in uni_keywords):
                campus = ""
                if idx > 0 and texts[idx - 1] in {"(北京)", "（北京）", "(武汉)", "（武汉）", "(华东)", "（华东）"}:
                    campus = texts[idx - 1].replace("(", "（").replace(")", "）")
                uni_name = f"{t}{campus}"
                break

        # Find 主管部门
        dept = None
        dept_keywords = ["教育部", "工信部", "中科院", "科学院", "省", "市", "部"]
        for t in texts:
            if any(kw in t for kw in dept_keywords) and t != uni_name:
                dept = t
                break

        # Find budget value (亿元 number > 10)
        budget_val = None
        budget_text = None
        numbers = [(extract_number(t), t) for t in texts]
        budget_candidates = [(n, t) for n, t in numbers if n is not None and n > 10 and n < 500]
        for n, t in budget_candidates:
            if n != rank_val:
                budget_val = n
                budget_text = t
                break

        # Filter: only 教育部直属
        if uni_name == "广西大学":
            continue
        if dept and "教育部" not in dept:
            continue
        if uni_name in MIIT_UNIS or uni_name in CAS_UNIS:
            continue

        # If no dept detected but uni is known 教育部, include it
        if uni_name and budget_val:
            results.append({
                "year": 2022,
                "rank": int(rank_val) if rank_val == int(rank_val) else None,
                "university": uni_name,
                "budget_original": f"{budget_val}亿元",
                "budget_unit": "亿元",
                "budget_yi_yuan": budget_val,
                "source_image": "2022.jpg",
                "source_url": "https://m.mp.oeeee.com/a/BAAFRD000020210414468623.html",
                "extraction_method": "paddleocr_strip",
                "verified": False,
                "notes": "原图为全国高校汇总; 已按主管部门筛选为教育部直属高校" if not dept else "主管部门=教育部",
            })

    return results


def write_csv(results: list[dict], path: Path):
    """Write results to CSV file."""
    fieldnames = ["year", "rank", "university", "budget_original", "budget_unit",
                  "budget_yi_yuan", "source_image", "source_url", "extraction_method",
                  "verified", "notes"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)


def main():
    print("Processing 2017 strip OCR data...")
    results_2017 = process_2017()
    print(f"  Found {len(results_2017)} entries")
    write_csv(results_2017, OUT_DIR / "2017_extracted.csv")

    print("Processing 2022 strip OCR data...")
    results_2022 = process_2022()
    print(f"  Found {len(results_2022)} 教育部直属 entries")
    write_csv(results_2022, OUT_DIR / "2022_extracted.csv")

    print("Done. CSV files written to:", OUT_DIR)


if __name__ == "__main__":
    main()
