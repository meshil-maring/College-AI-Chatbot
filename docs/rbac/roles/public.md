# Public / anonymous access

**Status: DRAFT — REVIEW ONLY. Canonical role: none.** Read [shared rules](../shared-rules.md). Public access is an endpoint policy, not an authenticated role or permission grant.

## Allowed entry points

Proposed public access includes anonymous AI chat, permitted institution lookup, supported account-registration entry points, and content explicitly published for a public audience. Public notices or learning resources are available only where an endpoint actually enables public access; their visibility is not inferred from the module name.

**Source-observed — S14, S21:** Public student/faculty/staff registration uses strict contracts and pending workflows. A dedicated public-knowledge policy checks source institution, public visibility, published lifecycle, and effective dates. This is representative source evidence, not complete retrieval certification.

## Restrictions

- No private student profiles, academic records, authenticated conversations, or restricted institutional evidence.
- No staff, Faculty, Admin, or platform operations.
- No official-register imports, identity decisions, academic mutations, role grants, or approvals.
- No ability to bypass request limits, resource visibility, or institution validation through public chat.

## Permission boundary

There is no Public entry in the authenticated bootstrap grant map. Public endpoints MUST enforce their explicit policy and abuse controls. A registration's selected type or institution code does not authorize a role or prove membership.

## Relevant review cases

Use V16, V19, and V20 in [verification](../verification.md): public retrieval must exclude restricted/foreign content, policy failures must fail closed, and injected role/scope/status fields must not establish authority.

## Related reading and sources

- [Student registration workflow](../workflows/student-registration.md) for public signup versus class pre-registration.
- [Module policies](../module-policies.md) for public content and AI retrieval.
- S14 and S21 in [source references](../source-references.md).
