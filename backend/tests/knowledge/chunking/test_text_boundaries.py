"""Document chunking regressions: text boundaries."""

from __future__ import annotations

from .support import (
    _active_institution_authorization,
    _build_chunks,
    _is_heading,
)


class TestOverlap:
    def test_overlap_text_appears_in_consecutive_chunks(self):
        # Build text that forces at least 2 chunks
        para_a = "Alpha content. " * 80   # ~1200 chars
        para_b = "Beta content. " * 80    # ~1120 chars
        para_c = "Gamma content. " * 80   # ~1200 chars
        text = para_a.strip() + "\n\n" + para_b.strip() + "\n\n" + para_c.strip()
        chunks = _build_chunks(text, target=2000, overlap=200)
        assert len(chunks) >= 2
        # The tail of chunk N should appear somewhere in chunk N+1
        tail = chunks[0]["content_text"][-100:]
        assert tail in chunks[1]["content_text"]

    def test_overlap_does_not_exceed_target_significantly(self):
        para = "sentence content here. " * 200
        chunks = _build_chunks(para, target=2000, overlap=200)
        for c in chunks:
            # Allow some slack for sentence-boundary rounding
            assert len(c["content_text"]) <= 2000 + 500


class TestOversizedParagraph:
    def test_single_oversized_paragraph_split_into_multiple_chunks(self):
        big = "word " * 1000  # ~5000 chars
        chunks = _build_chunks(big, target=2000, overlap=200)
        assert len(chunks) >= 2

    def test_hard_limit_applied_when_no_sentence_boundary(self):
        no_sentences = "x" * 6000
        chunks = _build_chunks(no_sentences, target=2000, overlap=200)
        assert len(chunks) >= 2
        for c in chunks:
            # Allow for overlap separator ("\n\n" = 2 chars) on top of target
            assert len(c["content_text"]) <= 2300


# ===========================================================================
# Section-boundary chunking (conversational RAG optimization)
# ===========================================================================


class TestSectionBoundaries:
    def test_numbered_heading_starts_new_chunk_even_with_single_newlines(self):
        """A hostel-style PDF whose lines are single-newline separated must not
        collapse all sections into one merged chunk."""
        doc = (
            "1. Hostel Fee Structure\n"
            "Boys Hostel Standard Room 48000/year\n"
            "Girls Hostel Standard Room 48000/year\n"
            "2. Admission and Eligibility\n"
            "Students must submit a hostel application form.\n"
            "3. Payment Rules\n"
            "Fees may be paid in two equal installments.\n"
        )
        chunks = _build_chunks(doc, target=2000, overlap=200)
        assert len(chunks) >= 3
        sections = [c["section_title"] for c in chunks]
        assert any(s == "1. Hostel Fee Structure" for s in sections)
        assert any(s == "2. Admission and Eligibility" for s in sections)
        assert any(s == "3. Payment Rules" for s in sections)

    def test_title_case_heading_is_detected(self):
        assert _is_heading("Hostel Fee Structure")
        assert _is_heading("Admission and Eligibility")

    def test_table_labels_and_rows_are_not_headings(self):
        # table column headers stay body text so tables never fragment
        assert not _is_heading("Annual Fee")
        assert not _is_heading("Security Deposit")
        assert not _is_heading("Mess Fee")
        assert not _is_heading("Hostel Type")
        # table row labels (dash-separated) stay body text
        assert not _is_heading("Boys Hostel - Standard Room")
        assert not _is_heading("Girls Hostel - Standard Room")
        # data lines with mid-line colons stay body text
        assert not _is_heading("Hostel Office: Administration Block, Ground Floor")

    def test_title_case_heading_starts_new_chunk(self):
        doc = (
            "1. Hostel Fee Structure\n"
            "Boys Hostel Standard Room 48000/year\n"
            "2. Mess Charges\n"
            "The standard mess charge is 36000 per year.\n"
        )
        chunks = _build_chunks(doc, target=2000, overlap=200)
        sections = [c["section_title"] for c in chunks]
        assert "1. Hostel Fee Structure" in sections
        assert "2. Mess Charges" in sections
        # the fee table stays inside the fee section chunk
        fee_chunk = next(c for c in chunks if c["section_title"] == "1. Hostel Fee Structure")
        assert "48000/year" in fee_chunk["content_text"]
        assert "Boys Hostel Standard Room" in fee_chunk["content_text"]

    def test_ordinary_sentence_is_not_a_heading(self):
        assert not _is_heading("The annual hostel fee is Rs. 48000 per year.")
        assert not _is_heading("This is a normal sentence with lowercase letters.")

    def test_table_row_with_digits_is_not_a_heading(self):
        assert not _is_heading("Boys Hostel - Standard Room 48000 5000 36000")
        assert not _is_heading("Girls Hostel - Standard Room 66000 5000 36000")

    def test_heading_text_is_not_lost(self):
        doc = (
            "1. Hostel Fee Structure\n"
            "Boys Hostel Standard Room 48000/year\n"
            "2. Payment Rules\n"
            "Fees may be paid in two equal installments.\n"
        )
        chunks = _build_chunks(doc)
        combined = "\n".join(c["content_text"] for c in chunks)
        assert "1. Hostel Fee Structure" in combined
        assert "2. Payment Rules" in combined
        assert "Boys Hostel Standard Room 48000/year" in combined

    def test_all_caps_heading_still_behaves(self):
        chunks = _build_chunks("INTRODUCTION\n\nThis section covers the basics of the program.")
        assert any(c["section_title"] == "INTRODUCTION" for c in chunks)
