from __future__ import annotations

from sqlite3 import IntegrityError

import pandas as pd
import streamlit as st

from services.ai_client import AIClient, AIConfigurationError
from services.analysis import build_review_report, compute_weak_point_stats
from services.prompts import build_training_prompt
from services.storage import Storage


SUBJECTS = ["刑法", "民法", "法理", "宪法", "法制史"]
QUESTION_TYPES = ["单选", "多选", "简答", "论述", "案例分析"]
MISTAKE_REASONS = ["概念混淆", "要件遗漏", "法条不熟", "案例事实误判", "记忆不牢", "表达不规范"]
MASTERY_LEVELS = ["陌生", "模糊", "基本会", "熟练"]
PAGES = ["今日学习", "错题/薄弱点录入", "苏格拉底训练", "模板管理", "薄弱点分析", "周度/月度复盘"]


@st.cache_resource
def get_storage() -> Storage:
    store = Storage()
    store.init_db()
    store.seed_templates()
    return store


def get_ai_client() -> AIClient:
    return AIClient(
        api_base=st.session_state.get("api_base", ""),
        api_key=st.session_state.get("api_key", ""),
        model=st.session_state.get("model", ""),
    )


def main() -> None:
    st.set_page_config(page_title="法硕苏格拉底学习器", layout="wide")
    store = get_storage()
    render_sidebar()
    page = st.sidebar.radio("页面", PAGES)

    if page == "今日学习":
        page_today(store)
    elif page == "错题/薄弱点录入":
        page_entry(store)
    elif page == "苏格拉底训练":
        page_training(store)
    elif page == "模板管理":
        page_templates(store)
    elif page == "薄弱点分析":
        page_analysis(store)
    else:
        page_review(store)


def render_sidebar() -> None:
    st.sidebar.header("AI 配置")
    st.session_state["api_base"] = st.sidebar.text_input(
        "API Base",
        value=st.session_state.get("api_base", "https://api.openai.com/v1"),
    )
    st.session_state["model"] = st.sidebar.text_input(
        "Model",
        value=st.session_state.get("model", "gpt-4.1-mini"),
    )
    st.session_state["api_key"] = st.sidebar.text_input(
        "API Key",
        value=st.session_state.get("api_key", ""),
        type="password",
    )


def page_today(store: Storage) -> None:
    st.title("今日学习")
    weak_points = store.list_weak_points()
    sessions = store.list_sessions()
    stats = compute_weak_point_stats(weak_points, sessions)

    col1, col2, col3 = st.columns(3)
    col1.metric("薄弱点", stats["total_weak_points"])
    col2.metric("训练次数", stats["total_sessions"])
    col3.metric("完成训练", stats["finished_sessions"])

    st.subheader("建议优先处理")
    if stats["low_mastery"]:
        for row in stats["low_mastery"][:5]:
            st.write(
                f"- {row['subject']}｜{row['knowledge_point']}｜{row['mistake_reason']}｜{row['mastery_level']}"
            )
    else:
        st.info("先录入一个错题或薄弱点，再开始苏格拉底训练。")


def page_entry(store: Storage) -> None:
    st.title("错题/薄弱点录入")
    with st.form("weak_point_form", clear_on_submit=True):
        uploaded_file = st.file_uploader("错题照片", type=["png", "jpg", "jpeg", "webp"])
        subject = st.selectbox("科目", SUBJECTS)
        question_type = st.selectbox("题型", QUESTION_TYPES)
        knowledge_point = st.text_input("考点")
        mistake_reason = st.selectbox("错因", MISTAKE_REASONS)
        mastery_level = st.selectbox("掌握度", MASTERY_LEVELS)
        question_text = st.text_area("题干，可选", height=120)
        reference_answer = st.text_area("参考答案，可选", height=120)
        notes = st.text_area("备注，可选", height=80)
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
    st.title("苏格拉底训练")
    weak_points = store.list_weak_points()
    templates = store.list_templates()
    if not weak_points:
        st.info("请先录入错题或薄弱点。")
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
    prompt_override = st.text_area("本次提示词，可临时修改", value=template["body"], height=220)
    save_as = st.text_input("保存为新模板名称，可留空")
    recent_weaknesses = [row["knowledge_point"] for row in weak_points[:5]]
    prompt_snapshot = build_training_prompt(
        weak_point=weak_point,
        template=template,
        student_goal=student_goal,
        recent_weaknesses=recent_weaknesses,
        prompt_override=prompt_override,
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


def page_templates(store: Storage) -> None:
    st.title("模板管理")
    templates = store.list_templates(active_only=False)
    if templates:
        selected = st.selectbox(
            "选择模板",
            templates,
            format_func=lambda row: f"{row['name']} v{row['current_version']}",
        )
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
    st.title("薄弱点分析")
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
    st.title("周度/月度复盘")
    period = st.radio("复盘周期", ["本周", "本月"], horizontal=True)
    report = build_review_report(period, store.list_weak_points(), store.list_sessions())
    st.markdown(report)
    st.download_button(
        "下载 Markdown",
        data=report.encode("utf-8"),
        file_name=f"{period}复盘.md",
        mime="text/markdown",
    )


if __name__ == "__main__":
    main()
