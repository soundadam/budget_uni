# Official Budget Table Candidates

本目录保存官方 PDF 抽取出的表格候选和长表候选。默认被 `.gitignore` 忽略，只保留 `.gitkeep` 和本 README；批量抽取结果不直接进入版本库。

## 当前样本

### 北京理工大学 2026 年度部门预算

来源：

```text
data/raw/official/pdfs/bit_2026_budget.pdf
https://xxgk.bit.edu.cn/docs/2026-04/122c058af442403a836ae073ac2af456.pdf
```

运行命令：

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python budget_uni/scripts/official_pdf_extract.py budget_uni/data/raw/official/pdfs/bit_2026_budget.pdf \
  --source-url 'https://xxgk.bit.edu.cn/docs/2026-04/122c058af442403a836ae073ac2af456.pdf' \
  --university 北京理工大学 \
  --year 2026 \
  --document-type budget \
  --prefix bit_2026_budget

python budget_uni/scripts/official_tables_to_fact.py \
  budget_uni/data/interim/official_budget_tables/bit_2026_budget_tables.csv
```

验证结果：

| 指标 | 原始值 | 单位 | 亿元 |
| --- | ---: | --- | ---: |
| 财政拨款收入 | 328,257.46 | 万元 | 32.825746 |
| 事业收入 | 647,129.46 | 万元 | 64.712946 |
| 其他收入 | 185,491.35 | 万元 | 18.549135 |
| 本年收入合计 | 1,160,878.27 | 万元 | 116.087827 |
| 使用非财政拨款结余 | 35,216.23 | 万元 | 3.521623 |
| 上年结转 | 595,003.91 | 万元 | 59.500391 |
| 收入总计 | 1,791,098.41 | 万元 | 179.109841 |
| 本年支出合计 | 1,230,990.23 | 万元 | 123.099023 |
| 支出总计 | 1,791,098.41 | 万元 | 179.109841 |

注意：

- `本年收入合计`、`收入总计`、`财政拨款收入` 是不同口径，不能互相替代。
- 该样本说明工信部直属高校官方 PDF 可以进入全高校经费事实表，但不能进入旧的“教育部直属高校预算主表”。
- 当前 `*_facts.csv` 是机器转换候选，进入 `processed/` 前仍需人工确认表名和指标映射。

## 批量输出文件

批量处理前，可先从官方索引页发现并下载多年 PDF：

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python budget_uni/scripts/discover_download_official_pdfs.py
python budget_uni/scripts/process_all_official_pdfs.py
python budget_uni/scripts/normalize_official_source_metadata.py
python budget_uni/scripts/process_all_official_pdfs.py
```

第一个脚本会把新发现的 PDF URL 追加回 `data/raw/official_sources.csv`，并把 PDF 下载到
`data/raw/official/pdfs/`。下载报告位于：

```text
data/interim/source_discovery/official_pdf_download_report.csv
```

第一次 `process_all_official_pdfs.py` 负责生成可供判别的 PDF 文本。`normalize_official_source_metadata.py` 会用已抽出的 PDF 文本修正 `finance_document`、`unknown_year` 和预算/决算误判，并把明显非经费 PDF 从来源表移出。最后再跑一次批处理，让 inventory 和事实候选表反映规范化后的来源表。

如果网络权限不可用，报告中会出现 `fetch_failed` 和 `Operation not permitted`，这表示本机沙箱阻止联网，
不是官方来源表或抽取脚本本身失败。

运行：

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python budget_uni/scripts/process_all_official_pdfs.py
```

会生成：

| 文件 | 粒度 | 用途 |
| --- | --- | --- |
| `official_pdf_processing_inventory.csv` | 一个 PDF 一行 | 记录来源、PDF、本地路径、文本/表/字段输出路径和抽取行数。 |
| `official_finance_fact_candidates.csv` | 一个 PDF-指标 一行 | 汇总全部 PDF 的长表事实候选。 |
| `official_pdf_field_catalog.csv` | 一个 PDF-字段 一行 | 更轻的字段目录，用于检查已经抽到哪些口径。 |

这些 CSV 仍属于 interim，默认不进入 git。后续应从 `official_finance_fact_candidates.csv` 人工复核后，再生成 `processed/university_finance_fact.csv` 或相应分析快照表。

## 当前批量处理状态

最近一次运行：

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
python budget_uni/scripts/discover_download_official_pdfs.py --sleep 0.2
python budget_uni/scripts/discover_download_official_pdfs.py --university 南京大学 --sleep 0.1
python budget_uni/scripts/discover_download_official_pdfs.py --university 上海交通大学 --sleep 0.1
python budget_uni/scripts/normalize_official_source_metadata.py
python budget_uni/scripts/process_all_official_pdfs.py --reuse-existing-outputs
python budget_uni/scripts/build_c9_official_preferred.py
```

已处理 201 个官方财务 PDF，覆盖预算和部分决算：

| 机构 | 口径 | PDF | 长表事实候选行 |
| --- | --- | ---: | ---: |
| 清华大学 | 预算 | 14 | 722 |
| 北京大学 | 预算/决算 | 24 | 297 |
| 浙江大学 | 预算/决算 | 19 | 259 |
| 上海交通大学 | 预算 | 10 | 308 |
| 复旦大学 | 预算/决算 | 36 | 731 |
| 南京大学 | 预算 | 14 | 166 |
| 中国科学技术大学 | 预算 | 10 | 232 |
| 哈尔滨工业大学 | 预算 | 6 | 93 |
| 北京理工大学 | 预算/决算 | 12 | 185 |
| 北京科技大学 | 预算/决算 | 5 | 121 |
| 教育部 | 预算/决算 | 11 | 355 |
| 中国科学院 | 预算/决算 | 15 | 1019 |
| 中国科学院上海药物研究所 | 预算 | 1 | 56 |
| 西安交通大学 | 预算/决算 | 24 | 804 |

总计：

| 输出 | 数量 |
| --- | ---: |
| PDF | 201 |
| 长表事实候选行 | 5348 |
| 暂无字段候选的 PDF | 14 |

当前核心字段已经覆盖 `收入总计`、`本年收入合计`、`财政拨款/一般公共预算拨款收入`、`事业收入`、`其他收入`、`上年结转`、`使用非财政拨款结余`、`本年支出合计`、`支出总计` 等。但这些仍是机器候选，进入 processed 前必须核对 PDF 原表。

## 横向比较维度

官方 PDF 不只适合抽预算总额。后续清洗进 `processed/` 时，建议优先派生这些可比较指标：

| 维度 | 字段 | 可派生指标 | 备注 |
| --- | --- | --- | --- |
| 总量口径 | `budget_total`、`income_total`、`expense_total` | 年度预算规模、年度同比增速 | 优先级建议为 `budget_total > income_total > expense_total`。 |
| 本年口径 | `current_year_income_total`、`current_year_expense_total` | 本年收入/支出规模、本年口径增速 | 与 `income_total` 的差额通常来自结转结余。 |
| 财政依赖 | `fiscal_appropriation_income`、`general_public_budget_appropriation_income`、`government_fund_budget_appropriation_income` | 财政拨款占比、一般公共预算拨款占比 | 不同主管部门高校可横向比较财政依赖度。 |
| 自筹能力 | `undertaking_income`、`other_income` | 事业收入占比、其他收入占比、非财政收入占比 | 适合比较高校自身收入结构。 |
| 结转结余 | `carryover_from_previous_year`、`carryover_to_next_year`、`non_fiscal_surplus_used` | 上年结转占比、结转下年占比、结余使用规模 | 适合观察预算执行压力和资金沉淀。 |
| 支出结构 | `education_expense`、`science_technology_expense`、`social_security_employment_expense`、`housing_security_expense` | 教育支出占比、科研支出占比、刚性支出占比 | 科目在不同主管部门、不同年份会有差异，需保留原指标名。 |
| 主管部门 | `source_site` 或后续 `university_dimensions.department` | 教育部/工信部/中科院系统分组 | C9 内部尤其需要区分主管部门。 |

建议下一步生成一个宽表 `data/processed/university_finance_fact_derived.csv`，粒度为 `institution_name + year + document_type`。不要把预算、决算、本年收入、收入总计混成一个字段；需要同时保留原始 `metric_code` 和最终选用的 `comparison_metric`。

## C9 官方预算缺口

截至当前批次，C9 官方预算来源覆盖情况如下：

| 高校 | 已有官方预算来源年份 | 2013-2026 缺口/备注 |
| --- | --- | --- |
| 清华大学 | 2013-2026 | 已覆盖。 |
| 北京大学 | 2016-2026 | 缺 2013-2015；C9 分析中 2021 仍回退，需核对 2021 官方 PDF 是否为有效预算文件而非误抓附件。 |
| 浙江大学 | 2014-2026 | 缺 2013。 |
| 上海交通大学 | 2016-2026 | 缺 2013-2015；2016 为官方 HTML 正文预算页，已由 HTML 抽取候选进入 C9 图。 |
| 复旦大学 | 2012、2013、2015、2017-2026 | 缺 2014、2016；2016 C9 图暂用旧 OCR 回退。 |
| 南京大学 | 2013-2026 | 已覆盖；2013-2020、2022-2025 主要由 OCR/正文候选补出，仍需人工核表。 |
| 中国科学技术大学 | 2017-2026 | 缺 2013-2016。 |
| 哈尔滨工业大学 | 2021-2026 | 缺 2013-2020。 |
| 西安交通大学 | 2014-2020、2022-2026 | 用户已迁移本地官方 PDF，已纳入抽取。缺 2013、2021；2013 仅有决算，2021 C9 图暂用旧 OCR 回退。 |

当前 C9 图 `data/processed/figures/c9_budget_trend_official_preferred.png` 和
`data/processed/figures/c9_budget_growth_official_preferred.png` 使用官方 PDF/HTML 候选优先、旧第三方 OCR 回退。当前分析窗口已扩展为 2013-2026；上交 2016 已使用官方 HTML 候选，上交 2017-2026、南大 2013-2026、西交 2014-2020 和 2022-2026 已切到官方 PDF 候选。西交 2021、复旦 2016 仍是回退或待抽取状态。
