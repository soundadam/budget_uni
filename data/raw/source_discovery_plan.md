# 官方来源批量发现计划

检索日期：2026-05-05

目标：把项目从“教育部直属高校预算 OCR 校正”扩展为“中国高校经费支出/收入/财政拨款/预算/决算/宏观财政多维分析”的官方来源发现流程。范围包括教育部直属、工信部直属、中国科学院直属、地方高校和其他可公开检索高校。

## 发现顺序

1. 先建高校维表候选池：学校名称、主管部门、省份、城市、学校层级、是否双一流/985/211/C9、信息公开网域名、财务处域名。
2. 按主管部门分批检索学校本级公开页：
   - 教育部直属高校。
   - 工信部直属 7 校。
   - 中国科学院直属高校。
   - 省属/市属重点高校。
3. 对每所学校按年度检索预算和决算：
   - 预算：`年度部门预算`、`部门预算`、`收支预算总表`、`收入预算表`、`财政拨款支出预算表`。
   - 决算：`年度部门决算`、`部门决算`、`收入支出决算总表`、`财政拨款收入支出决算总表`。
4. 同步检索主管部门和宏观背景：
   - 财政部财政收支、中央预算/决算、政府收支分类科目。
   - 教育部教育经费执行公告、教育部部门预算/决算。
   - 国家统计局统计年鉴、中国教育经费统计年鉴、教育经费统计调查制度。
   - 省级财政厅、教育厅年度预算/决算和教育经费公告。
5. 将发现结果先写入 `data/raw/official_sources.csv` 或后续同类来源表，只记录元数据，不直接写 processed CSV。

## 批量检索分组

| batch | 范围 | 主要目标 | 备注 |
| --- | --- | --- | --- |
| `batch_01_c9` | C9 和已有样本 | 验证不同主管部门的字段兼容性 | 包含教育部、工信部、中科院。 |
| `batch_02_moe_75` | 教育部直属高校 | 建立 2016-2026 预算/决算链接库 | 可优先找信息公开网列表页。 |
| `batch_03_miit_7` | 工信部直属高校 | 建立工信部高校官方预算/决算链接库 | 不再排除，应作为独立主管部门分组。 |
| `batch_04_cas` | 中国科学技术大学、中国科学院大学 | 处理科研项目结转较高的特殊口径 | 需记录上年结转、财政拨款、事业收入。 |
| `batch_05_local_double_first_class` | 地方双一流/省属重点高校 | 验证地方高校公开模式 | 省财政、学校本级、教育厅可能同时出现。 |
| `batch_06_macro` | 全国和地方宏观财政教育经费 | 建宏观背景变量 | 与学校事实表分开。 |

## 字段映射优先级

预算文件优先抽取：

| 原始表/文本 | 推荐指标代码 | 说明 |
| --- | --- | --- |
| 收入总计、收支总预算、预算总收入 | `budget_income_total` | 可作为预算总量候选，但需保留原始表名。 |
| 本年收入合计 | `current_year_income_total` | 不一定等于收入总计。 |
| 财政拨款收入、一般公共预算财政拨款收入 | `fiscal_appropriation_income` | 分析财政依赖度。 |
| 事业收入 | `undertaking_income` | 高校自有事业收入。 |
| 其他收入 | `other_income` | 需防止与事业收入混淆。 |
| 使用非财政拨款结余 | `non_fiscal_surplus_used` | 预算来源之一。 |
| 上年结转、上年结转结余 | `carryover_from_previous_year` | 科研项目较多高校可能很大。 |
| 支出总计、支出总预算 | `budget_expense_total` | 预算支出口径。 |
| 本年支出合计 | `current_year_expense_total` | 和支出总计区分。 |
| 基本支出、项目支出 | `basic_expense`、`project_expense` | 结构分析。 |

决算文件优先抽取：

| 原始表/文本 | 推荐指标代码 | 说明 |
| --- | --- | --- |
| 收入支出决算总表收入总计 | `final_account_income_total` | 决算收入，不进入预算趋势。 |
| 收入支出决算总表支出总计 | `final_account_expense_total` | 决算支出。 |
| 财政拨款收入支出决算总表财政拨款收入 | `final_account_fiscal_income` | 决算财政拨款。 |
| 一般公共预算财政拨款支出 | `final_account_general_public_budget_expense` | 决算财政支出。 |

宏观变量优先抽取：

| 来源 | 推荐指标代码 | 说明 |
| --- | --- | --- |
| 财政部财政收支情况 | `national_general_public_budget_revenue`、`national_general_public_budget_expenditure`、`national_education_expenditure` | 全国财政分母。 |
| 财政部中央预算/决算 | `central_budget_education_expenditure`、`central_final_account_education_expenditure` | 中央教育支出口径。 |
| 教育经费执行公告 | `national_education_funding_total`、`national_fiscal_education_funding`、`general_public_budget_education_funding` | 教育经费总投入和财政性教育经费。 |
| 国家统计局年鉴 | `gdp`、`population`、`regional_fiscal_revenue`、`regional_education_expenditure` | 区域背景。 |

## 目录和产物

建议先只新增 raw/interim 元数据，不改现有 processed 表：

```text
data/raw/official_sources.csv
data/raw/source_discovery_plan.md
data/raw/official/{source_class}/...
data/interim/source_discovery/
data/interim/official_pdf_text/
data/interim/official_budget_tables/
```

后续确认字段后再生成新的 processed 长表，避免污染既有 OCR 结果。

## 批量检索策略

1. 先抓列表页，不直接抓单个 PDF：每个学校优先定位 `预算信息`、`预决算信息`、`财务资产及收费信息` 列表页。
2. 对列表页抽取候选链接：标题包含 `部门预算`、`年度预算`、`部门决算`、`年度决算`、`收支预算总表`、`财政拨款`。
3. 对每个候选链接记录元数据：学校、年份、标题、URL、发布站点、PDF/HTML、是否官方、是否可下载。
4. 再下载或抽取文本：PDF 优先用文本抽取；扫描件或图片再走 OCR。
5. 先做字段长表：所有指标按 `metric_code` 入库，再从长表派生排名/趋势用宽表。
6. 对每年每校设置口径状态：`official_exact`、`official_needs_mapping`、`third_party_hint_only`、`missing`。
7. 每轮检索生成缺口清单：缺年份、缺预算、缺决算、缺财政拨款字段、缺主管部门字段。

## 不做事项

- 不把第三方排行榜直接作为正式数据源。
- 不把预算和决算合并为同一时间序列。
- 不把 `本年收入`、`收入总计`、`预算总收入` 默认视为同一字段。
- 不在来源发现阶段修改 `data/processed/*.csv`。
