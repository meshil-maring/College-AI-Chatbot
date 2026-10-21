"""
Phase 3.5 — Text Chunking Service.

Splits extracted_text into knowledge_chunks using this priority:
  1. Section heading boundary  (detected headings start a new section)
  2. Paragraph boundary        (\\n\\n)
  3. Sentence boundary         (. / ? / !)
  4. Hard character limit

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
# Title-case heading heuristic (e.g. "Hostel Fee Structure"). Used only for
# short lines that end without sentence punctuation and contain no digits or
# currency symbols, so ordinary sentences and table rows are not mis-detected.
_TITLE_CASE_WORD_LIMIT = 6
_TITLE_CASE_RATIO = 0.66
_TITLE_CASE_MAX_LEN = 60


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _is_title_case_heading(line: str) -> bool:
    """Return True for short title-case lines (no sentence punctuation).

    Conservative on purpose: requires at least three capitalized words, and
    rejects dash-separated labels (table rows such as "Boys Hostel - Standard
    Room") and mid-line colons (data lines such as "Hostel Office: ..."), so
    table column headers ("Annual Fee", "Mess Fee") and row labels never
    fragment a section into tiny chunks. Two-word headings are left as body
    text; all-caps and numbered headings are still detected by ``_HEADING``.
    """
    if not line or len(line) > _TITLE_CASE_MAX_LEN:
        return False
    if line[-1:] in ".!?:;":
        return False
    if re.search(r"[0-9\u20b9]", line):
        return False
    if re.search(r"\s[\u2013\u2014-]\s", line):
        return False
    if ": " in line:
        return False
    words = line.split()
    if len(words) > _TITLE_CASE_WORD_LIMIT:
        return False
    alpha_words = [w for w in words if any(ch.isalpha() for ch in w)]
    if len(alpha_words) < 3:
        return False
    upper_start = sum(1 for w in alpha_words if w[0].isupper())
    return upper_start / len(alpha_words) >= _TITLE_CASE_RATIO


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 80:
        return False
    if _HEADING.match(stripped):
        return True
    return _is_title_case_heading(stripped)


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

    # Walk the text line by line. A detected section heading is kept as its own
    # unit (never flattened into body text) so documents whose lines are joined
    # by single newlines still produce one chunk per section instead of one
    # merged chunk for the whole document.
    paragraphs: list[str] = []
    body_lines: list[str] = []

    def _flush_body() -> None:
        nonlocal body_lines
        if not body_lines:
            return
        merged = " ".join(line.strip() for line in body_lines if line.strip())
        body_lines = []
        if not merged:
            return
        if len(merged) <= target:
            paragraphs.append(merged)
        else:
            paragraphs.extend(_split_paragraph(merged, target))

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            _flush_body()
        elif _is_heading(line):
            _flush_body()
            paragraphs.append(line)
        else:
            body_lines.append(line)
    _flush_body()

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
            # A section heading closes the previous section: flush the
            # accumulated paragraphs so each section becomes its own chunk.
            if current_parts:
                _flush(current_parts, current_section)
                current_parts = []
                current_len = 0
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
