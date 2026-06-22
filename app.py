from __future__ import annotations

import html
import hashlib
import importlib
import json
from pathlib import Path
from sqlite3 import IntegrityError

import pandas as pd
import streamlit as st

from services.ai_client import AIClient, AIConfigurationError
from services.analysis import build_review_report, compute_weak_point_stats
from services.backup import collect_table_counts, create_backup, integrity_check, list_backups
from services.cloud_sync import (
    CloudSyncConfig,
    CloudSyncError,
    GitHubSnapshotSync,
    get_cloud_sync_status_label,
    load_cloud_sync_config,
    validate_cloud_sync_config,
)
from services.course_generator import CourseGenerationError, generate_course, normalize_lessons
from services.document_processor import OCRUnavailableError, UnsupportedDocumentError, process_document_file
from services.error_analysis import build_error_analysis, build_review_drill_pack
from services.migrations import SchemaTooNewError, apply_migrations, get_schema_version, list_applied_migrations
from services.prompts import build_training_prompt
from services.provenance import save_provenance_files
from services.rag import format_rag_context, search_chunks
from services.storage import Storage
from services.versioning import APP_VERSION, SUPPORTED_SCHEMA_VERSION
from services.workflow import build_learning_loop_state, build_review_dashboard_state


DATA_ROOT = Path("data")
PROVENANCE_ROOT = DATA_ROOT / "provenance"
FOCUS_WEAK_POINT_KEY = "focus_weak_point_id"
REVIEW_FOCUS_KEY = "review_focus_keyword"
ANALYSIS_SUBJECT_FILTER_KEY = "analysis_subject_filter"
WORKFLOW_LOOP_STEPS = ["录入训练点", "苏格拉底训练", "薄弱点分析", "周度/月度复盘", "下一轮训练"]


SUBJECTS = ["刑法", "民法", "法理", "宪法", "法制史"]
QUESTION_TYPES = ["单选", "多选", "简答", "论述", "案例分析"]
MISTAKE_REASONS = ["概念混淆", "要件遗漏", "法条不熟", "案例事实误判", "记忆不牢", "表达不规范"]
MASTERY_LEVELS = ["陌生", "模糊", "基本会", "熟练"]
PAGES = ["今日学习", "错题/薄弱点录入", "苏格拉底训练", "资料知识库", "模板管理", "薄弱点分析", "周度/月度复盘", "系统与备份"]
NAV_GROUPS = [
    ("学习", ["今日学习", "错题/薄弱点录入", "苏格拉底训练"]),
    ("资料", ["资料知识库", "模板管理"]),
    ("分析", ["薄弱点分析", "周度/月度复盘"]),
    ("系统", ["系统与备份"]),
]
PAGE_SUBTITLES = {
    "今日学习": "从今日任务、薄弱点和复盘建议开始。",
    "错题/薄弱点录入": "快速记录实体书错题、薄弱考点和错因。",
    "苏格拉底训练": "围绕一个训练点进行连续追问。",
    "资料知识库": "上传资料、检索片段，并生成可执行训练计划。",
    "模板管理": "维护不同题型和科目的追问模板。",
    "薄弱点分析": "查看科目、考点和错因的高频分布。",
    "周度/月度复盘": "生成阶段复盘和下一轮训练安排。",
    "系统与备份": "检查版本、数据库状态和备份。",
}
BEGINNER_MODE_DEFAULT = True
COURSE_GENERATION_SECTION_TITLE = "3. 生成可执行训练计划并导入训练点"
LESSON_SUBJECT_LABEL = "训练点科目"
IMPORT_LESSON_BUTTON_LABEL = "导入为训练点"
APP_GUIDE_STEPS = [
    "录入薄弱点，或从生成课程中导入训练点。",
    "进入苏格拉底训练，用追问暴露真实薄弱处。",
    "每周或每月查看复盘，按高频考点和错因安排下一轮训练。",
]
ENTRY_WORKFLOW_STEPS = ["上传或拍照", "结构化训练点", "AI 抽取与确认"]
KNOWLEDGE_WORKFLOW_STEPS = ["上传并建立索引", "检索资料片段", "生成可执行训练计划", "导入为训练点"]
TRAINING_PANEL_SECTIONS = ["模板提示", "参考资料片段", "掌握度评估", "本次训练记录"]
DEFAULT_MIN_DIALOGUE_ROUNDS = 3
MAX_DIALOGUE_ROUND_OPTIONS = ["不限制", "3轮", "4轮", "5轮", "6轮", "8轮", "10轮", "15轮", "20轮"]
REVIEW_WORKFLOW_STEPS = ["选择周期", "查看训练队列", "定位高频问题", "安排下一轮训练", "导出复盘"]
REVIEW_DASHBOARD_SECTIONS = ["学习概况", "高频薄弱考点", "高频错因", "下一轮训练计划"]
ERROR_ANALYSIS_SECTIONS = ["错误还原", "根因证据", "复盘练习", "变式练习", "溯源记录"]
SIDEBAR_STATUS_TITLE = "系统状态"
SIDEBAR_WORKFLOW_TITLE = "学习闭环"
APP_SHELL_STYLE = """
<style>
html, body, [data-testid="stAppViewContainer"] {
    background: #f5f7fb;
}
[data-testid="stSidebar"] {
    background: #f7f8fb;
    border-right: 1px solid #e5e7ef;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 24px;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #4b5563;
}
[data-testid="stSidebar"] .stButton > button {
    background: #ffffff;
    border: 1px solid #dfe3eb;
    color: #374151;
    justify-content: flex-start;
}
[data-testid="stSidebar"] .stButton > button p {
    color: #374151;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #eef4ff;
    border-color: #bfdbfe;
    color: #1d4ed8;
}
[data-testid="stSidebar"] .stButton > button:hover p {
    color: #1d4ed8;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: #2563eb;
    border-color: #2563eb;
    color: #ffffff;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] p {
    color: #ffffff;
}
.block-container {
    max-width: 1180px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}
.sidebar-brand {
    background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    margin: 0 0 12px;
    padding: 14px 14px 15px;
}
.sidebar-brand-title {
    color: #111827;
    font-size: 19px;
    font-weight: 750;
    line-height: 1.2;
}
.sidebar-brand-subtitle {
    color: #6b7280;
    font-size: 12px;
    margin-top: 4px;
}
.sidebar-status-card,
.sidebar-workflow-card {
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    margin: 10px 0 14px;
    padding: 12px 13px;
}
.sidebar-card-title {
    color: #111827;
    font-size: 13px;
    font-weight: 760;
    margin-bottom: 8px;
}
.sidebar-status-row {
    align-items: center;
    border-top: 1px solid #eef0f5;
    color: #4b5563;
    display: flex;
    font-size: 12px;
    justify-content: space-between;
    padding: 8px 0 0;
    margin-top: 7px;
}
.sidebar-status-row:first-of-type {
    border-top: 0;
    margin-top: 0;
    padding-top: 0;
}
.sidebar-status-value {
    color: #1d4ed8;
    font-weight: 760;
    text-align: right;
}
.sidebar-flow-list {
    counter-reset: sidebarFlow;
    list-style: none;
    margin: 0;
    padding: 0;
}
.sidebar-flow-list li {
    color: #4b5563;
    font-size: 12px;
    line-height: 1.55;
    margin: 7px 0;
    padding-left: 24px;
    position: relative;
}
.sidebar-flow-list li::before {
    background: #eaf2ff;
    border-radius: 999px;
    color: #1d4ed8;
    content: counter(sidebarFlow);
    counter-increment: sidebarFlow;
    font-size: 11px;
    font-weight: 760;
    height: 17px;
    left: 0;
    line-height: 17px;
    position: absolute;
    text-align: center;
    top: 1px;
    width: 17px;
}
.sidebar-group-title {
    color: #8a94a6;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: .02em;
    margin: 16px 0 6px;
}
.app-topbar {
    align-items: center;
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    display: flex;
    justify-content: space-between;
    margin: 0 0 18px;
    padding: 18px 22px;
}
.app-topbar-meta {
    color: #2563eb;
    font-size: 13px;
    font-weight: 650;
    margin-bottom: 4px;
}
.app-topbar h1 {
    color: #111827;
    font-size: 28px;
    letter-spacing: 0;
    line-height: 1.18;
    margin: 0;
}
.app-topbar p {
    color: #6b7280;
    font-size: 14px;
    margin: 8px 0 0;
}
.app-topbar-status {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: flex-end;
}
.status-pill {
    background: #f3f4f6;
    border: 1px solid #e5e7eb;
    border-radius: 999px;
    color: #374151;
    font-size: 12px;
    font-weight: 650;
    padding: 6px 10px;
    white-space: nowrap;
}
.status-pill-primary {
    background: #eaf2ff;
    border-color: #bfdbfe;
    color: #1d4ed8;
}
.workbench-grid {
    display: grid;
    gap: 14px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 8px 0 18px;
}
.kpi-grid-4 {
    grid-template-columns: repeat(4, minmax(0, 1fr));
}
.workbench-card {
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    padding: 16px 18px;
}
.workbench-card-label {
    color: #6b7280;
    font-size: 13px;
    margin-bottom: 8px;
}
.workbench-card-value {
    color: #111827;
    font-size: 30px;
    font-weight: 760;
    line-height: 1;
}
.next-action-card {
    background: #ffffff;
    border: 1px solid #dbeafe;
    border-left: 4px solid #2563eb;
    border-radius: 8px;
    margin: 10px 0 18px;
    padding: 16px 18px;
}
.next-action-title {
    color: #111827;
    font-size: 16px;
    font-weight: 750;
    margin-bottom: 6px;
}
.next-action-detail {
    color: #4b5563;
    font-size: 14px;
}
.priority-list {
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    padding: 6px 16px;
}
.priority-row {
    border-bottom: 1px solid #eef0f5;
    color: #374151;
    padding: 11px 0;
}
.priority-row:last-child {
    border-bottom: 0;
}
.loop-steps {
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    margin: 8px 0 18px;
}
.loop-step {
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    color: #374151;
    font-size: 13px;
    font-weight: 650;
    padding: 12px 14px;
}
.loop-step-index {
    color: #2563eb;
    font-size: 12px;
    margin-bottom: 4px;
}
.workflow-table {
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    margin: 10px 0 18px;
    overflow: hidden;
}
.workflow-row {
    align-items: center;
    border-bottom: 1px solid #eef0f5;
    display: grid;
    gap: 12px;
    grid-template-columns: 0.75fr 0.75fr 1.35fr 2fr 0.8fr 0.9fr;
    padding: 13px 16px;
}
.workflow-row:last-child {
    border-bottom: 0;
}
.workflow-header {
    background: #f8fafc;
    color: #6b7280;
    font-size: 12px;
    font-weight: 700;
}
.workflow-main {
    color: #111827;
    font-weight: 700;
}
.workflow-muted {
    color: #6b7280;
    font-size: 13px;
}
.chip {
    border-radius: 999px;
    display: inline-block;
    font-size: 12px;
    font-weight: 700;
    padding: 4px 9px;
}
.chip-blue {
    background: #eaf2ff;
    color: #1d4ed8;
}
.chip-green {
    background: #eaf8f0;
    color: #15803d;
}
.chip-amber {
    background: #fff7ed;
    color: #c2410c;
}
.chip-gray {
    background: #f3f4f6;
    color: #4b5563;
}
.process-strip {
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 8px 0 16px;
    padding: 12px;
}
.process-strip-four {
    grid-template-columns: repeat(4, minmax(0, 1fr));
}
.process-step {
    background: #f8fafc;
    border: 1px solid #eef2f7;
    border-radius: 8px;
    padding: 12px 13px;
}
.process-step-index {
    color: #2563eb;
    font-size: 12px;
    font-weight: 760;
    margin-bottom: 3px;
}
.process-step-title {
    color: #111827;
    font-size: 14px;
    font-weight: 760;
}
.section-panel {
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    margin: 10px 0 16px;
    padding: 16px;
}
.section-panel-soft {
    background: #f8fafc;
}
.section-panel-title {
    color: #111827;
    font-size: 16px;
    font-weight: 760;
    margin-bottom: 5px;
}
.section-panel-subtitle {
    color: #6b7280;
    font-size: 13px;
    line-height: 1.55;
    margin-bottom: 12px;
}
.entry-workspace-grid {
    display: grid;
    gap: 14px;
    grid-template-columns: 1fr 1.4fr 1fr;
    margin: 8px 0 18px;
}
.entry-ai-card,
.training-control-card,
.source-result-card,
.lesson-plan-card,
.document-list-card {
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    padding: 14px 15px;
}
.entry-ai-row {
    align-items: center;
    border-bottom: 1px solid #eef0f5;
    display: flex;
    gap: 10px;
    justify-content: space-between;
    padding: 9px 0;
}
.entry-ai-row:last-child {
    border-bottom: 0;
}
.entry-ai-label,
.source-result-meta,
.lesson-meta {
    color: #6b7280;
    font-size: 12px;
}
.entry-ai-value,
.source-result-title,
.lesson-plan-title {
    color: #111827;
    font-weight: 760;
}
.training-cockpit-grid {
    display: grid;
    gap: 16px;
    grid-template-columns: minmax(0, 1.7fr) minmax(320px, .8fr);
    margin: 10px 0 18px;
}
.training-context-bar {
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    display: grid;
    gap: 12px;
    grid-template-columns: 1.2fr 1fr 1.2fr .75fr;
    margin: 8px 0 18px;
    padding: 14px 16px;
}
.training-context-item {
    border-right: 1px solid #eef0f5;
    padding-right: 12px;
}
.training-context-item:last-child {
    border-right: 0;
}
.training-context-label {
    color: #6b7280;
    font-size: 12px;
    margin-bottom: 4px;
}
.training-context-value {
    color: #111827;
    font-size: 15px;
    font-weight: 760;
}
.chat-shell {
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    min-height: 420px;
    padding: 14px 16px;
}
.training-timeline {
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin: 10px 0 18px;
    padding: 12px;
}
.timeline-node {
    background: #f8fafc;
    border: 1px solid #eef2f7;
    border-radius: 8px;
    padding: 11px 12px;
}
.knowledge-workflow-grid {
    display: grid;
    gap: 14px;
    grid-template-columns: minmax(280px, 1fr) minmax(320px, 1.1fr) minmax(320px, 1fr);
    margin: 10px 0 18px;
}
.document-row,
.source-result-card {
    margin: 8px 0;
}
.document-row {
    align-items: center;
    background: #f8fafc;
    border: 1px solid #eef2f7;
    border-radius: 8px;
    display: flex;
    gap: 10px;
    justify-content: space-between;
    padding: 10px 12px;
}
.document-title {
    color: #111827;
    font-weight: 720;
}
.document-meta {
    color: #6b7280;
    font-size: 12px;
    margin-top: 3px;
}
.source-result-card {
    background: #f8fafc;
}
.lesson-plan-grid {
    display: grid;
    gap: 14px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 10px 0 18px;
}
.lesson-plan-card {
    display: flex;
    flex-direction: column;
    gap: 9px;
}
.lesson-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}
.review-dashboard-grid {
    display: grid;
    gap: 14px;
    grid-template-columns: 1.25fr .95fr;
    margin: 10px 0 18px;
}
.review-summary-card,
.review-plan-card,
.review-insight-card {
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    padding: 15px 16px;
}
.review-summary-card {
    min-height: 260px;
}
.review-period-bar {
    align-items: center;
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    justify-content: space-between;
    margin: 8px 0 16px;
    padding: 12px 14px;
}
.review-period-title {
    color: #111827;
    font-size: 15px;
    font-weight: 760;
}
.review-period-subtitle {
    color: #6b7280;
    font-size: 12px;
    margin-top: 2px;
}
.progress-row {
    margin: 10px 0;
}
.progress-row-top {
    align-items: center;
    display: flex;
    justify-content: space-between;
    color: #374151;
    font-size: 13px;
    margin-bottom: 5px;
}
.progress-track {
    background: #edf1f7;
    border-radius: 999px;
    height: 8px;
    overflow: hidden;
}
.progress-fill {
    background: #2563eb;
    border-radius: 999px;
    height: 8px;
}
.review-insight-grid {
    display: grid;
    gap: 14px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 10px 0 18px;
}
.review-insight-row {
    border-bottom: 1px solid #eef0f5;
    padding: 10px 0;
}
.review-insight-row:last-child {
    border-bottom: 0;
}
.review-plan-grid {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 10px 0 18px;
}
.review-plan-card {
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.review-plan-day {
    color: #2563eb;
    font-size: 12px;
    font-weight: 760;
}
.review-plan-title {
    color: #111827;
    font-size: 15px;
    font-weight: 760;
}
.review-checklist {
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin: 8px 0 18px;
}
.review-check-item {
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    color: #374151;
    font-size: 13px;
    font-weight: 650;
    padding: 12px 13px;
}
.loop-card-grid {
    display: grid;
    gap: 14px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin: 8px 0 18px;
}
.loop-card {
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    padding: 15px 16px;
}
.loop-card-title {
    color: #111827;
    font-size: 16px;
    font-weight: 750;
    margin-bottom: 6px;
}
.loop-card-meta {
    color: #6b7280;
    font-size: 13px;
}
.rank-row {
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    margin: 8px 0;
    padding: 13px 15px;
}
.rank-title {
    color: #111827;
    font-weight: 750;
}
.rank-meta {
    color: #6b7280;
    font-size: 13px;
    margin-top: 4px;
}
div[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e5e7ef;
    border-radius: 8px;
    padding: 14px 16px;
}
div[data-testid="stExpander"] {
    background: #ffffff;
    border-radius: 8px;
}
.stButton > button,
.stDownloadButton > button {
    border-radius: 8px;
}
.fashuo-guide {
    animation: fashuoGuideIn 420ms ease-out;
    border: 1px solid #d7e8ff;
    border-radius: 8px;
    background: #ffffff;
    padding: 16px 18px;
    margin: 8px 0 18px;
}
.fashuo-guide-title {
    font-weight: 700;
    margin-bottom: 8px;
}
.fashuo-guide ol {
    margin-bottom: 0;
    padding-left: 22px;
}
@keyframes fashuoGuideIn {
    from { opacity: 0; transform: translateY(-8px); }
    to { opacity: 1; transform: translateY(0); }
}
@media (max-width: 900px) {
    .app-topbar {
        align-items: flex-start;
        flex-direction: column;
        gap: 14px;
    }
    .app-topbar-status {
        justify-content: flex-start;
    }
    .workbench-grid,
    .kpi-grid-4 {
        grid-template-columns: 1fr;
    }
    .loop-steps,
    .loop-card-grid,
    .process-strip,
    .knowledge-workflow-grid,
    .entry-workspace-grid,
    .training-cockpit-grid,
    .training-context-bar,
    .training-timeline,
    .lesson-plan-grid,
    .review-dashboard-grid,
    .review-insight-grid,
    .review-plan-grid,
    .review-checklist {
        grid-template-columns: 1fr;
    }
    .workflow-row {
        grid-template-columns: 1fr;
    }
}
</style>
"""


def get_next_action(
    weak_points: list[dict[str, object]],
    sessions: list[dict[str, object]],
) -> dict[str, str]:
    if not weak_points:
        return {
            "title": "先录入一个薄弱点",
            "detail": "只需要填写科目、题型、考点、错因和掌握度，照片和题干可以后补。",
            "page": "错题/薄弱点录入",
        }

    active_sessions = [session for session in sessions if session.get("status") == "active"]
    if active_sessions:
        return {
            "title": "继续当前训练",
            "detail": "已有训练正在进行，可以继续回答，也可以结束训练并保存复盘。",
            "page": "苏格拉底训练",
        }

    finished_sessions = [session for session in sessions if session.get("status") == "finished"]
    if finished_sessions:
        return {
            "title": "看一次复盘",
            "detail": "已有训练记录，先查看周度/月度复盘，再决定下一轮训练重点。",
            "page": "周度/月度复盘",
        }

    first_point = weak_points[0]
    return {
        "title": "开始一次苏格拉底训练",
        "detail": f"建议先训练：{first_point.get('knowledge_point', '')}（{first_point.get('mastery_level', '')}）。",
        "page": "苏格拉底训练",
    }


def should_show_prompt_editor(beginner_mode: bool, advanced_enabled: bool) -> bool:
    return advanced_enabled or not beginner_mode


def get_page_group(page: str) -> str:
    for group_name, pages in NAV_GROUPS:
        if page in pages:
            return group_name
    return NAV_GROUPS[0][0]


def get_ai_status_label(config: dict[str, str]) -> str:
    return "AI 已配置" if config.get("api_key") else "AI 未配置"


def get_focused_weak_point_index(rows: list[dict[str, object]], weak_point_id: object) -> int:
    if not rows:
        return 0
    try:
        target_id = int(weak_point_id)
    except (TypeError, ValueError):
        return 0
    for index, row in enumerate(rows):
        try:
            if int(row.get("id", -1)) == target_id:
                return index
        except (TypeError, ValueError):
            continue
    return 0


def route_to_page(page: str) -> None:
    st.session_state["current_page"] = page
    st.rerun()


def route_to_training(weak_point_id: int) -> None:
    st.session_state[FOCUS_WEAK_POINT_KEY] = weak_point_id
    st.session_state["current_page"] = "苏格拉底训练"
    st.rerun()


def route_to_review(keyword: str) -> None:
    st.session_state[REVIEW_FOCUS_KEY] = keyword
    st.session_state["current_page"] = "周度/月度复盘"
    st.rerun()


def escape_html(value: object) -> str:
    return html.escape(str(value), quote=True)


def get_app_version() -> str:
    try:
        import services.versioning as versioning_module

        return str(importlib.reload(versioning_module).APP_VERSION)
    except Exception:
        return APP_VERSION


def normalize_min_dialogue_rounds(value: object) -> int:
    try:
        rounds = int(value)
    except (TypeError, ValueError):
        rounds = DEFAULT_MIN_DIALOGUE_ROUNDS
    return max(DEFAULT_MIN_DIALOGUE_ROUNDS, rounds)


def normalize_max_dialogue_rounds(value: object, min_rounds: int) -> int | None:
    min_rounds = normalize_min_dialogue_rounds(min_rounds)
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "不限制":
        return None
    digits = "".join(char for char in text if char.isdigit())
    if not digits:
        return None
    return max(min_rounds, int(digits))


def count_student_dialogue_rounds(messages: list[dict[str, object]]) -> int:
    return sum(1 for message in messages if message.get("role") == "user")


def can_finish_training(completed_rounds: int, min_rounds: int) -> bool:
    return completed_rounds >= normalize_min_dialogue_rounds(min_rounds)


def format_round_policy_label(min_rounds: int, max_rounds: int | None) -> str:
    min_rounds = normalize_min_dialogue_rounds(min_rounds)
    if max_rounds is None:
        return f"最少 {min_rounds} 轮｜不限制"
    return f"最少 {min_rounds} 轮｜最多 {max(max_rounds, min_rounds)} 轮"


def format_error_analysis_markdown(weak_point: dict[str, object], analysis: dict[str, object]) -> str:
    return "\n".join(
        [
            f"# 错因还原：{weak_point.get('knowledge_point', '')}",
            "",
            f"- 科目：{weak_point.get('subject', '')}",
            f"- 题型：{weak_point.get('question_type', '')}",
            f"- 错误位置：{analysis.get('error_location', '')}",
            f"- 根因：{analysis.get('root_cause', '')}",
            "",
            "## 根因证据",
            str(analysis.get("evidence", "")),
            "",
            "## 复盘练习",
            str(analysis.get("review_drill", "")),
            "",
            "## 变式练习",
            str(analysis.get("variant_drill", "")),
        ]
    )


def record_provenance_event(
    store: Storage,
    entity_type: str,
    entity_id: int | None,
    event_type: str,
    input_payload: dict[str, object],
    output_text: str,
    metadata: dict[str, object] | None = None,
) -> int | None:
    try:
        saved = save_provenance_files(
            PROVENANCE_ROOT,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            input_payload=input_payload,
            output_text=output_text,
            metadata=metadata,
        )
        return store.create_provenance_event(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "event_type": event_type,
                "input_path": str(saved["input_path"]),
                "output_path": str(saved["output_path"]),
                "metadata": saved["metadata"],
            }
        )
    except Exception as exc:
        st.warning(f"溯源文件保存失败：{exc}")
        return None


def create_or_refresh_error_analysis(
    store: Storage,
    weak_point: dict[str, object],
    session_context: dict[str, object] | None = None,
    event_type: str = "weak_point_error_analysis",
) -> dict[str, object]:
    weak_point_id = int(weak_point["id"])
    analysis = build_error_analysis(weak_point, session_context=session_context)
    payload = {"weak_point_id": weak_point_id, **analysis}
    latest = store.get_latest_error_analysis(weak_point_id)
    if latest:
        store.update_error_analysis(int(latest["id"]), payload)
        analysis_id = int(latest["id"])
    else:
        analysis_id = store.create_error_analysis(payload)

    saved_analysis = {
        **analysis,
        "id": analysis_id,
        "weak_point_id": weak_point_id,
        "subject": weak_point.get("subject", ""),
        "question_type": weak_point.get("question_type", ""),
        "knowledge_point": weak_point.get("knowledge_point", ""),
        "mistake_reason": weak_point.get("mistake_reason", ""),
        "mastery_level": weak_point.get("mastery_level", ""),
    }
    output_text = format_error_analysis_markdown(weak_point, saved_analysis)
    record_provenance_event(
        store,
        entity_type="weak_point",
        entity_id=weak_point_id,
        event_type=event_type,
        input_payload={"weak_point": weak_point, "session_context": session_context or {}},
        output_text=output_text,
        metadata={"analysis_id": analysis_id},
    )
    return saved_analysis


def render_error_analysis_card(
    analysis: dict[str, object],
    key_prefix: str,
    events: list[dict[str, object]] | None = None,
) -> None:
    with st.container(border=True):
        st.markdown(f"**{analysis.get('subject', '')}｜{analysis.get('knowledge_point', '')}**")
        chip_cols = st.columns(3)
        chip_cols[0].caption(f"{ERROR_ANALYSIS_SECTIONS[0]}：{analysis.get('error_location', '')}")
        chip_cols[1].caption(f"{ERROR_ANALYSIS_SECTIONS[1]}：{analysis.get('root_cause', '')}")
        chip_cols[2].caption(f"状态：{analysis.get('status', '')}")
        st.write(str(analysis.get("evidence", "")))
        drill_col, variant_col = st.columns(2)
        with drill_col:
            st.markdown(f"**{ERROR_ANALYSIS_SECTIONS[2]}**")
            st.write(str(analysis.get("review_drill", "")))
        with variant_col:
            st.markdown(f"**{ERROR_ANALYSIS_SECTIONS[3]}**")
            st.write(str(analysis.get("variant_drill", "")))
        if events:
            with st.expander(f"{ERROR_ANALYSIS_SECTIONS[4]}（{len(events)} 条）", expanded=False):
                for event in events[:6]:
                    st.caption(
                        f"#{event.get('id')} {event.get('event_type')}｜输入：{event.get('input_path')}｜输出：{event.get('output_path')}"
                    )
        if st.button("围绕这个错误开始训练", key=f"{key_prefix}_train_{analysis.get('weak_point_id')}"):
            route_to_training(int(analysis["weak_point_id"]))


def render_review_drill_packs(error_analyses: list[dict[str, object]], key_prefix: str) -> None:
    packs = build_review_drill_pack(error_analyses)
    if not packs:
        st.info("暂无错因练习包。先录入薄弱点或完成一次训练后，系统会生成复盘练习和变式练习。")
        return
    for index, pack in enumerate(packs[:6], start=1):
        with st.container(border=True):
            st.markdown(f"**#{index} {pack['root_cause']}｜{pack['count']} 次**")
            st.caption(f"涉及考点：{pack['focus_points']}｜错误位置：{pack['error_locations']}")
            if pack["review_drills"]:
                st.write("复盘练习：" + "；".join(pack["review_drills"][:2]))
            if pack["variant_drills"]:
                st.write("变式练习：" + "；".join(pack["variant_drills"][:2]))
            weak_point_ids = pack.get("weak_point_ids") or []
            if weak_point_ids and st.button("训练这个错因", key=f"{key_prefix}_pack_{index}"):
                route_to_training(int(weak_point_ids[0]))


def filter_error_analyses_for_points(
    error_analyses: list[dict[str, object]],
    weak_points: list[dict[str, object]],
) -> list[dict[str, object]]:
    point_ids = {int(row["id"]) for row in weak_points if row.get("id") is not None}
    return [row for row in error_analyses if int(row.get("weak_point_id", -1)) in point_ids]


def save_review_report_provenance_once(
    store: Storage,
    period: str,
    weak_points: list[dict[str, object]],
    sessions: list[dict[str, object]],
    error_analyses: list[dict[str, object]],
    report: str,
) -> None:
    signature_payload = {
        "period": period,
        "weak_point_ids": [row.get("id") for row in weak_points],
        "session_ids": [row.get("id") for row in sessions],
        "error_analysis_ids": [row.get("id") for row in error_analyses],
        "report_hash": hashlib.sha256(report.encode("utf-8")).hexdigest(),
    }
    signature = hashlib.sha256(
        json.dumps(signature_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    if st.session_state.get("last_review_report_trace") == signature:
        return
    record_provenance_event(
        store,
        entity_type="review_report",
        entity_id=None,
        event_type="review_report",
        input_payload=signature_payload,
        output_text=report,
        metadata={"period": period},
    )
    st.session_state["last_review_report_trace"] = signature


@st.cache_resource
def get_storage() -> Storage:
    cloud_config = get_persistence_config()
    cloud_sync: GitHubSnapshotSync | None = None
    if cloud_config.enabled:
        try:
            validate_cloud_sync_config(cloud_config)
            cloud_sync = GitHubSnapshotSync(cloud_config, app_version=get_app_version())
            cloud_sync.restore(DATA_ROOT)
        except CloudSyncError as exc:
            st.error(f"云端数据恢复失败：{exc}")
            st.stop()
        except Exception as exc:
            st.error(f"云端数据恢复失败：{exc}")
            st.stop()

    store = Storage()
    store.init_db()
    try:
        apply_migrations(store, reason=f"startup_{get_app_version()}")
    except SchemaTooNewError as exc:
        st.error(str(exc))
        st.stop()
    store.seed_templates()
    if cloud_sync is not None:
        store.after_write = lambda reason: cloud_sync.upload(DATA_ROOT, reason=reason)
    return store


def get_persistence_config(secrets: object | None = None) -> CloudSyncConfig:
    if secrets is None:
        try:
            secrets = st.secrets
        except Exception:
            secrets = {}
    return load_cloud_sync_config(secrets)


def get_persistence_status_label(config: CloudSyncConfig | None = None) -> str:
    return get_cloud_sync_status_label(config or get_persistence_config())


def get_ai_client() -> AIClient:
    defaults = get_default_ai_config()
    return AIClient(
        api_base=st.session_state.get("api_base", defaults["api_base"]),
        api_key=st.session_state.get("api_key", defaults["api_key"]),
        model=st.session_state.get("model", defaults["model"]),
    )


def get_default_ai_config(secrets: object | None = None) -> dict[str, str]:
    if secrets is None:
        try:
            secrets = st.secrets
        except Exception:
            secrets = {}

    ai_secrets = _mapping_get(secrets, "ai", {})
    return {
        "api_base": str(
            _mapping_get(ai_secrets, "api_base", "")
            or _mapping_get(secrets, "API_BASE", "")
            or "https://api.openai.com/v1"
        ),
        "model": str(
            _mapping_get(ai_secrets, "model", "")
            or _mapping_get(secrets, "MODEL", "")
            or "gpt-4.1-mini"
        ),
        "api_key": str(
            _mapping_get(ai_secrets, "api_key", "")
            or _mapping_get(secrets, "API_KEY", "")
            or ""
        ),
    }


def _mapping_get(mapping: object, key: str, default: object = "") -> object:
    if not hasattr(mapping, "get"):
        return default
    try:
        return mapping.get(key, default)  # type: ignore[attr-defined]
    except Exception:
        return default


def render_global_style() -> None:
    st.markdown(APP_SHELL_STYLE, unsafe_allow_html=True)


def render_process_steps(steps: list[str], columns: int = 3) -> None:
    extra_class = " process-strip-four" if columns == 4 else ""
    items = "".join(
        f"""
<div class="process-step">
  <div class="process-step-index">Step {index}</div>
  <div class="process-step-title">{escape_html(step)}</div>
</div>
"""
        for index, step in enumerate(steps, start=1)
    )
    st.markdown(f'<div class="process-strip{extra_class}">{items}</div>', unsafe_allow_html=True)


def render_panel_intro(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
<div class="section-panel section-panel-soft">
  <div class="section-panel-title">{escape_html(title)}</div>
  <div class="section-panel-subtitle">{escape_html(subtitle)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_kpi_cards(cards: list[tuple[str, object, str]]) -> None:
    items = "".join(
        f"""
<div class="workbench-card">
  <div class="workbench-card-label">{escape_html(label)}</div>
  <div class="workbench-card-value">{escape_html(value)}</div>
  <div class="workflow-muted">{escape_html(caption)}</div>
</div>
"""
        for label, value, caption in cards
    )
    grid_class = "workbench-grid kpi-grid-4" if len(cards) == 4 else "workbench-grid"
    st.markdown(f'<div class="{grid_class}">{items}</div>', unsafe_allow_html=True)


def render_document_cards(documents: list[dict[str, object]]) -> None:
    if not documents:
        st.caption("还没有上传资料。")
        return
    rows = "".join(
        f"""
<div class="document-row">
  <div>
    <div class="document-title">{escape_html(row.get("filename", ""))}</div>
    <div class="document-meta">#{escape_html(row.get("id", ""))} · {escape_html(row.get("status", ""))} · {escape_html(row.get("created_at", ""))}</div>
  </div>
  <span class="chip {document_status_class(row.get("status"))}">{escape_html(document_status_label(row.get("status")))}</span>
</div>
"""
        for row in documents[:6]
    )
    st.markdown(f'<div class="document-list-card">{rows}</div>', unsafe_allow_html=True)


def document_status_label(status: object) -> str:
    labels = {
        "ready": "已完成",
        "uploaded": "待处理",
        "processing": "处理中",
        "error": "失败",
    }
    return labels.get(str(status), str(status or "未知"))


def document_status_class(status: object) -> str:
    if str(status) == "ready":
        return "chip-green"
    if str(status) == "error":
        return "chip-amber"
    return "chip-blue"


def render_source_result_cards(results: list[dict[str, object]]) -> None:
    if not results:
        st.info("没有检索到资料片段。请先上传资料，或换一个更具体的考点。")
        return
    for result in results:
        score = result.get("score", 0)
        try:
            score_text = f"{float(score):.3f}"
        except (TypeError, ValueError):
            score_text = str(score)
        st.markdown(
            f"""
<div class="source-result-card">
  <div class="source-result-title">{escape_html(result.get("source_label", ""))}</div>
  <div class="source-result-meta">相关度 {escape_html(score_text)}</div>
  <div class="section-panel-subtitle">{escape_html(result.get("content", ""))}</div>
</div>
""",
            unsafe_allow_html=True,
        )


def render_lesson_plan_card(lesson: dict[str, object]) -> None:
    chips = "".join(
        f'<span class="chip chip-blue">{escape_html(point)}</span>'
        for point in lesson.get("knowledge_points", [])[:4]
    )
    risks = "".join(
        f'<span class="chip chip-amber">{escape_html(risk)}</span>'
        for risk in lesson.get("mistake_risks", [])[:3]
    )
    st.markdown(
        f"""
<div class="lesson-plan-card">
  <div class="lesson-meta">第 {escape_html(lesson.get("lesson_index", ""))} 课</div>
  <div class="lesson-plan-title">{escape_html(lesson.get("title", ""))}</div>
  <div class="section-panel-subtitle">{escape_html(lesson.get("objective", ""))}</div>
  <div class="lesson-chip-row">{chips}</div>
  <div class="lesson-chip-row">{risks}</div>
  <div class="lesson-meta">模板：{escape_html(lesson.get("recommended_template", ""))}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_review_period_bar(period: str, weak_count: int, finished_count: int) -> None:
    st.markdown(
        f"""
<div class="review-period-bar">
  <div>
    <div class="review-period-title">{escape_html(period)}复盘</div>
    <div class="review-period-subtitle">训练点 {escape_html(weak_count)} 个 · 已完成训练 {escape_html(finished_count)} 次</div>
  </div>
  <div class="lesson-chip-row">
    <span class="chip chip-blue">复盘驾驶舱</span>
    <span class="chip chip-green">下一轮计划</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_review_kpis(kpis: dict[str, object]) -> None:
    render_kpi_cards(
        [
            ("新增训练点", kpis.get("新增训练点", 0), "本期进入复盘范围"),
            ("完成训练", kpis.get("完成训练", 0), "已结束并保存"),
            ("高风险考点", kpis.get("高风险考点", 0), "陌生或模糊"),
            ("待复训", kpis.get("待复训", 0), "未完成闭环"),
        ]
    )


def render_subject_progress(rows: list[dict[str, object]]) -> None:
    if not rows:
        st.caption("暂无科目训练进度。")
        return
    for row in rows[:5]:
        rate = float(row.get("completion_rate", 0) or 0)
        width = max(4, min(100, int(rate * 100)))
        st.markdown(
            f"""
<div class="progress-row">
  <div class="progress-row-top"><span>{escape_html(row.get("subject", ""))}</span><span>{escape_html(row.get("completion_text", ""))}</span></div>
  <div class="progress-track"><div class="progress-fill" style="width:{width}%"></div></div>
</div>
""",
            unsafe_allow_html=True,
        )


def render_review_insight_rows(rows: list[dict[str, object]], title_key: str, meta_builder: object) -> None:
    if not rows:
        st.caption("暂无数据。")
        return
    for row in rows[:5]:
        meta = meta_builder(row) if callable(meta_builder) else ""
        st.markdown(
            f"""
<div class="review-insight-row">
  <div class="rank-title">{escape_html(row.get(title_key, ""))}</div>
  <div class="rank-meta">{escape_html(meta)}</div>
</div>
""",
            unsafe_allow_html=True,
        )


def render_review_training_queue(rows: list[dict[str, object]], key_prefix: str) -> None:
    if not rows:
        st.info("本期没有待处理训练点。")
        return
    for index, row in enumerate(rows[:4]):
        st.markdown(
            f"""
<div class="review-summary-card">
  <div class="lesson-chip-row">
    <span class="chip chip-blue">{escape_html(row.get("subject", ""))}</span>
    <span class="chip chip-amber">{escape_html(row.get("mastery_level", ""))}</span>
    <span class="chip chip-gray">{escape_html(row.get("training_status", ""))}</span>
  </div>
  <div class="lesson-plan-title">{escape_html(row.get("knowledge_point", ""))}</div>
  <div class="section-panel-subtitle">错因：{escape_html(row.get("mistake_reason", ""))}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button(str(row.get("workflow_action", "开始训练")), key=f"{key_prefix}_{index}_{row.get('id')}"):
            route_to_training(int(row["id"]))


def render_review_plan_cards(plan_rows: list[dict[str, object]], key_prefix: str) -> None:
    if not plan_rows:
        st.info("暂无下一轮训练计划。先录入或导入训练点后再复盘。")
        return
    cols = st.columns(3)
    for index, row in enumerate(plan_rows):
        with cols[index % 3]:
            st.markdown(
                f"""
<div class="review-plan-card">
  <div class="review-plan-day">{escape_html(row.get("day", ""))}</div>
  <div class="review-plan-title">{escape_html(row.get("title", ""))}</div>
  <div class="lesson-chip-row">
    <span class="chip chip-blue">{escape_html(row.get("subject", ""))}</span>
    <span class="chip chip-amber">{escape_html(row.get("mastery_level", ""))}</span>
  </div>
  <div class="section-panel-subtitle">模板：{escape_html(row.get("template", ""))} · 预计 {escape_html(row.get("estimated_minutes", ""))} 分钟</div>
</div>
""",
                unsafe_allow_html=True,
            )
            weak_point_id = row.get("weak_point_id")
            if weak_point_id is not None and st.button("开始训练", key=f"{key_prefix}_{weak_point_id}", use_container_width=True):
                route_to_training(int(weak_point_id))


def render_review_checklist(items: list[str]) -> None:
    html_items = "".join(
        f'<div class="review-check-item">✓ {escape_html(item)}</div>'
        for item in items
    )
    st.markdown(f'<div class="review-checklist">{html_items}</div>', unsafe_allow_html=True)


def render_sidebar_status(ai_status: str, persistence_status: str) -> None:
    app_version = get_app_version()
    st.sidebar.markdown(
        f"""
<div class="sidebar-status-card">
  <div class="sidebar-card-title">{SIDEBAR_STATUS_TITLE}</div>
  <div class="sidebar-status-row"><span>应用版本</span><span class="sidebar-status-value">v{escape_html(app_version)}</span></div>
  <div class="sidebar-status-row"><span>大模型</span><span class="sidebar-status-value">{escape_html(ai_status)}</span></div>
  <div class="sidebar-status-row"><span>数据保存</span><span class="sidebar-status-value">{escape_html(persistence_status)}</span></div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_sidebar_workflow() -> None:
    items = "".join(f"<li>{escape_html(step)}</li>" for step in WORKFLOW_LOOP_STEPS)
    st.sidebar.markdown(
        f"""
<div class="sidebar-workflow-card">
  <div class="sidebar-card-title">{SIDEBAR_WORKFLOW_TITLE}</div>
  <ol class="sidebar-flow-list">{items}</ol>
</div>
""",
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="法硕苏格拉底学习器", layout="wide")
    render_global_style()
    store = get_storage()
    page = render_sidebar()
    render_workspace_header(page)

    if page == "今日学习":
        page_today(store)
    elif page == "错题/薄弱点录入":
        page_entry(store)
    elif page == "苏格拉底训练":
        page_training(store)
    elif page == "资料知识库":
        page_knowledge_base(store)
    elif page == "模板管理":
        page_templates(store)
    elif page == "薄弱点分析":
        page_analysis(store)
    elif page == "周度/月度复盘":
        page_review(store)
    else:
        page_system_backup(store)


def render_sidebar() -> str:
    ai_defaults = get_default_ai_config()
    api_key = st.session_state.get("api_key", ai_defaults["api_key"])
    ai_status = get_ai_status_label({"api_key": str(api_key or "")})
    persistence_status = get_persistence_status_label()
    st.sidebar.markdown(
        f"""
<div class="sidebar-brand">
  <div class="sidebar-brand-title">法硕知识助手</div>
  <div class="sidebar-brand-subtitle">苏格拉底式学习工作台</div>
</div>
""",
        unsafe_allow_html=True,
    )
    render_sidebar_status(ai_status, persistence_status)
    render_sidebar_workflow()
    st.session_state["beginner_mode"] = st.sidebar.checkbox(
        "新手模式",
        value=st.session_state.get("beginner_mode", BEGINNER_MODE_DEFAULT),
        help="默认隐藏提示词编辑等高级选项；需要细调模板时可以关闭。",
    )
    st.sidebar.caption("优先顺序：先录入训练点，再训练和复盘。")
    with st.sidebar.expander(
        "AI 配置",
        expanded=not st.session_state["beginner_mode"],
    ):
        st.session_state["api_base"] = st.text_input(
            "API Base",
            value=st.session_state.get("api_base", ai_defaults["api_base"]),
        )
        st.session_state["model"] = st.text_input(
            "Model",
            value=st.session_state.get("model", ai_defaults["model"]),
        )
        st.session_state["api_key"] = st.text_input(
            "API Key",
            value=st.session_state.get("api_key", ai_defaults["api_key"]),
            type="password",
        )
    current_page = st.session_state.get("current_page", PAGES[0])
    if current_page not in PAGES:
        current_page = PAGES[0]
    st.sidebar.markdown("页面")
    for group_name, pages in NAV_GROUPS:
        st.sidebar.markdown(f'<div class="sidebar-group-title">{group_name}</div>', unsafe_allow_html=True)
        for nav_page in pages:
            button_type = "primary" if nav_page == current_page else "secondary"
            if st.sidebar.button(
                nav_page,
                key=f"nav_{nav_page}",
                type=button_type,
                use_container_width=True,
            ):
                current_page = nav_page
                st.session_state["current_page"] = nav_page
                st.rerun()
            if nav_page == current_page:
                st.sidebar.caption(PAGE_SUBTITLES.get(nav_page, ""))
    return current_page


def render_workspace_header(page: str) -> None:
    app_version = get_app_version()
    defaults = get_default_ai_config()
    api_key = st.session_state.get("api_key", defaults["api_key"])
    ai_status = get_ai_status_label({"api_key": str(api_key or "")})
    persistence_config = get_persistence_config()
    persistence_status = get_persistence_status_label(persistence_config)
    group_name = get_page_group(page)
    subtitle = PAGE_SUBTITLES.get(page, "")
    persistence_class = "status-pill status-pill-primary" if persistence_config.enabled else "status-pill"
    status_class = "status-pill status-pill-primary" if ai_status == "AI 已配置" else "status-pill"
    st.markdown(
        f"""
<div class="app-topbar">
  <div>
    <div class="app-topbar-meta">{escape_html(group_name)}</div>
    <h1>{escape_html(page)}</h1>
    <p>{escape_html(subtitle)}</p>
  </div>
  <div class="app-topbar-status">
    <span class="status-pill">v{escape_html(app_version)}</span>
    <span class="{status_class}">{escape_html(ai_status)}</span>
    <span class="{persistence_class}">{escape_html(persistence_status)}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def page_today(store: Storage) -> None:
    render_beginner_guide()
    weak_points = store.list_weak_points()
    sessions = store.list_sessions()
    state = build_learning_loop_state(weak_points, sessions)

    render_learning_loop_steps()
    render_workbench_metrics(
        {
            "total_weak_points": state["totals"]["weak_points"],
            "total_sessions": state["totals"]["sessions"],
            "finished_sessions": state["totals"]["finished_sessions"],
        }
    )

    next_action = state["next_action"]
    st.markdown(
        f"""
<div class="next-action-card">
  <div class="next-action-title">{escape_html(next_action["title"])}</div>
  <div class="next-action-detail">{escape_html(next_action["detail"])}</div>
</div>
""",
        unsafe_allow_html=True,
    )
    render_action_button(next_action, key="today_next_action")

    st.subheader("今日优先队列")
    render_workflow_worktable(state["recent_entries"], limit=5, key_prefix="today_recent")

    st.subheader("下一轮训练重点")
    if state["priority_queue"]:
        render_priority_training_cards(state["priority_queue"][:3], key_prefix="today_priority")
    else:
        st.info("暂无需要排队处理的训练点。")


def render_workbench_metrics(stats: dict[str, object]) -> None:
    cards = [
        ("薄弱点", stats["total_weak_points"]),
        ("训练次数", stats["total_sessions"]),
        ("完成训练", stats["finished_sessions"]),
    ]
    items = "".join(
        f"""
<div class="workbench-card">
  <div class="workbench-card-label">{escape_html(label)}</div>
  <div class="workbench-card-value">{escape_html(value)}</div>
</div>
"""
        for label, value in cards
    )
    st.markdown(f'<div class="workbench-grid">{items}</div>', unsafe_allow_html=True)


def render_next_action_card(action: dict[str, str]) -> None:
    st.markdown(
        f"""
<div class="next-action-card">
  <div class="next-action-title">{escape_html(action["title"])}</div>
  <div class="next-action-detail">{escape_html(action["detail"])}</div>
  <div class="next-action-detail">下一步：在左侧页面选择「{escape_html(action["page"])}」。</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_priority_list(rows: list[dict[str, object]]) -> None:
    items = "".join(
        f"""
<div class="priority-row">
  {escape_html(row["subject"])} ｜ {escape_html(row["knowledge_point"])} ｜ {escape_html(row["mistake_reason"])} ｜ {escape_html(row["mastery_level"])}
</div>
"""
        for row in rows
    )
    st.markdown(f'<div class="priority-list">{items}</div>', unsafe_allow_html=True)


def render_learning_loop_steps() -> None:
    items = "".join(
        f"""
<div class="loop-step">
  <div class="loop-step-index">Step {index}</div>
  <div>{escape_html(step)}</div>
</div>
"""
        for index, step in enumerate(WORKFLOW_LOOP_STEPS, start=1)
    )
    st.markdown(f'<div class="loop-steps">{items}</div>', unsafe_allow_html=True)


def render_action_button(action: dict[str, object], key: str) -> None:
    label = str(action.get("title", "继续"))
    if st.button(label, key=key, type="primary"):
        page = str(action.get("page", ""))
        if page == "苏格拉底训练" and action.get("weak_point_id") is not None:
            route_to_training(int(action["weak_point_id"]))
        elif page == "周度/月度复盘":
            route_to_review(str(action.get("review_focus", "")))
        elif page:
            route_to_page(page)


def render_workflow_worktable(rows: list[dict[str, object]], limit: int, key_prefix: str) -> None:
    if not rows:
        st.info("当前没有训练点记录。先录入一个训练点后，这里会形成可执行队列。")
        return
    st.markdown(
        """
<div class="workflow-row workflow-header">
  <div>科目</div><div>题型</div><div>考点</div><div>错因</div><div>掌握度</div><div>训练状态</div>
</div>
""",
        unsafe_allow_html=True,
    )
    for row in rows[:limit]:
        st.markdown(
            f"""
<div class="workflow-row">
  <div><span class="chip chip-blue">{escape_html(row.get("科目", ""))}</span></div>
  <div class="workflow-muted">{escape_html(row.get("题型", ""))}</div>
  <div class="workflow-main">{escape_html(row.get("考点", ""))}</div>
  <div class="workflow-muted">{escape_html(row.get("错因", ""))}</div>
  <div><span class="chip chip-amber">{escape_html(row.get("掌握度", ""))}</span></div>
  <div><span class="chip chip-green">{escape_html(row.get("训练状态", ""))}</span></div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button(str(row.get("workflow_action", "开始训练")), key=f"{key_prefix}_train_{row['id']}"):
            route_to_training(int(row["id"]))


def render_subject_cards(cards: list[dict[str, object]]) -> None:
    if not cards:
        st.info("暂无科目分布。")
        return
    cols = st.columns(min(3, len(cards)))
    for index, card in enumerate(cards):
        with cols[index % len(cols)]:
            st.markdown(
                f"""
<div class="loop-card">
  <div class="loop-card-title">{escape_html(card["subject"])}</div>
  <div class="loop-card-meta">训练点 {escape_html(card["count"])} 个｜低掌握 {escape_html(card["low_mastery_count"])} 个</div>
</div>
""",
                unsafe_allow_html=True,
            )
            st.progress(float(card.get("completion_rate", 0)))
            if st.button("查看该科目训练点", key=f"subject_filter_{card['subject']}"):
                st.session_state[ANALYSIS_SUBJECT_FILTER_KEY] = card["subject"]
                st.rerun()


def render_knowledge_rankings(rows: list[dict[str, object]], key_prefix: str) -> None:
    if not rows:
        st.info("暂无考点排行。")
        return
    for index, row in enumerate(rows[:8], start=1):
        st.markdown(
            f"""
<div class="rank-row">
  <div class="rank-title">#{index} {escape_html(row["knowledge_point"])}</div>
  <div class="rank-meta">{escape_html(row["subjects"])}｜出现 {escape_html(row["count"])} 次｜{escape_html(row["recommendation"])}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("复盘这个考点", key=f"{key_prefix}_review_{index}_{row['knowledge_point']}"):
            route_to_review(str(row["knowledge_point"]))


def render_priority_training_cards(rows: list[dict[str, object]], key_prefix: str) -> None:
    for index, row in enumerate(rows, start=1):
        st.markdown(
            f"""
<div class="rank-row">
  <div class="rank-title">#{index} {escape_html(row["subject"])}｜{escape_html(row["knowledge_point"])}</div>
  <div class="rank-meta">错因：{escape_html(row["mistake_reason"])}｜掌握度：{escape_html(row["mastery_level"])}｜状态：{escape_html(row["training_status"])}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button(str(row.get("workflow_action", "开始训练")), key=f"{key_prefix}_train_{row['id']}"):
            route_to_training(int(row["id"]))


def render_mistake_reason_queue(rows: list[dict[str, object]]) -> None:
    if not rows:
        st.info("暂无错因队列。")
        return
    for row in rows[:6]:
        st.markdown(
            f"""
<div class="priority-row">
  {escape_html(row["mistake_reason"])}｜{escape_html(row["count"])} 次｜建议：{escape_html(row["workflow_action"])}
</div>
""",
            unsafe_allow_html=True,
        )


def render_beginner_guide() -> None:
    if not st.session_state.get("beginner_mode", BEGINNER_MODE_DEFAULT):
        return
    if st.session_state.get("hide_beginner_guide", False):
        return

    steps = "".join(f"<li>{step}</li>" for step in APP_GUIDE_STEPS)
    st.markdown(
        f"""
<div class="fashuo-guide">
  <div class="fashuo-guide-title">第一次使用可以按这 3 步走</div>
  <ol>{steps}</ol>
</div>
""",
        unsafe_allow_html=True,
    )
    if st.button("收起指引"):
        st.session_state["hide_beginner_guide"] = True


def page_entry(store: Storage) -> None:
    render_panel_intro(
        "从实体书错题到可训练点",
        "第一次只需要补齐科目、题型、考点、错因和掌握度；照片、题干和答案可以作为后续追问依据。",
    )
    render_process_steps(ENTRY_WORKFLOW_STEPS)
    with st.form("weak_point_form", clear_on_submit=True):
        source_col, structure_col, ai_col = st.columns([1, 1.35, 1])
        with source_col:
            with st.container(border=True):
                st.markdown("**来源材料**")
                st.caption("拍照或上传文件后，先留档；后续可接入 OCR 自动抽取。")
                uploaded_file = st.file_uploader(
                    "错题照片",
                    type=["png", "jpg", "jpeg", "webp"],
                    help="实体书拍照即可；第一版先做留档，不强制 OCR。",
                )
                st.caption("建议拍清楚题干、选项、页码和答案区。")
        with structure_col:
            with st.container(border=True):
                st.markdown("**结构化训练点**")
                subject = st.selectbox("科目", SUBJECTS, help="不知道归类时，先按你做题册所在科目选。")
                question_type = st.selectbox("题型", QUESTION_TYPES)
                knowledge_point = st.text_input(
                    "考点",
                    placeholder="例如：共同犯罪、表见代理、宪法监督",
                    help="写一个短考点名即可，不用复制完整题干。",
                )
                mistake_reason = st.selectbox(
                    "错因",
                    MISTAKE_REASONS,
                    help="不确定就选最接近的，后续训练会继续暴露真正问题。",
                )
                mastery_level = st.selectbox(
                    "掌握度",
                    MASTERY_LEVELS,
                    help="按直觉选：看见就不会是陌生，说不清是模糊，能做但不稳是基本会。",
                )
        with ai_col:
            st.markdown(
                f"""
<div class="entry-ai-card">
  <div class="section-panel-title">AI 抽取与下一步</div>
  <div class="section-panel-subtitle">当前版本先用你填写的字段形成训练点；后续接入拍照 OCR 后会在这里展示候选抽取结果。</div>
  <div class="entry-ai-row"><span class="entry-ai-label">保存后</span><span class="entry-ai-value">进入训练点池</span></div>
  <div class="entry-ai-row"><span class="entry-ai-label">建议动作</span><span class="entry-ai-value">立即苏格拉底追问</span></div>
  <div class="entry-ai-row"><span class="entry-ai-label">复盘依据</span><span class="entry-ai-value">错因 + 掌握度</span></div>
</div>
""",
                unsafe_allow_html=True,
            )

        detail_col, answer_col, note_col = st.columns(3)
        with detail_col:
            question_text = st.text_area(
                "题干，可选",
                height=120,
                placeholder="可以先空着；后面需要案例分析时再补。",
            )
        with answer_col:
            reference_answer = st.text_area(
                "参考答案，可选",
                height=120,
                placeholder="可以粘贴答案或写采分点。",
            )
        with note_col:
            notes = st.text_area("备注，可选", height=120, placeholder="例如：书名、页码、题号。")
        submitted = st.form_submit_button("保存训练点", type="primary")

    if submitted:
        if not knowledge_point.strip():
            st.error("考点不能为空。")
            return
        image_path = store.save_upload(uploaded_file) if uploaded_file else ""
        weak_point_id = store.create_weak_point(
            {
                "subject": subject,
                "question_type": question_type,
                "knowledge_point": knowledge_point.strip(),
                "mistake_reason": mistake_reason,
                "mastery_level": mastery_level,
                "image_path": image_path,
                "question_text": question_text,
                "reference_answer": reference_answer,
                "notes": notes,
            }
        )
        st.session_state[FOCUS_WEAK_POINT_KEY] = weak_point_id
        st.session_state["last_saved_weak_point_id"] = weak_point_id
        saved_weak_point = store.get_weak_point(weak_point_id)
        create_or_refresh_error_analysis(
            store,
            saved_weak_point,
            event_type="entry_error_analysis",
        )
        st.success(f"已保存训练点 #{weak_point_id}")

    last_saved_id = st.session_state.get("last_saved_weak_point_id")
    if last_saved_id:
        latest_analysis = store.get_latest_error_analysis(int(last_saved_id))
        if latest_analysis:
            st.subheader("错误还原")
            render_error_analysis_card(
                latest_analysis,
                key_prefix=f"entry_analysis_{last_saved_id}",
                events=store.list_provenance_events("weak_point", int(last_saved_id), limit=5),
            )
        if st.button("进入苏格拉底训练", type="primary"):
            route_to_training(int(last_saved_id))

    st.subheader("最近录入")
    recent = store.list_weak_points()[:10]
    if recent:
        state = build_learning_loop_state(store.list_weak_points(), store.list_sessions())
        render_workflow_worktable(state["recent_entries"], limit=10, key_prefix="entry_recent")
    else:
        st.caption("还没有录入记录。")


def page_training(store: Storage) -> None:
    beginner_mode = st.session_state.get("beginner_mode", BEGINNER_MODE_DEFAULT)
    weak_points = store.list_weak_points()
    templates = store.list_templates()
    render_panel_intro(
        "围绕一个训练点连续追问",
        "先固定训练对象和追问模板，再通过多轮回答暴露真正薄弱处。",
    )
    if not weak_points:
        st.info("请先去「错题/薄弱点录入」保存一个训练点。只填科目、题型、考点、错因和掌握度即可。")
        st.markdown(
            """
<div class="training-control-card">
  <div class="section-panel-title">训练控制台</div>
  <div class="section-panel-subtitle">保存训练点后，这里会显示模板提示、参考资料、掌握度评估和训练记录。</div>
</div>
""",
            unsafe_allow_html=True,
        )
        return
    if not templates:
        st.warning("没有启用中的模板，请先在模板管理中启用模板。")
        return

    setup_col, control_col = st.columns([1.45, 1])
    with setup_col:
        weak_point = st.selectbox(
            "选择训练点",
            weak_points,
            index=get_focused_weak_point_index(weak_points, st.session_state.get(FOCUS_WEAK_POINT_KEY)),
            format_func=lambda row: f"{row['subject']}｜{row['knowledge_point']}｜{row['mastery_level']}",
        )
        template = st.selectbox("选择追问模板", templates, format_func=lambda row: row["name"])
        student_goal = st.text_input("本次训练目标", value=template["default_goal"])
    with control_col:
        st.markdown(
            f"""
<div class="training-control-card">
  <div class="section-panel-title">训练控制台</div>
  <div class="section-panel-subtitle">本页只围绕当前训练点推进，不混入其它错题。</div>
  <div class="lesson-chip-row">
    <span class="chip chip-blue">{escape_html(weak_point["subject"])}</span>
    <span class="chip chip-amber">{escape_html(weak_point["mastery_level"])}</span>
    <span class="chip chip-gray">{escape_html(weak_point["mistake_reason"])}</span>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        min_dialogue_rounds = normalize_min_dialogue_rounds(
            st.number_input(
                "最少追问轮次",
                min_value=DEFAULT_MIN_DIALOGUE_ROUNDS,
                max_value=20,
                value=DEFAULT_MIN_DIALOGUE_ROUNDS,
                step=1,
                help="未满这个轮次前，系统不会允许保存复盘。",
            )
        )
        max_round_label = st.selectbox(
            "最大追问轮次",
            MAX_DIALOGUE_ROUND_OPTIONS,
            index=0,
            help="默认不限制；如设置上限，达到后模型会转入总结或巩固。",
        )
        max_dialogue_rounds = normalize_max_dialogue_rounds(max_round_label, min_dialogue_rounds)
        st.caption(f"本次规则：{format_round_policy_label(min_dialogue_rounds, max_dialogue_rounds)}")

    advanced_enabled = st.checkbox(
        "我要临时修改本次提示词",
        value=not beginner_mode,
        help="第一次使用建议不勾选，直接使用内置模板。",
    )
    if should_show_prompt_editor(beginner_mode, advanced_enabled):
        prompt_override = st.text_area("本次提示词，可临时修改", value=template["body"], height=220)
        save_as = st.text_input("保存为新模板名称，可留空")
    else:
        prompt_override = template["body"]
        save_as = ""
        st.caption("当前使用内置模板；需要改追问方式时再勾选上面的高级编辑。")
    recent_weaknesses = [row["knowledge_point"] for row in weak_points[:5]]
    rag_results = search_chunks(
        f"{weak_point['knowledge_point']} {weak_point.get('question_text', '')}",
        store.list_document_chunks(),
        top_k=4,
    )
    source_context = format_rag_context(rag_results)
    prompt_snapshot = build_training_prompt(
        weak_point=weak_point,
        template=template,
        student_goal=student_goal,
        recent_weaknesses=recent_weaknesses,
        prompt_override=prompt_override,
        source_context=source_context,
        min_dialogue_rounds=min_dialogue_rounds,
        max_dialogue_rounds=max_dialogue_rounds,
    )

    st.markdown(
        f"""
<div class="training-context-bar">
  <div class="training-context-item">
    <div class="training-context-label">当前训练点</div>
    <div class="training-context-value">{escape_html(weak_point["subject"])}｜{escape_html(weak_point["knowledge_point"])}</div>
  </div>
  <div class="training-context-item">
    <div class="training-context-label">追问模板</div>
    <div class="training-context-value">{escape_html(template["name"])}</div>
  </div>
  <div class="training-context-item">
    <div class="training-context-label">当前目标</div>
    <div class="training-context-value">{escape_html(student_goal)}</div>
  </div>
  <div class="training-context-item">
    <div class="training-context-label">掌握度</div>
    <div class="training-context-value">{escape_html(weak_point["mastery_level"])}</div>
  </div>
  <div class="training-context-item">
    <div class="training-context-label">轮次规则</div>
    <div class="training-context-value">{escape_html(format_round_policy_label(min_dialogue_rounds, max_dialogue_rounds))}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    preview_col, source_col = st.columns(2)
    with preview_col:
        with st.expander(TRAINING_PANEL_SECTIONS[0]):
            st.code(prompt_snapshot)
    with source_col:
        with st.expander(TRAINING_PANEL_SECTIONS[1]):
            st.text(source_context or "暂无匹配资料片段。训练会优先依据你录入的题干、答案和错因。")

    if save_as.strip() and st.button("保存本次提示词为新模板"):
        try:
            store.create_template(
                {
                    "name": save_as.strip(),
                    "subject_scope": weak_point["subject"],
                    "question_type_scope": weak_point["question_type"],
                    "body": prompt_override,
                    "default_goal": student_goal,
                    "end_condition": template["end_condition"],
                    "is_active": True,
                }
            )
            st.success("已保存为新模板。")
        except IntegrityError:
            st.error("模板名称已存在，请换一个名称。")

    if "active_session_id" not in st.session_state:
        st.session_state["active_session_id"] = None

    if st.button("开始训练", type="primary"):
        session_id = store.create_session(
            weak_point_id=weak_point["id"],
            template_id=template["id"],
            template_version=template["current_version"],
            prompt_snapshot=prompt_snapshot,
            mastery_before=weak_point["mastery_level"],
        )
        st.session_state["active_session_id"] = session_id
        st.session_state[f"session_min_dialogue_rounds_{session_id}"] = min_dialogue_rounds
        st.session_state[f"session_max_dialogue_rounds_{session_id}"] = max_dialogue_rounds
        try:
            reply = get_ai_client().chat([{"role": "system", "content": prompt_snapshot}])
            store.add_message(session_id, "assistant", reply)
            record_provenance_event(
                store,
                entity_type="session",
                entity_id=session_id,
                event_type="training_initial_ai_call",
                input_payload={
                    "weak_point": weak_point,
                    "template": template,
                    "student_goal": student_goal,
                    "prompt_snapshot": prompt_snapshot,
                    "source_context": source_context,
                    "round_policy": {
                        "min_dialogue_rounds": min_dialogue_rounds,
                        "max_dialogue_rounds": max_dialogue_rounds,
                    },
                },
                output_text=reply,
                metadata={"model": st.session_state.get("model", get_default_ai_config()["model"])},
            )
            st.rerun()
        except AIConfigurationError as exc:
            st.warning(str(exc))
        except Exception as exc:
            st.error(f"AI 调用失败：{exc}")

    session_id = st.session_state.get("active_session_id")
    if not session_id:
        return

    messages = store.list_messages(session_id)
    session_min_rounds = normalize_min_dialogue_rounds(
        st.session_state.get(f"session_min_dialogue_rounds_{session_id}", DEFAULT_MIN_DIALOGUE_ROUNDS)
    )
    session_max_rounds = normalize_max_dialogue_rounds(
        st.session_state.get(f"session_max_dialogue_rounds_{session_id}"),
        session_min_rounds,
    )
    completed_rounds = count_student_dialogue_rounds(messages)
    chat_col, panel_col = st.columns([1.55, 1])
    with chat_col:
        st.subheader(f"当前训练 #{session_id}")
        with st.container(border=True):
            if messages:
                for message in messages:
                    with st.chat_message(message["role"]):
                        st.write(message["content"])
            else:
                st.caption("训练已创建，等待 AI 首轮追问。")
    with panel_col:
        with st.container(border=True):
            st.markdown(f"**{TRAINING_PANEL_SECTIONS[2]}**")
            st.caption(f"训练前：{weak_point['mastery_level']}｜错因：{weak_point['mistake_reason']}")
            st.markdown(f"**{TRAINING_PANEL_SECTIONS[3]}**")
            st.caption(f"已记录消息：{len(messages)} 条")
            st.caption(
                f"已完成轮次：{completed_rounds} / 至少 {session_min_rounds} 轮；"
                + ("最大轮次：不限制" if session_max_rounds is None else f"最大轮次：{session_max_rounds} 轮")
            )
            st.markdown(
                """
<div class="training-timeline">
  <div class="timeline-node"><b>开始</b><br><span class="workflow-muted">选择训练点</span></div>
  <div class="timeline-node"><b>追问</b><br><span class="workflow-muted">暴露漏洞</span></div>
  <div class="timeline-node"><b>修正</b><br><span class="workflow-muted">补齐表达</span></div>
  <div class="timeline-node"><b>复盘</b><br><span class="workflow-muted">保存结论</span></div>
</div>
""",
                unsafe_allow_html=True,
            )

    user_input = st.chat_input("回答上一个问题")
    if user_input:
        store.add_message(session_id, "user", user_input)
        session = store.get_session(session_id)
        history = [{"role": "system", "content": session["prompt_snapshot"]}]
        history.extend(
            {"role": message["role"], "content": message["content"]}
            for message in store.list_messages(session_id)
        )
        try:
            reply = get_ai_client().chat(history)
            store.add_message(session_id, "assistant", reply)
            record_provenance_event(
                store,
                entity_type="session",
                entity_id=session_id,
                event_type="training_followup_ai_call",
                input_payload={
                    "user_input": user_input,
                    "history": history,
                    "completed_rounds": completed_rounds + 1,
                },
                output_text=reply,
                metadata={"model": st.session_state.get("model", get_default_ai_config()["model"])},
            )
            st.rerun()
        except AIConfigurationError as exc:
            st.warning(str(exc))
        except Exception as exc:
            st.error(f"AI 调用失败：{exc}")

    with st.form("finish_session_form"):
        st.markdown("**保存复盘**")
        finish_col1, finish_col2 = st.columns([1, 2])
        with finish_col1:
            mastery_after = st.selectbox("训练后掌握度", MASTERY_LEVELS, index=2)
        with finish_col2:
            summary = st.text_area("训练总结", height=80)
        issue_col, next_col = st.columns(2)
        with issue_col:
            exposed_issues = st.text_area("暴露问题", height=80)
        with next_col:
            next_review_suggestion = st.text_area("下次复习建议", height=80)
        st.caption(f"保存前至少完成 {session_min_rounds} 轮学生回答；当前已完成 {completed_rounds} 轮。")
        finish = st.form_submit_button("结束训练并保存复盘", type="primary")
    if finish:
        messages = store.list_messages(session_id)
        completed_rounds = count_student_dialogue_rounds(messages)
        if not can_finish_training(completed_rounds, session_min_rounds):
            st.error(f"当前只完成 {completed_rounds} 轮，至少完成 {session_min_rounds} 轮后再保存复盘。")
            return
        store.finish_session(
            session_id,
            mastery_after,
            summary,
            exposed_issues,
            next_review_suggestion,
        )
        finished_session = store.get_session(session_id)
        session_weak_point = store.get_weak_point(int(finished_session["weak_point_id"]))
        session_context = {
            "summary": summary,
            "exposed_issues": exposed_issues,
            "next_review_suggestion": next_review_suggestion,
            "mastery_before": finished_session.get("mastery_before", ""),
            "mastery_after": mastery_after,
            "messages": messages,
        }
        create_or_refresh_error_analysis(
            store,
            session_weak_point,
            session_context=session_context,
            event_type="training_finished_error_analysis",
        )
        record_provenance_event(
            store,
            entity_type="session",
            entity_id=session_id,
            event_type="training_session_summary",
            input_payload={"session": finished_session, "messages": messages},
            output_text="\n".join(
                [
                    f"# 训练复盘 #{session_id}",
                    f"- 训练后掌握度：{mastery_after}",
                    f"- 暴露问题：{exposed_issues}",
                    f"- 下次复习建议：{next_review_suggestion}",
                    "",
                    summary,
                ]
            ),
            metadata={"weak_point_id": int(finished_session["weak_point_id"])},
        )
        st.session_state["active_session_id"] = None
        st.success("训练已结束并保存。")


def page_knowledge_base(store: Storage) -> None:
    documents = store.list_documents()
    chunks = store.list_document_chunks()
    courses = store.list_courses()

    imported_lesson_count = 0
    for course in courses:
        imported_lesson_count += sum(
            1 for lesson in store.list_course_lessons(course["id"]) if lesson["imported_weak_point_id"]
        )

    render_panel_intro(
        "资料驱动训练计划",
        "上传资料后先建立本地索引，再检索关键片段，最后生成可执行训练计划并导入为训练点。",
    )
    render_kpi_cards(
        [
            ("资料", len(documents), "已上传文件"),
            ("文本片段", len(chunks), "可检索 RAG 片段"),
            ("训练计划", len(courses), "已生成课程"),
            ("已导入", imported_lesson_count, "课程小节转训练点"),
        ]
    )
    render_process_steps(KNOWLEDGE_WORKFLOW_STEPS, columns=4)

    upload_col, search_col, generate_col = st.columns([1, 1.1, 1])
    with upload_col:
        with st.container(border=True):
            st.markdown("**1. 上传并建立索引**")
            st.caption("支持 PDF、图片、TXT、Markdown；图片会尝试本地 OCR。")
            with st.form("document_upload_form", clear_on_submit=True):
                uploaded_file = st.file_uploader(
                    "上传 PDF、图片、TXT 或 Markdown",
                    type=["pdf", "png", "jpg", "jpeg", "webp", "txt", "md", "markdown"],
                    help="PDF 会优先直接抽文字；图片会尝试用本地 Tesseract OCR。",
                )
                submitted = st.form_submit_button("上传并建立索引", type="primary")

            if submitted:
                if uploaded_file is None:
                    st.error("请先选择一个文件。")
                else:
                    path = store.save_document_upload(uploaded_file)
                    document_id = store.create_document(
                        {
                            "filename": uploaded_file.name,
                            "file_type": "." + uploaded_file.name.split(".")[-1].lower(),
                            "file_path": path,
                            "status": "uploaded",
                        }
                    )
                    try:
                        text, text_chunks, status = process_document_file(path)
                        store.update_document_processing(document_id, text, status)
                        store.replace_document_chunks(
                            document_id,
                            [
                                {
                                    "content": chunk,
                                    "source_label": f"{uploaded_file.name}#{index}",
                                }
                                for index, chunk in enumerate(text_chunks, start=1)
                            ],
                        )
                        record_provenance_event(
                            store,
                            entity_type="document",
                            entity_id=document_id,
                            event_type="document_processing",
                            input_payload={
                                "filename": uploaded_file.name,
                                "file_type": "." + uploaded_file.name.split(".")[-1].lower(),
                                "file_path": path,
                            },
                            output_text=text,
                            metadata={"status": status, "chunk_count": len(text_chunks)},
                        )
                        if text_chunks:
                            st.success(f"已处理 {uploaded_file.name}，生成 {len(text_chunks)} 个检索片段。")
                        else:
                            st.warning("文件已保存，但没有抽取到有效文本。扫描版 PDF 可以先转成图片再上传 OCR。")
                    except OCRUnavailableError as exc:
                        store.update_document_processing(document_id, "", "error", str(exc))
                        record_provenance_event(
                            store,
                            entity_type="document",
                            entity_id=document_id,
                            event_type="document_processing_error",
                            input_payload={"filename": uploaded_file.name, "file_path": path},
                            output_text=str(exc),
                            metadata={"status": "error"},
                        )
                        st.error(str(exc))
                    except UnsupportedDocumentError as exc:
                        store.update_document_processing(document_id, "", "error", str(exc))
                        record_provenance_event(
                            store,
                            entity_type="document",
                            entity_id=document_id,
                            event_type="document_processing_error",
                            input_payload={"filename": uploaded_file.name, "file_path": path},
                            output_text=str(exc),
                            metadata={"status": "error"},
                        )
                        st.error(str(exc))
                    except Exception as exc:
                        store.update_document_processing(document_id, "", "error", str(exc))
                        record_provenance_event(
                            store,
                            entity_type="document",
                            entity_id=document_id,
                            event_type="document_processing_error",
                            input_payload={"filename": uploaded_file.name, "file_path": path},
                            output_text=str(exc),
                            metadata={"status": "error"},
                        )
                        st.error(f"处理失败：{exc}")
            documents = store.list_documents()
            render_document_cards(documents)

    documents = store.list_documents()
    chunks = store.list_document_chunks()
    with search_col:
        with st.container(border=True):
            st.markdown("**2. 检索资料片段**")
            query = st.text_input("输入要查的考点或问题", placeholder="例如：共同犯罪成立条件")
            if st.button("检索资料", key="knowledge_search_button"):
                if not query.strip():
                    st.error("请先输入考点或问题。")
                else:
                    results = search_chunks(query, chunks, top_k=5)
                    query_id = store.create_rag_query(query, [int(result["id"]) for result in results])
                    record_provenance_event(
                        store,
                        entity_type="rag_query",
                        entity_id=query_id,
                        event_type="rag_search",
                        input_payload={"query": query},
                        output_text=format_rag_context(results),
                        metadata={"chunk_ids": [int(result["id"]) for result in results]},
                    )
                    st.session_state["last_rag_query"] = query
                    st.session_state["last_rag_results"] = results
            last_results = st.session_state.get("last_rag_results", [])
            if last_results:
                st.caption(f"最近检索：{st.session_state.get('last_rag_query', '')}")
                render_source_result_cards(last_results)
            else:
                st.caption("检索结果会显示来源、相关度和可引用片段。")

    ready_documents = [row for row in documents if row["status"] == "ready"]
    with generate_col:
        with st.container(border=True):
            st.markdown(f"**{COURSE_GENERATION_SECTION_TITLE}**")
            if not ready_documents:
                st.info("先上传并成功处理一份资料后，再生成训练计划。")
            else:
                selected_document = st.selectbox(
                    "选择课程来源资料",
                    ready_documents,
                    format_func=lambda row: f"#{row['id']} {row['filename']}",
                )
                course_goal = st.text_input("课程目标", value="围绕这份资料生成法硕考前可执行训练计划")
                days = st.slider("复习周期（天）", min_value=3, max_value=30, value=7)
                document_chunks = store.list_document_chunks(selected_document["id"])
                source_results = search_chunks(course_goal, document_chunks, top_k=8) or document_chunks[:8]
                source_context = format_rag_context(source_results, max_chars=5000)

                with st.expander("生成训练计划将参考的资料片段"):
                    st.text(source_context or "暂无资料片段")

                if st.button("生成训练计划", type="primary"):
                    if not source_context:
                        st.error("该资料没有可用文本片段，无法生成训练计划。")
                    else:
                        try:
                            course = generate_course(get_ai_client(), source_context, course_goal, days)
                            lessons = normalize_lessons(course)
                            course_id = store.create_course(
                                title=course["title"],
                                source_document_id=selected_document["id"],
                                raw_json=json.dumps(course, ensure_ascii=False),
                                lessons=lessons,
                            )
                            record_provenance_event(
                                store,
                                entity_type="course",
                                entity_id=course_id,
                                event_type="course_generation",
                                input_payload={
                                    "document_id": selected_document["id"],
                                    "course_goal": course_goal,
                                    "days": days,
                                    "source_context": source_context,
                                },
                                output_text=json.dumps(course, ensure_ascii=False, indent=2),
                                metadata={"lesson_count": len(lessons)},
                            )
                            st.success(f"已生成训练计划 #{course_id}：{course['title']}")
                        except AIConfigurationError as exc:
                            st.warning(str(exc))
                        except CourseGenerationError as exc:
                            st.error(str(exc))
                        except Exception as exc:
                            st.error(f"生成失败：{exc}")

    courses = store.list_courses()
    if courses:
        st.subheader("已生成训练计划")
        selected_course = st.selectbox(
            "选择训练计划",
            courses,
            format_func=lambda row: f"#{row['id']} {row['title']}",
        )
        lessons = store.list_course_lessons(selected_course["id"])
        if not lessons:
            st.caption("这个训练计划还没有小节。")
            return
        lesson_columns = st.columns(3)
        for index, lesson in enumerate(lessons):
            with lesson_columns[index % 3]:
                render_lesson_plan_card(lesson)
                if lesson["imported_weak_point_id"]:
                    st.success(f"已导入为训练点 #{lesson['imported_weak_point_id']}")
                else:
                    subject = st.selectbox(LESSON_SUBJECT_LABEL, SUBJECTS, key=f"lesson_subject_{lesson['id']}")
                    if st.button(IMPORT_LESSON_BUTTON_LABEL, key=f"import_lesson_{lesson['id']}", use_container_width=True):
                        weak_point_id = store.import_lesson_as_weak_point(lesson["id"], subject)
                        imported_weak_point = store.get_weak_point(weak_point_id)
                        imported_analysis = create_or_refresh_error_analysis(
                            store,
                            imported_weak_point,
                            event_type="course_import_error_analysis",
                        )
                        record_provenance_event(
                            store,
                            entity_type="course_lesson",
                            entity_id=int(lesson["id"]),
                            event_type="course_lesson_import",
                            input_payload={"lesson": lesson, "subject": subject},
                            output_text=format_error_analysis_markdown(imported_weak_point, imported_analysis),
                            metadata={"weak_point_id": weak_point_id},
                        )
                        st.success(f"已导入为训练点 #{weak_point_id}")


def page_templates(store: Storage) -> None:
    beginner_mode = st.session_state.get("beginner_mode", BEGINNER_MODE_DEFAULT)
    st.caption("不会改模板也可以跳过本页；内置模板已经可以直接用于训练。")
    templates = store.list_templates(active_only=False)
    if templates:
        selected = st.selectbox(
            "选择模板",
            templates,
            format_func=lambda row: f"{row['name']} v{row['current_version']}",
        )
        with st.expander("编辑当前模板", expanded=not beginner_mode):
            with st.form("template_edit_form"):
                name = st.text_input("模板名称", value=selected["name"])
                subject_scope = st.text_input("适用科目", value=selected["subject_scope"])
                question_type_scope = st.text_input("适用题型", value=selected["question_type_scope"])
                body = st.text_area("模板正文", value=selected["body"], height=260)
                default_goal = st.text_area("默认训练目标", value=selected["default_goal"], height=80)
                end_condition = st.text_area("结束条件", value=selected["end_condition"], height=80)
                is_active = st.checkbox("启用", value=bool(selected["is_active"]))
                save = st.form_submit_button("保存新版本")
            if save:
                try:
                    store.update_template(
                        selected["id"],
                        {
                            "name": name,
                            "subject_scope": subject_scope,
                            "question_type_scope": question_type_scope,
                            "body": body,
                            "default_goal": default_goal,
                            "end_condition": end_condition,
                            "is_active": is_active,
                        },
                    )
                    st.success("已保存模板新版本。")
                except IntegrityError:
                    st.error("模板名称已存在，请换一个名称。")

            copy_name = st.text_input("复制为新模板名称", value=f"{selected['name']} 副本")
            if st.button("复制模板"):
                try:
                    store.copy_template(selected["id"], copy_name)
                    st.success("已复制模板。")
                except IntegrityError:
                    st.error("模板名称已存在，请换一个名称。")

    st.subheader("新建模板")
    with st.form("template_create_form"):
        new_name = st.text_input("新模板名称")
        new_body = st.text_area("新模板正文", height=180)
        create = st.form_submit_button("创建模板")
    if create:
        if not new_name.strip() or not new_body.strip():
            st.error("模板名称和正文不能为空。")
            return
        try:
            store.create_template(
                {
                    "name": new_name.strip(),
                    "subject_scope": "通用",
                    "question_type_scope": "通用",
                    "body": new_body,
                    "default_goal": "通过连续追问修复薄弱点。",
                    "end_condition": "学生能独立说出正确路径。",
                    "is_active": True,
                }
            )
            st.success("已创建模板。")
        except IntegrityError:
            st.error("模板名称已存在，请换一个名称。")


def page_analysis(store: Storage) -> None:
    weak_points = store.list_weak_points()
    sessions = store.list_sessions()
    error_analyses = store.list_error_analyses()
    if not weak_points:
        st.info("暂无薄弱点记录。")
        return

    state = build_learning_loop_state(weak_points, sessions)
    st.caption("这里不再只是展示统计表，而是把薄弱点转成下一步训练、复盘和错因修复队列。")

    st.subheader("科目概览")
    render_subject_cards(state["subject_cards"])

    subject_options = ["全部"] + [card["subject"] for card in state["subject_cards"]]
    current_subject = st.session_state.get(ANALYSIS_SUBJECT_FILTER_KEY, "全部")
    if current_subject not in subject_options:
        current_subject = "全部"
    col1, col2 = st.columns([1, 1])
    with col1:
        subject_filter = st.selectbox(
            "筛选科目",
            subject_options,
            index=subject_options.index(current_subject),
        )
    with col2:
        mastery_filter = st.selectbox("筛选掌握度", ["全部"] + MASTERY_LEVELS)
    st.session_state[ANALYSIS_SUBJECT_FILTER_KEY] = subject_filter

    filtered_points = [
        row
        for row in weak_points
        if (subject_filter == "全部" or row["subject"] == subject_filter)
        and (mastery_filter == "全部" or row["mastery_level"] == mastery_filter)
    ]
    filtered_state = build_learning_loop_state(filtered_points, sessions)
    filtered_analyses = filter_error_analyses_for_points(error_analyses, filtered_points)

    st.subheader("训练点工作表")
    render_workflow_worktable(filtered_state["recent_entries"], limit=12, key_prefix="analysis_recent")

    st.subheader("错因还原与证据链")
    if filtered_analyses:
        analysis_columns = st.columns(2)
        for index, analysis in enumerate(filtered_analyses[:4]):
            with analysis_columns[index % 2]:
                weak_point_id = int(analysis["weak_point_id"])
                render_error_analysis_card(
                    analysis,
                    key_prefix=f"analysis_error_{index}",
                    events=store.list_provenance_events("weak_point", weak_point_id, limit=4),
                )
    else:
        st.info("还没有错因还原。录入训练点或完成训练后，系统会自动生成错误位置、根因证据、复盘练习和变式练习。")

    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("高频考点排行")
        render_knowledge_rankings(filtered_state["knowledge_rankings"], key_prefix="analysis")
    with right:
        st.subheader("错因修复队列")
        render_mistake_reason_queue(filtered_state["mistake_reason_queue"])

    st.subheader("优先训练")
    render_priority_training_cards(filtered_state["priority_queue"][:5], key_prefix="analysis_priority")

    st.subheader("复盘练习包")
    render_review_drill_packs(filtered_analyses, key_prefix="analysis_drill")


def page_review(store: Storage) -> None:
    render_panel_intro(
        "把阶段结果转成下一轮训练",
        "复盘页先看训练队列和高频问题，再安排下一轮苏格拉底追问，最后导出 Markdown 留档。",
    )
    render_process_steps(REVIEW_WORKFLOW_STEPS)
    period = st.radio("复盘周期", ["本周", "本月"], horizontal=True)
    weak_points = store.list_weak_points()
    sessions = store.list_sessions()
    all_error_analyses = store.list_error_analyses()
    review_focus = st.session_state.get(REVIEW_FOCUS_KEY, "")
    if review_focus:
        st.info(f"当前复盘焦点：{review_focus}")
        focused_points = [
            row
            for row in weak_points
            if review_focus in row.get("knowledge_point", "")
            or review_focus in row.get("mistake_reason", "")
            or review_focus in row.get("subject", "")
        ]
        if focused_points:
            focused_ids = {int(row["id"]) for row in focused_points}
            weak_points = focused_points
            sessions = [
                row
                for row in sessions
                if row.get("weak_point_id") is not None and int(row["weak_point_id"]) in focused_ids
            ]
        if st.button("清除复盘焦点"):
            st.session_state[REVIEW_FOCUS_KEY] = ""
            st.rerun()

    review_error_analyses = filter_error_analyses_for_points(all_error_analyses, weak_points)
    state = build_review_dashboard_state(weak_points, sessions)
    render_review_period_bar(
        period,
        int(state["kpis"]["新增训练点"]),
        int(state["kpis"]["完成训练"]),
    )
    render_review_kpis(state["kpis"])

    left, right = st.columns([1.25, 1])
    with left:
        st.subheader("复盘前训练队列")
        render_review_training_queue(state["training_queue"], key_prefix="review_queue")
    with right:
        st.subheader(REVIEW_DASHBOARD_SECTIONS[0])
        with st.container(border=True):
            st.markdown("**科目训练完成度**")
            render_subject_progress(state["subject_progress"])
            st.markdown("**本期复盘判断**")
            if state["kpis"]["待复训"]:
                st.caption("仍有训练点没有完成追问闭环，建议先处理待复训项目。")
            else:
                st.caption("本期训练点已完成追问闭环，可以进入巩固和表达修复。")

    insight_col1, insight_col2, insight_col3 = st.columns(3)
    with insight_col1:
        with st.container(border=True):
            st.markdown(f"**{REVIEW_DASHBOARD_SECTIONS[1]}**")
            render_review_insight_rows(
                state["knowledge_focus"],
                "knowledge_point",
                lambda row: f"{row.get('subjects', '')} · {row.get('count', 0)} 次 · {row.get('recommendation', '')}",
            )
    with insight_col2:
        with st.container(border=True):
            st.markdown(f"**{REVIEW_DASHBOARD_SECTIONS[2]}**")
            render_review_insight_rows(
                state["mistake_focus"],
                "mistake_reason",
                lambda row: f"{row.get('count', 0)} 次 · {row.get('workflow_action', '')}",
            )
    with insight_col3:
        with st.container(border=True):
            st.markdown("**本期关键结论**")
            if state["knowledge_focus"]:
                first = state["knowledge_focus"][0]
                st.caption(f"优先处理：{first.get('knowledge_point', '')}")
            if state["mistake_focus"]:
                first_reason = state["mistake_focus"][0]
                st.caption(f"主要错因：{first_reason.get('mistake_reason', '')}")
            st.caption("下一轮训练应优先修复低掌握度考点，再补主观题采分表达。")

    st.subheader(REVIEW_DASHBOARD_SECTIONS[3])
    render_review_plan_cards(state["next_cycle_plan"], key_prefix="review_plan")

    st.subheader("错因复盘与变式练习")
    render_review_drill_packs(review_error_analyses, key_prefix="review_drill")

    st.subheader("复盘清单")
    render_review_checklist(state["checklist"])

    report = build_review_report(period, weak_points, sessions, error_analyses=review_error_analyses)
    save_review_report_provenance_once(store, period, weak_points, sessions, review_error_analyses, report)
    with st.expander("Markdown 原文"):
        st.markdown(report)
    st.download_button(
        "下载 Markdown",
        data=report.encode("utf-8"),
        file_name=f"{period}复盘.md",
        mime="text/markdown",
    )


def page_system_backup(store: Storage) -> None:
    st.caption("这里用于检查系统版本、数据库版本、数据完整性，并手动创建完整备份。")

    schema_version = get_schema_version(store)
    col1, col2, col3 = st.columns(3)
    col1.metric("应用版本", get_app_version())
    col2.metric("数据库版本", schema_version)
    col3.metric("支持版本", SUPPORTED_SCHEMA_VERSION)

    if schema_version > SUPPORTED_SCHEMA_VERSION:
        st.error("数据库版本高于当前应用支持版本。为保护数据，当前版本不应继续写入。")
    elif schema_version < SUPPORTED_SCHEMA_VERSION:
        st.warning("数据库版本低于当前应用支持版本。启动流程会尝试备份后迁移。")
    else:
        st.success("数据库版本与当前应用匹配。")

    persistence_config = get_persistence_config()
    st.subheader("云端持久化")
    if persistence_config.enabled:
        st.success("已开启 GitHub 云端快照。应用启动会先恢复快照，写入数据后会上传新快照。")
        st.write(f"仓库：`{persistence_config.repo}`")
        st.write(f"快照分支：`{persistence_config.branch}`")
        st.write(f"快照文件：`{persistence_config.snapshot_path}`")
    else:
        st.info("当前使用本地临时存储。Streamlit Cloud 重启或重新部署后，运行时新增数据可能丢失。")

    st.subheader("数据完整性")
    current_integrity = integrity_check(store)
    st.write(f"SQLite integrity_check：`{current_integrity}`")
    counts = collect_table_counts(store)
    st.dataframe(
        pd.DataFrame([{"table": table, "count": count} for table, count in counts.items()]),
        use_container_width=True,
    )

    st.subheader("手动备份")
    st.write("备份会复制数据库、错题图片目录、资料目录和溯源文件目录，并生成 manifest.json。")
    if st.button("立即创建备份"):
        backup_dir = create_backup(store, reason="manual_backup")
        st.success(f"已创建备份：{backup_dir}")

    st.subheader("迁移记录")
    migrations = list_applied_migrations(store)
    if migrations:
        st.dataframe(pd.DataFrame(migrations), use_container_width=True)
    else:
        st.info("暂无迁移记录。")

    st.subheader("最近溯源记录")
    provenance_events = store.list_provenance_events(limit=10)
    if provenance_events:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "id": row.get("id", ""),
                        "entity_type": row.get("entity_type", ""),
                        "entity_id": row.get("entity_id", ""),
                        "event_type": row.get("event_type", ""),
                        "input_path": row.get("input_path", ""),
                        "output_path": row.get("output_path", ""),
                        "created_at": row.get("created_at", ""),
                    }
                    for row in provenance_events
                ]
            ),
            use_container_width=True,
        )
    else:
        st.info("暂无溯源记录。录入、训练、资料处理或复盘后会在这里看到输入输出文件路径。")

    st.subheader("最近备份")
    backups = list_backups()
    if backups:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "backup_time": row.get("backup_time", ""),
                        "reason": row.get("reason", ""),
                        "integrity": row.get("integrity", ""),
                        "path": row.get("path", ""),
                    }
                    for row in backups
                ]
            ),
            use_container_width=True,
        )
    else:
        st.info("还没有备份。")


if __name__ == "__main__":
    main()
