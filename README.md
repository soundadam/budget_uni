# 中国高校预算与决算数据

China University Budget Dataset (`budget_uni`) collects public university budget and final-account data from official disclosures and legacy third-party ranking images. The project keeps source URLs, extraction scripts, reviewed CSVs, and reproducible analysis figures together so the data can be audited and extended.

![C9 official-preferred budget trend and symlog growth](data/processed/figures/c9_budget_trend_growth_official_preferred.png)

## What Is Included

The current dataset focuses on annual university finance disclosures in China, especially C9 and former Project 985 universities. It separates:

- **Official sources**: university information-disclosure sites, finance-office pages, ministry pages, PDFs, and HTML disclosure pages.
- **Legacy third-party images**: yearly summary charts used for OCR fallback and cross-checking.
- **Reviewed data**: cleaned CSVs under `data/processed/`.
- **Regenerable extraction outputs**: OCR/PDF/text/table candidates under `data/interim/`, ignored by Git by default.

The preferred C9 analysis uses official PDF/HTML values first and falls back to third-party OCR only when no official value has been extracted for that university-year.

## Quick Start

Use the reviewed CSVs directly:

```text
data/processed/ministry_university_budget.csv
data/processed/ministry_university_final_accounts.csv
data/processed/c9_budget_official_preferred.csv
data/processed/c9_budget_growth_official_preferred.csv
data/processed/c9_budget_cagr_official_preferred.csv
```

Regenerate the C9 official-preferred tables and figures:

```zsh
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/build_c9_official_preferred.py
```

Check official source and extraction coverage:

```zsh
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/report_official_source_coverage.py
```

## Repository Layout

```text
budget_uni/
  data/
    raw/
      images/                  # legacy third-party source images
      official_sources.csv      # source registry; main provenance index
      official/                 # official PDFs/pages when stored locally
      third_party/              # third-party source notes
      external/                 # macro or comparison sources
    interim/                    # OCR/PDF/table candidates; regenerable
    processed/                  # reviewed CSVs, schema, reports, figures
  docs/
    prompts/                    # extraction prompts and task notes
  notebooks/                    # exploratory analysis
  scripts/                      # discovery, extraction, cleaning, plotting
```

Large official PDFs can make the Git repository heavy. For public release, either track `data/raw/official/pdfs/**/*.pdf` with Git LFS or keep them outside normal Git and rely on `data/raw/official_sources.csv` plus the download/extraction scripts for reproducibility.

## Data Model And Provenance

The main reviewed budget table is:

```text
data/processed/ministry_university_budget.csv
```

Key fields:

| Field | Meaning |
| --- | --- |
| `year` | Budget year. |
| `university` | Normalized Chinese university name. |
| `budget_yi_yuan` | Amount normalized to 亿元. |
| `source_url` | Source page or PDF URL when available. |
| `extraction_method` | OCR, vision model, manual check, or combined method. |
| `verified` | Whether the row has been manually checked. |
| `notes` | Scope, metric, source, or quality notes. |

Official-preferred C9 tables add:

| Field | Meaning |
| --- | --- |
| `source_type` | `official_pdf`, `official_html`, or `third_party_ocr_fallback`. |
| `metric_code` | Extracted metric used for that value, such as `budget_total` or `income_total`. |
| `source_coverage_notes` | Source mix or coverage notes for summary outputs. |

See `data/processed/schema.md` for the longer schema and validation rules.

## Source Priority

1. Use official PDF/HTML disclosures when available.
2. Keep budget and final-account values in separate tables.
3. Do not mix annual budget, income total, current-year income, expenditure, fiscal appropriation, and final-account values into one time series unless the metric is explicitly recorded.
4. Use third-party OCR rows only as fallback or as discovery clues.
5. Keep source URLs and notes in downstream derived datasets.

## Analysis Notes

The C9 growth chart uses a symmetric log (`symlog`) y-axis for year-over-year growth. This preserves negative values while making both small and unusually large growth rates readable. The linear region is `-5%` to `5%`; minor y-axis ticks are enabled to improve reading away from zero.

CAGR is included as a long-run summary in:

```text
data/processed/c9_budget_cagr_official_preferred.csv
```

CAGR is useful for comparing long-run growth between schools, but it should not replace annual growth analysis. Year-over-year growth remains better for identifying policy shocks, data gaps, source changes, and one-year budget jumps.

## Main Scripts

| Script | Purpose |
| --- | --- |
| `scripts/discover_download_official_pdfs.py` | Discover and download official budget/final-account PDFs from registered sources. |
| `scripts/process_all_official_pdfs.py` | Batch extract text, tables, and fact candidates from official PDFs. |
| `scripts/official_html_extract.py` | Extract finance facts from official HTML disclosure pages. |
| `scripts/build_c9_official_preferred.py` | Build C9 official-preferred tables, growth, CAGR, and figures. |
| `scripts/report_official_source_coverage.py` | Report C9 official source and extraction coverage for 2013-2026. |

More detailed script notes are in `scripts/README.md`.

## Citation

If you use this repository, cite the repository and preserve the source fields in derived work:

```text
Adam. China University Budget Dataset (budget_uni). 2026.
```

Code is released under the MIT License. Data rows compiled by this project are intended for reuse with attribution; original source PDFs, pages, and third-party images remain subject to their original publishers' rights and terms.
