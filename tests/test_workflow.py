from __future__ import annotations

from services.workflow import build_learning_loop_state


def _weak_point(
    item_id: int,
    subject: str,
    knowledge_point: str,
    mastery_level: str,
    mistake_reason: str = "要件遗漏",
) -> dict[str, object]:
    return {
        "id": item_id,
        "subject": subject,
        "question_type": "简答",
        "knowledge_point": knowledge_point,
        "mistake_reason": mistake_reason,
        "mastery_level": mastery_level,
        "created_at": f"2026-06-2{item_id}T10:00:00+00:00",
    }


def test_learning_loop_state_routes_empty_data_to_entry():
    state = build_learning_loop_state([], [])

    assert state["next_action"]["page"] == "错题/薄弱点录入"
    assert state["next_action"]["kind"] == "entry"
    assert state["totals"]["untrained_weak_points"] == 0


def test_learning_loop_state_prioritizes_untrained_low_mastery_point():
    weak_points = [
        _weak_point(1, "刑法", "共同犯罪", "陌生"),
        _weak_point(2, "民法", "表见代理", "熟练"),
    ]

    state = build_learning_loop_state(weak_points, [])

    assert state["next_action"]["page"] == "苏格拉底训练"
    assert state["next_action"]["weak_point_id"] == 1
    assert state["priority_queue"][0]["id"] == 1
    assert state["priority_queue"][0]["workflow_action"] == "开始训练"
    assert state["totals"]["untrained_weak_points"] == 2


def test_learning_loop_state_counts_finished_training_and_routes_review():
    weak_points = [
        _weak_point(1, "刑法", "共同犯罪", "模糊"),
        _weak_point(2, "刑法", "共同犯罪", "陌生", mistake_reason="概念混淆"),
        _weak_point(3, "民法", "表见代理", "基本会"),
    ]
    sessions = [
        {"id": 10, "weak_point_id": 1, "status": "finished", "started_at": "2026-06-22T10:00:00+00:00"},
        {"id": 11, "weak_point_id": 2, "status": "finished", "started_at": "2026-06-22T11:00:00+00:00"},
    ]

    state = build_learning_loop_state(weak_points, sessions)

    assert state["totals"]["finished_sessions"] == 2
    assert state["totals"]["untrained_weak_points"] == 1
    assert state["subject_cards"][0]["subject"] == "刑法"
    assert state["subject_cards"][0]["count"] == 2
    assert state["knowledge_rankings"][0]["knowledge_point"] == "共同犯罪"
    assert state["knowledge_rankings"][0]["count"] == 2
    assert state["knowledge_rankings"][0]["recommendation"] == "优先复盘"
    assert state["mistake_reason_queue"][0]["mistake_reason"] in {"概念混淆", "要件遗漏"}


def test_recent_entries_use_chinese_column_ready_fields():
    weak_points = [_weak_point(1, "刑法", "罪刑法定原则", "模糊")]
    sessions = [{"weak_point_id": 1, "status": "active"}]

    state = build_learning_loop_state(weak_points, sessions)
    row = state["recent_entries"][0]

    assert row["科目"] == "刑法"
    assert row["题型"] == "简答"
    assert row["考点"] == "罪刑法定原则"
    assert row["训练状态"] == "训练中"
    assert row["workflow_action"] == "继续训练"
