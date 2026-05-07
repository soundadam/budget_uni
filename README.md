# 中国高校经费数据

目标：整理中国主要高校的经费收入、支出、预算、决算和财政拨款数据，先从现有第三方汇总图抽取结构化数据，再逐步回到学校官网、主管部门和宏观财政官方来源做校验与扩展。

## 目录

```text
budget_uni/
  data/
    raw/
      images/              # legacy 第三方汇总截图/图片，按年份命名，内容不直接修改
      official_sources.csv # 官方来源注册表
      official/            # 后续保存官方网页/PDF/附件
      third_party/         # 第三方聚合来源登记
      external/            # 宏观财政、教育经费、统计年鉴等外部比较来源
      source_page.md       # 早期第三方来源页面和备注
    interim/
      ocr/                 # PaddleOCR 或多模态模型的临时 OCR 结果
      official_pdf_text/   # 官方 PDF 抽出的纯文本
      official_budget_tables/ # 官方 PDF 抽出的表候选
      official_html_budget_pages/ # 官方 HTML 正文页抽出的事实候选
      source_discovery/    # 批量来源发现的中间结果
    processed/             # 人工校验后的标准数据
  docs/
    prompts/               # 交给 Claude Code / 多模态模型的任务提示词
  notebooks/               # 后续数据分析 notebook 或 interactive py
  scripts/                 # OCR、清洗、校验、分析脚本
```

## 当前原始图片

| 文件 | 口径 |
| --- | --- |
| `data/raw/images/2016.jpg` | 2016 年教育部直属高校预算图 |
| `data/raw/images/2017.png` | 2017 年教育部直属高校预算图 |
| `data/raw/images/2017决算.jpg` | 2017 年教育部直属高校决算图，单独进入决算表 |
| `data/raw/images/2018.jpeg` | 2018 年教育部直属高校预算图 |
| `data/raw/images/2018决算.jpg` | 2018 年教育部直属高校决算图，当前先忽略 |
| `data/raw/images/2019.jpg` | 2019 年教育部直属高校预算图 |
| `data/raw/images/2020预算.jpg` | 2020 年教育部直属高校预算图 |
| `data/raw/images/2020决算.jpg` | 2020 年教育部直属高校决算图，OCR 原始结果已备份，暂不进入预算主表 |
| `data/raw/images/2021.png` | 2021 年教育部直属高校预算图 |
| `data/raw/images/2021_miit_excluded.jpg` | 2021 年工信部高校图，当前不纳入教育部直属口径 |
| `data/raw/images/2022.jpg` | 2022 年教育部直属高校预算图 |
| `data/raw/images/2023.webp` | 2023 年教育部直属高校预算图 |
| `data/raw/images/2023决算.png` | 2023 年教育部直属高校决算图，OCR 原始结果已备份，暂不进入预算主表 |
| `data/raw/images/2024.png` | 2024 年教育部直属高校预算图 |
| `data/raw/images/2025.webp` | 2025 年教育部直属高校预算图 |
| `data/raw/images/2026.png` | 2026 年教育部直属高校预算图 |

## 数据原则

1. `data/raw` 只放来源材料和来源说明，不手工改图。
2. `data/interim/ocr` 放机器抽取的中间结果，可以反复生成。
3. `data/processed` 只放人工校验后的标准表。
4. 一行数据表示“某一年、某高校、某项预算指标”的记录。
5. 所有金额保留原图单位，并额外提供统一为亿元的数值列，便于分析。
6. `data/raw/images` 是 legacy 第三方汇总图来源，继续用于追溯现有 OCR 主表，但后续校验应优先使用 `official_sources.csv` 中登记的官方来源。
7. 后续研究对象扩展为“中国各大高校经费”，不再限定教育部直属高校；工信部、中科院、地方高校、部省合建高校都可以进入来源注册表和横向比较表。
8. 当前教育部直属预算主表范围是 `2016.jpg`、`2017.png`、`2018.jpeg`、`2019.jpg`、`2020预算.jpg`、`2021.png` 到 `2026.png`；决算图和 `2021_miit_excluded.jpg` 不进入该主表。
9. 决算数据另存为 `data/processed/ministry_university_final_accounts.csv`，避免预算趋势分析混入口径差异。
10. 如果原图或官方 PDF 同时包含年度预算、收入总计、本年收入、本年支出、财政拨款、上年结转、结转下年等列，必须分字段保存，不得把不同统计名目混成一个时间序列。
11. 2023 原图列为“本年收入/收入总计”，预算趋势主表取“收入总计”，不是“本年收入”。

## 建议标准表

主表建议保存为：

```text
data/processed/ministry_university_budget.csv
```

字段见 `data/processed/schema.md`。

全字段明细表保存为：

```text
data/processed/ministry_university_financial_table.csv
```

## 下一步工作流

1. 用 `docs/prompts/claude_ocr_extraction.md` 交给 Claude Code 生成或完善抽取流程。
2. 优先在 dev 环境下跑 `scripts/paddleocr_extract.py` 得到原始 OCR JSON。
3. 对 OCR 或多模态识别结果做逐年人工校验，输出 `data/processed/ministry_university_budget.csv`。
4. 在 `notebooks/` 里做年度总量、排名变化、同比增速和高校分组分析。

官方来源补全时，预算和决算必须同步检索。可用下面的脚本检查 C9 在 2013-2026 年的预算/决算覆盖缺口：

```zsh
source /Users/adam/.venvs/dev/.venv/bin/activate
python budget_uni/scripts/report_official_source_coverage.py
```

报告输出到 `data/processed/c9_official_source_coverage_2013_2026.md`。预算、决算和主管部门汇总口径要分开入表，不能把决算值补进预算趋势。

## 官方 HTML 预算页抽取

`scripts/official_html_extract.py` 读取 `data/raw/official_sources.csv`，筛选 `source_level=official_page` 且 `document_type=budget` 的官方 HTML 正文页，输出与 `official_finance_fact_candidates.csv` 同列的候选表：

```zsh
source /Users/adam/.venvs/dev/.venv/bin/activate
python scripts/official_html_extract.py
```

当前最小可用样本优先覆盖上海交通大学 2016 官方 HTML 页面，可单页复现：

```zsh
python scripts/official_html_extract.py --only-url https://gk.sjtu.edu.cn/Phone/View/502 --sleep 0
```

输出位置：`data/interim/official_html_budget_pages/official_html_finance_fact_candidates.csv`。其中 `source_pdf` 留空，`source_url` 保留官方 HTML 页面地址。
