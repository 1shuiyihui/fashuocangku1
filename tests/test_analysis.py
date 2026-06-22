from services.analysis import build_review_report, compute_weak_point_stats


def _create_sample_weak_points(storage):
    for payload in [
        {
            "subject": "刑法",
            "question_type": "案例分析",
            "knowledge_point": "共同犯罪",
            "mistake_reason": "要件遗漏",
            "mastery_level": "模糊",
            "image_path": "",
            "question_text": "",
            "reference_answer": "",
            "notes": "",
        },
        {
            "subject": "刑法",
            "question_type": "单选",
            "knowledge_point": "共同犯罪",
            "mistake_reason": "概念混淆",
            "mastery_level": "陌生",
            "image_path": "",
            "question_text": "",
            "reference_answer": "",
            "notes": "",
        },
        {
            "subject": "民法",
            "question_type": "多选",
            "knowledge_point": "表见代理",
            "mistake_reason": "要件遗漏",
            "mastery_level": "基本会",
            "image_path": "",
            "question_text": "",
            "reference_answer": "",
            "notes": "",
        },
    ]:
        storage.create_weak_point(payload)


def test_compute_weak_point_stats_groups_by_subject_point_and_reason(storage):
    _create_sample_weak_points(storage)

    stats = compute_weak_point_stats(storage.list_weak_points(), storage.list_sessions())

    assert stats["total_weak_points"] == 3
    assert stats["by_subject"][0]["subject"] == "刑法"
    assert stats["by_subject"][0]["count"] == 2
    assert stats["by_knowledge_point"][0]["knowledge_point"] == "共同犯罪"
    assert stats["by_knowledge_point"][0]["count"] == 2
    assert stats["by_mistake_reason"][0]["mistake_reason"] == "要件遗漏"
    assert stats["by_mistake_reason"][0]["count"] == 2


def test_review_report_mentions_priorities_and_training_recommendations(storage):
    _create_sample_weak_points(storage)

    report = build_review_report(
        period_label="本周",
        weak_points=storage.list_weak_points(),
        sessions=storage.list_sessions(),
    )

    assert "# 本周复盘" in report
    assert "共同犯罪" in report
    assert "要件遗漏" in report
    assert "建议优先训练" in report


def test_review_report_includes_error_reconstruction_and_drills(storage):
    _create_sample_weak_points(storage)
    weak_point = storage.list_weak_points()[0]
    storage.create_error_analysis(
        {
            "weak_point_id": weak_point["id"],
            "error_location": "构成要件与采分表达",
            "root_cause": "要件遗漏",
            "evidence": "漏写共同故意和共同实行行为。",
            "review_drill": "默写共同犯罪成立条件。",
            "variant_drill": "把共同故意改成单方意思联络后判断。",
            "status": "confirmed",
        }
    )

    report = build_review_report(
        period_label="本周",
        weak_points=storage.list_weak_points(),
        sessions=storage.list_sessions(),
        error_analyses=storage.list_error_analyses(),
    )

    assert "## 错因还原" in report
    assert "漏写共同故意" in report
    assert "## 复盘练习与变式练习" in report
    assert "默写共同犯罪成立条件" in report
