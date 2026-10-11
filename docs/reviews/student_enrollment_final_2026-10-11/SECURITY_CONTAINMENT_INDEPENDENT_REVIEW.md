# Independent security-containment candidate review

Prepared 2026-10-11, Asia/Calcutta. **REVIEW ONLY. No execution or installation approval.**

The three original artifacts exist at the exact paths below. Direct byte hashes of the SQL and Markdown match the original results JSON. Both unconditional exceptions remain, and the final statement is `ROLLBACK;`. Source review identifies a concrete reset-maintenance incompatibility and limits in the catalog assertions. B01–B07 remain open; matching hashes and static assertions do not establish database compatibility.

## Original files and directly computed SHA-256

Workspace root: `F:\Git Project\CollegeAIChatbot`. All three files are in `docs/reviews/student_enrollment_final_2026-10-11/`.

| Original artifact | SHA-256 of original file bytes | Comparison |
| --- | --- | --- |
| [SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql](SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql) | `897a4c786adc487bce04462690f8a4bbcab215f2e3e53841f84a82f40c1a63c7` | MATCH: JSON `artifact_hashes.SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql` |
| [SECURITY_CONTAINMENT_MIGRATION_REVIEW.md](SECURITY_CONTAINMENT_MIGRATION_REVIEW.md) | `43bd8294163c4a1cc1158e85979873dbece914d065f83f003df63324016d50d8` | MATCH: JSON `artifact_hashes.SECURITY_CONTAINMENT_MIGRATION_REVIEW.md` |
| [SECURITY_CONTAINMENT_CANDIDATE_RESULTS.json](SECURITY_CONTAINMENT_CANDIDATE_RESULTS.json) | `42e4678c417b0b0c73fc85107323802a3746b3ce134f4a5fb937cbe0d2e2ca5a` | External fingerprint; JSON embeds no expected self-hash |

Hashes were calculated with PowerShell `Get-FileHash -Algorithm SHA256 -LiteralPath` against these originals. SQL and Markdown comparisons were independently repeated with Python standard-library `hashlib.sha256(path.read_bytes())`. Neither calculation reconstructs SQL from Markdown, normalizes line endings, or hashes an extracted code block. The JSON's `enrollment_sql_sha256` concerns the separate enrollment draft; it is not the candidate hash. Artifact agreement establishes internal byte consistency, not authenticated provenance, exact-byte approval, or correctness.

## Work performed and preservation

Only local file reads, hashes, an independent in-memory lexical check, Git status, and read-only consultation of PostgreSQL 17 documentation were used. No SQL, PostgreSQL parser, database connection, Docker startup, application import, database-dependent test, remote Supabase operation, push, or deployment was performed. The reproduction block in the original Markdown was read but **not run**: it rewrites the existing results JSON.

All 1,150 entries in the JSON preservation baseline exist and match their recorded hashes. All 39 source migration hashes match. Existing tracked script edits and untracked review/evidence work were retained. This report is a new file; none of the three originals, application files, migration files, or existing evidence files was edited. The preservation baseline is a bounded inventory, not a claim that every ignored file in the workspace was inventoried.

## Independently checked static assertions

An independent scanner read the original SQL, recognized quoted literals, dollar bodies and comments, and split only top-level statements. It did not execute SQL or reuse the original verifier's code. The following checks passed:

| Assertion | Exact evidence |
| --- | --- |
| Complete ordered statement inventory | 51 top-level statements and unique markers `C001` through `C051`; statement texts and their UTF-8 SHA-256 values agree with JSON `statement_inventory` |
| Review stop remains unconditional | `C002`, SQL line 28: `DO $review_stop$ BEGIN RAISE EXCEPTION 'REVIEW-ONLY: NOT FOR EXECUTION; independent exact-byte approval required'; END $review_stop$;` |
| Unresolved-dependency stop remains unconditional | `C003`, SQL line 31: `DO $dependency_stop$ BEGIN RAISE EXCEPTION 'BLOCKED B01-B07: catalog/service/default/retention/security acceptance required for executable successor'; END $dependency_stop$;` |
| Stops precede proposed mutations | `C001` begins the transaction; `C002`/`C003` precede `C004`–`C007` session/preflight statements and the first default-ACL mutation, `C008` |
| Final statement remains rollback | `C051`, SQL line 443: `ROLLBACK;`; no top-level `COMMIT` |
| Original bytes and source fingerprints agree | Both artifact-hash comparisons, all 39 migration hashes and all 1,150 preservation hashes pass |

The stops have no conditional bypass. In ordinary transaction execution, the first exception would abort the transaction, so later statements would not constitute a successful containment installation. A client that stops on error may never send the final rollback; the textual final statement is nevertheless exactly `ROLLBACK;`. No runtime transaction behavior was exercised.

The original JSON's `automated_checks_passed: true` records bounded lexical assertions. It does not mean its proposed `C007` preflight or `C050` postflight has run. This review does not independently certify every original automated or manual conclusion.

## Source-verified facts

These findings describe checked repository source, not current catalog state:

- The reconstructed baseline grants future public functions to `anon`, `authenticated`, and `service_role` at [migration lines 1172–1175](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L1172). `C008` removes the postgres global PUBLIC function default; `C009` removes the two direct public-schema client defaults. Neither removes the future service default.
- Source declarations for the six sensitive signatures match `C010`–`C021` and the `C007` return/language/default expectations. The claim routine returns `SETOF public.email_outbox`; completion returns boolean with three default arguments; the later resolver replacement uses SQL and returns JSONB. See [outbox declarations](../../../supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql#L139), [completion](../../../supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql#L344), [resolver replacement](../../../supabase/migrations/20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql#L71), and [Mailgun declaration](../../../supabase/migrations/20261002010000_phase_7_18_mailgun_webhook_reconciliation.sql#L55).
- The separately declared seven-argument invitation overload is present in [onboarding source](../../../supabase/migrations/20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql#L20); the candidate does not revoke or replace it. The renamed assignment implementation is explicitly client/service-denied in [responsibility source lines 281–284](../../../supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql#L281), consistent with `C050`'s service-denial expectation.
- [Admin-1 lines 479–509](../../../supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql#L479) define the audit columns, defaults, checks, primary key and actor restrictive FK. [Phase 8.1 lines 41–43](../../../supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql#L41) add the eleventh column and institution restrictive FK. These source declarations support `C007`'s audit-layout expectations. [Lines 505–519](../../../supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql#L505) install the rejecting row UPDATE/DELETE guard retained by `C007`/`C050`.
- The [audit repository](../../../backend/app/repositories/admin_audit.py#L24) performs INSERT and SELECT, consistent with retaining them in `C044`. [Admin-client construction](../../../backend/app/db/supabase.py#L20) uses configured server credentials and describes BYPASSRLS; source comments do not verify actual credentials, claims or target role attributes.
- [Academic master source lines 142–150](../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L142) already specify client denial, RLS, service DELETE/TRUNCATE denial, service SELECT/INSERT/UPDATE, and validation triggers. `C049` reasserts that contract rather than proving it is absent today.

## Specific compatibility findings and assertion limits

**F01 — Confirmed source-level maintenance incompatibility; B06; `C046`/`C048` (SQL lines 312–320).** The new helper rejects TRUNCATE and the new trigger binds it to the audit table. The existing [reset script lines 38–43](../../../scripts/maintenance/reset_supabase_data.sql#L38) rejects *any* noninternal public TRUNCATE trigger before its [TRUNCATE operation at line 82](../../../scripts/maintenance/reset_supabase_data.sql#L82). An installed `C048` therefore makes this existing reset workflow refuse to proceed. This is an intentional protective consequence, not an observed execution failure or justification to disable the guard. The maintenance owner must accept that the reset workflow becomes unavailable or approve a separately reviewed preservation/retention workflow before compatibility acceptance.

**F02 — Catalog assertions are not definition-equivalence proof; B04/B05; `C007`/`C050`.** `C007` lines 111–113 and `C050` lines 405–407 check trigger identity, function binding, enable state and event mask. They do not compare trigger `WHEN` conditions, UPDATE-column lists, arguments or function bodies. `C007` lines 157–169 check constraint counts/validation, selected non-null flags and default presence, not exact constraint columns, referenced relations, check expressions or default expressions. A changed condition/body/default can satisfy those limited predicates. This is a directly verified assertion-coverage limit, already acknowledged by the original report's external-comparison requirement; it is not evidence such drift exists. The later definition comparison must cover these details, not merely repeat these predicates.

**F03 — Future-default effects are broader than the existing six-signature repair; B02/B03; `C008`/`C009` (lines 189–192).** PostgreSQL's `ON FUNCTIONS` default-privilege category also includes procedures and aggregates; global changes apply across schemas for the selected creator. Existing routine ACLs are unaffected. These documented semantics require creator/extension/consumer acceptance beyond `C010`–`C021`'s six signatures. The automatic future service grant is intentionally retained. This is an unresolved compatibility and scope dependency, not an accidental missing removal statement. [PostgreSQL 17 ALTER DEFAULT PRIVILEGES](https://www.postgresql.org/docs/17/sql-alterdefaultprivileges.html)

**F04 — Fixed target and first-install assumptions; B01/B04/B07; `C007` (lines 46–67, 143–147).** The candidate requires postgres session/current identity, PostgreSQL 17, service-role BYPASSRLS, an exact 39-version ledger and no existing new helper/TRUNCATE guard. A PostgreSQL 18 target, non-bypass service contract, additional ledger entry or rerun after installation is rejected. These are explicit fail-closed compatibility constraints. Source hashes do not prove the target satisfies them; no idempotent rerun contract is supplied.

No additional confirmed syntax error or sensitive-signature/return/default mismatch was found in the examined source. This is not PostgreSQL grammar validation. In particular, the outer PL/pgSQL `END` without an internal trailing semicolon in the DO/function dollar bodies is not itself a defect: PostgreSQL permits omission at the end of a function body. [PostgreSQL 17 PL/pgSQL structure](https://www.postgresql.org/docs/17/plpgsql-structure.html)

The PostgreSQL 17 documentation also supports the candidate's `MAINTAIN` privilege and role `USAGE`/`SET` inquiries; this consultation does not replace engine tests. [Privilege inquiry functions](https://www.postgresql.org/docs/17/functions-info.html#FUNCTIONS-INFO-ACCESS-TABLE)

## Unresolved assumptions and required providers: B01–B07

Provider labels below identify responsible functions; no named individual or organization is assumed. Evidence collection involving a database remains outside this review's authorization. Each blocker requires recorded review acceptance, not just an additional assertion in the SQL.

| Blocker | Required evidence and acceptance | Who or what must provide it |
| --- | --- | --- |
| **B01 — Service claims, roles and RLS** | Credential-mode/claim mapping for actual server requests, `auth.role()` behavior, object owners, effective role memberships/SET paths and BYPASSRLS, plus exact policies for affected tables and observed service read/write behavior. Use redacted evidence without secret values. A non-bypass target needs its own reviewed policy variant; `C007` rejects it. | Backend authentication/deployment maintainer supplies request-mode evidence; authorized database administrator/catalog collector supplies role/owner/policy exports; security reviewer accepts the contract; a later approved runner validates it. |
| **B02 — Future service EXECUTE** | An explicit per-creator grant contract listing future service entry points, private helpers, trigger creators and invoker/definer nested dependencies. Demonstrate that legitimate service calls work with explicit grants and intended private helpers stay private. No future service-default removal is present or approved here. | Migration/routine owners and backend/worker maintainers supply the dependency/grant inventory; security reviewer accepts it; a later disposable runner provides fresh-object tests. |
| **B03 — Global defaults and actual creators** | Actual creating roles, global/schema function defaults, effective inherited client access, and migration/extension behavior across affected schemas, including procedures/aggregates. Document acceptance of the postgres global PUBLIC change; additional creator/default repairs need exact separate scope. | Database platform administrator and migration/extension owners supply creator/default inventories and impact evidence; service consumers and security reviewer accept the scope; later creator-specific fixtures validate it. |
| **B04 — Current catalog and applied bytes** | Authorized, current catalog export tied to target identity/version and collection time: ledger plus applied-source provenance, table/column ACLs and grantors/options, role inheritance/SET, owners, RLS policies, constraints/defaults, full trigger/function definitions, overloads, views and RPC exposure. Compare with the 39 hashed sources; ledger versions alone do not attest bytes. Unknown variants require review. | Authorized catalog collector/DB administrator supplies current state; migration provenance owner supplies applied-byte evidence; independent reviewer compares it with source. Existing historical snapshots cannot stand in for this collection. |
| **B05 — SC-06/SC-07 assessment and order** | Command-by-command request-role/human-actor binding and definer schema/name-resolution assessment, including nested/dynamic lookup. Record whether a separate hardening candidate must precede containment acceptance. Decide any separate scope for adjacent audit ledgers, test tables and assignment/responsibility assertions. Do not clear search paths on unqualified bodies as a shortcut. | Backend authorization and SQL routine owners supply call/body analysis; database/security reviewer accepts scope and order; later approved claim and hostile-name fixtures validate any authored hardening. |
| **B06 — Consumers, maintenance and concurrency policy** | Inventory external direct consumers; their read/write/RPC and default-grant requirements; audit retention/reset/recovery procedure and owner authority; explicit disposition of F01; and an accepted policy for blocked/in-flight commands during revocation. A denied retry is insufficient to define the fate of already authorized work. | Application/integration owners and direct consumers supply usage evidence; audit/maintenance owner accepts retention/reset changes; security/product owner accepts revocation semantics; later runner verifies that policy. |
| **B07 — Exact bytes and disposable validation** | Independent approval identifying the SQL/Markdown/JSON fingerprints, plus a separately authorized executable validation copy with deliberate stop/transaction handling. Provide dedicated run-owned engine identity, PostgreSQL/bootstrap/extension/role/ledger setup, storage/cleanup ownership, full-chain runner, populated fixtures, role/claim matrix and concurrency/rollback test design. Record results for T01–T14 as applicable. | User or designated approver accepts exact bytes and later execution scope; validation/environment owner supplies readiness and isolation evidence; independent reviewer checks the runner/fixtures; the explicitly authorized disposable runner supplies runtime results. |

None of these provider statements authorizes contacting anyone, collecting live catalogs, removing either stop, changing the production chain, or executing the existing candidate.

## Runtime tests: pending, not inferred

The JSON records **T01–T14 NOT RUN**. This review ran none of them. Required test intent comes from the [change plan](SECURITY_CONTAINMENT_CHANGE_PLAN.md#L55):

| Tests | Later evidence required |
| --- | --- |
| T01–T04 | Effective audit ACL/column/options denial; populated row-guard failures; empty/populated and cascade TRUNCATE rejection with transaction rollback; retained service audit read/append and atomic failure behavior |
| T05–T08 | Actual creator defaults, explicit/private grants, six/seven overload routing and default arguments, trigger/nested execution, worker leasing/completion/retry behavior and verified Mailgun path |
| T09–T12 | Two-tenant authority and legacy academic denials through all relevant access paths; verified server-derived actor/scoped authorization; retained application workflows and enabled integrity/publication guards |
| T13 | Conditional separate schema/definer-hardening tests, if included; otherwise record its deferred scope explicitly rather than marking it passed |
| T14 | Concurrent revocation/in-flight-command behavior under the accepted contract and atomic rollback at relevant mutation/audit steps |

Table privilege checks, RLS flags, service-role labels, source comments and matching hashes cannot establish these behaviors. PostgreSQL documents that BYPASSRLS bypasses row policies and that TRUNCATE is outside row security; service and owner boundaries therefore need their own acceptance. [PostgreSQL 17 row security](https://www.postgresql.org/docs/17/ddl-rowsecurity.html)

## Go/no-go for the next stage

**GO for continued review-only evidence planning and blocker resolution. NO-GO for executable validation, SQL installation, production-chain placement or deployment.** Original artifact integrity and review controls are verified. Resolve B01–B07, including the reset incompatibility and exact-definition comparison, before requesting a separately scoped next-stage approval. This report completes an independent source review; it does not close runtime or security acceptance.
