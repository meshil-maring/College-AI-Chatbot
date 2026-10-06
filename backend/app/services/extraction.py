import io

from app.config import settings
from app.core.errors import AppError
from app.services.ingestion import validate_file_content


def extract_text(data: bytes, file_type: str) -> str:
    validate_file_content(f"document.{file_type}", data)
    if file_type == "txt":
        return _bounded_text(data.decode("utf-8-sig", errors="strict"))
    if file_type == "pdf":
        return _extract_pdf(data)
    if file_type == "docx":
        return _extract_docx(data)
    raise AppError(
        f"Unsupported file type for extraction: {file_type}",
        status_code=422,
        code="UNSUPPORTED_EXTRACTION_TYPE",
    )


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    if len(reader.pages) > settings.max_document_pages:
        raise AppError(
            "PDF exceeds the configured page limit",
            status_code=422,
            code="DOCUMENT_TOO_MANY_PAGES",
        )
    pages: list[str] = []
    length = 0
    for page in reader.pages:
        page_text = page.extract_text() or ""
        length += len(page_text) + 1
        if length > settings.max_extracted_text_chars:
            raise AppError(
                "Extracted document text exceeds the configured limit",
                status_code=422,
                code="EXTRACTED_TEXT_TOO_LARGE",
            )
        pages.append(page_text)
    return "\n".join(pages).strip()


def _extract_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(data))
    return _bounded_text("\n".join(p.text for p in doc.paragraphs if p.text.strip()))


def _bounded_text(text: str) -> str:
    if len(text) > settings.max_extracted_text_chars:
        raise AppError(
            "Extracted document text exceeds the configured limit",
            status_code=422,
            code="EXTRACTED_TEXT_TOO_LARGE",
        )
    return text
