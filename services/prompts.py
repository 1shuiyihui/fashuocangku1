from __future__ import annotations

import re
from typing import Any


SYSTEM_RULES = """你是法硕考研苏格拉底式导师。
目标是通过连续追问帮助学生掌握考点，而不是直接灌输答案。
每次只问一个问题。
不要一次性给完整解析。
学生回答后，先判断回答质量，再决定追问、提示、纠错或提高难度。
训练内容必须围绕法硕考试表达、考点辨析、案例适用和主观题采分点。"""


VARIABLE_PATTERN = re.compile(r"{([a-zA-Z_][a-zA-Z0-9_]*)}")


def render_template(body: str, values: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        value = values.get(match.group(1), "")
        if isinstance(value, list):
            return "、".join(str(item) for item in value)
        return str(value)

    return VARIABLE_PATTERN.sub(replace, body)


def build_training_prompt(
    weak_point: dict[str, Any],
    template: dict[str, Any],
    student_goal: str,
    recent_weaknesses: list[str],
    prompt_override: str | None,
) -> str:
    values = {
        "subject": weak_point.get("subject", ""),
        "question_type": weak_point.get("question_type", ""),
        "knowledge_point": weak_point.get("knowledge_point", ""),
        "mistake_reason": weak_point.get("mistake_reason", ""),
        "mastery_level": weak_point.get("mastery_level", ""),
        "question_text": weak_point.get("question_text", ""),
        "reference_answer": weak_point.get("reference_answer", ""),
        "notes": weak_point.get("notes", ""),
        "student_goal": student_goal,
        "recent_weaknesses": recent_weaknesses,
    }
    body = prompt_override if prompt_override is not None else template.get("body", "")
    rendered_body = render_template(body, values)
    return "\n\n".join(
        [
            SYSTEM_RULES,
            "【模板默认目标】\n" + template.get("default_goal", ""),
            "【本次训练目标】\n" + (student_goal or template.get("default_goal", "")),
            "【结束条件】\n" + template.get("end_condition", ""),
            "【薄弱点信息】\n"
            + f"科目：{values['subject']}\n"
            + f"题型：{values['question_type']}\n"
            + f"考点：{values['knowledge_point']}\n"
            + f"错因：{values['mistake_reason']}\n"
            + f"掌握度：{values['mastery_level']}\n"
            + f"近期薄弱点：{render_template('{recent_weaknesses}', values)}",
            "【追问模板】\n" + rendered_body,
            "请先提出第一个问题。问题必须具体、短小，并且只包含一个问点。",
        ]
    )
