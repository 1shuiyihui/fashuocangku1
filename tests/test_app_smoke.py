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


def test_v012_beginner_guide_and_course_import_labels():
    import app
    from services.versioning import APP_VERSION

    assert APP_VERSION == "0.13.0"
    assert app.COURSE_GENERATION_SECTION_TITLE == "3. 生成可执行训练计划并导入训练点"
    assert app.LESSON_SUBJECT_LABEL == "训练点科目"
    assert app.IMPORT_LESSON_BUTTON_LABEL == "导入为训练点"
    assert app.APP_GUIDE_STEPS == [
        "录入薄弱点，或从生成课程中导入训练点。",
        "进入苏格拉底训练，用追问暴露真实薄弱处。",
        "每周或每月查看复盘，按高频考点和错因安排下一轮训练。",
    ]


def test_v070_feishu_style_navigation_groups_cover_all_pages():
    import app

    grouped_pages = [page for _, pages in app.NAV_GROUPS for page in pages]

    assert grouped_pages == app.PAGES
    assert app.get_page_group("今日学习") == "学习"
    assert app.get_page_group("资料知识库") == "资料"
    assert app.get_page_group("周度/月度复盘") == "分析"
    assert app.get_page_group("系统与备份") == "系统"


def test_v070_shell_style_and_status_helpers():
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


def test_persistence_config_reads_streamlit_secrets_shape():
    import app

    config = app.get_persistence_config(
        {
            "persistence": {
                "enabled": True,
                "provider": "github",
                "repo": "1shuiyihui/fashuocangku1",
                "branch": "cloud-data",
                "source_branch": "codex/fashuo-socratic-local-tool",
                "snapshot_path": "fashuo-cloud-snapshot.zip",
                "github_token": "token",
            }
        }
    )

    assert config.enabled is True
    assert config.repo == "1shuiyihui/fashuocangku1"
    assert app.get_persistence_status_label(config) == "GitHub 云端快照"
    assert app.get_persistence_status_label() in {"GitHub 云端快照", "本地临时存储"}


def test_v012_workflow_navigation_contract():
    import app
    from services.versioning import APP_VERSION

    assert APP_VERSION == "0.13.0"
    assert app.FOCUS_WEAK_POINT_KEY == "focus_weak_point_id"
    assert app.REVIEW_FOCUS_KEY == "review_focus_keyword"
    assert app.WORKFLOW_LOOP_STEPS == [
        "录入训练点",
        "苏格拉底训练",
        "薄弱点分析",
        "周度/月度复盘",
        "下一轮训练",
    ]


def test_get_focused_weak_point_index_falls_back_safely():
    import app

    rows = [{"id": 1}, {"id": 7}, {"id": 9}]

    assert app.get_focused_weak_point_index(rows, 7) == 1
    assert app.get_focused_weak_point_index(rows, 999) == 0
    assert app.get_focused_weak_point_index([], 7) == 0


def test_v012_workspace_ui_contract():
    import app
    from services.versioning import APP_VERSION

    assert APP_VERSION == "0.13.0"
    assert app.get_app_version() == "0.13.0"
    assert app.ENTRY_WORKFLOW_STEPS == ["上传或拍照", "结构化训练点", "AI 抽取与确认"]
    assert app.KNOWLEDGE_WORKFLOW_STEPS == [
        "上传并建立索引",
        "检索资料片段",
        "生成可执行训练计划",
        "导入为训练点",
    ]
    assert app.TRAINING_PANEL_SECTIONS == ["模板提示", "参考资料片段", "掌握度评估", "本次训练记录"]
    assert app.SIDEBAR_STATUS_TITLE == "系统状态"
    assert app.REVIEW_WORKFLOW_STEPS == [
        "选择周期",
        "查看训练队列",
        "定位高频问题",
        "安排下一轮训练",
        "导出复盘",
    ]
    assert app.REVIEW_DASHBOARD_SECTIONS == ["学习概况", "高频薄弱考点", "高频错因", "下一轮训练计划"]
    assert app.DEFAULT_MIN_DIALOGUE_ROUNDS == 3
    assert app.MAX_DIALOGUE_ROUND_OPTIONS[0] == "不限制"
    assert app.ERROR_ANALYSIS_SECTIONS == ["错误还原", "根因证据", "复盘练习", "变式练习", "溯源记录"]
    assert app.VOICE_INPUT_SECTIONS == ["语音输入", "转写草稿", "提交文本"]


def test_v010_css_contains_workspace_layouts():
    import app

    expected_classes = [
        "sidebar-status-card",
        "sidebar-workflow-card",
        "entry-workspace-grid",
        "training-cockpit-grid",
        "knowledge-workflow-grid",
        "lesson-plan-card",
        "source-result-card",
        "review-dashboard-grid",
        "review-summary-card",
        "review-plan-card",
        "review-insight-card",
    ]

    for class_name in expected_classes:
        assert class_name in app.APP_SHELL_STYLE


def test_v011_dialogue_round_helpers():
    import app

    assert app.normalize_min_dialogue_rounds(1) == 3
    assert app.normalize_min_dialogue_rounds("5") == 5
    assert app.normalize_max_dialogue_rounds("不限制", 3) is None
    assert app.normalize_max_dialogue_rounds("4轮", 5) == 5
    assert app.count_student_dialogue_rounds(
        [
            {"role": "assistant", "content": "问一"},
            {"role": "user", "content": "答一"},
            {"role": "assistant", "content": "问二"},
            {"role": "user", "content": "答二"},
        ]
    ) == 2
    assert app.can_finish_training(2, 3) is False
    assert app.can_finish_training(3, 3) is True
