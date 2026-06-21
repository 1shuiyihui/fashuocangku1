from __future__ import annotations

from pathlib import Path

import pytesseract
from PIL import Image
from pypdf import PdfReader


TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


class OCRUnavailableError(RuntimeError):
    pass


class UnsupportedDocumentError(ValueError):
    pass


def extract_text_from_file(path: str | Path) -> str:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return file_path.read_text(encoding="utf-8").strip()
    if suffix == ".pdf":
        return extract_pdf_text(file_path).strip()
    if suffix in IMAGE_EXTENSIONS:
        return extract_image_text(file_path).strip()
    raise UnsupportedDocumentError(f"暂不支持的文件类型：{suffix or 'unknown'}")


def extract_pdf_text(path: str | Path) -> str:
    reader = PdfReader(str(path))
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[第 {page_number} 页]\n{text.strip()}")
    return "\n\n".join(pages)


def extract_image_text(path: str | Path) -> str:
    try:
        with Image.open(path) as image:
            try:
                return pytesseract.image_to_string(image, lang="chi_sim+eng")
            except pytesseract.TesseractError:
                return pytesseract.image_to_string(image)
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRUnavailableError("未检测到 Tesseract OCR，请先安装后再处理图片。") from exc


def chunk_text(text: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    normalized = "\n".join(line.strip() for line in text.splitlines())
    paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
    if not paragraphs and normalized.strip():
        paragraphs = [normalized.strip()]

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(_split_long_text(paragraph, max_chars, overlap))
            continue
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current.strip())
            current = paragraph
    if current:
        chunks.append(current.strip())
    return chunks


def process_document_file(path: str | Path) -> tuple[str, list[str], str]:
    text = extract_text_from_file(path)
    chunks = chunk_text(text)
    status = "ready" if chunks else "empty"
    return text, chunks, status


def _split_long_text(text: str, max_chars: int, overlap: int) -> list[str]:
    step = max(1, max_chars - max(0, overlap))
    return [text[index : index + max_chars].strip() for index in range(0, len(text), step) if text[index : index + max_chars].strip()]
