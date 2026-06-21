from services.prompts import SYSTEM_RULES, build_training_prompt, render_template


def test_render_template_replaces_known_variables_and_blanks_missing_values():
    body = "科目：{subject}\n考点：{knowledge_point}\n备注：{missing_value}"
    rendered = render_template(
        body,
        {
            "subject": "刑法",
            "knowledge_point": "共同犯罪",
        },
    )

    assert "科目：刑法" in rendered
    assert "考点：共同犯罪" in rendered
    assert "备注：" in rendered
    assert "{missing_value}" not in rendered


def test_build_training_prompt_includes_rules_template_and_context(storage):
    weak_point_id = storage.create_weak_point(
        {
            "subject": "宪法",
            "question_type": "简答",
            "knowledge_point": "宪法监督",
            "mistake_reason": "记忆不牢",
            "mastery_level": "模糊",
            "image_path": "",
            "question_text": "",
            "reference_answer": "",
            "notes": "容易漏掉主体",
        }
    )
    weak_point = storage.get_weak_point(weak_point_id)
    template = storage.list_templates()[0]

    prompt = build_training_prompt(
        weak_point=weak_point,
        template=template,
        student_goal="考前快速补齐采分点",
        recent_weaknesses=["宪法监督", "法律解释"],
        prompt_override=None,
    )

    assert SYSTEM_RULES in prompt
    assert "宪法监督" in prompt
    assert "考前快速补齐采分点" in prompt
    assert "法律解释" in prompt
    assert template["default_goal"] in prompt


def test_build_training_prompt_uses_override_body(storage):
    weak_point = storage.get_weak_point(
        storage.create_weak_point(
            {
                "subject": "民法",
                "question_type": "单选",
                "knowledge_point": "无权代理",
                "mistake_reason": "要件遗漏",
                "mastery_level": "陌生",
                "image_path": "",
                "question_text": "",
                "reference_answer": "",
                "notes": "",
            }
        )
    )
    template = storage.list_templates()[0]

    prompt = build_training_prompt(
        weak_point=weak_point,
        template=template,
        student_goal="只追问构成要件",
        recent_weaknesses=[],
        prompt_override="请先问本人可归责性是什么。",
    )

    assert "请先问本人可归责性是什么。" in prompt
    assert template["body"] not in prompt
