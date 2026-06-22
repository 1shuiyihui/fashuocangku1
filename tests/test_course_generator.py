import json

import pytest

from services.course_generator import (
    CourseGenerationError,
    build_course_prompt,
    generate_course,
    normalize_lessons,
    parse_course_json,
)


class FakeAIClient:
    def __init__(self, content: str):
        self.content = content
        self.messages = None

    def chat(self, messages):
        self.messages = messages
        return self.content


def _course_payload():
    return {
        "title": "刑法共同犯罪课程",
        "lessons": [
            {
                "title": "共同犯罪成立条件",
                "objective": "掌握共同犯罪要件",
                "knowledge_points": ["共同犯罪"],
                "mistake_risks": ["遗漏共同故意"],
                "recommended_template": "构成要件追问",
                "review_plan": "第 1 天训练，第 3 天复盘。",
            }
        ],
    }


def test_parse_course_json_accepts_plain_and_fenced_json():
    payload = _course_payload()
    plain = json.dumps(payload, ensure_ascii=False)
    fenced = f"```json\n{plain}\n```"

    assert parse_course_json(plain)["title"] == "刑法共同犯罪课程"
    assert parse_course_json(fenced)["lessons"][0]["title"] == "共同犯罪成立条件"


def test_parse_course_json_rejects_missing_lessons():
    with pytest.raises(CourseGenerationError):
        parse_course_json('{"title": "bad"}')


def test_build_course_prompt_includes_source_context_goal_and_days():
    messages = build_course_prompt(
        source_context="来源：刑法讲义\n共同犯罪要求共同故意。",
        course_goal="考前 7 天冲刺",
        days=7,
    )

    joined = "\n".join(message["content"] for message in messages)
    assert "共同犯罪要求共同故意" in joined
    assert "考前 7 天冲刺" in joined
    assert "7 天" in joined
    assert "JSON" in joined


def test_build_course_prompt_requests_executable_training_plan():
    messages = build_course_prompt(
        source_context="来源：刑法讲义\n共同犯罪要求二人以上共同故意。",
        course_goal="生成考前训练计划",
        days=7,
    )

    joined = "\n".join(message["content"] for message in messages)
    assert "可执行训练计划" in joined
    assert "estimated_minutes" in joined
    assert "daily_tasks" in joined
    assert "socratic_drills" in joined
    assert "review_checklist" in joined
    assert "importable_training_point" in joined


def test_generate_course_calls_ai_and_normalizes_lessons():
    payload = _course_payload()
    client = FakeAIClient(json.dumps(payload, ensure_ascii=False))

    course = generate_course(
        ai_client=client,
        source_context="共同犯罪要求共同故意。",
        course_goal="生成训练课",
        days=7,
    )
    lessons = normalize_lessons(course)

    assert client.messages is not None
    assert course["title"] == "刑法共同犯罪课程"
    assert lessons[0]["knowledge_points"] == ["共同犯罪"]


def test_normalize_lessons_accepts_executable_plan_fields():
    lessons = normalize_lessons(
        {
            "lessons": [
                {
                    "title": "共同犯罪成立条件",
                    "objective": "掌握共同犯罪成立条件",
                    "knowledge_points": [],
                    "mistake_risks": [],
                    "recommended_template": "构成要件追问",
                    "estimated_minutes": 25,
                    "daily_tasks": ["默写共同犯罪定义", "完成 3 轮构成要件追问"],
                    "socratic_drills": ["共同故意和同时犯如何区分？"],
                    "review_checklist": ["能直接引用《刑法》第25条第1款"],
                    "importable_training_point": {
                        "knowledge_point": "共同犯罪成立条件",
                        "mistake_reason": "共同故意与共同行为混淆",
                    },
                }
            ]
        }
    )

    lesson = lessons[0]
    assert lesson["knowledge_points"] == ["共同犯罪成立条件"]
    assert lesson["mistake_risks"] == ["共同故意与共同行为混淆"]
    assert "预计用时：25 分钟" in lesson["review_plan"]
    assert "当日任务：默写共同犯罪定义；完成 3 轮构成要件追问" in lesson["review_plan"]
    assert "苏格拉底追问：共同故意和同时犯如何区分？" in lesson["review_plan"]
    assert "复盘清单：能直接引用《刑法》第25条第1款" in lesson["review_plan"]
