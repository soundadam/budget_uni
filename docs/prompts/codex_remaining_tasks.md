# Codex 任务：高校经费官方来源发现与多口径数据结构

## 项目位置

```
/Users/adam/projects/statistics/budget_uni
```

## 背景

本项目早期从 10 张高校预算/决算图片中抽取表格数据，并生成教育部直属高校预算相关 CSV。后续任务已经扩展：主题不再限定教育部直属高校，而是转为“中国各大高校经费支出/收入/财政拨款/预算/决算/宏观财政多维分析”。

新范围包括：

- 教育部直属高校。
- 工业和信息化部直属高校。
- 中国科学院直属高校。
- 地方高校、部省合建高校、省属/市属重点高校。
- 财政部、教育部、国家统计局、省市财政/教育部门提供的宏观财政和教育经费背景变量。

本轮只做来源设计和后续任务记录，不修改 `data/processed/*.csv`。

## 当前写入范围

本阶段只允许更新：

- `data/raw/official_source_candidates.md`
- `data/raw/source_discovery_plan.md`
- `docs/prompts/codex_remaining_tasks.md`

不要修改：

- `data/processed/*.csv`
- `data/interim/ocr/*.csv`
- 现有 OCR 脚本，除非用户另行要求。

## 后续工作方向

接下来工作重点从单纯 OCR 抽取转为“官方来源发现 + 多口径事实表 + 宏观背景变量”：

1. 继续补全、复核各主管部门高校历年预算和决算数据。
2. 从学校信息公开网、学校财务处、主管部门预算公开、财政部、教育部、国家统计局等官方来源建立链接库。
3. 扩展可比较的外部宏观数据，例如全国财政收入、一般公共预算支出、教育支出、高等教育相关财政支出、GDP、CPI、人口、省份财政能力等。
4. 扩展高校侧维度，例如主管部门、所在地、省份、在校生规模、科研经费、双一流/985/211/C9 分类、中央/地方属性等。
5. 后续分析需要同时支持纵向变化和横向比较，避免只比较名义金额。

**最重要的口径提醒：所有统计名目必须分开建字段、分开入表、分开画图，不能把不同口径混为一个时间序列。**

尤其要区分：

- `年度预算数` / `预算总经费` / `收入总预算`：当前预算趋势主表使用的核心口径。
- `本年收入`：不是所有年份都等同于预算总额，不能默认进入预算主表。
- `收入总计`：部分年份可作为预算总量口径，例如 2023 预算图主表取此列，但必须在 schema 和 notes 中注明。
- `年度收入合计`、`年度支出合计`：属于收支/决算或全字段明细，不得误当年度预算。
- `财政拨款收入`、`财政拨款占比`：用于分析财政依赖度，不能替代总预算。
- `上一年预算`、`增减额`、`增长率`：用于校验和增速分析，不能替代当年预算。
- `决算`：单独进入决算表或全字段表，默认不进入预算趋势主表。
- `主管部门预算/决算`：是部门层面的宏观或汇总口径，不能替代学校本级年度预算。
- `财政部/教育部/国家统计局宏观数据`：作为背景变量或分母，不进入学校预算事实表。

每次新增来源时，先判定原图/原表标题和列名，再决定字段映射。无法确认口径时，宁可进入明细表并标注 `notes`，不要直接并入 `ministry_university_budget.csv`。

## 新的结构设计任务

### 任务 A：建立官方来源候选库

围绕 `data/raw/official_sources.csv` 扩展来源元数据。建议字段：

```text
source_id, institution_name, institution_type, supervisor, province, city,
year, fiscal_stage, document_type, source_class, title, url, source_site,
source_level, file_type, discovered_at, checked_at, status, notes
```

优先来源分类：

| source_class | 说明 |
| --- | --- |
| `school_info_disclosure` | 学校信息公开网、财务处、国资处等学校本级来源。 |
| `supervising_department_budget` | 教育部、工信部、中国科学院、地方教育厅/财政厅等主管部门预决算。 |
| `central_fiscal_macro` | 财政部财政收支、中央预算/决算、政府收支分类科目。 |
| `education_finance_macro` | 教育部/国家统计局/财政部全国教育经费公告和教育经费年鉴。 |
| `regional_fiscal_macro` | 省市财政收支、教育支出、高等教育支出、GDP、人口等。 |
| `school_dimension` | 学校属性维表来源。 |

### 任务 B：建立推荐事实表和维表

后续不要继续只维护一个预算总额 CSV。建议新增或派生：

| 表 | 粒度 | 用途 |
| --- | --- | --- |
| `university_finance_fact.csv` | 学校-年份-阶段-指标 | 保存预算、决算、收入、支出、财政拨款等所有长表指标。 |
| `university_budget_snapshot.csv` | 学校-年份 | 从长表中按规则选择预算总量口径，用于趋势和排名。 |
| `university_final_account_fact.csv` | 学校-年份-决算指标 | 决算独立分析。 |
| `macro_fiscal_fact.csv` | 全国/地区-年份-指标 | 财政、教育经费、GDP、人口等背景变量。 |
| `institution_dim.csv` | 学校 | 主管部门、所在地、分类标签等维度。 |

长表推荐字段：

```text
institution_name, institution_id, supervisor, province, city, year,
fiscal_stage, document_type, table_name, metric_code, metric_name,
amount_original, unit_original, amount_yi_yuan, currency,
source_id, source_url, extraction_method, verified, notes
```

### 任务 C：按主管部门分批检索

批次建议：

1. `batch_01_c9`: C9 和已有样本，用于验证教育部/工信部/中科院混合主管部门结构。
2. `batch_02_moe_75`: 教育部直属高校，建立 2016-2026 预算/决算链接库。
3. `batch_03_miit_7`: 工信部直属高校，哈尔滨工业大学、北京航空航天大学、北京理工大学、西北工业大学、南京航空航天大学、南京理工大学、哈尔滨工程大学。
4. `batch_04_cas`: 中国科学技术大学、中国科学院大学。
5. `batch_05_local_double_first_class`: 地方双一流和省属重点高校。
6. `batch_06_macro`: 财政部、教育部、国家统计局、省市财政/教育部门宏观变量。

### 任务 D：保留旧 OCR 任务但降优先级

旧 OCR 图片抽取仍可作为历史线索和第三方发现来源，但不应继续作为官方数据主线。后续进入 processed 前，必须用官方来源校验或替换。

## 历史 OCR 任务记录（暂不作为本阶段执行项）

以下内容保留用于理解既有 OCR 数据和第三方图片来源。当前阶段重点是官方来源发现与结构设计；除非用户另行要求，不要继续按本节直接写入 processed CSV。

**已完成的工作：**

1. PaddleOCR 已对所有 10 年图片运行完毕，原始 JSON 存放在：
   - `data/interim/ocr/{year}_paddleocr.json` (year = 2017–2026)
2. 2017 和 2022 使用 strip-based OCR 方案已处理完成：
   - Strip OCR JSON: `data/interim/ocr/crops/{year}_strip_ocr.json`
   - 处理脚本: `scripts/process_strip_ocr.py`（含 `compute_global_coords`, `group_into_rows`, `extract_number` 等核心函数）
   - 2017 提取结果: `data/interim/ocr/2017_extracted.csv` — 70 条数据（决算口径）
   - 2022 提取结果: `data/interim/ocr/2022_extracted.csv` — 60 条数据
3. 其余 8 年（2018, 2019, 2020, 2021, 2023, 2024, 2025, 2026）的 `_extracted.csv` 文件目前几乎为空（仅 2-3 条零星数据），需要重新处理。

## 历史 OCR 剩余任务

### 任务 1：处理所有年份的 PaddleOCR JSON 数据

对每个年份，编写 Python 代码读取 `data/interim/ocr/{year}_paddleocr.json`，重建表格行并提取高校预算数据到 `data/interim/ocr/{year}_extracted.csv`。

**每年 OCR 数据结构要点：**

| 年份 | 图片 | 数据口径 | OCR entries | 列结构 | 特殊处理 |
|------|------|----------|-------------|--------|----------|
| 2017 | 2017.jpg | 决算 | 381 (strip) | 排名/学校/总经费/收入/支出 | 已用 strip 处理完成(70条); notes需标"决算口径" |
| 2018 | 2018.jpg | 预算 | ~54 | ? | 图片仅500x601，约10所高校可见；提取能识别的部分，notes标"图片仅包含约10所高校" |
| 2019 | 2019.jpg | 预算 | ~176 | 排名/大学/预算总经费/财政拨款收入/占比 | 正常预算数据 |
| 2020 | 2020.jpg | 决算 | ~298 | 排名/学校/总经费/收入/支出(合并) | **决算口径，不进预算主表**；OCR会合并相邻数字列如"224.05140.77128.66" |
| 2021 | 2021.png | 预算 | ~375 | 排名/学校/收入总预算/比去年增加/增长率 | 正常预算数据 |
| 2022 | 2022.jpg | 预算 | 627 (strip) | 序号/学校/预算/收入/主管部门/省市 | 已用 strip 处理完成；旧教育部直属视图可筛选，扩展全高校库不再排除工信部/中科院高校 |
| 2023 | 2023.png | 决算 | ~436 | 排名/学校/收入/支出等 | **决算口径，不进预算主表**；OCR合并数字问题 |
| 2024 | 2024.png | 预算 | ~455 | 序号/学校/2024预算/2023预算/增减/增减比 | 最干净的结构；取2024预算列 |
| 2025 | 2025.webp | 预算 | ~374 | 序号/学校/预算等 | 含工信部/中科院高校；OCR丢失小数点(如"19906"应为"199.06"); 扩展全高校库应保留并标注主管部门 |
| 2026 | 2026.png | 预算 | ~373 | 序号/学校/预算等 | 同2025：含工信部/中科院；OCR丢失小数点；扩展全高校库应保留并标注主管部门 |

**关键技术难点：**

1. **OCR 数字合并问题**：PaddleOCR 会把相邻列的数字合并为一个字符串，如 `"224.05140.77128.66"` 应拆分为 `["224.05", "140.77", "128.66"]`。需要编写一个智能数字拆分函数，识别小数点后2位+整数部分构成的自然边界。

2. **OCR 小数点丢失**：2025/2026 中 `"19906"` 应为 `"199.06"`，`"18200"` 应为 `"182.00"`。需要根据上下文判断是否补小数点。

3. **工信部/中科院高校主管部门标注**（2025 和 2026 需要）：
   - 工信部：哈尔滨工业大学, 北京航空航天大学, 北京理工大学, 西北工业大学, 南京航空航天大学, 南京理工大学, 哈尔滨工程大学
   - 中科院：中国科学技术大学, 中国科学院大学
   - 旧的 `ministry_university_budget.csv` 如果继续表示“教育部直属高校”可用筛选视图排除；新的全高校事实表必须保留这些高校，并写入 `supervisor`。

4. **行重建方法**：PaddleOCR JSON 格式为 `[bbox, [text, confidence]]`，bbox 是四个坐标点。需要按 y 坐标近似分组为行（tolerance ~10-20px），再按 x 坐标排列为列。

**PaddleOCR JSON 解析示例：**
```python
data = json.loads(path.read_text())
raw = data["raw_result"]  # list of pages
for page in raw:
    for block in page:
        bbox = block[0]       # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        text, conf = block[1]  # text string, confidence float
```

### 任务 2：修复已有 CSV 的问题

- **2017**: 清华/北大缺少排名值(应为1/2); 上海财经大学排名62为空; 中国矿业大学北京括号格式不一致; 最后3所高校(中央美术学院/中央音乐学院/中央戏剧学院)缺失
- **2022**: 广西大学不是教育部直属应删除; 中国石油大学/中国地质大学缺少校区标注

### 任务 3：合并为最终 CSV（旧流程，暂停）

将所有年份校验后的数据合并到 `data/processed/ministry_university_budget.csv`，字段 11 列：

```
year,rank,university,budget_original,budget_unit,budget_yi_yuan,source_image,source_url,extraction_method,verified,notes
```

**合并规则：**
- 2020 和 2023 的“决算图”不进预算主表；预算图仍进入预算主表
- `2018决算.jpg` 和 `2021_miit_excluded.jpg` 不处理
- `verified` 全部设为 `False`（机器抽取，待人工核对）
- `year + university` 必须唯一
- `budget_yi_yuan` 必须 > 0
- 如果原图有多列金额，`budget_yi_yuan` 只能取本年度预算口径；年度收入合计、年度支出合计、本年收入、上一年预算、财政拨款等列另存到 `data/processed/ministry_university_financial_table.csv`
- 2023 预算图列名是“本年收入/收入总计”，主表预算趋势取“收入总计”

### 任务 4：生成校验报告

输出一个简短报告，包含：
- 每年记录数
- 疑似错误行（金额异常、名称不完整等）
- 需人工复核的高校列表

## 输出字段 Schema

参考 `data/processed/schema.md`：

| 字段 | 类型 | 说明 |
|------|------|------|
| year | int | 预算年份 |
| rank | int/null | 原图排名，无则留空 |
| university | string | 规范中文全称 |
| budget_original | string | 原图金额文本如 `190.72亿元` |
| budget_unit | string | 原图单位如 `亿元` |
| budget_yi_yuan | float | 统一换算为亿元 |
| source_image | string | 对应原始图片路径 |
| source_url | string/null | 来源页面URL |
| extraction_method | string | `paddleocr` / `vision_model` / `manual` |
| verified | bool | 是否人工核对 |
| notes | string/null | 口径备注、疑似错误 |

## 来源 URL

参考 `data/raw/source_page.md`：

- 2017: https://www.edu.cn/ke_yan_yu_fa_zhan/gao_xiao_cheng_guo/gao_xiao_zi_xun/201808/t20180813_1620842.shtml
- 2018预算: https://www.antpedia.com/news/99/n-2161799.html
- 2019: https://www.sohu.com/a/311077070_503494
- 2020: https://www.eol.cn/shuju/uni/202108/t20210805_2143174.shtml
- 2021: https://m.mp.oeeee.com/a/BAAFRD000020210414468623.html
- 2023: https://www.thepaper.cn/newsDetail_forward_28427582
- 2024: https://zhuanlan.zhihu.com/p/693822580
- 2025: https://news.qq.com/rain/a/20250418A08R7100

## 现有脚本

1. `scripts/paddleocr_extract.py` — 运行 PaddleOCR 生成原始 JSON（已完成，不需要再跑）
2. `scripts/parse_paddleocr_json.py` — 简单解析 PaddleOCR JSON 为行（当前太简陋，无法处理数字合并、决算过滤等问题）
3. `scripts/process_strip_ocr.py` — 处理 strip-based OCR JSON（仅2017和2022，含核心行重建逻辑）

**建议方案**：扩展 `scripts/process_strip_ocr.py` 或新建一个综合脚本，为每个年份编写单独的 `process_{year}()` 函数，处理该年份特有的列结构和过滤逻辑。也可以统一处理框架，用年份配置字典区分各年差异。

## Python 环境

```bash
source /Users/adam/.venvs/dev/.venv/bin/activate
```

PaddleOCR 已安装在该 venv 中。

## 旧 OCR 优先级（低于官方来源发现）

1. 最高：处理 2019, 2024, 2025, 2026（预算口径，数据最完整）
2. 中等：处理 2021（预算口径）
3. 较低：处理 2018（图片不完整，仅约10所）
4. 仅记录不合并：2020, 2023（决算口径）
5. 已完成：2017, 2022（需小修复）
