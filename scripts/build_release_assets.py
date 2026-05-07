#!/usr/bin/env python
"""Build local GitHub Release asset bundles."""

from __future__ import annotations

import argparse
import csv
import hashlib
import zipfile
from datetime import date
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".git", "__pycache__", "matplotlib", ".ipynb_checkpoints"}
EXCLUDE_NAMES = {".DS_Store", ".gitkeep"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat(), help="Date suffix for release assets.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=PROJECT_DIR / "release-assets",
        help="Directory where release asset folders are written.",
    )
    return parser.parse_args()


def should_include(path: Path) -> bool:
    rel_parts = path.relative_to(PROJECT_DIR).parts
    if any(part in EXCLUDE_DIRS for part in rel_parts):
        return False
    if path.name in EXCLUDE_NAMES:
        return False
    return path.is_file()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob("*") if should_include(path))
    return sorted(files, key=lambda path: path.relative_to(PROJECT_DIR).as_posix())


def write_package(package_path: Path, roots: list[Path]) -> list[dict[str, str | int]]:
    manifest_rows: list[dict[str, str | int]] = []
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in iter_files(roots):
            rel = path.relative_to(PROJECT_DIR).as_posix()
            zf.write(path, arcname=rel)
            manifest_rows.append(
                {
                    "package": package_path.name,
                    "path": rel,
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    return manifest_rows


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir / args.date
    out_dir.mkdir(parents=True, exist_ok=True)

    packages = {
        f"budget_uni_cn-raw-official-pdfs-{args.date}.zip": [PROJECT_DIR / "data" / "raw" / "official" / "pdfs"],
        f"budget_uni_cn-interim-cache-{args.date}.zip": [PROJECT_DIR / "data" / "interim"],
    }

    manifest_rows: list[dict[str, str | int]] = []
    asset_rows: list[tuple[str, str, int]] = []
    for package_name, roots in packages.items():
        package_path = out_dir / package_name
        manifest_rows.extend(write_package(package_path, roots))
        asset_rows.append((package_name, sha256(package_path), package_path.stat().st_size))

    manifest_path = out_dir / f"budget_uni_cn-release-manifest-{args.date}.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["package", "path", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(manifest_rows)
    asset_rows.append((manifest_path.name, sha256(manifest_path), manifest_path.stat().st_size))

    sha_path = out_dir / f"sha256sums-{args.date}.txt"
    with sha_path.open("w", encoding="utf-8") as f:
        for name, digest, _size in sorted(asset_rows):
            f.write(f"{digest}  {name}\n")
    asset_rows.append((sha_path.name, sha256(sha_path), sha_path.stat().st_size))

    print(out_dir)
    for name, digest, size in asset_rows:
        print(f"{size:>12}  {digest}  {name}")


if __name__ == "__main__":
    main()
