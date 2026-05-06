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

先登记来源到 `data/raw/official_sources.csv`，再下载官方 PDF 到 `data/raw/official/pdfs/`。PDF 抽取分两步：

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
