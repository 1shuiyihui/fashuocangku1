# Learning Loop UI v0.8 Design

## Goal

Refactor the Streamlit interface so it supports the study loop instead of showing raw tables:

`录入训练点 -> 苏格拉底训练 -> 薄弱点分析 -> 周度/月度复盘 -> 下一轮训练`

## Constraints

- No database schema change in v0.8.0.
- No user data deletion, migration, or rewrite.
- No decorative-only buttons. Every action must either navigate to a concrete next workflow step or use existing stored data.
- Keep the current Streamlit stack and Feishu-style shell from v0.6.0.
- Preserve v0.7.0 cloud persistence behavior.

## Architecture

- Add `services/workflow.py` for business-loop derived data.
- Keep `services/storage.py` unchanged except for existing v0.7 write callback.
- Keep `services/analysis.py` as the broad stats/report module.
- Let `app.py` render workflow cards/tables and set navigation session state.

## Business Actions

The UI actions are stateful workflow actions, not visual placeholders:

- `开始训练`: stores `focus_weak_point_id`, switches to `苏格拉底训练`, and the training page defaults to that weak point.
- `查看分析`: stores a subject/knowledge focus and filters the analysis workspace.
- `进入复盘`: stores `review_focus_keyword`, switches to `周度/月度复盘`, and the review page shows this focus.
- Empty-state actions route to `错题/薄弱点录入`.

## Page Changes

### 今日学习

Replace loose metrics with a loop dashboard:

- Current loop status: 训练点数, 未训练点数, 已完成训练数.
- Next action card generated from real data.
- Priority training queue from low mastery weak points.
- Buttons route to the relevant real workflow page.

### 薄弱点分析

Replace raw dataframe blocks with:

- Filter controls for subject and mastery.
- Recent weak point worktable with Chinese columns and real `开始训练` action.
- Subject summary cards with counts and progress.
- Knowledge point ranking with `复盘这个考点` action.
- Mistake reason repair queue from the same weak point data.

### 周度/月度复盘

Keep markdown report generation, but add:

- Focus context if the user entered from analysis.
- A priority queue summary before the markdown report.
- Download still exports the generated report.

## Data Impact

No schema migration. Existing `data/fashuo.db`, `data/uploads/`, and `data/documents/` are read only during the update. Runtime user actions after deployment continue to write through the existing storage layer and v0.7 cloud snapshot callback.

## Validation

- Add tests for `services.workflow`.
- Add smoke tests for v0.8 labels/helpers.
- Run full project verification and browser smoke before release.
