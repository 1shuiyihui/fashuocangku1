from services.rag import format_rag_context, search_chunks


def test_search_chunks_ranks_relevant_chunk_first():
    chunks = [
        {"id": 1, "content": "表见代理要求相对人善意且无过失。", "source_label": "民法#1"},
        {"id": 2, "content": "共同犯罪要求二人以上共同故意实施犯罪。", "source_label": "刑法#1"},
        {"id": 3, "content": "宪法监督包括合宪性审查相关制度。", "source_label": "宪法#1"},
    ]

    results = search_chunks("共同犯罪共同故意", chunks, top_k=2)

    assert results[0]["id"] == 2
    assert results[0]["score"] > 0
    assert len(results) == 2


def test_search_chunks_empty_inputs_return_empty_list():
    assert search_chunks("", [{"id": 1, "content": "共同犯罪", "source_label": "刑法#1"}]) == []
    assert search_chunks("共同犯罪", []) == []


def test_format_rag_context_includes_sources_and_content():
    context = format_rag_context(
        [
            {"source_label": "刑法#1", "content": "共同犯罪要求共同故意。", "score": 0.8},
            {"source_label": "刑法#2", "content": "共同犯罪需要二人以上。", "score": 0.5},
        ],
        max_chars=200,
    )

    assert "刑法#1" in context
    assert "共同故意" in context
