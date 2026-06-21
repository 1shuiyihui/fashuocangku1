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
