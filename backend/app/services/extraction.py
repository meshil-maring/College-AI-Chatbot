import io

from app.core.errors import AppError


def extract_text(data: bytes, file_type: str) -> str:
    if file_type == "txt":
        return data.decode("utf-8", errors="replace")
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
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def _extract_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
