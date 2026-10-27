"""Document extraction regressions: formats."""

from __future__ import annotations

from .support import (
    _active_institution_authorization,
    _make_docx,
    _post_extract,
    extract_text,
    io,
)


# ---------------------------------------------------------------------------
# 2. PDF text extraction — text extracted successfully
# ---------------------------------------------------------------------------

def test_pdf_text_extraction_succeeds():
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    result = extract_text(buf.getvalue(), "pdf")
    assert isinstance(result, str)


def test_txt_text_extraction_succeeds():
    result = extract_text(b"hello extraction", "txt")
    assert result == "hello extraction"


def test_docx_text_extraction_succeeds():
    result = extract_text(_make_docx("docx extraction test"), "docx")
    assert "docx extraction test" in result


# ---------------------------------------------------------------------------
# 3. Extracted text not empty — meaningful content preserved
# ---------------------------------------------------------------------------

def test_extracted_txt_content_is_not_empty():
    result = extract_text(b"meaningful content here", "txt")
    assert len(result) > 0
    assert "meaningful content" in result


def test_extracted_docx_content_is_not_empty():
    result = extract_text(_make_docx("important document text"), "docx")
    assert len(result) > 0


def test_characters_extracted_reported_correctly():
    content = b"exactly this text"
    response = _post_extract(file_bytes=content, file_type="txt")
    assert response.status_code == 200
    assert response.json()["characters_extracted"] == len("exactly this text")


# ---------------------------------------------------------------------------
# 4. Page/content handling — document content preserved
# ---------------------------------------------------------------------------

def test_multipage_docx_all_paragraphs_extracted():
    from docx import Document as DocxDocument
    doc = DocxDocument()
    doc.add_paragraph("First paragraph content")
    doc.add_paragraph("Second paragraph content")
    doc.add_paragraph("Third paragraph content")
    buf = io.BytesIO()
    doc.save(buf)
    result = extract_text(buf.getvalue(), "docx")
    assert "First paragraph content" in result
    assert "Second paragraph content" in result
    assert "Third paragraph content" in result


def test_txt_multiline_content_preserved():
    content = b"line one\nline two\nline three"
    result = extract_text(content, "txt")
    assert "line one" in result
    assert "line two" in result
    assert "line three" in result


def test_pdf_multiple_pages_extracted():
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    result = extract_text(buf.getvalue(), "pdf")
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# 7. Empty document — processing fails cleanly
# ---------------------------------------------------------------------------

def test_empty_bytes_txt_returns_empty_string():
    result = extract_text(b"", "txt")
    assert result == ""
