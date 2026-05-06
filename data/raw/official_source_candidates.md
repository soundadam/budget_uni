# 官方数据源候选

检索日期：2026-05-05

当前主表主要来自第三方统计图片。后续补数据、校验数据时，优先回到学校官网、学校信息公开网、财务处/财务计划处官网、财政部、教育部、国家统计局、主管部门和地方财政/教育部门等官方来源。

本项目后续主题不再限定为“教育部直属高校预算”。数据源发现范围扩展为：中国各大高校经费支出、收入、财政拨款、预算、决算，以及可作为分母或背景变量的宏观财政、教育经费和区域财政多维数据。教育部直属、工业和信息化部直属、中国科学院直属、地方高校、部省合建高校、地方重点高校都应纳入候选池，但必须保留 `主管部门`、`学校层级/类型` 和 `数据口径` 字段，避免混成一个不可解释的排行榜。

## 使用原则

1. 不直接用第三方排行榜替代原始数据。第三方页面只作为发现线索。
2. 学校官网原始 PDF/网页优先级最高，尤其是标题为“年度部门预算”“年度部门决算”的页面。
3. 同一学校同一年如果同时有“部门预算”和“部门决算”，必须分表保存。
4. 原始 PDF 内的 `收支预算总表`、`收入预算表`、`支出预算表`、`财政拨款支出预算表` 是不同口径，不能混成一个字段。
5. 横向比较时建议同时保存：
   - `收入总计` / `收支总预算`
   - `本年收入合计`
   - `财政拨款收入`
   - `事业收入`
   - `其他收入`
   - `上年结转`
   - `使用非财政拨款结余`
   - `本年支出合计`
   - `结转下年`
6. 不同主管部门高校不能简单互相排除。后续主数据应改为“全高校候选库 + 可筛选视图”，例如可按 `主管部门=教育部`、`主管部门=工业和信息化部`、`主管部门=中国科学院`、`主管部门=地方` 分析。
7. 宏观财政数据只作为背景变量、分母或解释变量，不与学校年度预算数混入同一事实表。

## 推荐来源分类

| source_class | 来源层级 | 典型来源 | 适合抽取的核心字段 | 备注 |
| --- | --- | --- | --- | --- |
| `school_info_disclosure` | 学校 | 学校信息公开网、财务处/财务计划处、国资处 | 预算、决算、收入总计、本年收入、财政拨款收入、事业收入、支出总计、本年支出 | 单校单年最可信来源；优先级最高。 |
| `supervising_department_budget` | 主管部门 | 教育部、工信部、中国科学院、地方教育厅/财政厅部门预算/决算 | 部门总收支、高等教育支出、所属单位预算汇总、项目支出 | 可确认主管部门口径和中央/地方拨款背景。 |
| `central_fiscal_macro` | 中央宏观财政 | 财政部国库司统计数据、中央预算/决算公开 | 全国一般公共预算收入/支出、中央本级支出、教育支出、科学技术支出 | 作为高校预算占财政规模的分母。 |
| `education_finance_macro` | 教育经费宏观统计 | 教育部、国家统计局、财政部联合公告；中国教育经费统计年鉴 | 全国教育经费总投入、国家财政性教育经费、一般公共预算教育经费、高等教育经费、生均经费 | 适合做全国和分省教育投入背景。 |
| `regional_fiscal_macro` | 地方财政/区域背景 | 省市财政厅预决算、统计年鉴、地方教育经费公告 | 地方一般公共预算收入/支出、教育支出、高等教育支出、GDP、人口、在校生 | 用于解释地方高校经费差异。 |
| `school_dimension` | 高校属性维度 | 教育部高校名单、双一流名单、主管部门官网、学校章程 | 主管部门、所在地、办学层次、双一流/985/211/C9、在校生、教职工 | 维表，不与财务事实混表。 |

## 建议字段设计

### 来源发现表 `official_sources.csv`

继续保留现有字段，并建议扩展为：

```text
source_id, institution_name, institution_type, supervisor, province, city,
year, fiscal_stage, document_type, source_class, title, url, source_site,
source_level, file_type, discovered_at, checked_at, status, notes
```

字段说明：

- `institution_name`: 学校、主管部门、省份或全国；宏观数据可用 `全国`、`教育部`、`财政部`、`北京市` 等。
- `institution_type`: `university`、`ministry`、`province`、`national_macro`、`city`。
- `supervisor`: 教育部、工信部、中国科学院、北京市、上海市等；宏观数据留空或填发布机关。
- `fiscal_stage`: `budget`、`final_account`、`execution`、`statistical_yearbook`、`notice`。
- `document_type`: `department_budget`、`department_final_account`、`income_table`、`expense_table`、`fiscal_appropriation_table`、`macro_fiscal`、`macro_education`、`dimension_list`。
- `source_class`: 使用上一节的分类。
- `status`: `candidate`、`confirmed_index`、`confirmed_document`、`downloaded`、`parsed`、`needs_manual_check`。

### 财务事实表建议

不要只维护一个“预算总额”表。建议拆成如下事实表：

| 表 | 粒度 | 用途 |
| --- | --- | --- |
| `university_finance_fact.csv` | 学校-年份-阶段-指标 | 长表，保存所有可比较指标，如收入总计、本年收入、财政拨款收入、本年支出等。 |
| `university_budget_snapshot.csv` | 学校-年份 | 从长表中挑选一个预算总量口径，用于趋势图；必须记录选取规则。 |
| `university_final_account_fact.csv` | 学校-年份-决算指标 | 决算单独保存，不能默认进入预算趋势。 |
| `macro_fiscal_fact.csv` | 地区/全国-年份-指标 | 全国和地方财政、教育经费、GDP、CPI、人口等背景变量。 |
| `institution_dim.csv` | 学校 | 主管部门、所在地、层次、双一流/985/211/C9 等维度。 |

### 推荐指标字段

财务事实长表建议字段：

```text
institution_name, institution_id, supervisor, province, city, year,
fiscal_stage, document_type, table_name, metric_code, metric_name,
amount_original, unit_original, amount_yi_yuan, currency,
source_id, source_url, extraction_method, verified, notes
```

宏观事实长表建议字段：

```text
region, region_level, year, metric_code, metric_name, value,
unit, source_id, source_url, notes
```

## 建议目录结构

当前不要移动 processed CSV。后续新增官方源流程时，建议按来源和处理阶段组织：

```text
budget_uni/
  data/
    raw/
      official_sources.csv
      official_source_candidates.md
      source_discovery_plan.md
      official/
        school/{supervisor}/{university}/{year}/
        supervisor/{agency}/{year}/
        macro/mof/{year}/
        macro/moe_education_finance/{year}/
        macro/nbs/{year}/
        regional/{province}/{year}/
    interim/
      official_pdf_text/
      official_budget_tables/
      source_discovery/
    processed/
      university_finance_fact.csv
      university_budget_snapshot.csv
      university_final_account_fact.csv
      macro_fiscal_fact.csv
      institution_dim.csv
```

目录命名原则：

- `raw/official/` 只放原始 PDF、HTML 快照、下载元数据，不放人工清洗结果。
- `interim/official_pdf_text/` 放 PDF/HTML 抽文本结果，便于重复解析。
- `interim/official_budget_tables/` 放从官方文件抽出的表格，保留原表名和原列名。
- `processed/` 只放经字段映射、单位统一、口径标注后的分析表。

## 高校官方预算入口候选

| 高校 | 官方入口/页面 | 初步判断 |
| --- | --- | --- |
| 清华大学 | https://www.tsinghua.edu.cn/zjqh/xxgk1/gksxx/cw_zcjsff/cwysxxx.htm | 财务预算信息列表，包含 2013-2026 年度部门预算。 |
| 北京大学 | https://xxgk.pku.edu.cn/gksx/cwzcsf/cwys/index.htm | 财务预算列表，包含 2013-2026 年部门预算，2014/2015 可能拆成两个文件。 |
| 浙江大学 | https://www.zju.edu.cn/xxgk/17961/list.htm | 收支预算总表列表，包含 2013-2026 年部门预算/财务预算信息。 |
| 上海交通大学 | https://gk.sjtu.edu.cn/Phone/View/5003 | 2026 年度部门预算页面；信息公开网可继续回溯其他年份。 |
| 复旦大学 | https://xxgk.fudan.edu.cn/_t435/yjsxx/list.htm | 预决算信息列表，包含 2026 预算和多年度预算/决算。 |
| 南京大学 | https://xxgk.nju.edu.cn/15419/list.htm | 财务预算列表，包含 2013-2026 年度部门预算。 |
| 西安交通大学 | https://xxgk.xjtu.edu.cn/xxgkml/cw_zcjsfxx/cwgl.htm | 财务管理列表，已检索到 2021-2025 年度部门预算和决算；2026 需后续再查。 |
| 中国科学技术大学 | https://xxgk.ustc.edu.cn/ysxx/list.htm | 预算信息列表，已检索到 2017-2025 年部门预算；2026 需后续再查。 |
| 哈尔滨工业大学 | https://xxgk.hit.edu.cn/12161/list.htm | 财务预算信息列表，已检索到 2021-2025 年度部门预算；2026 需后续再查。 |
| 北京科技大学 | https://xxgk.ustb.edu.cn/ | 官方信息公开网首页直接列出 2026、2025 预算和 2024 决算，可作为非 C9 教育部直属高校校验样本。 |

## 宏观财政/教育经费官方入口候选

| 指标方向 | 官方来源 | 用途 |
| --- | --- | --- |
| 全国一般公共预算收入/支出 | 财政部统计数据，例如 https://gks.mof.gov.cn/tongjishuju/202601/t20260130_3982923.htm | 作为高校预算占全国财政规模的分母。 |
| 中央一般公共预算支出、教育支出 | 财政部中央财政预算/决算表，例如 https://yss.mof.gov.cn/2025zyczys/202503/t20250324_3960482.htm | 比较高校预算与中央本级教育支出等口径。 |
| 全国教育经费执行情况 | 教育部、国家统计局、财政部联合公告 | 比较高校预算与全国教育经费、国家财政性教育经费、一般公共预算教育经费。 |
| 中国统计年鉴 | 国家统计局中国统计年鉴入口 https://www.stats.gov.cn/sj/ndsj/ | GDP、人口、财政收支、教育等宏观背景变量。 |
| 中国教育经费统计年鉴 | 国家统计局/教育部财务司相关年鉴页面 | 分地区、分教育层级、分来源/支出用途的教育经费背景。 |
| 全国教育经费统计调查制度 | 国家统计局部门统计调查项目页面 | 确认教育经费收入、支出、费用、负债、资产等统计口径。 |

## 主管部门预算公开入口候选

| 主管部门/层级 | 官方入口/检索方向 | 适合发现的高校/指标 |
| --- | --- | --- |
| 教育部 | 教育部财务信息、部门预算、部门决算、教育部直属高校信息公开网 | 教育部直属高校；教育部部门高等教育支出；中央高校项目支出。 |
| 工业和信息化部 | 工信部财务司、政府信息公开、部门预算/部门决算 | 哈尔滨工业大学、北京航空航天大学、北京理工大学、西北工业大学、南京航空航天大学、南京理工大学、哈尔滨工程大学。 |
| 中国科学院 | 中国科学院部门预算/部门决算、院属单位信息公开、学校信息公开网 | 中国科学技术大学、中国科学院大学；科教融合和科研项目结转口径需单独标注。 |
| 地方财政厅/教育厅 | 省市财政预决算公开、教育厅部门预算/决算、地方高校信息公开 | 省属高校、市属高校；地方财政拨款、高等教育支出、地方专项资金。 |
| 学校本级 | 学校信息公开网、财务处/财务计划处、国资处 | 单校预算/决算明细；表格字段最完整。 |

## 后续抽取建议

建议新增一个独立流程，不要直接改现有 OCR 主流程：

1. 扩展 `data/raw/official_sources.csv`，字段至少包括 `institution_name, institution_type, supervisor, province, city, year, fiscal_stage, document_type, source_class, title, url, source_site, discovered_at, status, notes`。
2. 对官方 PDF 建 `data/interim/official_pdf_text/`，保存抽出的文本，避免重复下载和重复 OCR。
3. 对每份官方预算 PDF 抽取“部门收支预算总表”“部门收入预算表”“部门支出预算表”“财政拨款支出预算表”，输出到 `data/interim/official_budget_tables/`。
4. 再从官方表生成新的长表和快照表；旧的 `data/processed/ministry_university_budget.csv` 只作为教育部直属历史视图，不直接覆盖。
5. 差异校验不要只比一个总额，应至少比较 `收入总计`、`本年收入合计`、`财政拨款收入` 三个口径。

## 检索关键词模板

```text
site:{school_domain} {高校名} {year}年度部门预算
site:{xxgk_domain} {高校名} 部门预算
site:{finance_domain} {高校名} 预算信息
{高校名} 信息公开 财务预算 部门预算 {year}
```

扩展检索模板：

```text
# 学校本级预算/决算
site:{school_domain} {高校名} {year} 年度部门预算 filetype:pdf
site:{school_domain} {高校名} {year} 年度部门决算 filetype:pdf
site:{school_domain} {高校名} 收支预算总表 {year}
site:{school_domain} {高校名} 收入预算表 财政拨款 {year}
site:{school_domain} {高校名} 支出预算表 {year}
site:{school_domain} {高校名} 财政拨款支出预算表 {year}
site:{school_domain} {高校名} 部门收入总表 {year}
site:{school_domain} {高校名} 部门支出总表 {year}

# 信息公开网
site:{xxgk_domain} {高校名} 预决算信息
site:{xxgk_domain} {高校名} 财务资产及收费信息 部门预算
site:{xxgk_domain} {高校名} 财务预算 财务决算
site:{xxgk_domain} {year} 年度部门预算
site:{xxgk_domain} {year} 年度部门决算

# 主管部门
site:moe.gov.cn {year} 教育部 部门预算 高等教育
site:moe.gov.cn {year} 教育部 部门决算 高等教育
site:miit.gov.cn {year} 工业和信息化部 部门预算 高校
site:miit.gov.cn {year} 工业和信息化部 部门决算 高校
site:cas.cn {year} 中国科学院 部门预算 中国科学技术大学
site:cas.cn {year} 中国科学院 部门预算 中国科学院大学
site:{province_finance_domain} {year} 教育厅 部门预算 高等教育
site:{province_edu_domain} {year} 部门预算 高等教育 高校

# 财政部/宏观财政
site:mof.gov.cn {year} 年财政收支情况 教育支出
site:mof.gov.cn {year} 中央一般公共预算支出 教育
site:mof.gov.cn {year} 中央部门预算 教育部
site:mof.gov.cn {year} 中央部门决算 教育部
site:mof.gov.cn 政府收支分类科目 高等教育

# 教育部/国家统计局宏观教育经费
site:moe.gov.cn {year} 全国教育经费执行情况统计公告
site:moe.gov.cn {year} 全国教育经费执行情况统计快报 高等教育
site:stats.gov.cn 中国统计年鉴 {year} 教育 财政
site:stats.gov.cn 中国教育经费统计年鉴 {year}
site:stats.gov.cn 全国教育经费统计调查制度

# 地方高校和区域背景
site:{province_finance_domain} {year} 一般公共预算收入 支出 教育
site:{province_finance_domain} {year} 省级部门预算 教育厅 高等教育
site:{city_finance_domain} {year} 市属高校 部门预算
site:{university_domain} 预算 决算 信息公开 {year}
```

## 当前注意事项

- C9 中中国科学技术大学、哈尔滨工业大学不属于教育部直属高校。旧的“教育部直属高校预算主表”不能混入它们；新的扩展项目应把它们纳入全高校库，并单独记录主管部门。
- 学校年度部门预算 PDF 常用单位是“万元”，现有主表单位是“亿元”，抽取时必须统一换算。
- 2023 等年份的第三方图可能把“本年收入”和“收入总计”并列展示；官方 PDF 更适合核对具体字段来源。
- 工信部、中科院、地方高校的预算公开标题和表名可能与教育部直属高校不同，抽取时以原始表名为准，不要强行映射到单一 `budget` 字段。
- 地方高校经费可能存在学校本级预算、教育厅部门预算、省财政专项、地方债/基建资金等多来源，应优先进入长表并标注来源，不要合并成一个无来源的总额。
