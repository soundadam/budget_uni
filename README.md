# Budget Uni CN：中国高校预算与决算数据

[English version](README.en.md)

`budget_uni_cn`（Budget Uni CN）正在整理中国高校年度财政预算、决算和相关经费数据。当前重点是爬取与核验 **教育部直属高校 2013-2026 年财政预算、决算等公开材料**，并把官网来源、第三方年度统计图、抽取脚本和已校验 CSV 放在一个便于复查和二次开发的仓库里。

![C9 official-preferred budget trend and symlog growth](data/processed/figures/c9_budget_trend_growth_official_preferred.png)

## 当前状态

- **研究范围**：优先覆盖教育部直属高校 2013-2026 年预算、决算、收入、支出、财政拨款等公开财务口径。
- **现有数据来源**：学校官网/信息公开网/财务处等官方 PDF 或 HTML，以及每年第三方汇总统计图。
- **官方来源进展**：目前已爬取并抽取了大部分 C9 高校的官方预算/决算材料；其他教育部直属高校仍在补全。
- **第三方来源进展**：已保留 2016-2026 年左右的年度统计图，并抽取为 `data/processed/ministry_university_budget.csv` 等表。
- **当前推荐使用**：如果只想直接分析，先看 `data/processed/`；如果要复核来源，再看 `data/raw/official_sources.csv` 和 Release 中的官方 PDF 包。

## TODO

- 补全教育部直属高校 2013-2026 年预算与决算官方来源。
- 区分并规范 `budget`、`final_account`、`income_total`、`current_year_income`、`expense_total`、`fiscal_appropriation_income` 等不同口径。
- 扩展官方来源抽取范围：从当前大部分 C9 高校，逐步覆盖更多教育部直属高校。
- 对第三方统计图 OCR 结果做逐年人工校验，并标记不能作为官方值使用的 fallback 行。
- 增加每条 processed 数据到原始 PDF/HTML、页码、表名、指标名的可追溯链路。
- 增加更多覆盖率报告，明确哪些学校/年份已有官方来源、哪些只有第三方数据、哪些仍缺失。

## 数据怎么用

最适合直接使用的是：

```text
data/processed/ministry_university_budget.csv
data/processed/ministry_university_final_accounts.csv
data/processed/ministry_university_financial_table.csv
data/processed/c9_budget_official_preferred.csv
data/processed/c9_budget_growth_official_preferred.csv
data/processed/c9_budget_cagr_official_preferred.csv
```

其中 `c9_budget_official_preferred.csv` 优先使用官方 PDF/HTML 抽取值；如果某个学校-年份暂无官方值，才回退到旧第三方 OCR 数据。

## English Summary

Budget Uni CN (`budget_uni_cn`) is an open dataset and extraction workflow for Chinese university budget and final-account disclosures. The current work focuses on Ministry of Education affiliated universities from 2013 to 2026, using official university disclosure pages/PDFs and legacy third-party yearly summary charts.

Official-source extraction currently covers most C9 universities, while broader MOE-affiliated university coverage is still in progress. Reviewed CSVs and analysis figures are kept in Git; large raw official PDFs and the interim extraction cache are distributed through GitHub Releases.

## Repository Layout

```text
budget_uni_cn/
  data/
    raw/
      images/                  # 第三方年度统计图，保留用于追溯 OCR
      official_sources.csv      # 官方来源注册表，核心溯源索引
      official/                 # 官方 PDF/页面的本地占位；大 PDF 不进 Git
      third_party/              # 第三方来源备注
      external/                 # 宏观或横向比较来源
    interim/                    # OCR/PDF/table 候选；可再生成，不进 Git
    processed/                  # 已校验 CSV、schema、报告和图表
  docs/
    prompts/                    # 抽取任务提示词和协作记录
  notebooks/                    # 探索分析
  scripts/                      # 发现、下载、抽取、清洗、绘图、打包脚本
```

## Releases

大文件不放入 Git 历史。目前 Release 包含：

```text
budget_uni_cn-raw-official-pdfs-2026-05-07.zip
budget_uni_cn-interim-cache-2026-05-07.zip
budget_uni_cn-release-manifest-2026-05-07.csv
sha256sums-2026-05-07.txt
```

Release 地址：

```text
https://github.com/soundadam/budget_uni_cn/releases/tag/raw-2026-05-07
```

## 复现图表

```zsh
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/build_c9_official_preferred.py
```

检查 C9 官方来源和抽取覆盖：

```zsh
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/report_official_source_coverage.py
```

重新生成 Release assets：

```zsh
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/build_release_assets.py --date 2026-05-07
```

## 给二次开发者和核验者

### 数据表

主预算表：

```text
data/processed/ministry_university_budget.csv
```

关键字段：

| 字段 | 含义 |
| --- | --- |
| `year` | 预算年份 |
| `university` | 规范中文高校名称 |
| `budget_yi_yuan` | 统一换算为亿元的金额 |
| `source_url` | 来源页面或 PDF URL |
| `extraction_method` | OCR、vision model、manual 或组合方法 |
| `verified` | 是否已人工核验 |
| `notes` | 口径、来源和质量备注 |

C9 官方优先表额外包含：

| 字段 | 含义 |
| --- | --- |
| `source_type` | `official_pdf`、`official_html` 或 `third_party_ocr_fallback` |
| `metric_code` | 本行采用的指标，例如 `budget_total`、`income_total` |
| `source_coverage_notes` | 汇总表中的来源覆盖备注 |

更完整的字段定义见：

```text
data/processed/schema.md
```

### 来源优先级

1. 优先使用官方 PDF/HTML。
2. 预算和决算必须分表或分字段保存。
3. 年度预算、收入总计、本年收入、支出、财政拨款等指标不能混成一个时间序列。
4. 第三方 OCR 只能作为 fallback 或发现线索。
5. 派生数据应保留 `source_url`、`source_type`、`metric_code` 和 `notes`。

### 分析说明

C9 增速图使用 symlog y 轴显示同比增速。这样可以保留负增长，同时让小增速和异常大增速都可读。当前线性区间是 `-5%` 到 `5%`，并启用了 y 轴小刻度。

CAGR 结果在：

```text
data/processed/c9_budget_cagr_official_preferred.csv
```

CAGR 适合做长期趋势概览，但不能替代年度同比；年度同比更适合识别政策冲击、口径跳变、缺失值和单年异常。

### 主要脚本

| 脚本 | 用途 |
| --- | --- |
| `scripts/discover_download_official_pdfs.py` | 从登记来源发现并下载官方预算/决算 PDF |
| `scripts/process_all_official_pdfs.py` | 批量抽取官方 PDF 文本、表格和事实候选 |
| `scripts/official_html_extract.py` | 从官方 HTML 披露页抽取财务事实 |
| `scripts/build_c9_official_preferred.py` | 生成 C9 官方优先表、增速、CAGR 和图表 |
| `scripts/report_official_source_coverage.py` | 报告 C9 2013-2026 官方来源覆盖情况 |
| `scripts/build_release_assets.py` | 生成官方 PDF 和 interim cache 的 Release 包 |

更多脚本说明见 `scripts/README.md`。

## Citation

If you use this repository, cite it and preserve source fields in derived work:

```text
Adam. Budget Uni CN: China University Budget Dataset (budget_uni_cn). 2026.
```

Code is released under the MIT License. Data rows compiled by this project are intended for reuse with attribution; original source PDFs, pages, and third-party images remain subject to their original publishers' rights and terms.
