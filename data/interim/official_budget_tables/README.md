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
python budget_uni/scripts/process_all_official_pdfs.py --ocr-empty-pdfs
```

已处理 7 个 2026 年官方预算 PDF：

| 学校 | PDF 状态 | 抽取方式 | 字段候选数 | 备注 |
| --- | --- | --- | ---: | --- |
| 清华大学 | 已下载 | PyMuPDF 表格候选 | 28 | 需人工复核重复表格行。 |
| 北京大学 | 已下载 | PaddleOCR + 正文正则 | 11 | 原 PDF 为扫描/图片层，无文本层。 |
| 浙江大学 | 已下载 | PyMuPDF 正文正则 | 11 | 有文本层但无可识别表格线。 |
| 上海交通大学 | 已下载 | PyMuPDF 表格候选 | 22 | 需人工复核重复表格行。 |
| 复旦大学 | 已下载 | PyMuPDF 表格候选 | 35 | 需人工复核重复表格行。 |
| 南京大学 | 已下载 | PyMuPDF 表格候选 | 38 | 需人工复核重复表格行。 |
| 北京理工大学 | 已下载 | PyMuPDF 表格候选 | 16 | 工信部直属高校样本。 |

总计：

| 输出 | 数量 |
| --- | ---: |
| PDF | 7 |
| 长表事实候选行 | 161 |
| 已覆盖学校 | 7 |

当前核心字段已经覆盖 `收入总计`、`本年收入合计`、`财政拨款/一般公共预算拨款收入`、`事业收入`、`其他收入`、`上年结转`、`使用非财政拨款结余`、`本年支出合计`、`支出总计` 等。但这些仍是机器候选，进入 processed 前必须核对 PDF 原表。
