from services.error_analysis import build_error_analysis, build_review_drill_pack


def test_build_error_analysis_restores_error_location_from_weak_point_fields():
    weak_point = {
        "subject": "刑法",
        "question_type": "案例分析",
        "knowledge_point": "抢劫罪",
        "mistake_reason": "要件遗漏",
        "mastery_level": "陌生",
        "question_text": "甲以暴力压制乙反抗后当场取走财物。",
        "reference_answer": "抢劫罪要求以暴力、胁迫或者其他方法压制反抗并劫取财物。",
        "notes": "漏写压制反抗，只写了取财。",
    }

    analysis = build_error_analysis(weak_point)

    assert analysis["error_location"] == "构成要件与采分表达"
    assert analysis["root_cause"] == "要件遗漏"
    assert "压制反抗" in analysis["evidence"]
    assert "复盘练习" not in analysis["review_drill"]
    assert "变式" in analysis["variant_drill"]


def test_build_error_analysis_uses_training_context_to_refine_evidence():
    weak_point = {
        "subject": "刑法",
        "question_type": "简答",
        "knowledge_point": "共同犯罪",
        "mistake_reason": "概念混淆",
        "mastery_level": "模糊",
        "question_text": "",
        "reference_answer": "",
        "notes": "",
    }
    session_context = {
        "summary": "学生把共同故意说成共同实施行为。",
        "exposed_issues": "定义有误，遗漏二人以上共同故意。",
        "next_review_suggestion": "重新默写法条定义。",
    }

    analysis = build_error_analysis(weak_point, session_context=session_context)

    assert analysis["error_location"] == "概念边界"
    assert analysis["root_cause"] == "概念混淆"
    assert "共同故意" in analysis["evidence"]
    assert "共同犯罪" in analysis["review_drill"]


def test_build_review_drill_pack_groups_error_analyses_by_root_cause():
    analyses = [
        {
            "weak_point_id": 1,
            "knowledge_point": "抢劫罪",
            "root_cause": "要件遗漏",
            "error_location": "构成要件与采分表达",
            "review_drill": "默写抢劫罪四要件。",
            "variant_drill": "改写案例中的手段行为。",
        },
        {
            "weak_point_id": 2,
            "knowledge_point": "共同犯罪",
            "root_cause": "要件遗漏",
            "error_location": "构成要件与采分表达",
            "review_drill": "默写共同犯罪成立条件。",
            "variant_drill": "把共同故意替换为过失共同。",
        },
    ]

    pack = build_review_drill_pack(analyses)

    assert pack[0]["root_cause"] == "要件遗漏"
    assert pack[0]["count"] == 2
    assert "抢劫罪" in pack[0]["focus_points"]
    assert len(pack[0]["variant_drills"]) == 2
