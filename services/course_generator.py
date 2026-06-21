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
        "输出必须是合法 JSON，不要输出 Markdown、解释或多余文字。"
    )
    user = f"""请基于以下资料片段生成法硕学习课程。

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
      "review_plan": "复习安排"
    }}
  ]
}}

要求：
1. 每节课都要能导入为后续苏格拉底训练点。
2. knowledge_points 使用短考点名。
3. mistake_risks 写最容易错的具体原因。
4. recommended_template 从“概念辨析追问、构成要件追问、案例分析追问、主观题采分追问、考前速记追问、错因修复追问”中选择。
5. lessons 数量控制在 3 到 8 个。"""
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
        knowledge_points = lesson.get("knowledge_points") or []
        mistake_risks = lesson.get("mistake_risks") or []
        if isinstance(knowledge_points, str):
            knowledge_points = [knowledge_points]
        if isinstance(mistake_risks, str):
            mistake_risks = [mistake_risks]
        lessons.append(
            {
                "title": lesson.get("title") or f"第 {index} 课",
                "objective": lesson.get("objective", ""),
                "knowledge_points": [str(item) for item in knowledge_points],
                "mistake_risks": [str(item) for item in mistake_risks],
                "recommended_template": lesson.get("recommended_template", "构成要件追问"),
                "review_plan": lesson.get("review_plan", ""),
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
