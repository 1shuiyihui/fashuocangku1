from pathlib import Path

import pytest

from services.document_processor import (
    OCRUnavailableError,
    UnsupportedDocumentError,
    chunk_text,
    extract_text_from_file,
)


def test_extract_text_from_txt_and_markdown(tmp_path: Path):
    txt_path = tmp_path / "刑法讲义.txt"
    md_path = tmp_path / "民法讲义.md"
    txt_path.write_text("共同犯罪要求共同故意。", encoding="utf-8")
    md_path.write_text("# 表见代理\n相对人需要善意且无过失。", encoding="utf-8")

    assert extract_text_from_file(txt_path) == "共同犯罪要求共同故意。"
    assert "表见代理" in extract_text_from_file(md_path)


def test_chunk_text_preserves_order_and_limits_size():
    text = "\n\n".join(
        [
            "共同犯罪要求二人以上共同故意实施犯罪。",
            "犯罪中止要求自动放弃犯罪或者自动有效防止结果发生。",
            "正当防卫要求存在现实不法侵害。",
        ]
    )

    chunks = chunk_text(text, max_chars=28, overlap=0)

    assert len(chunks) >= 3
    assert chunks[0].startswith("共同犯罪")
    assert all(len(chunk) <= 28 for chunk in chunks)


def test_unsupported_file_type_raises(tmp_path: Path):
    path = tmp_path / "archive.zip"
    path.write_text("content", encoding="utf-8")

    with pytest.raises(UnsupportedDocumentError):
        extract_text_from_file(path)


def test_image_ocr_unavailable_is_explicit(tmp_path: Path, monkeypatch):
    import pytesseract
    from PIL import Image

    image_path = tmp_path / "scan.png"
    Image.new("RGB", (10, 10), "white").save(image_path)

    def raise_missing_tesseract(*args, **kwargs):
        raise pytesseract.TesseractNotFoundError()

    monkeypatch.setattr(pytesseract, "image_to_string", raise_missing_tesseract)

    with pytest.raises(OCRUnavailableError):
        extract_text_from_file(image_path)
