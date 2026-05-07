#!/usr/bin/env python
"""Parse PaddleOCR JSON output and reconstruct table rows.

Groups OCR text blocks by y-coordinate proximity into rows,
then by x-coordinate into columns. Outputs a CSV per year.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
OCR_DIR = PROJECT_DIR / "data" / "interim" / "ocr"


def group_by_rows(entries, y_tolerance=20):
    """Group OCR entries into rows based on y-coordinate proximity."""
    if not entries:
        return []

    # Sort by y coordinate of the top-left corner
    sorted_entries = sorted(entries, key=lambda e: e["bbox"][0][1])

    rows = []
    current_row = [sorted_entries[0]]
    current_y = sorted_entries[0]["bbox"][0][1]

    for entry in sorted_entries[1:]:
        entry_y = entry["bbox"][0][1]
        if abs(entry_y - current_y) <= y_tolerance:
            current_row.append(entry)
        else:
            rows.append(sorted(current_row, key=lambda e: e["bbox"][0][0]))
            current_row = [entry]
            current_y = entry_y

    if current_row:
        rows.append(sorted(current_row, key=lambda e: e["bbox"][0][0]))

    return rows


def parse_ocr_json(json_path: Path) -> list[list[str]]:
    """Parse PaddleOCR JSON and return rows of text."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    raw = data["raw_result"]

    entries = []
    for page in raw:
        if page is None:
            continue
        for block in page:
            if block is None:
                continue
            bbox = block[0]  # list of 4 coordinate pairs
            text, confidence = block[1]
            entries.append({"bbox": bbox, "text": text, "confidence": confidence})

    rows = group_by_rows(entries)
    return [[e["text"] for e in row] for row in rows]


def extract_budget_table(rows: list[list[str]], year: int) -> list[dict]:
    """Extract university budget data from parsed rows.

    Handles various column layouts:
    - 2-col: rank/name, amount
    - 3-col: rank, name, amount
    - 4-col: rank, name, budget_total, income_total, expenditure_total
    - Variants with different headers
    """
    results = []

    # Skip header rows
    header_keywords = ["序号", "排名", "高校", "大学", "预算", "经费", "收入", "支出", "单位"]
    data_rows = []
    for row in rows:
        # Check if this row looks like a header
        is_header = any(kw in cell for cell in row for kw in header_keywords)
        # Also check title rows
        is_title = str(year) in "".join(row) or "教育部" in "".join(row)
        if not is_header and not is_title:
            data_rows.append(row)

    for row in data_rows:
        if len(row) < 2:
            continue

        # Try to identify the structure
        # Look for a number (rank) in the first cell
        rank = None
        name = None
        budget = None

        cells = row

        # Check if first cell is a rank number
        first_cell = cells[0].strip()
        if first_cell.isdigit():
            rank = int(first_cell)
            remaining = cells[1:]
        else:
            remaining = cells

        # Find university name (contains Chinese characters, typically 3-6 chars)
        for cell in remaining:
            # University name typically has Chinese chars and ends with 大学/学院
            if any(suffix in cell for suffix in ["大学", "学院", "科学院"]):
                name = cell
                break

        # Find budget amount (a number, possibly with decimal)
        for cell in remaining:
            if cell == name:
                continue
            # Check if it's a number
            try:
                val = float(cell)
                if budget is None:
                    budget = cell  # Take the first numeric value as budget
            except ValueError:
                pass

        if name and budget:
            results.append({
                "year": year,
                "rank": rank,
                "university": name,
                "budget_original": f"{budget}亿元",
                "budget_unit": "亿元",
                "budget_yi_yuan": float(budget),
            })

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--json-dir", default=OCR_DIR, type=Path)
    parser.add_argument("--out-dir", default=OCR_DIR, type=Path)
    args = parser.parse_args()

    json_path = args.json_dir / f"{args.year}_paddleocr.json"
    if not json_path.exists():
        raise SystemExit(f"No OCR JSON found: {json_path}")

    rows = parse_ocr_json(json_path)
    print(f"Parsed {len(rows)} rows from {json_path.name}")

    # Print all rows for inspection
    for i, row in enumerate(rows):
        print(f"  Row {i}: {row}")

    # Extract budget data
    budget_data = extract_budget_table(rows, args.year)
    print(f"\nExtracted {len(budget_data)} university entries")

    # Write CSV
    out_path = args.out_dir / f"{args.year}_extracted.csv"
    fieldnames = ["year", "rank", "university", "budget_original", "budget_unit", "budget_yi_yuan"]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(budget_data)

    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()