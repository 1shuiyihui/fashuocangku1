def test_app_exposes_expected_pages():
    import app

    assert app.PAGES == [
        "今日学习",
        "错题/薄弱点录入",
        "苏格拉底训练",
        "模板管理",
        "薄弱点分析",
        "周度/月度复盘",
    ]
    assert callable(app.main)
