# Claude Code 提示词：高校预算图片抽取与校验

你在本地仓库 `/Users/adam/projects/statistics` 工作。目标是把 `budget_uni/data/raw/images/` 中教育部直属高校近年预算图片抽取成可分析的 CSV，并校验识别错误。

## 任务边界

1. 原始图片不要修改。
2. `2021_miit_excluded.jpg` 是工信部高校预算图，当前不要纳入教育部直属高校主表。
3. `2018决算.jpg` 是 2018 年决算图，当前先忽略，不要纳入预算主表。
4. 机器识别的中间结果放在 `budget_uni/data/interim/ocr/`。
5. 人工校验后的最终结果放在 `budget_uni/data/processed/ministry_university_budget.csv`。
6. 如果某张图识别不完整，先保留可追溯的中间结果，不要凭空补数。

## 推荐工作流

1. 读取 `budget_uni/README.md` 和 `budget_uni/data/processed/schema.md`，确认字段约定。
2. 对预算图片逐年抽取表格：`2017.jpg`、`2018.jpg`、`2019.jpg`、`2020.jpg`、`2021.png`、`2022.jpg`、`2023.png`、`2024.png`、`2025.webp`、`2026.png`。
   不要处理 `2018决算.jpg` 和 `2021_miit_excluded.jpg`。
3. 优先使用 PaddleOCR。如果 PaddleOCR 对长图/密集表格效果差，可以把图片切块后识别，或交给 DeepSeek V4 Pro 多模态识别。
4. 每年生成一个中间文件：
   - `budget_uni/data/interim/ocr/2017_paddleocr.json`
   - `budget_uni/data/interim/ocr/2017_extracted.csv`
5. 对每年的 CSV 做校验：
   - 高校名称是否完整；
   - 金额是否漏小数点；
   - 排名是否与金额降序一致；
   - OCR 是否把 `0/O`、`1/I`、中文括号、单位识别错；
   - 是否混入非教育部直属高校、决算数据或排除图片。
6. 合并校验后的数据到：
   - `budget_uni/data/processed/ministry_university_budget.csv`

## 输出字段

最终 CSV 必须包含这些列：

```csv
year,rank,university,budget_original,budget_unit,budget_yi_yuan,source_image,source_url,extraction_method,verified,notes
```

## PaddleOCR 实现建议

可以先完善或调用：

```zsh
source /Users/adam/.venvs/dev/.venv/bin/activate
python budget_uni/scripts/paddleocr_extract.py --image budget_uni/data/raw/images/2024.png --year 2024
```

脚本应该至少输出原始 OCR JSON，后续再根据 OCR 文本和坐标重建表格。

## 多模态模型识别提示词

如果使用 DeepSeek V4 Pro 多模态，请对每张图使用下面的提示词：

```text
请从这张图片中提取高校预算表格。只提取教育部直属高校预算数据，不要加入图片外的知识。如果图片是决算表、工信部高校表或非预算口径，请返回空 CSV，只保留表头。

输出严格的 CSV，列为：
year,rank,university,budget_original,budget_unit,budget_yi_yuan,notes

要求：
1. year 使用图片对应年份。
2. rank 如果图片有排名就填写整数，没有就留空。
3. university 使用图片中的高校中文名称，尽量保持完整。
4. budget_original 保留图片原文金额和单位。
5. budget_unit 填写图片单位，例如 亿元、万元。
6. budget_yi_yuan 统一换算为亿元，保留合理小数。
7. 对不确定的字符或数值，在 notes 中写明“待核对：...”。
8. 不要输出解释性段落，只输出 CSV。
```

## 交付标准

1. 至少每张图片都有一个可追溯的 OCR 或多模态中间结果。
2. 最终 CSV 的每行都能追溯到 `source_image`。
3. 对不确定数据保留 `verified=false` 和 `notes`，不要伪装成已校验。
4. 给出一个简短校验报告，列出每年记录数、疑似错误行、需要人工复核的高校。
