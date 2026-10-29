# Authorized history citations

Generate `20261029020000_history_citations.sql` with
`scripts/maintenance/migrations/build_history_citations.py`; use `--check` for parity.
Apply after durable chat turns and before enabling history source cards.

The service-only reader verifies conversation ownership and each answer's current
knowledge policy. Cards require a citation, an operation belonging to that same
answer, selected retrieved evidence, a ready processing run and a document
version in the answer policy and current publication manifest. Context that was
retrieved but never cited does not become a card. Duplicate chunks are omitted.

Quotes, titles and sections come from authorized persisted evidence. Invalid
legacy relevance scores are returned as null. No storage keys, provider details,
internal policy stamps or another conversation's messages are exposed. Changed
access returns an unavailable marker so the service can redact dependent history.

The migration adds only a read function and its grants. It does not rewrite old
answers or fabricate citations whose earlier persistence failed. Browser roles
cannot call the reader directly. Validate with the isolated knowledge revision
runner and the real API/SQL Learning Resources browser journey.
