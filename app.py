from __future__ import annotations

import html
import json
from sqlite3 import IntegrityError

import pandas as pd
import streamlit as st

from services.ai_client import AIClient, AIConfigurationError
from services.analysis import build_review_report, compute_weak_point_stats
from services.backup import collect_table_counts, create_backup, integrity_check, list_backups
from services.course_generator import CourseGenerationError, generate_course, normalize_lessons
from services.document_processor import OCRUnavailableError, UnsupportedDocumentError, process_document_file
from services.migrations import SchemaTooNewError, apply_migrations, get_schema_version, list_applied_migrations
from services.prompts import build_training_prompt
from services.rag import format_rag_context, search_chunks
from services.storage import Storage
from services.versioning import APP_VERSION, SUPPORTED_SCHEMA_VERSION


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
APP_SHELL_STYLE = """
<style>
html, body, [data-testid="stAppViewContainer"] {
    background: #f5f7fb;
}
[data-testid="stSidebar"] {
    background: #f7f8fb;
    border-right: 1px solid #e5e7ef;
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
    padding: 8px 2px 16px;
}
.sidebar-brand-title {
    color: #111827;
    font-size: 20px;
    font-weight: 750;
    line-height: 1.2;
}
.sidebar-brand-subtitle {
    color: #6b7280;
    font-size: 12px;
    margin-top: 4px;
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
    .workbench-grid {
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


def escape_html(value: object) -> str:
    return html.escape(str(value), quote=True)


@st.cache_resource
def get_storage() -> Storage:
    store = Storage()
    store.init_db()
    try:
        apply_migrations(store, reason=f"startup_{APP_VERSION}")
    except SchemaTooNewError as exc:
        st.error(str(exc))
        st.stop()
    store.seed_templates()
    return store


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
    st.sidebar.markdown(
        f"""
<div class="sidebar-brand">
  <div class="sidebar-brand-title">法硕知识助手</div>
  <div class="sidebar-brand-subtitle">Socratic workbench · v{APP_VERSION}</div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.session_state["beginner_mode"] = st.sidebar.checkbox(
        "新手模式",
        value=st.session_state.get("beginner_mode", BEGINNER_MODE_DEFAULT),
        help="默认隐藏提示词编辑等高级选项；需要细调模板时可以关闭。",
    )
    st.sidebar.caption("推荐顺序：录入薄弱点 → 苏格拉底训练 → 周度/月度复盘")
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
    return current_page


def render_workspace_header(page: str) -> None:
    defaults = get_default_ai_config()
    api_key = st.session_state.get("api_key", defaults["api_key"])
    ai_status = get_ai_status_label({"api_key": str(api_key or "")})
    group_name = get_page_group(page)
    subtitle = PAGE_SUBTITLES.get(page, "")
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
    <span class="status-pill">v{escape_html(APP_VERSION)}</span>
    <span class="{status_class}">{escape_html(ai_status)}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def page_today(store: Storage) -> None:
    render_beginner_guide()
    weak_points = store.list_weak_points()
    sessions = store.list_sessions()
    stats = compute_weak_point_stats(weak_points, sessions)

    render_workbench_metrics(stats)

    action = get_next_action(weak_points, sessions)
    render_next_action_card(action)

    st.subheader("建议优先处理")
    if stats["low_mastery"]:
        render_priority_list(stats["low_mastery"][:5])
    else:
        st.info("先录入一个错题或薄弱点，再开始苏格拉底训练。")


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
    st.caption("第一次录入只填核心字段即可；照片、题干和参考答案都可以后补。")
    with st.form("weak_point_form", clear_on_submit=True):
        uploaded_file = st.file_uploader(
            "错题照片",
            type=["png", "jpg", "jpeg", "webp"],
            help="实体书拍照即可；第一版先做留档，不强制 OCR。",
        )
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
        question_text = st.text_area(
            "题干，可选",
            height=120,
            placeholder="可以先空着；后面需要案例分析时再补。",
        )
        reference_answer = st.text_area(
            "参考答案，可选",
            height=120,
            placeholder="可以粘贴答案或写采分点。",
        )
        notes = st.text_area("备注，可选", height=80, placeholder="例如：书名、页码、题号。")
        submitted = st.form_submit_button("保存薄弱点")

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
        st.success(f"已保存薄弱点 #{weak_point_id}")

    st.subheader("最近录入")
    recent = store.list_weak_points()[:10]
    if recent:
        st.dataframe(pd.DataFrame(recent), use_container_width=True)
    else:
        st.caption("还没有录入记录。")


def page_training(store: Storage) -> None:
    beginner_mode = st.session_state.get("beginner_mode", BEGINNER_MODE_DEFAULT)
    weak_points = store.list_weak_points()
    templates = store.list_templates()
    if not weak_points:
        st.info("请先去「错题/薄弱点录入」保存一个考点。只填科目、题型、考点、错因和掌握度即可。")
        return
    if not templates:
        st.warning("没有启用中的模板，请先在模板管理中启用模板。")
        return

    weak_point = st.selectbox(
        "选择薄弱点",
        weak_points,
        format_func=lambda row: f"{row['subject']}｜{row['knowledge_point']}｜{row['mastery_level']}",
    )
    template = st.selectbox("选择追问模板", templates, format_func=lambda row: row["name"])
    student_goal = st.text_input("本次训练目标", value=template["default_goal"])
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
    if source_context:
        with st.expander("本次训练会参考的资料片段"):
            st.text(source_context)
    prompt_snapshot = build_training_prompt(
        weak_point=weak_point,
        template=template,
        student_goal=student_goal,
        recent_weaknesses=recent_weaknesses,
        prompt_override=prompt_override,
        source_context=source_context,
    )

    with st.expander("预览本次完整提示词"):
        st.code(prompt_snapshot)

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

    if st.button("开始训练"):
        session_id = store.create_session(
            weak_point_id=weak_point["id"],
            template_id=template["id"],
            template_version=template["current_version"],
            prompt_snapshot=prompt_snapshot,
            mastery_before=weak_point["mastery_level"],
        )
        st.session_state["active_session_id"] = session_id
        try:
            reply = get_ai_client().chat([{"role": "system", "content": prompt_snapshot}])
            store.add_message(session_id, "assistant", reply)
            st.rerun()
        except AIConfigurationError as exc:
            st.warning(str(exc))
        except Exception as exc:
            st.error(f"AI 调用失败：{exc}")

    session_id = st.session_state.get("active_session_id")
    if not session_id:
        return

    st.divider()
    st.subheader(f"当前训练 #{session_id}")
    messages = store.list_messages(session_id)
    for message in messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

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
            st.rerun()
        except AIConfigurationError as exc:
            st.warning(str(exc))
        except Exception as exc:
            st.error(f"AI 调用失败：{exc}")

    with st.form("finish_session_form"):
        mastery_after = st.selectbox("训练后掌握度", MASTERY_LEVELS, index=2)
        summary = st.text_area("训练总结", height=80)
        exposed_issues = st.text_area("暴露问题", height=80)
        next_review_suggestion = st.text_area("下次复习建议", height=80)
        finish = st.form_submit_button("结束训练")
    if finish:
        store.finish_session(
            session_id,
            mastery_after,
            summary,
            exposed_issues,
            next_review_suggestion,
        )
        st.session_state["active_session_id"] = None
        st.success("训练已结束并保存。")


def page_knowledge_base(store: Storage) -> None:
    st.caption("上传讲义、真题解析或笔记后，系统会本地抽取文本、建立检索索引，并可用大模型生成后续课程。")

    documents = store.list_documents()
    chunks = store.list_document_chunks()
    courses = store.list_courses()

    col1, col2, col3 = st.columns(3)
    col1.metric("资料", len(documents))
    col2.metric("文本片段", len(chunks))
    col3.metric("生成课程", len(courses))

    st.subheader("1. 上传并处理资料")
    with st.form("document_upload_form", clear_on_submit=True):
        uploaded_file = st.file_uploader(
            "上传 PDF、图片、TXT 或 Markdown",
            type=["pdf", "png", "jpg", "jpeg", "webp", "txt", "md", "markdown"],
            help="PDF 会优先直接抽文字；图片会尝试用本地 Tesseract OCR。",
        )
        submitted = st.form_submit_button("上传并建立索引")

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
                if text_chunks:
                    st.success(f"已处理 {uploaded_file.name}，生成 {len(text_chunks)} 个检索片段。")
                else:
                    st.warning("文件已保存，但没有抽取到有效文本。扫描版 PDF 可以先转成图片再上传 OCR。")
            except OCRUnavailableError as exc:
                store.update_document_processing(document_id, "", "error", str(exc))
                st.error(str(exc))
            except UnsupportedDocumentError as exc:
                store.update_document_processing(document_id, "", "error", str(exc))
                st.error(str(exc))
            except Exception as exc:
                store.update_document_processing(document_id, "", "error", str(exc))
                st.error(f"处理失败：{exc}")

    documents = store.list_documents()
    chunks = store.list_document_chunks()
    if documents:
        with st.expander("已上传资料", expanded=False):
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "id": row["id"],
                            "filename": row["filename"],
                            "status": row["status"],
                            "error": row["error_message"],
                            "created_at": row["created_at"],
                        }
                        for row in documents
                    ]
                ),
                use_container_width=True,
            )

    st.subheader("2. 检索资料片段")
    query = st.text_input("输入要查的考点或问题", placeholder="例如：共同犯罪成立条件")
    if st.button("检索资料"):
        results = search_chunks(query, chunks, top_k=5)
        store.create_rag_query(query, [int(result["id"]) for result in results])
        if results:
            st.write("命中的资料片段：")
            for result in results:
                st.markdown(f"**{result['source_label']}** ｜相关度 {result['score']:.3f}")
                st.write(result["content"])
        else:
            st.info("没有检索到资料片段。请先上传资料，或换一个更具体的考点。")

    st.subheader(COURSE_GENERATION_SECTION_TITLE)
    ready_documents = [row for row in documents if row["status"] == "ready"]
    if not ready_documents:
        st.info("先上传并成功处理一份资料后，再生成课程。")
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

        with st.expander("生成课程将参考的资料片段"):
            st.text(source_context or "暂无资料片段")

        if st.button("调用大模型生成课程"):
            if not source_context:
                st.error("该资料没有可用文本片段，无法生成课程。")
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
                    st.success(f"已生成课程 #{course_id}：{course['title']}")
                except AIConfigurationError as exc:
                    st.warning(str(exc))
                except CourseGenerationError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"生成失败：{exc}")

    courses = store.list_courses()
    if courses:
        st.subheader("已生成课程")
        selected_course = st.selectbox(
            "选择课程",
            courses,
            format_func=lambda row: f"#{row['id']} {row['title']}",
        )
        lessons = store.list_course_lessons(selected_course["id"])
        for lesson in lessons:
            with st.expander(f"第 {lesson['lesson_index']} 课：{lesson['title']}", expanded=False):
                st.write(f"目标：{lesson['objective']}")
                st.write("训练点：" + "、".join(lesson["knowledge_points"]))
                st.write("易错风险：" + "、".join(lesson["mistake_risks"]))
                st.write(f"苏格拉底模板：{lesson['recommended_template']}")
                st.write(f"执行安排：{lesson['review_plan']}")
                if lesson["imported_weak_point_id"]:
                    st.success(f"已导入为薄弱点 #{lesson['imported_weak_point_id']}")
                else:
                    subject = st.selectbox(LESSON_SUBJECT_LABEL, SUBJECTS, key=f"lesson_subject_{lesson['id']}")
                    if st.button(IMPORT_LESSON_BUTTON_LABEL, key=f"import_lesson_{lesson['id']}"):
                        weak_point_id = store.import_lesson_as_weak_point(lesson["id"], subject)
                        st.success(f"已导入为薄弱点 #{weak_point_id}")


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
    stats = compute_weak_point_stats(weak_points, sessions)

    if not weak_points:
        st.info("暂无薄弱点记录。")
        return

    st.subheader("按科目")
    st.dataframe(pd.DataFrame(stats["by_subject"]), use_container_width=True)
    st.subheader("按考点")
    st.dataframe(pd.DataFrame(stats["by_knowledge_point"]), use_container_width=True)
    st.subheader("按错因")
    st.dataframe(pd.DataFrame(stats["by_mistake_reason"]), use_container_width=True)
    st.subheader("低掌握度优先清单")
    st.dataframe(pd.DataFrame(stats["low_mastery"]), use_container_width=True)


def page_review(store: Storage) -> None:
    period = st.radio("复盘周期", ["本周", "本月"], horizontal=True)
    report = build_review_report(period, store.list_weak_points(), store.list_sessions())
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
    col1.metric("应用版本", APP_VERSION)
    col2.metric("数据库版本", schema_version)
    col3.metric("支持版本", SUPPORTED_SCHEMA_VERSION)

    if schema_version > SUPPORTED_SCHEMA_VERSION:
        st.error("数据库版本高于当前应用支持版本。为保护数据，当前版本不应继续写入。")
    elif schema_version < SUPPORTED_SCHEMA_VERSION:
        st.warning("数据库版本低于当前应用支持版本。启动流程会尝试备份后迁移。")
    else:
        st.success("数据库版本与当前应用匹配。")

    st.subheader("数据完整性")
    current_integrity = integrity_check(store)
    st.write(f"SQLite integrity_check：`{current_integrity}`")
    counts = collect_table_counts(store)
    st.dataframe(
        pd.DataFrame([{"table": table, "count": count} for table, count in counts.items()]),
        use_container_width=True,
    )

    st.subheader("手动备份")
    st.write("备份会复制数据库、错题图片目录和资料目录，并生成 manifest.json。")
    if st.button("立即创建备份"):
        backup_dir = create_backup(store, reason="manual_backup")
        st.success(f"已创建备份：{backup_dir}")

    st.subheader("迁移记录")
    migrations = list_applied_migrations(store)
    if migrations:
        st.dataframe(pd.DataFrame(migrations), use_container_width=True)
    else:
        st.info("暂无迁移记录。")

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
