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


def test_v060_beginner_guide_and_course_import_labels():
    import app
    from services.versioning import APP_VERSION

    assert APP_VERSION == "0.6.0"
    assert app.COURSE_GENERATION_SECTION_TITLE == "3. 生成可执行训练计划并导入训练点"
    assert app.LESSON_SUBJECT_LABEL == "训练点科目"
    assert app.IMPORT_LESSON_BUTTON_LABEL == "导入为训练点"
    assert app.APP_GUIDE_STEPS == [
        "录入薄弱点，或从生成课程中导入训练点。",
        "进入苏格拉底训练，用追问暴露真实薄弱处。",
        "每周或每月查看复盘，按高频考点和错因安排下一轮训练。",
    ]


def test_v060_feishu_style_navigation_groups_cover_all_pages():
    import app

    grouped_pages = [page for _, pages in app.NAV_GROUPS for page in pages]

    assert grouped_pages == app.PAGES
    assert app.get_page_group("今日学习") == "学习"
    assert app.get_page_group("资料知识库") == "资料"
    assert app.get_page_group("周度/月度复盘") == "分析"
    assert app.get_page_group("系统与备份") == "系统"


def test_v060_shell_style_and_status_helpers():
    import app

    assert "app-topbar" in app.APP_SHELL_STYLE
    assert "workbench-card" in app.APP_SHELL_STYLE
    assert '[data-testid="stSidebar"]' in app.APP_SHELL_STYLE
    assert app.get_ai_status_label({"api_key": "secret"}) == "AI 已配置"
    assert app.get_ai_status_label({"api_key": ""}) == "AI 未配置"
    assert app.get_ai_status_label({}) == "AI 未配置"


def test_default_ai_config_reads_streamlit_secrets_shape():
    import app

    config = app.get_default_ai_config(
        {
            "ai": {
                "api_base": "https://api.example.com/v1",
                "model": "example-model",
                "api_key": "secret-key",
            }
        }
    )

    assert config == {
        "api_base": "https://api.example.com/v1",
        "model": "example-model",
        "api_key": "secret-key",
    }
