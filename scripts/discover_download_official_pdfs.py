#!/usr/bin/env python
"""Discover and download official university finance PDFs from registered pages."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import ssl
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse, urlsplit, urlunsplit
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
    parser.add_argument("--university", default="", help="Only inspect rows for this university.")
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
    request_url = quote_url_for_request(url)
    req = Request(
        request_url,
        headers={
            "User-Agent": "Mozilla/5.0 budget_uni_cn official source crawler",
            "Accept": "*/*",
        },
    )
    context = ssl._create_unverified_context() if request_url.startswith("https://") else None
    try:
        with urlopen(req, timeout=timeout, context=context) as resp:
            return resp.read(), resp.geturl()
    except (HTTPError, URLError, TimeoutError, OSError):
        return fetch_url_with_curl(request_url, timeout=timeout)


def quote_url_for_request(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            quote(parts.path, safe="/%:@"),
            quote(parts.query, safe="=&?/%:@"),
            quote(parts.fragment, safe="=&?/%:@"),
        )
    )


def fetch_url_with_curl(url: str, *, timeout: int = 25) -> tuple[bytes, str]:
    with tempfile.TemporaryDirectory(prefix="budget_uni_cn_curl_") as tmp_dir:
        cookie_jar = Path(tmp_dir) / "cookies.txt"
        content, final_url, status_code = curl_get(url, cookie_jar, timeout=timeout)
        if is_challenge_page(content):
            solve_dynamic_challenge(content, final_url, cookie_jar, timeout=timeout)
            content, final_url, status_code = curl_get(url, cookie_jar, timeout=timeout)
    if int(status_code or 0) >= 400:
        raise URLError(f"curl HTTP status {status_code} for {url}")
    return content, final_url


def curl_get(url: str, cookie_jar: Path, *, timeout: int) -> tuple[bytes, str, str]:
    result = subprocess.run(
        [
            "curl",
            "-L",
            "-sS",
            "--max-time",
            str(timeout),
            "-A",
            "Mozilla/5.0 budget_uni_cn official source crawler",
            "-b",
            str(cookie_jar),
            "-c",
            str(cookie_jar),
            "-w",
            "\n%{url_effective}\n%{http_code}",
            url,
        ],
        check=True,
        capture_output=True,
    )
    content_and_url, _, status = result.stdout.rpartition(b"\n")
    content, _, final_url = content_and_url.rpartition(b"\n")
    return content, final_url.decode("utf-8", errors="ignore") or url, status.decode("ascii", errors="ignore")


def is_challenge_page(content: bytes) -> bool:
    return b"/dynamic_challenge" in content and b"challengeId" in content


def solve_dynamic_challenge(content: bytes, final_url: str, cookie_jar: Path, *, timeout: int) -> None:
    text = decode_html(content)
    challenge_match = re.search(r'challengeId\s*=\s*"([^"]+)"', text)
    answer_match = re.search(r"answer\s*=\s*([0-9]+)", text)
    if not challenge_match or not answer_match:
        return
    challenge_url = urljoin(final_url, "/dynamic_challenge")
    payload = {
        "challenge_id": challenge_match.group(1),
        "answer": int(answer_match.group(1)),
        "browser_info": {
            "userAgent": "Mozilla/5.0 budget_uni_cn official source crawler",
            "language": "zh-CN",
            "platform": "MacIntel",
            "cookieEnabled": True,
            "hardwareConcurrency": 8,
            "deviceMemory": 8,
            "timezone": "Asia/Shanghai",
        },
    }
    subprocess.run(
        [
            "curl",
            "-L",
            "-sS",
            "--max-time",
            str(timeout),
            "-A",
            "Mozilla/5.0 budget_uni_cn official source crawler",
            "-H",
            "Content-Type: application/json",
            "-b",
            str(cookie_jar),
            "-c",
            str(cookie_jar),
            "-X",
            "POST",
            "--data",
            json.dumps(payload, ensure_ascii=False),
            challenge_url,
        ],
        check=True,
        capture_output=True,
    )


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
    except (HTTPError, URLError, TimeoutError, OSError, subprocess.CalledProcessError) as exc:
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
    for match in re.finditer(
        r"""<div\b[^>]*class\s*=\s*["'][^"']*mui-card-header[^"']*["'][^>]*>([\s\S]*?)</div>[\s\S]{0,1200}?<a\b[^>]*?\bhref\s*=\s*["']([^"']+)["']""",
        text,
        flags=re.I,
    ):
        label = strip_tags(match.group(1))
        href = html.unescape(match.group(2)).strip()
        if href and not href.startswith(("javascript:", "mailto:", "#")):
            rows.append((label, urljoin(page_url, href)))
    for match in re.finditer(r"""<a\b[^>]*?\bhref\s*=\s*["']([^"']+)["'][^>]*>([\s\S]*?)</a>""", text, flags=re.I):
        href = html.unescape(match.group(1)).strip()
        label = strip_tags(match.group(2))
        if href and not href.startswith(("javascript:", "mailto:", "#")):
            rows.append((label, urljoin(page_url, href)))
    for match in re.finditer(r"""\b(?:href|src|pdfsrc)\s*=\s*["']([^"']+\.pdf(?:\?[^"']*)?)["']""", text, flags=re.I):
        href = html.unescape(match.group(1)).strip()
        rows.append(("", urljoin(page_url, href)))
    for match in re.finditer(r"""viewer\.html\?([^"']*?\bfile=([^"']+?\.pdf)(?:[&#"']|$))""", text, flags=re.I):
        query = html.unescape(match.group(1))
        file_values = parse_qs(query).get("file")
        pdf_path = file_values[0] if file_values else match.group(2)
        rows.append(("", urljoin(page_url, unquote(pdf_path))))
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


def infer_document_type(title: str, url: str, source_url: str = "") -> str:
    combined = f"{title} {url} {source_url}"
    if "决算" in combined or "final" in combined.lower():
        return "final_account"
    if "预算" in combined or "budget" in combined.lower() or "/cwys/" in combined or "szys" in combined.lower():
        return "budget"
    return "finance_document"


def short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]


def filename_for_pdf(row: dict[str, str], pdf: Candidate) -> str:
    university = row.get("university", "unknown")
    slug = SCHOOL_SLUGS.get(university) or short_hash(university)
    year = infer_year(pdf.title, pdf.url) or "unknown_year"
    document_type = infer_document_type(pdf.title, pdf.url, pdf.source_url)
    return f"{slug}_{year}_{document_type}_{short_hash(pdf.url)}.pdf"


def download_pdf(url: str, path: Path) -> tuple[str, str]:
    if path.exists() and path.stat().st_size > 0:
        if path.read_bytes()[:4] == b"%PDF":
            return "exists", "local file already exists"
        path.unlink()
    try:
        content, _ = fetch_url(url, binary=True, timeout=60)
    except (HTTPError, URLError, TimeoutError, OSError, subprocess.CalledProcessError) as exc:
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
        "document_type": infer_document_type(title, pdf.url, pdf.source_url),
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

    source_rows = source_rows_for_discovery(rows)
    if args.university:
        source_rows = [row for row in source_rows if row.get("university") == args.university]

    for source_row in source_rows:
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
