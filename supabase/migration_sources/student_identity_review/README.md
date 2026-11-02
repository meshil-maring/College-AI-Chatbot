# Student identity review

Adds a tenant-scoped administrator lookup for duplicate student registration
details. The lookup reports matching student account, approval and sign-in state,
plus pending setup invitation delivery status. It never returns records from
another institution.

Generate using `python scripts/maintenance/student_onboarding/build_identity_review.py`;
use `--check` to verify parity. The generated migration does not deploy SQL.
