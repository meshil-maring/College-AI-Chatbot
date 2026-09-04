"""
Phase 3.5 — Text Chunking Service.

Splits extracted_text into knowledge_chunks using this priority:
  1. Paragraph boundary  (\n\n)
  2. Sentence boundary   (. / ? / !)
  3. Hard character limit

Target: ~2 000 characters per chunk, ~200 characters of overlap.
token_count is an estimate: len(content_text) // 4  (no tokenizer installed).
page_start / page_end remain NULL — Phase 3.4 does not preserve page data.
"""

import re

_TARGET = 2_000
_OVERLAP = 200
_SENTENCE_END = re.compile(r"(?<=[.?!])\s+")
_HEADING = re.compile(
    r"^(?:[A-Z][A-Z0-9 \t]{2,}|(?:\d+\.)+\s+\S.{0,60}|[A-Z][^a-z\n]{0,60})$"
)


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 80:
        return False
    return bool(_HEADING.match(stripped))


def _split_paragraph(para: str, target: int) -> list[str]:
    """Split a single oversized paragraph at sentence boundaries, then hard-cut."""
    sentences = _SENTENCE_END.split(para)
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = (current + " " + sentence).strip() if current else sentence
        if len(candidate) <= target:
            current = candidate
        else:
            if current:
                pieces.append(current)
            # sentence itself may exceed target — hard-cut it
            while len(sentence) > target:
                pieces.append(sentence[:target])
                sentence = sentence[target:]
            current = sentence
    if current:
        pieces.append(current)
    return pieces or [para[:target]]


def _build_chunks(text: str, target: int = _TARGET, overlap: int = _OVERLAP) -> list[dict]:
    """
    Return a list of dicts with keys:
      content_text, token_count, section_title, chunk_sequence (1-based)
    """
    if not text or not text.strip():
        return []

    # Normalise line endings; collapse 3+ blank lines to 2
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)

    raw_paragraphs = text.split("\n\n")

    # Flatten each raw paragraph: single \n → space, then split if oversized
    paragraphs: list[str] = []
    for raw in raw_paragraphs:
        merged = " ".join(line.strip() for line in raw.splitlines() if line.strip())
        if not merged:
            continue
        if len(merged) <= target:
            paragraphs.append(merged)
        else:
            paragraphs.extend(_split_paragraph(merged, target))

    if not paragraphs:
        return []

    # Accumulate paragraphs into chunks with overlap
    chunks: list[dict] = []
    current_parts: list[str] = []
    current_len = 0
    current_section: str | None = None
    sequence = 1

    def _flush(parts: list[str], section: str | None) -> None:
        nonlocal sequence
        body = "\n\n".join(parts).strip()
        if not body:
            return
        chunks.append({
            "chunk_sequence": sequence,
            "content_text": body,
            "token_count": _estimate_tokens(body),
            "section_title": section,
        })
        sequence += 1

    for para in paragraphs:
        if _is_heading(para):
            current_section = para.strip()

        if current_len + len(para) > target and current_parts:
            _flush(current_parts, current_section)
            # carry overlap: take tail of accumulated text
            tail = "\n\n".join(current_parts)
            overlap_text = tail[-overlap:].strip() if len(tail) > overlap else tail
            current_parts = [overlap_text] if overlap_text else []
            current_len = len(overlap_text)

        current_parts.append(para)
        current_len += len(para)

    if current_parts:
        _flush(current_parts, current_section)

    return chunks


def chunk_text(text: str) -> list[dict]:
    """Public entry point. Returns chunk dicts ready for DB insertion."""
    return _build_chunks(text)
