"""Document chunking regressions: chunk building."""

from __future__ import annotations

from .support import (
    _active_institution_authorization,
    _build_chunks,
    _is_heading,
    _split_paragraph,
    chunk_text,
)


# ===========================================================================
# Unit tests — chunking service
# ===========================================================================


class TestIsHeading:
    def test_all_caps_short_line(self):
        assert _is_heading("INTRODUCTION")

    def test_numbered_section(self):
        assert _is_heading("1.2. Admission Requirements")

    def test_mixed_case_long_line_not_heading(self):
        assert not _is_heading("This is a normal sentence with lowercase letters.")

    def test_empty_string_not_heading(self):
        assert not _is_heading("")

    def test_line_over_80_chars_not_heading(self):
        assert not _is_heading("A" * 81)


class TestSplitParagraph:
    def test_splits_at_sentence_boundary(self):
        para = "First sentence. Second sentence. Third sentence."
        pieces = _split_paragraph(para, target=30)
        assert all(len(p) <= 30 for p in pieces)
        # All original words must appear across the pieces
        combined = " ".join(pieces)
        for word in ["First", "Second", "Third"]:
            assert word in combined

    def test_hard_cut_when_sentence_exceeds_target(self):
        long_word = "x" * 100
        pieces = _split_paragraph(long_word, target=40)
        assert all(len(p) <= 40 for p in pieces)
        assert "".join(pieces) == long_word

    def test_single_sentence_within_target_unchanged(self):
        para = "Short sentence."
        pieces = _split_paragraph(para, target=200)
        assert pieces == ["Short sentence."]


class TestBuildChunks:
    def test_empty_text_returns_empty(self):
        assert _build_chunks("") == []

    def test_whitespace_only_returns_empty(self):
        assert _build_chunks("   \n\n   ") == []

    def test_single_short_paragraph_one_chunk(self):
        chunks = _build_chunks("Hello world.")
        assert len(chunks) == 1
        assert chunks[0]["content_text"] == "Hello world."

    def test_sequence_starts_at_one(self):
        text = "\n\n".join(["Para " + str(i) + " " + "x" * 100 for i in range(5)])
        chunks = _build_chunks(text, target=200, overlap=20)
        assert chunks[0]["chunk_sequence"] == 1

    def test_sequence_is_contiguous(self):
        text = "\n\n".join(["Para " + str(i) + " " + "x" * 300 for i in range(10)])
        chunks = _build_chunks(text, target=400, overlap=50)
        seqs = [c["chunk_sequence"] for c in chunks]
        assert seqs == list(range(1, len(chunks) + 1))

    def test_multi_paragraph_produces_multiple_chunks(self):
        para = "word " * 500  # ~2500 chars
        text = para + "\n\n" + para
        chunks = _build_chunks(text, target=2000, overlap=200)
        assert len(chunks) >= 2

    def test_token_count_is_estimate(self):
        chunks = _build_chunks("Hello world this is a test.")
        assert chunks[0]["token_count"] == len(chunks[0]["content_text"]) // 4

    def test_token_count_non_negative(self):
        chunks = _build_chunks("Hi.")
        assert chunks[0]["token_count"] >= 0

    def test_page_metadata_absent(self):
        """chunk_text returns dicts — page_start/page_end are not in the service output."""
        chunks = chunk_text("Some text here.")
        for c in chunks:
            assert "page_start" not in c
            assert "page_end" not in c

    def test_content_text_not_empty(self):
        text = "\n\n".join(["Paragraph " + str(i) for i in range(20)])
        chunks = _build_chunks(text)
        for c in chunks:
            assert c["content_text"].strip() != ""

    def test_all_text_preserved_across_chunks(self):
        """Every word in the source appears in at least one chunk."""
        words = ["alpha", "beta", "gamma", "delta", "epsilon"]
        text = "\n\n".join(w * 10 + " content" for w in words)
        chunks = _build_chunks(text, target=100, overlap=20)
        combined = " ".join(c["content_text"] for c in chunks)
        for w in words:
            assert w in combined


class TestSectionTitles:
    def test_heading_captured_as_section_title(self):
        text = "INTRODUCTION\n\nThis section covers the basics of the program."
        chunks = _build_chunks(text)
        assert any(c["section_title"] == "INTRODUCTION" for c in chunks)

    def test_section_title_propagates_to_following_chunk(self):
        heading = "POLICIES AND PROCEDURES"
        body = ("This is policy content. " * 100).strip()
        text = heading + "\n\n" + body
        chunks = _build_chunks(text, target=300, overlap=50)
        # All chunks after the heading should carry the section title
        content_chunks = [c for c in chunks if c["content_text"] != heading]
        assert all(c["section_title"] == heading for c in content_chunks)

    def test_no_heading_section_title_is_none(self):
        text = "Just a normal paragraph without any heading."
        chunks = _build_chunks(text)
        assert chunks[0]["section_title"] is None

    def test_numbered_heading_detected(self):
        text = "1.1. Eligibility Criteria\n\nStudents must meet the following requirements."
        chunks = _build_chunks(text)
        assert any(c["section_title"] is not None for c in chunks)
