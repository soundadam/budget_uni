# 标准数据表 Schema

建议文件：`data/processed/ministry_university_budget.csv`

决算口径另存：

```text
data/processed/ministry_university_final_accounts.csv
```

保留原表全部已抽取数值列的明细表：

```text
data/processed/ministry_university_financial_table.csv
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `year` | int | 预算年份，例如 `2024` |
| `rank` | int/null | 原图中的排名；如果原图无排名则留空 |
| `university` | string | 高校名称，使用规范中文全称 |
| `budget_original` | string | 原图中的预算文本，例如 `190.72亿元` |
| `budget_unit` | string | 原图单位，例如 `亿元`、`万元` |
| `budget_yi_yuan` | float | 统一换算为“亿元”的预算值 |
| `source_image` | string | 对应原始图片路径 |
| `source_url` | string/null | 来源页面 URL；没有则留空 |
| `extraction_method` | string | `paddleocr`、`vision_model`、`manual` 或组合 |
| `verified` | bool | 是否已经人工核对 |
| `notes` | string/null | 口径备注、疑似错误、跨年名称变化等 |

## 全字段明细表

`ministry_university_financial_table.csv` 用于保留原图中除年度预算外的其他字段。不同年份原图列名不同，无法填充的列留空。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `annual_budget_yi_yuan` | float/null | 原图“年度预算数” |
| `current_year_income_yi_yuan` | float/null | 原图“本年收入”或“本年度收入” |
| `income_total_yi_yuan` | float/null | 原图“收入总计”；2023 主表预算值取此列 |
| `annual_income_total_yi_yuan` | float/null | 原图“年度收入合计” |
| `annual_expenditure_total_yi_yuan` | float/null | 原图“年度支出合计” |
| `prior_year_budget_yi_yuan` | float/null | 原图上一年度预算，例如 `2023年预算` |
| `change_yi_yuan` | float/null | 原图预算增减额 |
| `change_ratio` | string/null | 原图预算增减比或增长率 |
| `fiscal_appropriation_income_yi_yuan` | float/null | 原图财政拨款收入 |
| `fiscal_appropriation_ratio` | string/null | 原图财政拨款占比 |
| `department` | string/null | 原图主管部门 |
| `province` | string/null | 原图所在省市 |

预算趋势分析只使用主表 `budget_yi_yuan`，即年度预算列。

## 扩展比较维度

后续如果加入国家或地区层面的横向比较数据，建议单独建表，不要直接塞进高校预算主表。

建议文件：

```text
data/processed/macro_fiscal_indicators.csv
data/processed/university_dimensions.csv
```

## C9 官方优先分析表

官方优先 C9 趋势表：

```text
data/processed/c9_budget_official_preferred.csv
data/processed/c9_budget_growth_official_preferred.csv
data/processed/c9_budget_cagr_official_preferred.csv
```

`c9_budget_official_preferred.csv` 在 C9 范围内优先使用官方 PDF/HTML 抽取值；只有官方值缺失时才回退到旧第三方 OCR 主表。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `university` | string | C9 高校名称 |
| `year` | int | 预算年份 |
| `budget_yi_yuan` | float | 统一换算为亿元的预算或官方优先指标值 |
| `source_type` | string | `official_pdf`、`official_html`、`third_party_ocr_fallback` |
| `metric_code` | string | 采用的指标代码，例如 `budget_total`、`income_total`、`legacy_budget_yi_yuan` |
| `source_url` | string/null | 官方 URL 或旧来源 URL |
| `notes` | string/null | 指标优先级、回退来源、口径备注 |

`c9_budget_growth_official_preferred.csv` 在上表基础上追加：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `growth_rate` | float | 同比增速小数，例如 `0.1` 表示 10% |
| `growth_percent` | float | 同比增速百分数 |

`c9_budget_cagr_official_preferred.csv` 用于长期增速概览：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `start_year` / `end_year` | int | 该校可用序列的起止年份 |
| `start_budget_yi_yuan` / `end_budget_yi_yuan` | float | 起止年份经费值 |
| `n_years` | int | CAGR 年数，等于 `end_year - start_year` |
| `observed_year_count` | int | 起止区间内实际有值的年份数 |
| `missing_years` | string/null | 起止区间内缺失的年份 |
| `cagr` | float | 复合年均增长率小数 |
| `cagr_percent` | float | 复合年均增长率百分数 |
| `source_coverage_notes` | string | 起止区间内来源类型计数 |

原始官方来源登记表：

```text
data/raw/official_sources.csv
```

`official_sources.csv` 建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `university` | string | 高校名；宏观数据可填 `全国` |
| `year` | int/null | 资料年份；索引页可留空 |
| `document_type` | string | `budget`、`final_account`、`budget_index`、`budget_final_account_index`、`ministry_budget`、`ministry_budget_final_account_index`、`institute_budget`、`macro_fiscal`、`macro_education`、`macro_yearbook_index` 等 |
| `title` | string | 页面或文件标题 |
| `url` | string | 官方页面、索引页或 PDF URL |
| `source_site` | string | 来源站点名称 |
| `source_level` | string | `official_page`、`official_index`、`official_pdf`、`official_index_entry`、`third_party_pointer` 等 |
| `discovered_at` | date | 发现或登记日期 |
| `notes` | string/null | 口径、缺口、后续抽取注意事项 |

## 官方 PDF 抽取中间产物

建议先把已下载的官方高校预算/决算 PDF 抽成中间文件，不直接写入最终主表：

```text
data/interim/official_pdf_text/{pdf_stem}.txt
data/interim/official_budget_tables/{pdf_stem}_tables.csv
data/interim/official_budget_tables/{pdf_stem}_line_candidates.csv
data/interim/official_budget_tables/{pdf_stem}_facts.csv
```

`*_tables.csv` 和 `*_line_candidates.csv` 保留下列来源与口径字段，后续人工清洗时再映射到 `ministry_university_budget.csv`、`ministry_university_final_accounts.csv` 或全字段明细表：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `source_pdf` | string | 本地 PDF 路径 |
| `source_url` | string/null | 官方页面或 PDF URL |
| `university` | string/null | 高校名称，优先来自 `official_sources.csv` |
| `year` | int/null | 资料年份 |
| `document_type` | string | `budget`、`final_account` 等，预算和决算不得混写 |
| `title` | string/null | 官方来源登记标题 |
| `source_site` | string/null | 来源站点 |
| `source_level` | string/null | `official_page`、`official_pdf` 等 |
| `unit_hint` | string/null | 从页面文字粗略识别的单位，例如 `万元`、`亿元` |
| `extraction_method` | string | 初始为 `pymupdf` |

`*_facts.csv` 是由表格候选初步转换出的长表候选，仍属于 interim，不等于已校验 processed 数据。建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `institution_name` | string | 高校或机构名称 |
| `year` | int/null | 资料年份 |
| `fiscal_stage` | string | `budget`、`final_account` 等 |
| `document_type` | string | 原始文档类型 |
| `table_name` | string | PDF 页码和表序号；后续可人工映射为原表名 |
| `metric_code` | string | 规范指标代码，例如 `income_total`、`fiscal_appropriation_income` |
| `metric_name` | string | 原表指标名 |
| `amount_original` | string | 原始金额文本 |
| `unit_original` | string | 原始单位 |
| `amount_yi_yuan` | float/null | 换算为亿元后的金额 |
| `source_pdf` | string | 本地 PDF 路径 |
| `source_url` | string/null | 官方来源 URL |
| `extraction_method` | string | 抽取方法 |
| `verified` | bool | 是否复核 |
| `notes` | string/null | 表格/指标口径备注 |

`macro_fiscal_indicators.csv` 建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `year` | int | 统计年份 |
| `indicator` | string | 指标名，例如全国一般公共预算收入、中央一般公共预算支出、全国教育支出、GDP、CPI |
| `value` | float | 指标数值 |
| `unit` | string | 原始单位，例如亿元、万人、% |
| `source_name` | string | 数据来源名称 |
| `source_url` | string/null | 来源链接 |
| `notes` | string/null | 口径说明 |

`university_dimensions.csv` 建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `university` | string | 规范中文全称 |
| `department` | string/null | 主管部门 |
| `province` | string/null | 所在省份 |
| `city` | string/null | 所在城市 |
| `is_c9` | bool | 是否 C9 |
| `is_985` | bool | 是否 985 |
| `is_211` | bool | 是否 211 |
| `is_double_first_class` | bool | 是否双一流 |
| `notes` | string/null | 名称变体、合并校区、口径说明 |

## 校验规则

1. `year + university` 应该唯一。
2. `budget_yi_yuan` 必须为数值，且大于 0。
3. 同一年内如果有 `rank`，应检查排名与预算降序是否一致。
4. 高校名称需要统一，例如不要混用简称和全称。
5. 决算图不能进入预算主表；可进入 `ministry_university_final_accounts.csv` 并在 `notes` 中标注决算口径。
6. `2021_miit_excluded.jpg` 当前只是排除样本，不能进入教育部直属高校主表。
7. 如果原图同时有预算、收入、支出等多列，主表只能取年度预算列，其他列进入全字段明细表。
