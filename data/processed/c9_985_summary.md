# C9 与 985 提取说明

- C9 明细：`data/processed/c9_budget.csv`
- C9 透视表：`data/processed/c9_budget_pivot.csv`
- C9 折线图：`data/processed/figures/c9_budget_trend.png`
- C9 增速明细：`data/processed/c9_budget_growth_rate.csv`
- C9 增速透视表：`data/processed/c9_budget_growth_rate_pivot.csv`
- C9 增速图：`data/processed/figures/c9_budget_growth_rate.png`
- 985 明细：`data/processed/project_985_budget.csv`
- 985 透视表：`data/processed/project_985_budget_pivot.csv`
- 985 热力图：`data/processed/figures/project_985_budget_heatmap.png`
- 985 折线 trend 图线条过密，当前先不作为默认产物生成。

## 口径提醒

- 当前主表来自教育部直属高校预算抽取，budget_yi_yuan 只取年度预算列。
- 2016 原图同时含年度预算、年度收入合计、年度支出合计，收入/支出另存于 ministry_university_financial_table.csv。
- 2017 决算图已单独保存为 ministry_university_final_accounts.csv，未进入预算主表。
- 2020、2023 决算口径未进入主表。
- 2025/2026 原图含教育部、工信部、中国科学院，主表已按名称排除工信部/中科院高校。
- 因此 C9 中中国科学技术大学、哈尔滨工业大学目前不在主表中。

## 缺失名单

C9 缺失：中国科学技术大学、哈尔滨工业大学

985 缺失：中国科学技术大学、中央民族大学、北京理工大学、北京航空航天大学、哈尔滨工业大学、国防科技大学、西北工业大学

## C9 记录数

| 高校 | 记录数 |
| --- | ---: |
| 上海交通大学 | 11 |
| 北京大学 | 11 |
| 南京大学 | 11 |
| 复旦大学 | 11 |
| 浙江大学 | 11 |
| 清华大学 | 10 |
| 西安交通大学 | 11 |
