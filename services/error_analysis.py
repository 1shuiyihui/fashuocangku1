from __future__ import annotations

from collections import defaultdict
from typing import Any


ERROR_LOCATION_BY_REASON = {
    "概念混淆": "概念边界",
    "要件遗漏": "构成要件与采分表达",
    "法条不熟": "法条依据",
    "案例事实误判": "题干事实识别",
    "记忆不牢": "定义与关键词记忆",
    "表达不规范": "主观题表达",
}


def build_error_analysis(
    weak_point: dict[str, Any],
    session_context: dict[str, Any] | None = None,
) -> dict[str, str]:
    session_context = session_context or {}
    subject = str(weak_point.get("subject", ""))
    knowledge_point = str(weak_point.get("knowledge_point", ""))
    mistake_reason = str(weak_point.get("mistake_reason", "") or "待分析")
    question_type = str(weak_point.get("question_type", ""))
    error_location = ERROR_LOCATION_BY_REASON.get(mistake_reason, "作答路径")

    evidence_parts = _non_empty(
        [
            _source_line("题干", weak_point.get("question_text")),
            _source_line("参考答案", weak_point.get("reference_answer")),
            _source_line("备注", weak_point.get("notes")),
            _source_line("训练总结", session_context.get("summary")),
            _source_line("暴露问题", session_context.get("exposed_issues")),
            _source_line("下次建议", session_context.get("next_review_suggestion")),
        ]
    )
    evidence = "；".join(evidence_parts)
    if not evidence:
        evidence = f"当前记录仅包含“{subject}｜{knowledge_point}｜{mistake_reason}”，建议补充题干、原答案或参考答案后再精确还原。"

    review_drill = _build_review_drill(subject, knowledge_point, mistake_reason, question_type)
    variant_drill = _build_variant_drill(knowledge_point, mistake_reason, question_type)

    return {
        "error_location": error_location,
        "root_cause": mistake_reason,
        "evidence": evidence,
        "review_drill": review_drill,
        "variant_drill": variant_drill,
        "status": "confirmed" if session_context else "draft",
    }


def build_review_drill_pack(error_analyses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in error_analyses:
        root_cause = str(row.get("root_cause") or row.get("mistake_reason") or "待分析")
        grouped[root_cause].append(row)

    packs = []
    for root_cause, rows in grouped.items():
        focus_points = sorted(
            {
                str(row.get("knowledge_point", "")).strip()
                for row in rows
                if str(row.get("knowledge_point", "")).strip()
            }
        )
        review_drills = _unique_non_empty(str(row.get("review_drill", "")) for row in rows)
        variant_drills = _unique_non_empty(str(row.get("variant_drill", "")) for row in rows)
        locations = _unique_non_empty(str(row.get("error_location", "")) for row in rows)
        packs.append(
            {
                "root_cause": root_cause,
                "count": len(rows),
                "focus_points": "、".join(focus_points) or "待补充考点",
                "error_locations": "、".join(locations) or "待分析",
                "review_drills": review_drills,
                "variant_drills": variant_drills,
                "weak_point_ids": [int(row["weak_point_id"]) for row in rows if row.get("weak_point_id") is not None],
            }
        )
    return sorted(packs, key=lambda row: (-row["count"], row["root_cause"]))


def _build_review_drill(subject: str, knowledge_point: str, mistake_reason: str, question_type: str) -> str:
    prefix = f"{subject}｜{knowledge_point}".strip("｜")
    if mistake_reason == "要件遗漏":
        return f"{prefix}：默写核心构成要件，并用 3 句话说明每个要件对应的采分关键词。"
    if mistake_reason == "概念混淆":
        return f"{prefix}：写出相邻概念的定义、区别标准和一个反例。"
    if mistake_reason == "案例事实误判":
        return f"{prefix}：把题干事实拆成主体、行为、结果、主观状态四栏，再逐项匹配考点。"
    if mistake_reason == "表达不规范" or question_type in {"简答", "论述", "案例分析"}:
        return f"{prefix}：按“定义-要件-事实匹配-结论”重写一版可采分答案。"
    return f"{prefix}：先默写定义和关键词，再完成一轮苏格拉底追问。"


def _build_variant_drill(knowledge_point: str, mistake_reason: str, question_type: str) -> str:
    if mistake_reason == "要件遗漏":
        return f"变式：保留“{knowledge_point}”考点，替换一个关键要件事实，重新判断结论并写出理由。"
    if mistake_reason == "概念混淆":
        return f"变式：把“{knowledge_point}”替换为相邻概念，比较两个概念的成立条件。"
    if mistake_reason == "案例事实误判":
        return f"变式：改变题干中的主体身份或行为时间点，重新提取事实并判断。"
    if question_type in {"单选", "多选"}:
        return f"变式：为“{knowledge_point}”自拟 2 个干扰选项，并解释为什么错误。"
    return f"变式：围绕“{knowledge_point}”改写一个新案例，要求先列采分点再作答。"


def _source_line(label: str, value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return f"{label}：{text}"


def _non_empty(values: list[str]) -> list[str]:
    return [value for value in values if value]


def _unique_non_empty(values: Any) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result
