# Scripts

Run Python scripts from the `budget_uni_cn` repo root with the shared dev environment active:

```zsh
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/paddleocr_extract.py --image data/raw/images/2024.png --year 2024
```

`paddleocr_extract.py` currently saves raw OCR JSON only. The next step is to add a table-reconstruction script after inspecting OCR quality.

Analysis figures:

```zsh
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/analyze_c9_985.py
```

This regenerates C9/985 CSVs and figures under `data/processed/figures/`.
Generated figures are watermarked with `@soundadam`.

To watermark existing images manually:

```zsh
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/watermark_figures.py data/processed/figures
```

## 官方 PDF 抽取

先登记来源到 `data/raw/official_sources.csv`，再下载官方 PDF 到 `data/raw/official/pdfs/`。

从已登记的官方索引页继续发现并下载多年预算/决算 PDF：

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/discover_download_official_pdfs.py
```

脚本会：

- 读取 `official_sources.csv` 中的官方索引页和年度页面。
- 在同站点内查找标题或 URL 含预算、决算等关键词的页面；补数据时预算和决算要一起找，不要只扫预算页。
- 进入年度页面查找 PDF，并下载到 `data/raw/official/pdfs/`。
- 对新 PDF 追加 `source_level=official_pdf` 的来源行，`notes` 中记录本地文件名。
- 写出 `data/interim/source_discovery/official_pdf_download_report.csv` 作为下载报告。

查看 C9 学校 2013-2026 预算/决算官方来源缺口：

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/report_official_source_coverage.py
```

输出：

- `data/processed/c9_official_source_coverage_2013_2026.csv`
- `data/processed/c9_official_extraction_coverage_2013_2026.csv`
- `data/processed/c9_official_source_coverage_2013_2026.md`

新下载批次建议先跑一次批量抽取，再用抽出的 PDF 首页文本规范化年份和预算/决算口径，并移出明显非经费 PDF：

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/process_all_official_pdfs.py
python scripts/normalize_official_source_metadata.py
python scripts/process_all_official_pdfs.py
```

PDF 抽取分两步：

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/official_pdf_extract.py data/raw/official/pdfs/bit_2026_budget.pdf \
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
python scripts/official_tables_to_fact.py \
  data/interim/official_budget_tables/bit_2026_budget_tables.csv
```

输出 `data/interim/official_budget_tables/{prefix}_facts.csv`。该文件仍是中间产物，进入 `processed/` 前必须复核表名、指标名和预算/决算口径。

批量处理当前登记/下载的所有官方 PDF：

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/process_all_official_pdfs.py --ocr-empty-pdfs
```

默认只处理 `official_sources.csv` 中 `source_level=official_pdf` 且口径为预算/决算的 PDF。若要调试下载目录里的未登记 PDF，可追加 `--include-unregistered-pdfs`。
如果某些扫描 PDF 已经用 OCR 生成了逐 PDF 输出，只想重建总 inventory 和合并 facts，可追加 `--reuse-existing-outputs`。

批量输出：

- `data/interim/official_budget_tables/official_pdf_processing_inventory.csv`
- `data/interim/official_budget_tables/official_finance_fact_candidates.csv`
- `data/interim/official_budget_tables/official_pdf_field_catalog.csv`

## 官方优先 C9 图表与 CAGR

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/build_c9_official_preferred.py
```

输出：

- `data/processed/c9_budget_official_preferred.csv`
- `data/processed/c9_budget_growth_official_preferred.csv`
- `data/processed/c9_budget_cagr_official_preferred.csv`
- `data/processed/figures/c9_budget_trend_growth_official_preferred.png`
- `data/processed/figures/c9_budget_growth_symlog_official_preferred.png`

增速图的 y 轴采用 symlog，并启用 minor ticks；CAGR 只作为长期概览，不替代年度同比。

如果需要区分“收支总预算/收入总计/支出总计”和“本年收入/本年支出/结转”等口径，生成官方财务事实派生宽表：

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/build_official_finance_derived.py
```

输出：

- `data/processed/university_finance_fact_derived.csv`
- `data/processed/c9_official_finance_fact_derived.csv`
- `data/processed/c9_official_finance_comparison_budget_total_pivot.csv`
- `data/processed/c9_official_finance_current_year_income_total_pivot.csv`
- `data/processed/c9_official_finance_current_year_expense_total_pivot.csv`
- `data/processed/c9_official_finance_carryover_from_previous_year_pivot.csv`
- `data/processed/c9_official_finance_carryover_to_next_year_pivot.csv`
- `data/processed/c9_official_finance_metric_coverage.csv`
- `data/processed/figures/dev/c9_official_finance_total_budget_dev.png`
- `data/processed/figures/dev/c9_official_finance_current_year_expense_dev.png`
- `data/processed/figures/dev/c9_official_finance_carryover_to_next_year_dev.png`
- `data/processed/figures/dev/c9_official_finance_current_expense_share_dev.png`
- `data/processed/figures/dev/c9_official_finance_2026_structure_dev.png`

缺失指标保持空值；`comparison_metric_code` 记录总规模比较实际采用 `budget_total`、`income_total` 还是 `expense_total`。

## Release Assets

官方 PDF 和 `data/interim/` cache 不进入 Git；发布时生成本地 Release assets：

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/build_release_assets.py --date 2026-05-07
```

输出目录：

```text
release-assets/2026-05-07/
```

默认生成：

- `budget_uni_cn-raw-official-pdfs-2026-05-07.zip`
- `budget_uni_cn-interim-cache-2026-05-07.zip`
- `budget_uni_cn-release-manifest-2026-05-07.csv`
- `sha256sums-2026-05-07.txt`

`release-assets/` 已被 `.gitignore` 忽略，生成后手动上传到 GitHub Releases。
