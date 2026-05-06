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
