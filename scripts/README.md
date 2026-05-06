# Scripts

Run Python scripts from the repo root with the shared dev environment active:

```zsh
source /Users/adam/.venvs/dev/.venv/bin/activate
python budget_uni/scripts/paddleocr_extract.py --image budget_uni/data/raw/images/2024.png --year 2024
```

`paddleocr_extract.py` currently saves raw OCR JSON only. The next step is to add a table-reconstruction script after inspecting OCR quality.

Analysis figures:

```zsh
source /Users/adam/.venvs/dev/.venv/bin/activate
python budget_uni/scripts/analyze_c9_985.py
```

This regenerates C9/985 CSVs and figures under `data/processed/figures/`.
Generated figures are watermarked with `@soundadam`.

To watermark existing images manually:

```zsh
source /Users/adam/.venvs/dev/.venv/bin/activate
python budget_uni/scripts/watermark_figures.py budget_uni/data/processed/figures
```

## 官方 PDF 抽取

先登记来源到 `data/raw/official_sources.csv`，再下载官方 PDF 到 `data/raw/official/pdfs/`。

从已登记的官方索引页继续发现并下载多年预算/决算 PDF：

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python budget_uni/scripts/discover_download_official_pdfs.py
```

脚本会：

- 读取 `official_sources.csv` 中的官方索引页和年度页面。
- 在同站点内查找标题或 URL 含预算、决算等关键词的页面。
- 进入年度页面查找 PDF，并下载到 `data/raw/official/pdfs/`。
- 对新 PDF 追加 `source_level=official_pdf` 的来源行，`notes` 中记录本地文件名。
- 写出 `data/interim/source_discovery/official_pdf_download_report.csv` 作为下载报告。

新下载批次建议先跑一次批量抽取，再用抽出的 PDF 首页文本规范化年份和预算/决算口径，并移出明显非经费 PDF：

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python budget_uni/scripts/process_all_official_pdfs.py
python budget_uni/scripts/normalize_official_source_metadata.py
python budget_uni/scripts/process_all_official_pdfs.py
```

PDF 抽取分两步：

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python budget_uni/scripts/official_pdf_extract.py budget_uni/data/raw/official/pdfs/bit_2026_budget.pdf \
  --source-url 'https://xxgk.bit.edu.cn/docs/2026-04/122c058af442403a836ae073ac2af456.pdf' \
  --university 北京理工大学 \
  --year 2026 \
  --document-type budget \
  --prefix bit_2026_budget
```

输出：

- `data/interim/official_pdf_text/{prefix}.txt`
- `data/interim/official_budget_tables/{prefix}_tables.csv`
- `data/interim/official_budget_tables/{prefix}_line_candidates.csv`

再把表格候选转成长表事实候选：

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python budget_uni/scripts/official_tables_to_fact.py \
  budget_uni/data/interim/official_budget_tables/bit_2026_budget_tables.csv
```

输出 `data/interim/official_budget_tables/{prefix}_facts.csv`。该文件仍是中间产物，进入 `processed/` 前必须复核表名、指标名和预算/决算口径。

批量处理当前登记/下载的所有官方 PDF：

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python budget_uni/scripts/process_all_official_pdfs.py --ocr-empty-pdfs
```

默认只处理 `official_sources.csv` 中 `source_level=official_pdf` 且口径为预算/决算的 PDF。若要调试下载目录里的未登记 PDF，可追加 `--include-unregistered-pdfs`。
如果某些扫描 PDF 已经用 OCR 生成了逐 PDF 输出，只想重建总 inventory 和合并 facts，可追加 `--reuse-existing-outputs`。

批量输出：

- `data/interim/official_budget_tables/official_pdf_processing_inventory.csv`
- `data/interim/official_budget_tables/official_finance_fact_candidates.csv`
- `data/interim/official_budget_tables/official_pdf_field_catalog.csv`
