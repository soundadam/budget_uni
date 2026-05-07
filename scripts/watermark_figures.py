#!/usr/bin/env python
"""Add a repeated @soundadam watermark to generated figure files."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_FIG_DIR = PROJECT_DIR / "data" / "processed" / "figures"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path, help="Image files or directories to watermark.")
    parser.add_argument("--text", default="@soundadam", help="Watermark text.")
    parser.add_argument("--suffix", default="", help="Output suffix before extension. Empty means overwrite.")
    parser.add_argument("--opacity", default=42, type=int, help="Watermark opacity, 0-255.")
    return parser.parse_args()


def iter_images(paths: list[Path]) -> list[Path]:
    if not paths:
        paths = [DEFAULT_FIG_DIR]

    images: list[Path] = []
    for path in paths:
        path = path.resolve()
        if path.is_dir():
            for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
                images.extend(sorted(path.glob(pattern)))
        elif path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            images.append(path)
    return images


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ):
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def add_watermark(path: Path, text: str, suffix: str, opacity: int) -> Path:
    image = Image.open(path).convert("RGBA")
    width, height = image.size
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    large_font = font(max(24, width // 16))
    small_font = font(max(12, width // 95))
    color = (51, 65, 85, max(0, min(255, opacity)))

    tile = max(220, width // 3)
    for y in range(-height, height * 2, tile):
        for x in range(-width, width * 2, tile):
            draw.text((x, y), text, font=large_font, fill=color)

    bottom_color = (51, 65, 85, max(0, min(255, opacity + 80)))
    text_box = draw.textbbox((0, 0), text, font=small_font)
    draw.text((width - text_box[2] - 18, height - text_box[3] - 14), text, font=small_font, fill=bottom_color)

    rotated = overlay.rotate(28, expand=False, resample=Image.Resampling.BICUBIC)
    output = Image.alpha_composite(image, rotated).convert("RGB")

    out_path = path.with_name(f"{path.stem}{suffix}{path.suffix}") if suffix else path
    output.save(out_path)
    return out_path


def main() -> None:
    args = parse_args()
    for image in iter_images(args.paths):
        out = add_watermark(image, args.text, args.suffix, args.opacity)
        print(out)


if __name__ == "__main__":
    main()
