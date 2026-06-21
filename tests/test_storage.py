def test_seed_templates_are_inserted_once(storage):
    first = storage.list_templates(active_only=False)
    storage.seed_templates()
    second = storage.list_templates(active_only=False)

    assert len(first) == 6
    assert len(second) == 6
    assert {row["name"] for row in first} == {
        "概念辨析追问",
        "构成要件追问",
        "案例分析追问",
        "主观题采分追问",
        "考前速记追问",
        "错因修复追问",
    }


def test_create_weak_point_with_image_path(storage):
    weak_point_id = storage.create_weak_point(
        {
            "subject": "刑法",
            "question_type": "案例分析",
            "knowledge_point": "盗窃罪与侵占罪区分",
            "mistake_reason": "概念混淆",
            "mastery_level": "模糊",
            "image_path": "data/uploads/example.png",
            "question_text": "甲将代为保管的财物占为己有。",
            "reference_answer": "应围绕占有转移和非法占有目的分析。",
            "notes": "实体书第 23 页",
        }
    )

    row = storage.get_weak_point(weak_point_id)

    assert row["subject"] == "刑法"
    assert row["knowledge_point"] == "盗窃罪与侵占罪区分"
    assert row["image_path"] == "data/uploads/example.png"


def test_template_update_creates_new_version(storage):
    template = storage.list_templates()[0]
    new_version = storage.update_template(
        template["id"],
        {
            "name": template["name"],
            "subject_scope": "刑法",
            "question_type_scope": template["question_type_scope"],
            "body": template["body"] + "\n请加入一个反例追问。",
            "default_goal": template["default_goal"],
            "end_condition": template["end_condition"],
            "is_active": True,
        },
    )

    updated = storage.get_template(template["id"])
    versions = storage.list_template_versions(template["id"])

    assert new_version == 2
    assert updated["current_version"] == 2
    assert len(versions) == 2
    assert "反例追问" in versions[-1]["body"]


def test_training_session_messages_and_finish(storage):
    weak_point_id = storage.create_weak_point(
        {
            "subject": "民法",
            "question_type": "单选",
            "knowledge_point": "表见代理",
            "mistake_reason": "要件遗漏",
            "mastery_level": "陌生",
            "image_path": "",
            "question_text": "",
            "reference_answer": "",
            "notes": "",
        }
    )
    template = storage.list_templates()[0]
    session_id = storage.create_session(
        weak_point_id=weak_point_id,
        template_id=template["id"],
        template_version=template["current_version"],
        prompt_snapshot="系统规则 + 模板正文",
        mastery_before="陌生",
    )

    storage.add_message(session_id, "assistant", "表见代理首先要保护谁的信赖？")
    storage.add_message(session_id, "user", "保护相对人的合理信赖。")
    storage.finish_session(
        session_id,
        mastery_after="基本会",
        summary="能说出核心保护对象，但构成要件还不完整。",
        exposed_issues="遗漏权利外观和本人可归责性。",
        next_review_suggestion="2 天后用构成要件追问模板复习。",
    )

    session = storage.get_session(session_id)
    messages = storage.list_messages(session_id)

    assert session["status"] == "finished"
    assert session["mastery_after"] == "基本会"
    assert len(messages) == 2
    assert messages[0]["role"] == "assistant"


def test_copy_template_creates_independent_template(storage):
    template = storage.list_templates()[0]

    copied_id = storage.copy_template(template["id"], template["name"] + " 副本")
    copied = storage.get_template(copied_id)

    assert copied["name"].endswith("副本")
    assert copied["body"] == template["body"]
    assert copied["id"] != template["id"]


def test_document_chunks_course_and_lesson_import(storage):
    document_id = storage.create_document(
        {
            "filename": "刑法讲义.txt",
            "file_type": ".txt",
            "file_path": "data/documents/xingfa.txt",
            "status": "uploaded",
        }
    )
    storage.update_document_processing(
        document_id,
        text_content="共同犯罪要求二人以上共同故意实施犯罪。",
        status="ready",
    )
    storage.replace_document_chunks(
        document_id,
        [
            {"content": "共同犯罪要求二人以上共同故意实施犯罪。", "source_label": "刑法讲义.txt#1"},
            {"content": "犯罪中止要求自动放弃犯罪或者自动有效防止结果发生。", "source_label": "刑法讲义.txt#2"},
        ],
    )

    document = storage.get_document(document_id)
    chunks = storage.list_document_chunks(document_id)

    assert document["status"] == "ready"
    assert len(chunks) == 2
    assert chunks[0]["source_label"] == "刑法讲义.txt#1"

    query_id = storage.create_rag_query("共同犯罪", [chunks[0]["id"]])
    assert query_id > 0

    course_id = storage.create_course(
        title="刑法共同犯罪冲刺课",
        source_document_id=document_id,
        raw_json='{"title":"刑法共同犯罪冲刺课"}',
        lessons=[
            {
                "title": "共同犯罪成立条件",
                "objective": "掌握共同犯罪的成立要件",
                "knowledge_points": ["共同犯罪"],
                "mistake_risks": ["遗漏共同故意"],
                "recommended_template": "构成要件追问",
                "review_plan": "第 1 天完成追问，第 3 天复盘。",
            }
        ],
    )
    lessons = storage.list_course_lessons(course_id)
    weak_point_id = storage.import_lesson_as_weak_point(lessons[0]["id"], subject="刑法")
    imported = storage.get_weak_point(weak_point_id)
    updated_lesson = storage.list_course_lessons(course_id)[0]

    assert imported["knowledge_point"] == "共同犯罪"
    assert imported["mistake_reason"] == "遗漏共同故意"
    assert updated_lesson["imported_weak_point_id"] == weak_point_id
