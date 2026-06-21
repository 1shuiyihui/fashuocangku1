from __future__ import annotations

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer


def search_chunks(
    query: str,
    chunks: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    clean_query = query.strip()
    usable_chunks = [chunk for chunk in chunks if str(chunk.get("content", "")).strip()]
    if not clean_query or not usable_chunks:
        return []

    corpus = [str(chunk["content"]) for chunk in usable_chunks]
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
    matrix = vectorizer.fit_transform(corpus)
    query_vector = vectorizer.transform([clean_query])
    scores = (matrix @ query_vector.T).toarray().ravel()

    ranked = sorted(
        enumerate(scores),
        key=lambda item: item[1],
        reverse=True,
    )
    results = []
    for index, score in ranked[:top_k]:
        chunk = dict(usable_chunks[index])
        chunk["score"] = float(score)
        results.append(chunk)
    return results


def format_rag_context(results: list[dict[str, Any]], max_chars: int = 2400) -> str:
    parts = []
    used = 0
    for index, result in enumerate(results, start=1):
        source = result.get("source_label", f"片段 {index}")
        content = str(result.get("content", "")).strip()
        if not content:
            continue
        block = f"[{index}] 来源：{source}\n{content}"
        if used + len(block) > max_chars:
            remaining = max_chars - used
            if remaining <= 80:
                break
            block = block[:remaining].rstrip()
        parts.append(block)
        used += len(block)
        if used >= max_chars:
            break
    return "\n\n".join(parts)
