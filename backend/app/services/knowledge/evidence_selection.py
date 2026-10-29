"""Recover rule sections when document metadata fills the nearest matches.

Only rank candidates returned by the existing authorized search. Expansion is
bounded and stays within the same document version as the original results.
"""

import re


_CONTEXT_SECTION = re.compile(
    r"^(?:\d+(?:\.\d+)*[.)]?\s+)?(?:"
    r"purpose(?:\s+and\s+scope)?|scope|"
    r"(?:document\s+)?(?:authority|metadata|control|revision history)|"
    r"(?:suggested|recommended)\s+(?:retrieval\s+metadata|"
    r"(?:ai\s+)?ingestion(?:\s+and\s+chunking)?\s+notes))\b",
    re.IGNORECASE,
)
_DOCUMENT_FIELD = re.compile(
    r"\b(?:document\s+(?:id|type)|version|effective date|policy owner)\s*:",
    re.IGNORECASE,
)
_QUALIFICATION = re.compile(r'\b(?:sample|draft|illustrative|unapproved)\b', re.IGNORECASE)


def _is_context(row):
    text = row.get('content_text') or ''
    section = row.get('section_title') or ''
    return bool(
        _CONTEXT_SECTION.search(section.strip())
        or len(_DOCUMENT_FIELD.findall(text)) >= 2
        or (len(text) < 120 and re.search(r'\bPage\s+\d+\b', text, re.IGNORECASE))
        or (section and ' '.join(text.split()) == ' '.join(section.split()))
    )


def _version(row):
    return row.get('document_id'), row.get('document_version_id')


def candidate_limit(rows, top_k):
    """Request a larger pool only for a full, metadata-heavy document result."""
    if not 2 <= top_k < 20 or len(rows) < top_k:
        return top_k
    versions = {_version(row) for row in rows}
    if len(versions) != 1 or None in next(iter(versions)):
        return top_k
    if sum(_is_context(row) for row in rows) * 2 < len(rows):
        return top_k
    return min(20, max(top_k * 3, top_k + 4))


def select_evidence(original, expanded, top_k):
    """Keep substantive sections and one intact context/authority passage."""
    versions = {_version(row) for row in original}
    candidates = []
    seen = set()
    for row in expanded:
        text = ' '.join((row.get('content_text') or '').split()).casefold()
        if _version(row) in versions and text and text not in seen:
            candidates.append(row)
            seen.add(text)
    substantive = [row for row in candidates if not _is_context(row)]
    if not substantive:
        return original
    context = [row for row in original if _is_context(row)]
    # Keep the complete cover/authority passage, including sample/draft caveats.
    def authority_priority(row):
        text = row.get('content_text') or ''
        return bool(_QUALIFICATION.search(text)), len(text)

    retained = [max(context, key=authority_priority)] if context else []
    selected = substantive[:top_k - len(retained)] + retained
    selected_ids = {row['chunk_id'] for row in selected}
    # Preserve vector order and original content/provenance for downstream checks.
    ordered = [row for row in candidates if row['chunk_id'] in selected_ids]
    ordered_ids = {row['chunk_id'] for row in ordered}
    ordered.extend(row for row in retained if row['chunk_id'] not in ordered_ids)
    return ordered[:top_k]
