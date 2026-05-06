# Raw Data Layout

本目录只保存原始来源、来源登记和未清洗的下载材料。

## Source Tiers

| 目录/文件 | 用途 | 说明 |
| --- | --- | --- |
| `images/` | legacy 第三方汇总图 | 当前 OCR 主表来源；这些图片大多来自第三方统计页面，不等同于学校官网原始预算 PDF。 |
| `third_party/` | 第三方来源登记 | 后续把排行榜、新闻、公众号转载、聚合图表等来源放这里，只作为发现线索或交叉检查。 |
| `official_sources.csv` | 官方来源注册表 | 学校信息公开网、财务处、主管部门、财政部、教育部、国家统计局等官方入口。 |
| `official/` | 官方材料 | 后续下载的官方网页快照、PDF、附件索引等放这里。 |
| `external/` | 宏观和横向比较来源 | 全国财政、教育经费、GDP、CPI、省级财政等高校外部比较指标。 |
| `source_page.md` | legacy 来源备注 | 早期第三方页面记录，保留用于追溯，不再作为唯一来源清单。 |

## Recommended Flow

1. `official_sources.csv` 先登记来源，不急着覆盖现有数据。
2. 官方 PDF 下载到 `official/pdfs/`。
3. 官方 PDF 抽出的纯文本放到 `../interim/official_pdf_text/`。
4. 官方 PDF 抽出的表候选放到 `../interim/official_budget_tables/`。
5. 经过字段口径确认后，再进入 `../processed/`。

## Scope

项目主题已扩展为“中国各大高校经费收入与支出”。后续不再限定教育部直属高校，工信部、中科院、地方高校、部省合建高校都可以进入官方来源注册表。分析时通过 `governing_body`、`province`、`university_group` 等维度区分口径。
