#!/usr/bin/env python
"""Discover and download official university finance PDFs from registered pages."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CSV = PROJECT_DIR / "data" / "raw" / "official_sources.csv"
DEFAULT_PDF_DIR = PROJECT_DIR / "data" / "raw" / "official" / "pdfs"
DEFAULT_REPORT_DIR = PROJECT_DIR / "data" / "interim" / "source_discovery"
DISCOVERED_AT = "2026-05-06"

SOURCE_FIELDS = [
    "university",
    "year",
    "document_type",
    "title",
    "url",
    "source_site",
    "source_level",
    "discovered_at",
    "notes",
]

REPORT_FIELDS = [
    "university",
    "source_url",
    "candidate_title",
    "candidate_url",
    "pdf_url",
    "local_pdf",
    "status",
    "notes",
]

SCHOOL_SLUGS = {
    "清华大学": "tsinghua",
    "北京大学": "pku",
    "浙江大学": "zju",
    "上海交通大学": "sjtu",
    "复旦大学": "fudan",
    "南京大学": "nju",
    "西安交通大学": "xjtu",
    "中国科学技术大学": "ustc",
    "哈尔滨工业大学": "hit",
    "北京科技大学": "ustb",
    "北京理工大学": "bit",
    "中国科学院": "cas",
    "中国科学院上海药物研究所": "simm",
    "教育部": "moe",
    "工业和信息化部": "miit",
}

KEYWORDS = ("预算", "决算", "预决算", "财务", "部门预算", "部门决算")
PAGE_HINTS = (
    "ysxx",
    "yjsxx",
    "cwys",
    "cwjs",
    "szys",
    "szjs",
    "budget",
    "final",
    "account",
)


@dataclass
class PageFetch:
    url: str
    text: str
    final_url: str
    status: str
    notes: str = ""


@dataclass
class Candidate:
    title: str
    url: str
    source_url: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover and download official budget/final-account PDFs.")
    parser.add_argument("--source-csv", type=Path, default=DEFAULT_SOURCE_CSV)
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--limit-pages", type=int, default=0, help="Maximum non-PDF candidate pages to inspect; 0 means no limit.")
    parser.add_argument("--sleep", type=float, default=0.3, help="Delay between network requests.")
    parser.add_argument("--dry-run", action="store_true", help="Discover without downloading or updating source CSV.")
    return parser.parse_args()


def read_sources(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_sources(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SOURCE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def fetch_url(url: str, *, binary: bool = False, timeout: int = 25) -> tuple[bytes, str]:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 budget_uni official source crawler",
            "Accept": "*/*",
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.geturl()


def decode_html(content: bytes) -> str:
    for encoding in ("utf-8", "gb18030", "gbk"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def fetch_page(url: str) -> PageFetch:
    try:
        content, final_url = fetch_url(url)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return PageFetch(url=url, text="", final_url=url, status="fetch_failed", notes=str(exc))
    return PageFetch(url=url, text=decode_html(content), final_url=final_url, status="fetched")


def is_pdf_url(url: str) -> bool:
    return urlparse(url).path.lower().endswith(".pdf")


def strip_tags(value: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", value, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def page_title(text: str) -> str:
    for pattern in (
        r"<h1[^>]*>([\s\S]*?)</h1>",
        r"<title[^>]*>([\s\S]*?)</title>",
    ):
        match = re.search(pattern, text, flags=re.I)
        if match:
            title = strip_tags(match.group(1))
            title = re.sub(r"[-_].*$", "", title).strip()
            if title:
                return title
    return ""


def attr_links(page_url: str, text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for match in re.finditer(r"""<a\b[^>]*?\bhref\s*=\s*["']([^"']+)["'][^>]*>([\s\S]*?)</a>""", text, flags=re.I):
        href = html.unescape(match.group(1)).strip()
        label = strip_tags(match.group(2))
        if href and not href.startswith(("javascript:", "mailto:", "#")):
            rows.append((label, urljoin(page_url, href)))
    for match in re.finditer(r"""\b(?:href|src|pdfsrc)\s*=\s*["']([^"']+\.pdf(?:\?[^"']*)?)["']""", text, flags=re.I):
        href = html.unescape(match.group(1)).strip()
        rows.append(("", urljoin(page_url, href)))
    return rows


def interesting_title_or_url(title: str, url: str) -> bool:
    combined = f"{title} {url}".lower()
    if any(keyword in combined for keyword in KEYWORDS):
        return True
    return any(hint in combined for hint in PAGE_HINTS) and bool(re.search(r"20\d{2}", combined))


def same_site(base_url: str, next_url: str) -> bool:
    return urlparse(base_url).netloc == urlparse(next_url).netloc


def source_rows_for_discovery(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for row in rows:
        url = row.get("url", "")
        if not url.startswith(("http://", "https://")):
            continue
        if row.get("source_level") == "official_pdf" or is_pdf_url(url):
            continue
        doc_type = row.get("document_type", "")
        title = row.get("title", "")
        if "全国" == row.get("university"):
            continue
        if any(token in doc_type for token in ("budget", "final", "account", "ministry", "institute")):
            result.append(row)
        elif any(keyword in title for keyword in KEYWORDS):
            result.append(row)
    return result


def discover_candidates(source_row: dict[str, str], page: PageFetch) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[str] = set()
    if page.status != "fetched":
        return candidates
    for title, url in attr_links(page.final_url, page.text):
        if not same_site(page.final_url, url):
            continue
        if url in seen:
            continue
        seen.add(url)
        if is_pdf_url(url) or interesting_title_or_url(title, url):
            candidates.append(Candidate(title=title or page_title(page.text) or source_row.get("title", ""), url=url, source_url=page.url))
    if is_pdf_url(page.final_url):
        candidates.append(Candidate(title=source_row.get("title", ""), url=page.final_url, source_url=page.url))
    return candidates


def pagination_urls(page: PageFetch) -> list[str]:
    urls: list[str] = []
    seen: set[str] = {page.final_url}
    for label, url in attr_links(page.final_url, page.text):
        if not same_site(page.final_url, url) or url in seen:
            continue
        normalized_label = re.sub(r"\s+", "", label)
        if normalized_label in {"下一页", "尾页"} or normalized_label.isdigit():
            seen.add(url)
            urls.append(url)
    return urls


def discover_pdf_urls(candidate: Candidate, sleep_seconds: float) -> list[Candidate]:
    if is_pdf_url(candidate.url):
        return [candidate]
    time.sleep(sleep_seconds)
    page = fetch_page(candidate.url)
    if page.status != "fetched":
        return []
    title = page_title(page.text) or candidate.title
    pdfs: list[Candidate] = []
    seen: set[str] = set()
    for _, url in attr_links(page.final_url, page.text):
        if is_pdf_url(url) and url not in seen:
            seen.add(url)
            pdfs.append(Candidate(title=title, url=url, source_url=candidate.url))
    return pdfs


def infer_year(title: str, url: str) -> str:
    match = re.search(r"(20\d{2})", f"{title} {url}")
    return match.group(1) if match else ""


def infer_document_type(title: str, url: str) -> str:
    combined = f"{title} {url}"
    if "决算" in combined or "final" in combined.lower():
        return "final_account"
    if "预算" in combined or "budget" in combined.lower():
        return "budget"
    return "finance_document"


def short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]


def filename_for_pdf(row: dict[str, str], pdf: Candidate) -> str:
    university = row.get("university", "unknown")
    slug = SCHOOL_SLUGS.get(university) or short_hash(university)
    year = infer_year(pdf.title, pdf.url) or "unknown_year"
    document_type = infer_document_type(pdf.title, pdf.url)
    return f"{slug}_{year}_{document_type}_{short_hash(pdf.url)}.pdf"


def download_pdf(url: str, path: Path) -> tuple[str, str]:
    if path.exists() and path.stat().st_size > 0:
        return "exists", "local file already exists"
    try:
        content, _ = fetch_url(url, binary=True, timeout=60)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return "download_failed", str(exc)
    if not content.startswith(b"%PDF"):
        return "not_pdf_content", f"downloaded {len(content)} bytes without PDF header"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return "downloaded", f"{len(content)} bytes"


def source_row_for_pdf(source_row: dict[str, str], pdf: Candidate, local_pdf: Path) -> dict[str, str]:
    title = pdf.title or source_row.get("title", "")
    return {
        "university": source_row.get("university", ""),
        "year": infer_year(title, pdf.url),
        "document_type": infer_document_type(title, pdf.url),
        "title": title,
        "url": pdf.url,
        "source_site": source_row.get("source_site", ""),
        "source_level": "official_pdf",
        "discovered_at": DISCOVERED_AT,
        "notes": f"官方页面自动发现；来源页{pdf.source_url}；本地文件{local_pdf.name}",
    }


def main() -> None:
    args = parse_args()
    rows = read_sources(args.source_csv)
    existing_urls = {row.get("url", "") for row in rows}
    report_rows: list[dict[str, str]] = []
    new_rows: list[dict[str, str]] = []
    inspected_pages = 0

    for source_row in source_rows_for_discovery(rows):
        time.sleep(args.sleep)
        page = fetch_page(source_row["url"])
        if page.status != "fetched":
            report_rows.append(
                {
                    "university": source_row.get("university", ""),
                    "source_url": source_row.get("url", ""),
                    "candidate_title": source_row.get("title", ""),
                    "candidate_url": source_row.get("url", ""),
                    "pdf_url": "",
                    "local_pdf": "",
                    "status": page.status,
                    "notes": page.notes,
                }
            )
            continue

        pages_to_scan = [page]
        seen_page_urls = {page.final_url}
        for pagination_url in pagination_urls(page)[:5]:
            time.sleep(args.sleep)
            extra_page = fetch_page(pagination_url)
            if extra_page.status == "fetched" and extra_page.final_url not in seen_page_urls:
                seen_page_urls.add(extra_page.final_url)
                pages_to_scan.append(extra_page)

        candidates: list[Candidate] = []
        for scan_page in pages_to_scan:
            candidates.extend(discover_candidates(source_row, scan_page))

        for candidate in candidates:
            if args.limit_pages and inspected_pages >= args.limit_pages:
                break
            pdfs = [candidate] if is_pdf_url(candidate.url) else discover_pdf_urls(candidate, args.sleep)
            if not is_pdf_url(candidate.url):
                inspected_pages += 1
            if not pdfs:
                report_rows.append(
                    {
                        "university": source_row.get("university", ""),
                        "source_url": source_row.get("url", ""),
                        "candidate_title": candidate.title,
                        "candidate_url": candidate.url,
                        "pdf_url": "",
                        "local_pdf": "",
                        "status": "no_pdf_found",
                        "notes": "",
                    }
                )
            for pdf in pdfs:
                if pdf.url in existing_urls:
                    status = "registered"
                    local_name = ""
                else:
                    local_name = filename_for_pdf(source_row, pdf)
                    local_path = args.pdf_dir / local_name
                    if args.dry_run:
                        status, notes = "dry_run", ""
                    else:
                        status, notes = download_pdf(pdf.url, local_path)
                    if status in {"downloaded", "exists"}:
                        new_row = source_row_for_pdf(source_row, pdf, local_path)
                        rows.append(new_row)
                        new_rows.append(new_row)
                        existing_urls.add(pdf.url)
                    else:
                        local_name = ""
                report_rows.append(
                    {
                        "university": source_row.get("university", ""),
                        "source_url": source_row.get("url", ""),
                        "candidate_title": pdf.title,
                        "candidate_url": candidate.url,
                        "pdf_url": pdf.url,
                        "local_pdf": local_name,
                        "status": status,
                        "notes": "already in source registry" if status == "registered" else notes,
                    }
                )
        if args.limit_pages and inspected_pages >= args.limit_pages:
            break

    if not args.dry_run and new_rows:
        write_sources(args.source_csv, rows)
    report_path = args.report_dir / "official_pdf_download_report.csv"
    write_report(report_path, report_rows)

    print(f"source pages inspected: {inspected_pages}")
    print(f"new official PDF rows: {len(new_rows)}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
