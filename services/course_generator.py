from __future__ import annotations

import json
import re
from typing import Any


class CourseGenerationError(RuntimeError):
    pass


def build_course_prompt(
    source_context: str,
    course_goal: str,
    days: int,
) -> list[dict[str, str]]:
    system = (
        "你是法硕考研课程规划与苏格拉底训练设计助手。"
        "你必须只基于用户提供的资料片段生成课程；资料不足时写“资料不足”。"
        "你的输出目标不是泛泛大纲，而是能当天执行、能导入训练点的可执行训练计划。"
        "输出必须是合法 JSON，不要输出 Markdown、解释或多余文字。"
    )
    user = f"""请基于以下资料片段生成法硕考研可执行训练计划。

课程目标：{course_goal}
复习周期：{days} 天

资料片段：
{source_context}

JSON 格式必须严格如下：
{{
  "title": "课程标题",
  "lessons": [
    {{
      "title": "小节标题",
      "objective": "学习目标",
      "knowledge_points": ["考点1"],
      "mistake_risks": ["易错点1"],
      "recommended_template": "构成要件追问",
      "estimated_minutes": 25,
      "daily_tasks": ["当天必须完成的训练动作1"],
      "socratic_drills": ["用于训练的苏格拉底追问1"],
      "review_checklist": ["完成后必须自检的标准1"],
      "importable_training_point": {{
        "knowledge_point": "可导入的短训练点",
        "mistake_reason": "导入后用于训练的具体错因"
      }},
      "review_plan": "间隔复习安排"
    }}
  ]
}}

要求：
1. 每节课都要能直接导入为后续苏格拉底训练点。
2. knowledge_points 使用短考点名。
3. mistake_risks 写最容易错的具体原因。
4. recommended_template 从“概念辨析追问、构成要件追问、案例分析追问、主观题采分追问、考前速记追问、错因修复追问”中选择。
5. daily_tasks 必须写成考生可以照做的动作，例如默写定义、完成追问、补写采分表达。
6. socratic_drills 必须是能暴露薄弱点的追问，不要写成普通知识点摘要。
7. review_checklist 必须写成完成标准，例如能否引用法条、能否区分相邻概念。
8. review_plan 必须包含当天训练、间隔复盘和考前回看安排。
9. lessons 数量控制在 3 到 8 个。"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_course_json(content: str) -> dict[str, Any]:
    raw = _strip_fenced_json(content.strip())
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CourseGenerationError(f"模型没有返回合法 JSON：{exc}") from exc
    if not isinstance(payload, dict) or not payload.get("title") or not isinstance(payload.get("lessons"), list):
        raise CourseGenerationError("课程 JSON 缺少 title 或 lessons。")
    if not payload["lessons"]:
        raise CourseGenerationError("课程 JSON 至少需要 1 个 lesson。")
    return payload


def normalize_lessons(course: dict[str, Any]) -> list[dict[str, Any]]:
    lessons = []
    for index, lesson in enumerate(course.get("lessons", []), start=1):
        importable_training_point = lesson.get("importable_training_point") or {}
        if not isinstance(importable_training_point, dict):
            importable_training_point = {}
        knowledge_points = _as_text_list(lesson.get("knowledge_points"))
        mistake_risks = _as_text_list(lesson.get("mistake_risks"))
        importable_knowledge_point = str(importable_training_point.get("knowledge_point") or "").strip()
        importable_mistake_reason = str(importable_training_point.get("mistake_reason") or "").strip()
        if not knowledge_points and importable_knowledge_point:
            knowledge_points = [importable_knowledge_point]
        if not mistake_risks and importable_mistake_reason:
            mistake_risks = [importable_mistake_reason]
        lessons.append(
            {
                "title": lesson.get("title") or f"第 {index} 课",
                "objective": lesson.get("objective", ""),
                "knowledge_points": knowledge_points,
                "mistake_risks": mistake_risks,
                "recommended_template": lesson.get("recommended_template", "构成要件追问"),
                "review_plan": _build_executable_review_plan(lesson),
            }
        )
    return lessons


def generate_course(
    ai_client: Any,
    source_context: str,
    course_goal: str,
    days: int,
) -> dict[str, Any]:
    messages = build_course_prompt(source_context, course_goal, days)
    content = ai_client.chat(messages)
    return parse_course_json(content)


def _strip_fenced_json(content: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)```", content, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return content


def _as_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, list):
        candidates = value
    else:
        candidates = [value]
    return [str(item).strip() for item in candidates if str(item).strip()]


def _build_executable_review_plan(lesson: dict[str, Any]) -> str:
    sections = []
    review_plan = str(lesson.get("review_plan") or "").strip()
    if review_plan:
        sections.append(review_plan)

    estimated_minutes = lesson.get("estimated_minutes")
    if estimated_minutes not in (None, ""):
        sections.append(f"预计用时：{estimated_minutes} 分钟")

    daily_tasks = _as_text_list(lesson.get("daily_tasks"))
    if daily_tasks:
        sections.append("当日任务：" + "；".join(daily_tasks))

    socratic_drills = _as_text_list(lesson.get("socratic_drills"))
    if socratic_drills:
        sections.append("苏格拉底追问：" + "；".join(socratic_drills))

    review_checklist = _as_text_list(lesson.get("review_checklist"))
    if review_checklist:
        sections.append("复盘清单：" + "；".join(review_checklist))

    return "\n".join(sections)
