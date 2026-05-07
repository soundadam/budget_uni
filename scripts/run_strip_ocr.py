#!/usr/bin/env python
"""Run PaddleOCR on vertical image strips and save merged OCR entries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageOps


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = PROJECT_DIR / "data" / "interim" / "ocr" / "crops"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--key", required=True, help="Output key, e.g. 2017_budget.")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, type=Path)
    parser.add_argument("--strip-height", default=600, type=int)
    parser.add_argument("--scale", default=3, type=int)
    parser.add_argument("--autocontrast", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise SystemExit(
            "PaddleOCR is not importable. Activate dev env first:\n"
            "source /Users/adam/.venvs/dev/.venv/bin/activate"
        ) from exc

    image = Image.open(args.image).convert("RGB")
    if args.autocontrast:
        image = ImageOps.autocontrast(image)

    ocr = PaddleOCR(use_angle_cls=True, lang="ch")
    all_entries: list[dict] = []

    width, height = image.size
    for strip_idx, top in enumerate(range(0, height, args.strip_height)):
        bottom = min(top + args.strip_height, height)
        strip = image.crop((0, top, width, bottom))
        if args.scale != 1:
            strip = strip.resize((strip.width * args.scale, strip.height * args.scale))
        strip_path = args.out_dir / f"{args.key}_strip_{strip_idx}.png"
        strip.save(strip_path)

        result = ocr.ocr(str(strip_path), cls=True)
        page = result[0] if result else []
        if not page:
            continue
        for block in page:
            bbox = block[0]
            text, confidence = block[1]
            all_entries.append(
                {
                    "strip": strip_idx,
                    "bbox": bbox,
                    "text": text,
                    "confidence": confidence,
                    "scale": args.scale,
                    "strip_height": args.strip_height,
                    "source_image": str(args.image),
                }
            )

    out_path = args.out_dir / f"{args.key}_strip_ocr.json"
    out_path.write_text(json.dumps(all_entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
