def test_app_exposes_expected_pages():
    import app

    assert app.PAGES == [
        "今日学习",
        "错题/薄弱点录入",
        "苏格拉底训练",
        "资料知识库",
        "模板管理",
        "薄弱点分析",
        "周度/月度复盘",
        "系统与备份",
    ]
    assert callable(app.main)


def test_next_action_starts_with_entry_when_no_weak_points():
    import app

    action = app.get_next_action([], [])

    assert action["page"] == "错题/薄弱点录入"
    assert action["title"] == "先录入一个薄弱点"


def test_next_action_starts_training_when_weak_point_exists_without_session():
    import app

    action = app.get_next_action(
        [{"knowledge_point": "共同犯罪", "mastery_level": "模糊"}],
        [],
    )

    assert action["page"] == "苏格拉底训练"
    assert "共同犯罪" in action["detail"]


def test_next_action_prioritizes_review_after_finished_training():
    import app

    action = app.get_next_action(
        [{"knowledge_point": "共同犯罪", "mastery_level": "模糊"}],
        [{"status": "finished"}],
    )

    assert action["page"] == "周度/月度复盘"
    assert action["title"] == "看一次复盘"


def test_beginner_mode_hides_advanced_prompt_editor_by_default():
    import app

    assert app.BEGINNER_MODE_DEFAULT is True
    assert app.should_show_prompt_editor(beginner_mode=True, advanced_enabled=False) is False
    assert app.should_show_prompt_editor(beginner_mode=True, advanced_enabled=True) is True
    assert app.should_show_prompt_editor(beginner_mode=False, advanced_enabled=False) is True
