#!/usr/bin/env python
"""Run PaddleOCR on one budget image and save raw OCR JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = PROJECT_DIR / "data" / "interim" / "ocr"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, type=Path, help="Path to a raw budget image.")
    parser.add_argument("--year", required=True, type=int, help="Budget year represented by the image.")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, type=Path, help="Output directory.")
    parser.add_argument("--lang", default="ch", help="PaddleOCR language code.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    image = args.image.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise SystemExit(
            "PaddleOCR is not importable. Activate dev env first:\n"
            "source /Users/adam/.venvs/dev/.venv/bin/activate"
        ) from exc

    ocr = PaddleOCR(use_angle_cls=True, lang=args.lang)
    result = ocr.ocr(str(image), cls=True)

    payload = {
        "year": args.year,
        "source_image": str(image),
        "ocr_engine": "paddleocr",
        "raw_result": result,
    }
    out_path = out_dir / f"{args.year}_paddleocr.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
