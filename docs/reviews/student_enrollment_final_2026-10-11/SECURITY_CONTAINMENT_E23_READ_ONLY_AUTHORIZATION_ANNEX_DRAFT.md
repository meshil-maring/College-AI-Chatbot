# E23 target-specific read-only collection authorization annex — draft

2026-10-11, Asia/Calcutta. **NON-EXECUTABLE, UNFILLED DRAFT. NO COLLECTION AUTHORITY. No target collection or owner contact authorized or performed. B01–B07 OPEN; N01–N03 OPEN; T01–T14 NOT RUN.**

This separate annex prepares the human completion and review fields required by [the read-only collection package](SECURITY_CONTAINMENT_READ_ONLY_COLLECTION_PACKAGE.md), sections 1–3, 7 and 10. It contains no SQL, connection commands, collector implementation or credentials. Local documentation review is the only current scope. It cannot authorize target access, attest policy acceptance, approve implementation or close blockers.

The actual package bytes were hashed locally before other review work and match the supplied reference:

| Binding | Value |
| --- | --- |
| Package | `SC-RO-2026-10-11-01`, `review-draft-1` |
| Supplied and locally verified package SHA-256 | `a9af4cab04cb134fa581d688eb75f94e3ffd0a8ced3a33548793702877cb1231` |
| Draft annex revision | `draft-1`; this labels a draft, not an approval |
| Final completed annex SHA-256 | **[UNFILLED: externally compute after completion; bind exact approved bytes]** |
| Completed manifest/method/boundary/output schedule hashes | **[UNFILLED: exact filenames, revisions, byte lengths and SHA-256]** |
| Fresh collection ID | **[UNFILLED: new collection identity]** |
| E23 approval record ID, controlled location and detached hash/signature | **[UNFILLED: human-issued approval record; no signature presently exists]** |
| Authorization disposition | **PENDING / NOT APPROVED** |

Every **[UNFILLED: …]** is an unresolved prerequisite. A required field must be completed and independently reviewed, or explicitly excluded with a named approver's reason and effect on coverage. A selected component cannot omit a prerequisite by calling it “not applicable.” No defaults, unchecked boxes, source examples, standing job titles or elapsed time imply approval. Proposed OP identifiers below come from the package; none is permitted for target execution by this draft. Changes to approved bytes, scope, methods or windows require fresh exact-byte review and approval.

## 1. Named people, authority and separation of duties

Repository-facing records use approved role/stable aliases; actual named identities and authority proof belong in a restricted approval record. Personal contact details and credentials do not belong here. All referenced identity mappings must be accessible to the authorized independent reviewer.

| Responsibility | Named identity / repository alias / organization | Authority, scope and evidence | Date and acceptance record |
| --- | --- | --- | --- |
| Accountable collection approver | **[UNFILLED: named approver and alias]** | **[UNFILLED: authority over exact target, operations, suppliers and window]** | **[UNFILLED: dated decision and detached record]** |
| DB metadata collector(s) | **[UNFILLED: every named collector and alias]** | **[UNFILLED: organizational role, RP-C/RP-L scope and login alias]** | **[UNFILLED: scope/handling acknowledgment]** |
| Source/document analyst(s) | **[UNFILLED: every named analyst and alias]** | **[UNFILLED: RP-S/RP-P scope and local source allowlist]** | **[UNFILLED: acknowledgment]** |
| Deployment/provenance supplier(s) | **[UNFILLED: named RP-V suppliers and aliases]** | **[UNFILLED: controlled-record authority and selected E items]** | **[UNFILLED: supplier authorization]** |
| Consumer/worker/operator supplier(s) | **[UNFILLED: named RP-X suppliers and aliases]** | **[UNFILLED: registry/aggregate authority and selected E items]** | **[UNFILLED: supplier authorization]** |
| Policy/attestation owner(s) | **[UNFILLED: named RP-O owners and aliases per policy]** | **[UNFILLED: accountable authority for their own area]** | **[UNFILLED: contact/attestation authorization]** |
| Independent scope/security reviewer | **[UNFILLED: named reviewer and alias]** | **[UNFILLED: independence, qualifications and permitted evidence access]** | **[UNFILLED: exact-byte review disposition]** |
| Independent database/method reviewer | **[UNFILLED: named reviewer and alias]** | **[UNFILLED: non-mutation/getter/engine-version review]** | **[UNFILLED: method review disposition]** |
| Evidence acceptance reviewers | **[UNFILLED: named reviewer(s) per selected E item]** | **[UNFILLED: domain coverage and independence from collection]** | **[UNFILLED: readiness acknowledgment; later acceptance remains separate]** |
| Storage/access/retention/legal-hold owner(s) | **[UNFILLED: named owners and aliases]** | **[UNFILLED: storage, access, retention and hold authority]** | **[UNFILLED: dated control approvals]** |
| Abort coordinator and resume approver | **[UNFILLED: named people and aliases]** | **[UNFILLED: stop, incident disposition and reauthorization authority]** | **[UNFILLED: approved procedure record]** |

A collector cannot sign for an accountable owner or self-certify blocked equality/coverage comparisons. Collection approval and future packet acceptance are separate decisions.

## 2. Target binding, window and identity checks

| Required field | Value to complete and approve |
| --- | --- |
| Target alias | **[UNFILLED: exact controlled alias]** |
| Environment class | **[UNFILLED: explicitly identified environment; no assumed production/disposable target]** |
| Database/service/deployment identifiers | **[UNFILLED: exact aliased identifiers and controlled mapping record]** |
| Controlled alias mapping | **[UNFILLED: restricted location, owner, readers and approved verification reference]** |
| Expected engine identity/version | **[UNFILLED: evidenced engine identity/version; do not assume PG17 from candidate comments]** |
| Expected database/session collector identity | **[UNFILLED: aliased database and exact expected login/session role metadata]** |
| Expected app/frontend/worker/gateway revisions and identities | **[UNFILLED: each component's expected revision and sanitized deployment evidence]** |
| Approved extension/schema identity/version markers | **[UNFILLED: explicit identities, versions and marker provenance]** |
| Pre-connection target check | **[UNFILLED: controlled-document comparison and named checker; no secret inspection]** |
| Minimal post-connection identity check | **[UNFILLED: independently reviewed OP-C0 method record/hash, exact non-secret fields and comparison criteria]** |
| Drift and consistency markers | **[UNFILLED: before/after revision markers, per-operation timestamps and invalidation rules]** |
| Start, Asia/Calcutta (UTC+05:30) | **[UNFILLED: YYYY-MM-DD HH:MM:SS +05:30]** |
| Start, UTC | **[UNFILLED: matching YYYY-MM-DD HH:MM:SS Z]** |
| End, Asia/Calcutta (UTC+05:30) | **[UNFILLED: YYYY-MM-DD HH:MM:SS +05:30]** |
| End, UTC | **[UNFILLED: matching YYYY-MM-DD HH:MM:SS Z]** |
| Approval expiry, both timezones | **[UNFILLED: expiry instants and revocation reference]** |
| Window conversion/validity reviewer | **[UNFILLED: named reviewer/date and verified conversion/order]** |
| Revocation and window-check procedure | **[UNFILLED: record source, checker and checks before contact/connection/each operation]** |

UTC equals Asia/Calcutta time minus 05:30; this states a conversion rule, not an approved window. Pre-connection checks use approved records. Only a separately approved minimal OP-C0 read can follow connection. If it cannot verify the target/caller safely, abort. Wrong identity, redirection, unexpected environment or drift must not trigger a retry against another host/project. Independent exports do not imply an atomic snapshot.

## 3. E01–E26 selection and exact operation selection

Each row needs a component-level INCLUDE or EXCLUDE decision, exact selected OP IDs, method/boundary/permission/output/supplier/reviewer record references, and a coverage reason. The package's B/OD/T mappings and item contracts remain governing; selection does not change their status. OP-S and OP-A are candidate offline routes for source preparation/review of each item. They must also be explicitly listed in the eventual per-item selection; they confer no target or contact authority.

The third column lists only package-supported acquisition candidates to help completion. It is **not** the selected permission list. Selection is unfilled for all 26 items. E23 is a mandatory prior authorization gate for any acquisition; it cannot be supplied retroactively after connection. For E24–E26, existing-artifact review/request preparation is the limit. All R components are **DEFERRED_VALIDATION / NOT RUN**, and **OP-R is EXCLUDED**.

| E item / proposed packet basename | Component decision | Candidate acquisition OP IDs only | Exact selected OP IDs and linked records |
| --- | --- | --- | --- |
| **E01** / `E01_request_modes.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-C0, OP-C1, OP-V, OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E02** / `E02_principal_identity.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-V, OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E03** / `E03_effective_access.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-C1, OP-C2, OP-C3, OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E04** / `E04_consumers.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-X, OP-V, OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E05** / `E05_explicit_grants.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E06** / `E06_dependencies_overloads.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-C3, OP-V | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E07** / `E07_creators_defaults.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-C1, OP-V | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E08** / `E08_global_impact.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-X, OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E09** / `E09_creator_acceptance.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E10** / `E10_versions_applied_bytes.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-C0, OP-C4, OP-V | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E11** / `E11_relations_policies.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-C2 | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E12** / `E12_definitions_bridges.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-C3, OP-V | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E13** / `E13_ordering_contract.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E14** / `E14_lookup_authority.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-C1, OP-C3, OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E15** / `E15_missing_consumers.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-X, OP-V, OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E16** / `E16_provider_semantics.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-P, OP-V, OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E17** / `E17_identity_reconciliation.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-V, OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E18** / `E18_audit_contract.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-C2, OP-C3, OP-X, OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E19** / `E19_recovery_revocation.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E20** / `E20_delivery_cutover.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-X, OP-V, OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E21** / `E21_data_rollout_plan.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-C2, OP-V, OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E22** / `E22_retention_maintenance.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-C2, OP-C3, OP-X, OP-O | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E23** / `E23_collection_authorization.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-O (prerequisite before acquisition) | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E24** / `E24_successor_review_request.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-O (request/existing-artifact review only) | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E25** / `E25_runner_bootstrap_request.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-O (request/existing-artifact review only) | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |
| **E26** / `E26_validation_request.md` | **[UNFILLED: INCLUDE/EXCLUDE each S/C/V/X/P/O component as applicable; reason]** | OP-O (request/existing-artifact review only) | **[UNFILLED: exact OP IDs; method, boundary, RP/H, output, supplier, reviewer and coverage references]** |

The final selected E/OP set and exclusions require a reconciliation against package section 4: **[UNFILLED: named reviewer/date, exact set and disposition record]**. Selected packets start REQUESTED / NOT COLLECTED. Later statuses use REQUESTED, SUPPLIED_UNREVIEWED, ACCEPTED_INPUT, PARTIAL, DENIED_VISIBILITY, REDACTED_LIMITATION, UNEXPECTED_VARIANT, REJECTED or DEFERRED_VALIDATION. ACCEPTED_INPUT accepts stated input scope/provenance only; it does not accept an OD decision, pass a T case or close a blocker.

## 4. Exact target catalog, schema, object, role and field boundaries

Appendix A copies known **source** identities from the preserved JSON for offline comparison. Every target identity/field/filter decision below remains unfilled. Names in Appendix A are not deployed facts or blanket approved export filters.

No wildcard catalog, schema, role, field or configuration selection is acceptable. Repeat each boundary record until every selected method has an exact finite approved boundary. A list reference must identify exact bytes and hash; “all dependencies,” “standard catalogs,” “source inventory” or a schema name alone is insufficient.

| Boundary dimension | Required explicit completion |
| --- | --- |
| Engine-specific catalog identities | **[UNFILLED: each exact catalog schema/name and engine-version evidence; no guessed query/catalog list]** |
| Catalog columns and derived fields | **[UNFILLED: per catalog, exact column names/types, permitted derived fields, joins/edge directions and excluded fields]** |
| Schema/database/language/extension identities | **[UNFILLED: finite exact identifiers/aliases, owner/ACL fields and whether discovery or detailed definition access is selected]** |
| Containment relations | **[UNFILLED: INCLUDE/EXCLUDE per Appendix A.1 identity; exact target mapping and permitted metadata fields]** |
| Application column metadata boundary | **[UNFILLED: exact relation/column identities or independently approved finite discovery fields; never column values]** |
| Routine signatures | **[UNFILLED: INCLUDE/EXCLUDE per Appendix A.2 identity; exact target schema/name/types/modes/named/default/result metadata and permitted definition fields]** |
| Sensitive/private/protected/helper entries | **[UNFILLED: exact per-entry selection from Appendix A.3, source-to-target rename history and proposed-only exclusions]** |
| Trigger bindings | **[UNFILLED: INCLUDE/EXCLUDE per Appendix A.4 relation/trigger/signature; exact target identities and fields]** |
| Creator/owner/caller role seeds | **[UNFILLED: exact role identities/OIDs/aliases, provenance and approved source comparison labels]** |
| Role/member/SET-path closure | **[UNFILLED: exact seed/edge scope, fields, direction, finite depth/object/size bounds and approved stop conditions; no SET ROLE]** |
| Defaults and ACLs | **[UNFILLED: per creator/schema/global/object category exact identities and raw/exploded ACL fields, grantors/options and NULL distinctions]** |
| Additional relations/routines/ledgers | **[UNFILLED: exact invitation/membership/delivery/recovery/adjacent audit/teaching/test/roster/knowledge identities; no automatic expansion]** |
| Views/rules/partitions/inheritance/dependencies | **[UNFILLED: exact bridge/edge identities, scope, owner/security/ACL/definition fields and finite bounds]** |
| Same-name overload discovery | **[UNFILLED: exact approved routine-name seeds, schemas and identity-only fields; unexpected variants pause detailed export]** |
| Initial identity/owner/edge discovery | **[UNFILLED: exact approved schemas/roles/objects/fields and finite bounds; no body/configuration export outside approved scope]** |
| Definition getters | **[UNFILLED: exact safe built-in getter identities/signatures/version and side-effect/dependency review; no application/extension getter fallback]** |
| Optional migration ledger exception | **[UNFILLED: INCLUDE/EXCLUDE and reason; if included, exact approved method/permission for only version/name]** |
| Non-secret deployment/config fields | **[UNFILLED: exact record sources, selected field names and alias substitutions; no environment/config dump]** |
| Local source read allowlist | **[UNFILLED: exact non-secret file paths/revisions/hashes for later collection preparation; no secret/config store access]** |
| Discovery and detailed-export separation reviewer | **[UNFILLED: named reviewer/date and exact reviewed boundary-record hashes]** |

The source package identifies `supabase_migrations.schema_migrations` with only `version` and `name` as the optional ledger exception. This does not establish that the target has that shape or grant read permission. Exclude `statements` and all other fields; shape mismatch stops the item. Obtain applied-byte provenance independently from authorized deployment suppliers. No application/Auth/audit/invitation/outbox/role-record rows, row counts, samples, user-value statistics, password catalogs, credential attributes, active-query text or unrestricted monitoring views may be read.

Exact boundary record template, repeated per catalog/object/role group:

- Boundary record ID, revision and detached hash: **[UNFILLED]**.
- Selected E/OP IDs and target alias: **[UNFILLED]**.
- Engine/schema/catalog/object/role identities and finite filters: **[UNFILLED]**.
- Exact allowed columns, definition fields, edge scope and excluded fields: **[UNFILLED]**.
- Discovery versus detailed export, visibility limits and unexpected-variant stop: **[UNFILLED]**.
- Safe definition handling/supplier record and output derivatives: **[UNFILLED]**.
- Independent reviewer, date and accountable approver disposition: **[UNFILLED]**.

## 5. Reviewed methods, tools, hashes and bounds

This annex supplies no statements or commands and does not author a read method. For each selected OP, an authorized human must identify a separate, concrete, independently reviewed method record. Where an exact statement is necessary, its reviewed bytes must be controlled and hash-bound there. A hash without review of the corresponding safe bytes is inadequate.

| Operation ID from package | Method/statement record, revision and SHA-256 | Tool identity/version/artifact hash and version provenance | Caller, boundary, permission, output and bounds |
| --- | --- | --- | --- |
| **OP-S** | **[UNFILLED: selected/excluded; exact read-only method record and reviewed byte hash]** | **[UNFILLED: tool/version/hash, or reviewer-accepted non-applicability reason]** | **[UNFILLED: exact caller/boundary/RP/H/output/time/size/retry records]** |
| **OP-C0** | **[UNFILLED: selected/excluded; exact read-only method record and reviewed byte hash]** | **[UNFILLED: tool/version/hash, or reviewer-accepted non-applicability reason]** | **[UNFILLED: exact caller/boundary/RP/H/output/time/size/retry records]** |
| **OP-C1** | **[UNFILLED: selected/excluded; exact read-only method record and reviewed byte hash]** | **[UNFILLED: tool/version/hash, or reviewer-accepted non-applicability reason]** | **[UNFILLED: exact caller/boundary/RP/H/output/time/size/retry records]** |
| **OP-C2** | **[UNFILLED: selected/excluded; exact read-only method record and reviewed byte hash]** | **[UNFILLED: tool/version/hash, or reviewer-accepted non-applicability reason]** | **[UNFILLED: exact caller/boundary/RP/H/output/time/size/retry records]** |
| **OP-C3** | **[UNFILLED: selected/excluded; exact read-only method record and reviewed byte hash]** | **[UNFILLED: tool/version/hash, or reviewer-accepted non-applicability reason]** | **[UNFILLED: exact caller/boundary/RP/H/output/time/size/retry records]** |
| **OP-C4** | **[UNFILLED: selected/excluded; exact read-only method record and reviewed byte hash]** | **[UNFILLED: tool/version/hash, or reviewer-accepted non-applicability reason]** | **[UNFILLED: exact caller/boundary/RP/H/output/time/size/retry records]** |
| **OP-V** | **[UNFILLED: selected/excluded; exact read-only method record and reviewed byte hash]** | **[UNFILLED: tool/version/hash, or reviewer-accepted non-applicability reason]** | **[UNFILLED: exact caller/boundary/RP/H/output/time/size/retry records]** |
| **OP-X** | **[UNFILLED: selected/excluded; exact read-only method record and reviewed byte hash]** | **[UNFILLED: tool/version/hash, or reviewer-accepted non-applicability reason]** | **[UNFILLED: exact caller/boundary/RP/H/output/time/size/retry records]** |
| **OP-P** | **[UNFILLED: selected/excluded; exact read-only method record and reviewed byte hash]** | **[UNFILLED: tool/version/hash, or reviewer-accepted non-applicability reason]** | **[UNFILLED: exact caller/boundary/RP/H/output/time/size/retry records]** |
| **OP-O** | **[UNFILLED: selected/excluded; exact read-only method record and reviewed byte hash]** | **[UNFILLED: tool/version/hash, or reviewer-accepted non-applicability reason]** | **[UNFILLED: exact caller/boundary/RP/H/output/time/size/retry records]** |
| **OP-A** | **[UNFILLED: selected/excluded; exact read-only method record and reviewed byte hash]** | **[UNFILLED: tool/version/hash, or reviewer-accepted non-applicability reason]** | **[UNFILLED: exact caller/boundary/RP/H/output/time/size/retry records]** |
| **OP-R** | **EXCLUDED: no runtime method authorized** | **EXCLUDED** | **R requests only; no engine/test/adapter/failure injection** |

Required per selected method record:

- Exact method/statement bytes reference, ID/revision, byte length/SHA-256 and E/OP IDs: **[UNFILLED]**.
- Tool name/version, supplier/build artifact reference and measured hash; version evidence from existing controlled records: **[UNFILLED]**. Do not execute SDK/application version commands.
- Exact caller login alias/effective role, RP profile, secure access reference and existing permission proof: **[UNFILLED]**.
- Exact catalog/column/object/signature/getter allowlist and filter/boundary record: **[UNFILLED]**.
- Independent non-mutation and side-effect review, including every getter/dependency and safe error/log behavior: **[UNFILLED]**.
- Per-operation start/end, timeout, output byte/file/object limits, approved retry count/conditions and rate bounds: **[UNFILLED]**.
- Pre-screen/sanitization route, original/derivative rules and exact output paths: **[UNFILLED]**.
- Reviewer identity/date, approved exact-byte hash and approver's selected method decision: **[UNFILLED]**.

No arbitrary SQL/RPC/shell capability follows from an OP selection. A read wrapper does not make side-effect functions safe. No application routine/default expression/trigger/auth helper may be invoked; unsafe or insufficient methods require a distinct reviewed scope, not a substitution.

## 6. Existing permissions and secure access

The package's RP-S/RP-C/RP-L/RP-V/RP-X/RP-P/RP-O/RP-A profiles are proposals, not grants; RP-R supplies no runtime permission.

| Access requirement | Completion and proof |
| --- | --- |
| Named collector and login alias per method | **[UNFILLED: identity, method IDs and approved target]** |
| Existing minimum profile per component | **[UNFILLED: exact RP profile and current rights evidence]** |
| Connection/catalog/getter visibility | **[UNFILLED: existing permitted connection and exact selected catalog fields/getters; pre-connection documentary evidence]** |
| Non-owner/non-superuser/non-BYPASSRLS status | **[UNFILLED: independent existing rights evidence and minimal approved OP-C0/C1 confirmation]** |
| Optional ledger version/name access | **[UNFILLED: existing column-limited right or authorized supplier alternative; no grants]** |
| Wider-credential exception | **[UNFILLED: explicitly exclude, or identify separate prior exception review, controls and exact scope; never default fallback]** |
| Permitted secure access mechanism | **[UNFILLED: approved existing mechanism name, custodian and controlled reference; no values, URLs or connection material]** |
| Credential delivery/use and logging controls | **[UNFILLED: authorized operator procedure, no secret inspection/copy, no tracing or credential output]** |
| Supplier permissions on existing records | **[UNFILLED: named supplier/record rights proof and sanitization authority]** |
| Missing visibility response | **[UNFILLED: reviewer/report channel; PARTIAL or DENIED_VISIBILITY and supplier alternative]** |
| Permission reviewer and acceptance | **[UNFILLED: named reviewer/date, proof hashes and scope approval]** |

No provisioning, privilege escalation, role changes, role switching, request-claim changes, owner/service credential substitution or application table SELECT is authorized. Denied visibility is a reported gap; it is not proof of object absence and must not be repaired through extra grants.

## 7. Exact output, restricted storage, redaction and provenance

The package proposes `docs/evidence/security_containment_read_only/<collection_id>/<target_alias>/`. That is a pattern, not a resolved path. No collection output directory, packet, manifest, approval or attestation has been created by this task; this annex is the sole new artifact.

| Required output/control | Completion |
| --- | --- |
| Exact repository-facing relative root | **[UNFILLED: collection ID and target alias resolved to one new path]** |
| Exact resolved absolute root | **[UNFILLED: canonical new workspace-contained root and path check record]** |
| Path safety | **[UNFILLED: new/non-overwriting filenames, symlink/reparse containment, checker/date and failure response]** |
| Common artifact full paths | **[UNFILLED: exact new paths for 00_manifest.json, 01_hashes.json, 02_redaction_and_coverage.md and 03_review_dispositions.md]** |
| Per-selected-E packet full paths | **[UNFILLED: exact new root plus selected section 3 basename; no unselected files]** |
| Metadata/definition derivative paths | **[UNFILLED: exact selected E##_metadata.json and per-object derivative names, no secret/person identifiers in names]** |
| Restricted non-secret original storage | **[UNFILLED: approved controlled location alias, exact protected path mapping and owner]** |
| Alias/approval record storage | **[UNFILLED: exact controlled mapping location, authorized readers and separation from repository]** |
| Encryption/access logging and access list | **[UNFILLED: mechanisms, named owner/readers, least-privilege policy and evidence]** |
| File/total/time/object bounds | **[UNFILLED: numerical limits per method and package, enforcement and abort response]** |
| H0 and H-S/H-C/H-V/H-X/H-P/H-O assignment | **[UNFILLED: per selected E/method profile mapping and accountable handling approval]** |
| Owner pre-screening/sanitization | **[UNFILLED: supplier, controlled process and safe-field review before ordinary collector output]** |
| Redaction/normalization log | **[UNFILLED: permitted transformations, retained structural distinctions and limitations; raw/normalized/derivative separation]** |
| Unsafe material containment | **[UNFILLED: approved restricted incident route and publication withholding procedure; no secret error bodies]** |
| Provenance/hashing reviewer | **[UNFILLED: named reviewer/date and exact schedule/control hashes]** |

H0 excludes keys, passwords and their digests/fingerprints, bearer/JWT/signature values, raw/digested invitation or resume capabilities, protected/ciphertext token payloads, provider response bodies, emails, connection strings and student/audit/application rows from acquisition/output, filenames, logs and chat. Operational identities/URLs/paths are approved aliases. Do not acquire/dump secrets to redact or hash them later. Unsafe definition handling stops the item before export; pre-screened non-secret owner exports are an alternative.

A0 applies to each selected E packet and supplemental file: record original source/target alias/revision, supplier/collector, timestamps in both timezones, method/tool/version/hash, existing permission/visibility, exact object/role/field coverage, missing/denied/redacted status, reviewer/date/disposition, file byte length and measured SHA-256. Each file must appear in `00_manifest.json` and `01_hashes.json`. Record source/deployment/release provenance and derivation links, not merely a digest.

Original-byte fingerprints require safely supplied non-secret originals and supplier attestation of how obtained. Keep separate original, derivative and normalized hashes and transformation logs; preserve meaningful body/ACL differences, NULL versus explicit ACL, inheritance/SET edges, owners, grantors/options and version limits. If safe originals are unavailable, record REDACTED_LIMITATION or the appropriate gap, not equivalence. File hashes identify bytes, not applied-byte provenance or runtime behavior.

Completed manifest field values and its exact-byte independent completeness review: **[UNFILLED: every package section 1 field, schedule references, reviewer/date and detached acceptance hash]**. Record manifest/annex/signature hashes outside the hashed artifact to avoid circular self-hashing. No hash value is supplied for a future artifact.

## 8. Retention, legal hold, access and disposition

| Required policy | Completion |
| --- | --- |
| Retention/data/access owner | **[UNFILLED: named accountable owner and authority record]** |
| Duration, start event and review deadline | **[UNFILLED: exact duration/events and deadline in both timezones]** |
| Legal-hold applicability and decision | **[UNFILLED: applicable policy, hold authority, restrictions and dated disposition]** |
| Repository/derivative/original/mapping readers | **[UNFILLED: separate explicit lists and access review intervals]** |
| Sharing/export/publication policy | **[UNFILLED: permitted readers/channels, approval controls and redaction limits]** |
| Storage encryption/audit/incident response | **[UNFILLED: approved mechanisms, owner and records]** |
| Expiry and hold review procedure | **[UNFILLED: named reviewer, schedule and stop/hold actions]** |
| Separate disposition request/procedure | **[UNFILLED: later authority and review requirements; no deletion granted here]** |
| Retention/access/legal-hold acceptance | **[UNFILLED: named owners/reviewer, dates, exact policy hashes and decision]** |

Unknown retention or safe storage blocks acquisition. This draft and later collection permission confer no purge/destruction authority.

## 9. Suppliers, contact authority, usage window and public documents

Fill a supplier record for every selected V/X/O component, including each deployment/provenance, authentication, identity, academic, worker, messaging, audit, maintenance, rollout and platform policy area actually selected. Job titles alone do not identify accountable suppliers.

| Required supplier/contact field | Completion |
| --- | --- |
| Supplier name, alias and accountable domain | **[UNFILLED: repeat for each supplier]** |
| Selected E/OP IDs and exact controlled records/fields | **[UNFILLED: finite approved record/field list, revisions and provenance]** |
| Supply/read authority and sanitization evidence | **[UNFILLED: existing rights, original acquisition attestation and pre-screen approval]** |
| Contact recipient and channel reference | **[UNFILLED: named recipient, permitted channel and restricted contact reference; no personal details here]** |
| Explicit contact authorizer, purpose and window | **[UNFILLED: approver/date/scope; no contact under current task]** |
| Consumer registry coverage | **[UNFILLED: caller aliases/types/versions/entries/grants, owners and seasonal coverage]** |
| Aggregate usage window, Asia/Calcutta and UTC | **[UNFILLED: exact start/end, dataset revision and approved aggregate fields]** |
| Sampling/retention/seasonality limitations | **[UNFILLED: completeness, missing consumers, counts/window meaning and reviewer]** |
| Attestation format and authority | **[UNFILLED: dated owner policy/consumer/permission record, evidence hashes and exceptions]** |
| Supplier/contact/aggregate acceptance | **[UNFILLED: independent reviewer/date and authorizer disposition]** |

OP-X is limited to owner-authorized registry and pre-sanitized aggregate records. No raw logs, mailboxes, query/URL text, payloads, emails, token or user IDs. Absence in source or aggregates does not prove no external or seasonal consumer.

Public-document retrieval decision: **[UNFILLED: INCLUDE/EXCLUDE with reason; presently NOT PERFORMED]**.

If included, fill exact selected E/OP-P IDs, official unauthenticated URLs/title/version/date scope, retrieval tool/method record, responsible analyst, bounded quotation/paraphrase limits, claim-to-section/version-applicability table, output paths and reviewer: **[UNFILLED: all fields and record hashes]**. No provider account login/API/project inspection/custom support contact. Owner-supplied extracts require their own approved supplier/contact/provenance record. Documentation establishes documented guarantees and their limits, not observed provider behavior.

## 10. Abort, incident and resume procedure

Stop before contact/connection if approval, identity, window, safe method, scope, permissions, storage, handling or review readiness is incomplete. Stop affected collection on wrong target/role, redirection, denied visibility, unexpected variants, sensitive material, unapproved method, engine/schema/revision drift, timeout/size overrun, storage/retention failure or expired/revoked authorization. If authority or target safety is uncertain, halt the run pending disposition; do not continue unaffected operations by assumption.

| Procedure field | Completion |
| --- | --- |
| Abort owner and scope-of-stop criteria | **[UNFILLED: named coordinator, per-item versus whole-run decision rules]** |
| Safe stop and logging procedure | **[UNFILLED: operation ID, target alias, timestamps, approved scope and redacted reason only]** |
| Safe artifact preservation / unsafe publication withholding | **[UNFILLED: incomplete status, controlled handling owner and restricted incident route]** |
| New observation record | **[UNFILLED: RO-OBS-### record location/reviewer; source/metadata anchors, confidence and runtime limitations]** |
| Denied/unexpected/drift review | **[UNFILLED: named reviewers, required evidence and disposition record]** |
| Permitted retry conditions/count/window | **[UNFILLED: same approved target/role/read scope only; no fallback/probe/scope expansion]** |
| Resume reviewer and approver | **[UNFILLED: named independent reviewer and accountable approver]** |
| Resume authorization record | **[UNFILLED: dated cause resolution, scope/window validity, exact byte hashes and revised approval if changed]** |

Do not copy secret error bodies, silently omit fields, switch target/role, broaden permissions, invoke application routines or run a behavioral test to fill gaps. Preserve safe artifacts with incomplete status and documented visibility limits. Observations do not rewrite/resolve original B/F/N records. Resume only after recorded independent review and named approval when authority, identity, scope, safety or provenance was affected.

## 11. Independent review, final human approval and later packet acceptance

| Review/approval field | Completion |
| --- | --- |
| Package binding review | **[UNFILLED: reviewer/date; verified supplied package hash and preserved reference]** |
| Completed annex/manifest/schedules byte review | **[UNFILLED: exact revisions/byte lengths/hashes and independent reviewer/date]** |
| Scope/method/getter/permission/handling review | **[UNFILLED: named reviewers, per-record ACCEPT/REJECT dispositions, exceptions and evidence hashes]** |
| Target/window/output/retention/contact review | **[UNFILLED: named responsible reviewers/owners, dates and disposition records]** |
| Conflict/independence check | **[UNFILLED: reviewer independence and permitted access confirmation]** |
| All unresolved fields/limitations reconciliation | **[UNFILLED: selected-item coverage, exclusions, residual gaps and approval impact]** |
| Final human decision | **[UNFILLED: APPROVE/REJECT by named accountable target approver; no decision currently exists]** |
| Decision date and validity | **[UNFILLED: date/time in both timezones, approved window/expiry and revocation controls]** |
| Detached approval/signature | **[UNFILLED: controlled human approval identity, record ID/hash/signature and exact approved byte set]** |
| Later E-by-E acceptance | **[UNFILLED: assigned independent reviewer/date/status, packet hashes, field/role/object coverage and disposition]** |

The exact human approval still required is a **dated, named, target-specific E23 read-only collection decision** binding the verified package SHA-256 above, the final completed annex/manifest and every exact method/permission/object/output/control schedule hash. It must explicitly approve selected E/OP components, target identities, existing permissions/access mechanism, suppliers/contact channels, window/expiry, handling/storage/retention and abort/resume rules after independent review. All required fields must first be concrete and reviewable. General “continue,” draft acknowledgment or design approval cannot substitute. No approval is requested or represented as granted by creating this draft.

A later reviewer may accept a supplied packet as ACCEPTED_INPUT within documented limits. That neither accepts owner decisions nor proves enforcement, applied bytes without independent provenance, provider certainty, clean data, gateway authentication, recovery/restoration or runtime outcomes.

## 12. Explicit exclusions

No target/Supabase connection or collection is authorized now. Even a future completed read-only approval must exclude:

- DDL/DML, database/provider mutations, privilege provisioning/escalation, role/claim switching, temporary/hostile object creation or helper installation.
- Application/Auth/user/role/invitation/outbox/audit/auth-session/password data reads, samples/counts, data conflict/reconciliation, full database/schema dumps, wildcard config/environment exports or unrestricted/raw logs.
- Application/provider/RPC/HTTP behavioral probes, application/extension routine calls, trigger/default-expression execution, auth helper calls, EXPLAIN/ANALYZE against application queries and behavioral privilege tests.
- Secret/config credential-store inspection, credentials/URLs in output, acquiring/hashing secret material, provider account/API/project access or unauthorized owner/support contact.
- Docker startup/inspection, engine readiness checks/replay/reset/restore, SQL/parser execution, builders/verifiers, application imports/version commands, tests, fixtures/adapters/concurrency/failure injection and every OP-R execution.
- Application/frontend/test/script/migration/report/candidate-history changes, fixes, executable successor/validation-copy authoring, implementation, deployment/install/push.
- Editing either original unconditional stop or the final ROLLBACK, overwriting existing artifacts or deleting/purging evidence under this authorization.

E21 data assessment and E24–E26 runtime components require distinct later authority. Original candidate remains review-only/stopped/rollback-only. B01–B07 and N01–N03 remain OPEN; T01–T14 remain NOT RUN. Conditional T13 is unpassed if deferred.

## 13. Final preflight checklist — PENDING / NOT PERFORMED

These unchecked fields specify future human checks, not current target checks. Pre-connection documentary checks precede any contact or connection; only approved minimal OP-C0 identity metadata may follow connection.

- [ ] **PF01 Authorization/bytes:** final named E23 decision covers verified package bytes, completed annex/manifest/schedules, selected E/OP set, exact method/tool hashes and valid window. Checker/date/record: **[UNFILLED]**.
- [ ] **PF02 Target alias:** approved controlled target/environment/deployment/database mapping; safe minimal C0 comparison and wrong-target/redirect abort defined. Checker/date/record: **[UNFILLED]**.
- [ ] **PF03 Collector identity:** every named collector/login/session role and secure access mechanism reconciled without secret output or role/claim change. Checker/date/record: **[UNFILLED]**.
- [ ] **PF04 Commands/methods:** exact safe read method bytes/getters/dependencies/tool versions independently reviewed; finite fields/filters/time/size/retry limits. Checker/date/record: **[UNFILLED]**.
- [ ] **PF05 Permissions/visibility:** existing minimum RP rights documented; missing visibility reported; no grants/escalation/owner-service fallback/application rows. Checker/date/record: **[UNFILLED]**.
- [ ] **PF06 Object/role boundary:** exact finite catalogs/columns/schemas/roles/signatures/bindings/dependencies and discovery/export separation approved; unexpected variants stop. Checker/date/record: **[UNFILLED]**.
- [ ] **PF07 Output paths:** exact new resolved output/restricted roots and filenames approved; no overwrite/symlink escape; bounds and controls ready. Checker/date/record: **[UNFILLED]**.
- [ ] **PF08 Secret/data handling:** H0 and per-item H profiles enforced before ordinary output, owner pre-screening ready, no secrets/application rows/raw logs/tracing. Checker/date/record: **[UNFILLED]**.
- [ ] **PF09 Provenance/time:** dual-timezone window/expiry and per-operation timestamps, revision/drift/consistency limits, supplier/method/role/hash/derivation records agreed. Checker/date/record: **[UNFILLED]**.
- [ ] **PF10 Abort conditions:** safe stop, redacted reasons, incomplete artifacts, reviewer dispositions and exact approved retry/resume controls ready. Checker/date/record: **[UNFILLED]**.
- [ ] **PF11 Evidence retention:** named owners approve duration/deadline/access/encryption/audit/legal hold/alias mapping; separate disposition only. Checker/date/record: **[UNFILLED]**.
- [ ] **PF12 Reviewer readiness:** named independent per-item reviewers have safe evidence access and understand coverage/redaction/runtime limits; supplier/contact/public-doc decisions explicit. Checker/date/record: **[UNFILLED]**.
- [ ] **PF13 Forbidden runtime boundary:** explicit exclusions acknowledged; E24–E26 requests only, all OP-R excluded, all T01–T14 NOT RUN, B01–B07/N01–N03 OPEN. Checker/date/record: **[UNFILLED]**.

Overall preflight disposition, named independent reviewer/date and detached approval link: **[UNFILLED: NOT PERFORMED; cannot be GO while required fields remain unresolved]**.

## Appendix A. Preserved source comparison identities — not target permission

Source authority: [preserved source evidence JSON](SECURITY_CONTAINMENT_SOURCE_EVIDENCE.json), `latest_source_routines` and `candidate_review_allowlists`; [routine inventory](SECURITY_CONTAINMENT_ROUTINE_INVENTORY.md); [blocker matrix](SECURITY_CONTAINMENT_BLOCKER_EVIDENCE_MATRIX.md). The JSON byte fingerprint measured in this task's local preservation inventory is `2aee432277ad5fb794fa179e22ea34148c7d8232277c47967d77861163c8f75a`. It identifies local source bytes, not deployed definitions or permission. No builder/verifier or SQL parser was run.

### A.1. Twenty-one source containment relation identities

- `public.admin_audit_log`.
- `public.users`.
- `public.user_roles`.
- `public.roles`.
- `public.role_permissions`.
- `public.permissions`.
- `public.institutions`.
- `public.user_permission_grants`.
- `public.students`.
- `public.student_attendance`.
- `public.student_results`.
- `public.student_result_items`.
- `public.student_notifications`.
- `public.departments`.
- `public.programs`.
- `public.courses`.
- `public.academic_years`.
- `public.semesters`.
- `public.program_courses`.
- `public.course_offerings`.
- `public.sections`.

These are metadata comparison seeds only. Detailed target fields, per-relation selection and discovery boundaries remain section 4 placeholders.

### A.2. Sixty-four latest source routine identities and parameter metadata

Parameter names/types/default-presence below are copied from existing JSON records. “yes” is the source `has_default` flag, not a default expression/value. Exact target defaults, argument modes/results and source-expression comparison fields must be supplied in the reviewed boundary; no SQL declarations are reproduced. Source lines locate declarations for later authorized text review. No source parameter metadata establishes target equivalence.

| Exact source signature | Parameters in source order: name/type/default present | Source file and declaration line |
| --- | --- | --- |
| `public.academic_master_tenant(text,uuid)` | `p_entity`: `text`, default no; `p_id`: `uuid`, default no | `supabase/migrations/20261016000000_academic_master_data_management.sql`:19 |
| `public.assert_faculty_academic_mutation(uuid,uuid,uuid,text)` | `p_actor`: `uuid`, default no; `p_tenant`: `uuid`, default no; `p_section`: `uuid`, default no; `p_permission`: `text`, default no | `supabase/migrations/20261013000000_faculty_tests_examination.sql`:66 |
| `public.assert_faculty_attendance_mutation(uuid,uuid,uuid)` | `p_actor`: `uuid`, default no; `p_tenant`: `uuid`, default no; `p_section`: `uuid`, default no | `supabase/migrations/20261013000000_faculty_tests_examination.sql`:104 |
| `public.assert_test_version(uuid,uuid,uuid,bigint)` | `p_actor`: `uuid`, default no; `p_tenant`: `uuid`, default no; `p_test`: `uuid`, default no; `p_version`: `bigint`, default no | `supabase/migrations/20261013000000_faculty_tests_examination.sql`:137 |
| `public.commit_faculty_attendance_import(uuid,uuid,uuid,timestamptz,jsonb)` | `p_actor`: `uuid`, default no; `p_tenant`: `uuid`, default no; `p_import_id`: `uuid`, default no; `p_expected_updated_at`: `timestamptz`, default no; `p_rows`: `jsonb`, default no | `supabase/migrations/20261012000000_faculty_attendance_workflow.sql`:211 |
| `public.commit_faculty_test_import(uuid,uuid,uuid,timestamptz,bigint)` | `p_actor`: `uuid`, default no; `p_tenant`: `uuid`, default no; `p_import`: `uuid`, default no; `p_updated_at`: `timestamptz`, default no; `p_version`: `bigint`, default no | `supabase/migrations/20261013000000_faculty_tests_examination.sql`:357 |
| `public.consume_auth_password_recovery_session(text,uuid,timestamptz)` | `p_session_fingerprint`: `text`, default no; `p_auth_user_id`: `uuid`, default no; `p_expires_at`: `timestamptz`, default no | `supabase/migrations/20261007000000_phase_9_auth_security_events.sql`:56 |
| `public.create_faculty_teaching_assignment(uuid,uuid,uuid,uuid,timestamptz,timestamptz,boolean)` | `p_actor_user_id`: `uuid`, default no; `p_institution_id`: `uuid`, default no; `p_faculty_user_id`: `uuid`, default no; `p_section_id`: `uuid`, default no; `p_start_at`: `timestamptz`, default no; `p_end_at`: `timestamptz`, default no; `p_is_active`: `boolean`, default no | `supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql`:315 |
| `public.faculty_assignment_touch()` | No source parameters | `supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql`:189 |
| `public.faculty_attendance_context_guard()` | No source parameters | `supabase/migrations/20261012000000_faculty_attendance_workflow.sql`:10 |
| `public.faculty_attendance_identity(uuid,text,text)` | `p_tenant`: `uuid`, default no; `p_register`: `text`, default no; `p_roll`: `text`, default no | `supabase/migrations/20261012000000_faculty_attendance_workflow.sql`:92 |
| `public.faculty_attendance_record_scope_guard()` | No source parameters | `supabase/migrations/20261010000000_phase_10_faculty_attendance_management.sql`:173 |
| `public.faculty_attendance_set_updated_at()` | No source parameters | `supabase/migrations/20261010000000_phase_10_faculty_attendance_management.sql`:91 |
| `public.faculty_responsibility_scope_guard()` | No source parameters | `supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql`:84 |
| `public.faculty_test_context_guard()` | No source parameters | `supabase/migrations/20261013000000_faculty_tests_examination.sql`:112 |
| `public.guard_test_import_workflow()` | No source parameters | `supabase/migrations/20261013000000_faculty_tests_examination.sql`:544 |
| `public.guard_workflow_result_delete()` | No source parameters | `supabase/migrations/20261013000000_faculty_tests_examination.sql`:129 |
| `public.manage_academic_master_record(uuid,uuid,text,uuid,jsonb)` | `p_actor_user_id`: `uuid`, default no; `p_institution_id`: `uuid`, default no; `p_entity`: `text`, default no; `p_record_id`: `uuid`, default no; `p_payload`: `jsonb`, default no | `supabase/migrations/20261016000000_academic_master_data_management.sql`:155 |
| `public.manage_faculty_responsibility(uuid,uuid,uuid,text,text,uuid,timestamptz,timestamptz,boolean,uuid,boolean,uuid)` | `p_actor_user_id`: `uuid`, default no; `p_institution_id`: `uuid`, default no; `p_faculty_user_id`: `uuid`, default no; `p_responsibility_code`: `text`, default no; `p_scope_type`: `text`, default no; `p_scope_id`: `uuid`, default no; `p_start_at`: `timestamptz`, default no; `p_end_at`: `timestamptz`, default no; `p_is_active`: `boolean`, default no; `p_responsibility_id`: `uuid`, default yes; `p_revoke`: `boolean`, default yes; `p_program_id`: `uuid`, default yes | `supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql`:195 |
| `public.manage_scoped_faculty_teaching_assignment(uuid,uuid,uuid,uuid,uuid,timestamptz,timestamptz,boolean,boolean)` | `p_actor_user_id`: `uuid`, default no; `p_institution_id`: `uuid`, default no; `p_assignment_id`: `uuid`, default no; `p_faculty_user_id`: `uuid`, default no; `p_section_id`: `uuid`, default no; `p_start_at`: `timestamptz`, default no; `p_end_at`: `timestamptz`, default no; `p_is_active`: `boolean`, default no; `p_revoke`: `boolean`, default yes | `supabase/migrations/20261014000000_scoped_faculty_teaching_assignment_management.sql`:26 |
| `public.mark_faculty_attendance(uuid,uuid,uuid,date,jsonb,text)` | `p_actor`: `uuid`, default no; `p_tenant`: `uuid`, default no; `p_section_id`: `uuid`, default no; `p_session_date`: `date`, default no; `p_attendance`: `jsonb`, default no; `p_notes`: `text`, default yes | `supabase/migrations/20261012000000_faculty_attendance_workflow.sql`:112 |
| `public.phase613_assert_child_organization()` | No source parameters | `supabase/migrations/20260915000000_phase_6_13_organization_institution_tenancy.sql`:720 |
| `public.phase613_assert_role_scope()` | No source parameters | `supabase/migrations/20260915000000_phase_6_13_organization_institution_tenancy.sql`:764 |
| `public.phase613_sync_institution_status()` | No source parameters | `supabase/migrations/20260915000000_phase_6_13_organization_institution_tenancy.sql`:305 |
| `public.phase712_assert_super_admin_scope()` | No source parameters | `supabase/migrations/20261001000000_phase_7_12_super_admin_identity_authorization.sql`:23 |
| `public.phase712_assign_super_admin(text,text)` | `p_target_email`: `text`, default no; `p_actor_identifier`: `text`, default no | `supabase/migrations/20261001000000_phase_7_12_super_admin_identity_authorization.sql`:116 |
| `public.phase712_revoke_super_admin(text,text)` | `p_target_email`: `text`, default no; `p_actor_identifier`: `text`, default no | `supabase/migrations/20261001000000_phase_7_12_super_admin_identity_authorization.sql`:188 |
| `public.phase714_assert_invitation_transition()` | No source parameters | `supabase/migrations/20261001020000_phase_7_14_super_admin_university_admin_lifecycle.sql`:116 |
| `public.phase715_assert_invitation_transition()` | No source parameters | `supabase/migrations/20261001030000_phase_7_15_invitation_delivery_email_verification.sql`:125 |
| `public.phase717_cancel_terminal_invitation_email()` | No source parameters | `supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql`:112 |
| `public.phase717_claim_email_outbox(integer,integer,integer)` | `p_batch_size`: `integer`, default no; `p_lock_seconds`: `integer`, default no; `p_retry_limit`: `integer`, default no | `supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql`:260 |
| `public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz)` | `p_outbox_id`: `uuid`, default no; `p_attempt_number`: `integer`, default no; `p_outcome`: `text`, default no; `p_provider_name`: `text`, default no; `p_provider_message_id`: `text`, default yes; `p_failure_category`: `text`, default yes; `p_available_at`: `timestamptz`, default yes | `supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql`:344 |
| `public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text)` | `p_institution_id`: `uuid`, default no; `p_email`: `text`, default no; `p_token_hash`: `text`, default no; `p_expires_at`: `timestamptz`, default no; `p_created_by`: `uuid`, default no; `p_protected_token`: `text`, default no | `supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql`:139 |
| `public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text,text)` | `p_institution_id`: `uuid`, default no; `p_email`: `text`, default no; `p_token_hash`: `text`, default no; `p_expires_at`: `timestamptz`, default no; `p_created_by`: `uuid`, default no; `p_protected_token`: `text`, default no; `p_role_name`: `text`, default no | `supabase/migrations/20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql`:20 |
| `public.phase717_resolve_email_outbox_context(uuid,text)` | `p_outbox_id`: `uuid`, default no; `p_token_hash`: `text`, default no | `supabase/migrations/20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql`:71 |
| `public.phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer)` | `p_invitation_id`: `uuid`, default no; `p_token_hash`: `text`, default no; `p_expires_at`: `timestamptz`, default no; `p_expected_updated_at`: `timestamptz`, default no; `p_protected_token`: `text`, default no; `p_lock_seconds`: `integer`, default no | `supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql`:180 |
| `public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz)` | `p_event_key`: `text`, default no; `p_replay_token_digest`: `text`, default no; `p_provider_event_id`: `text`, default no; `p_provider_message_id`: `text`, default no; `p_event_type`: `text`, default no; `p_event_timestamp`: `timestamptz`, default no | `supabase/migrations/20261002010000_phase_7_18_mailgun_webhook_reconciliation.sql`:55 |
| `public.phase723_approve_membership_and_grant_role(uuid,uuid,uuid,text)` | `p_request_id`: `uuid`, default no; `p_institution_id`: `uuid`, default no; `p_decided_by`: `uuid`, default no; `p_reason`: `text`, default no | `supabase/migrations/20261009000000_phase_7_24_immediate_staff_faculty_approval.sql`:5 |
| `public.phase723_approve_membership_with_invitation(uuid,uuid,uuid,text,text,timestamptz,text)` | `p_request_id`: `uuid`, default no; `p_institution_id`: `uuid`, default no; `p_decided_by`: `uuid`, default no; `p_reason`: `text`, default no; `p_token_hash`: `text`, default no; `p_expires_at`: `timestamptz`, default no; `p_protected_token`: `text`, default no | `supabase/migrations/20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql`:103 |
| `public.phase81_assert_institution_admin(uuid,uuid)` | `p_actor_user_id`: `uuid`, default no; `p_institution_id`: `uuid`, default no | `supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql`:132 |
| `public.phase81_assign_institution_role_audited(uuid,uuid,uuid,text)` | `p_actor_user_id`: `uuid`, default no; `p_target_user_id`: `uuid`, default no; `p_institution_id`: `uuid`, default no; `p_role_name`: `text`, default no | `supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql`:389 |
| `public.phase81_manage_faculty_section_assignment(uuid,uuid,uuid,uuid,boolean)` | `p_actor_user_id`: `uuid`, default no; `p_institution_id`: `uuid`, default no; `p_faculty_user_id`: `uuid`, default no; `p_section_id`: `uuid`, default no; `p_revoke`: `boolean`, default yes | `supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql`:285 |
| `public.phase81_manage_faculty_section_assignment_original(uuid,uuid,uuid,uuid,boolean)` | `p_actor_user_id`: `uuid`, default no; `p_institution_id`: `uuid`, default no; `p_faculty_user_id`: `uuid`, default no; `p_section_id`: `uuid`, default no; `p_revoke`: `boolean`, default yes | `supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql`:289 |
| `public.phase81_manage_staff_permission_grants(uuid,uuid,uuid,text[],boolean)` | `p_actor_user_id`: `uuid`, default no; `p_institution_id`: `uuid`, default no; `p_target_user_id`: `uuid`, default no; `p_permission_codes`: `text[]`, default no; `p_grant`: `boolean`, default no | `supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql`:167 |
| `public.phase81_prevent_audit_mutation()` | No source parameters | `supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql`:505 |
| `public.reconcile_faculty_attendance_roster_student()` | No source parameters | `supabase/migrations/20261012000000_faculty_attendance_workflow.sql`:289 |
| `public.reconcile_faculty_test_roster()` | No source parameters | `supabase/migrations/20261013000000_faculty_tests_examination.sql`:514 |
| `public.refresh_student_test_visibility()` | No source parameters | `supabase/migrations/20261013000000_faculty_tests_examination.sql`:529 |
| `public.review_faculty_attendance_import(uuid,uuid,uuid,jsonb,jsonb,timestamptz)` | `p_actor`: `uuid`, default no; `p_tenant`: `uuid`, default no; `p_import_id`: `uuid`, default no; `p_summary`: `jsonb`, default no; `p_rows`: `jsonb`, default no; `p_expected_updated_at`: `timestamptz`, default no | `supabase/migrations/20261012000000_faculty_attendance_workflow.sql`:162 |
| `public.review_faculty_test_import(uuid,uuid,uuid,timestamptz,jsonb,jsonb)` | `p_actor`: `uuid`, default no; `p_tenant`: `uuid`, default no; `p_import`: `uuid`, default no; `p_updated_at`: `timestamptz`, default no; `p_summary`: `jsonb`, default no; `p_rows`: `jsonb`, default no | `supabase/migrations/20261013000000_faculty_tests_examination.sql`:333 |
| `public.save_faculty_test(uuid,uuid,uuid,jsonb,uuid,bigint)` | `p_actor`: `uuid`, default no; `p_tenant`: `uuid`, default no; `p_section`: `uuid`, default no; `p_data`: `jsonb`, default no; `p_test`: `uuid`, default yes; `p_version`: `bigint`, default yes | `supabase/migrations/20261013000000_faculty_tests_examination.sql`:171 |
| `public.save_faculty_test_marks(uuid,uuid,uuid,bigint,jsonb,text)` | `p_actor`: `uuid`, default no; `p_tenant`: `uuid`, default no; `p_test`: `uuid`, default no; `p_version`: `bigint`, default no; `p_rows`: `jsonb`, default no; `p_reason`: `text`, default yes | `supabase/migrations/20261013000000_faculty_tests_examination.sql`:208 |
| `public.search_public_knowledge_chunks(extensions.vector,integer,uuid,uuid,text)` | `query_embedding`: `extensions.vector`, default no; `match_count`: `integer`, default no; `filter_institution_id`: `uuid`, default no; `filter_knowledge_source_id`: `uuid`, default yes; `filter_model_name`: `text`, default yes | `supabase/migrations/20260928010000_phase_7_4_public_rag_hardening.sql`:6 |
| `public.search_similar_chunks(extensions.vector,integer,uuid,uuid,uuid,uuid,uuid,text)` | `query_embedding`: `extensions.vector`, default no; `match_count`: `integer`, default no; `filter_institution_id`: `uuid`, default yes; `filter_knowledge_source_id`: `uuid`, default yes; `filter_document_id`: `uuid`, default yes; `filter_document_version_id`: `uuid`, default yes; `filter_processing_run_id`: `uuid`, default yes; `filter_model_name`: `text`, default yes | `supabase/migrations/20260905000002_phase_3_8_metadata_access_filtering.sql`:11 |
| `public.stage_faculty_attendance_import(uuid,uuid,uuid,uuid,text,text,text,boolean,jsonb,jsonb)` | `p_actor`: `uuid`, default no; `p_tenant`: `uuid`, default no; `p_section_id`: `uuid`, default no; `p_semester_id`: `uuid`, default no; `p_filename`: `text`, default no; `p_file_type`: `text`, default no; `p_strategy`: `text`, default no; `p_ai_confirmed`: `boolean`, default no; `p_summary`: `jsonb`, default no; `p_rows`: `jsonb`, default no | `supabase/migrations/20261012000000_faculty_attendance_workflow.sql`:186 |
| `public.stage_faculty_test_import(uuid,uuid,uuid,text,text,jsonb,jsonb)` | `p_actor`: `uuid`, default no; `p_tenant`: `uuid`, default no; `p_test`: `uuid`, default no; `p_filename`: `text`, default no; `p_strategy`: `text`, default no; `p_summary`: `jsonb`, default no; `p_rows`: `jsonb`, default no | `supabase/migrations/20261013000000_faculty_tests_examination.sql`:311 |
| `public.student_attendance_tenant_guard()` | No source parameters | `supabase/migrations/20260913000000_phase_6_7_attendance.sql`:82 |
| `public.student_results_tenant_guard()` | No source parameters | `supabase/migrations/20260913010000_phase_6_8_results.sql`:249 |
| `public.test_results_tenant_guard()` | No source parameters | `supabase/migrations/20261013000000_faculty_tests_examination.sql`:388 |
| `public.transition_faculty_test(uuid,uuid,uuid,bigint,text)` | `p_actor`: `uuid`, default no; `p_tenant`: `uuid`, default no; `p_test`: `uuid`, default no; `p_version`: `bigint`, default no; `p_action`: `text`, default no | `supabase/migrations/20261013000000_faculty_tests_examination.sql`:264 |
| `public.trg_student_notifications_tenant_guard()` | No source parameters | `supabase/migrations/20260914000000_phase_6_11_student_notifications.sql`:83 |
| `public.update_faculty_teaching_validity(uuid,uuid,uuid,timestamptz,timestamptz,boolean)` | `p_actor_user_id`: `uuid`, default no; `p_institution_id`: `uuid`, default no; `p_assignment_id`: `uuid`, default no; `p_start_at`: `timestamptz`, default no; `p_end_at`: `timestamptz`, default no; `p_is_active`: `boolean`, default no | `supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql`:249 |
| `public.validate_academic_master_record()` | No source parameters | `supabase/migrations/20261016000000_academic_master_data_management.sql`:38 |
| `public.validate_test_schedule(uuid,uuid,uuid,date,time,time)` | `p_tenant`: `uuid`, default no; `p_section`: `uuid`, default no; `p_id`: `uuid`, default no; `p_date`: `date`, default no; `p_start`: `time`, default no; `p_end`: `time`, default no | `supabase/migrations/20261013000000_faculty_tests_examination.sql`:151 |

### A.3. Sensitive, helper and protected source categories

The JSON field names include “approved”; that describes the preserved candidate review inventory, not approval for this collection. Category membership is copied exactly; overlaps do not widen target scope.

**Six sensitive source identities** (`approved_sensitive_signatures`):

- `public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text)`.
- `public.phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer)`.
- `public.phase717_claim_email_outbox(integer,integer,integer)`.
- `public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz)`.
- `public.phase717_resolve_email_outbox_context(uuid,text)`.
- `public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz)`.

**Client-helper source identities** (`approved_client_helper_signatures`):

- `public.faculty_assignment_touch()`.
- `public.faculty_attendance_context_guard()`.
- `public.faculty_attendance_record_scope_guard()`.
- `public.faculty_attendance_set_updated_at()`.
- `public.faculty_responsibility_scope_guard()`.
- `public.phase613_assert_child_organization()`.
- `public.phase613_assert_role_scope()`.
- `public.phase613_sync_institution_status()`.
- `public.phase712_assert_super_admin_scope()`.
- `public.phase714_assert_invitation_transition()`.
- `public.phase715_assert_invitation_transition()`.
- `public.phase717_cancel_terminal_invitation_email()`.
- `public.phase81_prevent_audit_mutation()`.
- `public.reconcile_faculty_attendance_roster_student()`.
- `public.student_attendance_tenant_guard()`.
- `public.student_results_tenant_guard()`.
- `public.test_results_tenant_guard()`.
- `public.trg_student_notifications_tenant_guard()`.

**Protected-service source identities** (`protected_service_signatures`):

- `public.academic_master_tenant(text,uuid)`.
- `public.commit_faculty_attendance_import(uuid,uuid,uuid,timestamptz,jsonb)`.
- `public.commit_faculty_test_import(uuid,uuid,uuid,timestamptz,bigint)`.
- `public.consume_auth_password_recovery_session(text,uuid,timestamptz)`.
- `public.create_faculty_teaching_assignment(uuid,uuid,uuid,uuid,timestamptz,timestamptz,boolean)`.
- `public.manage_academic_master_record(uuid,uuid,text,uuid,jsonb)`.
- `public.manage_faculty_responsibility(uuid,uuid,uuid,text,text,uuid,timestamptz,timestamptz,boolean,uuid,boolean,uuid)`.
- `public.manage_scoped_faculty_teaching_assignment(uuid,uuid,uuid,uuid,uuid,timestamptz,timestamptz,boolean,boolean)`.
- `public.mark_faculty_attendance(uuid,uuid,uuid,date,jsonb,text)`.
- `public.phase712_assign_super_admin(text,text)`.
- `public.phase712_revoke_super_admin(text,text)`.
- `public.phase723_approve_membership_and_grant_role(uuid,uuid,uuid,text)`.
- `public.phase723_approve_membership_with_invitation(uuid,uuid,uuid,text,text,timestamptz,text)`.
- `public.phase81_assert_institution_admin(uuid,uuid)`.
- `public.phase81_assign_institution_role_audited(uuid,uuid,uuid,text)`.
- `public.phase81_manage_faculty_section_assignment(uuid,uuid,uuid,uuid,boolean)`.
- `public.phase81_manage_staff_permission_grants(uuid,uuid,uuid,text[],boolean)`.
- `public.review_faculty_attendance_import(uuid,uuid,uuid,jsonb,jsonb,timestamptz)`.
- `public.review_faculty_test_import(uuid,uuid,uuid,timestamptz,jsonb,jsonb)`.
- `public.save_faculty_test(uuid,uuid,uuid,jsonb,uuid,bigint)`.
- `public.save_faculty_test_marks(uuid,uuid,uuid,bigint,jsonb,text)`.
- `public.search_public_knowledge_chunks(extensions.vector,integer,uuid,uuid,text)`.
- `public.search_similar_chunks(extensions.vector,integer,uuid,uuid,uuid,uuid,uuid,text)`.
- `public.stage_faculty_attendance_import(uuid,uuid,uuid,uuid,text,text,text,boolean,jsonb,jsonb)`.
- `public.stage_faculty_test_import(uuid,uuid,uuid,text,text,jsonb,jsonb)`.
- `public.transition_faculty_test(uuid,uuid,uuid,bigint,text)`.
- `public.update_faculty_teaching_validity(uuid,uuid,uuid,timestamptz,timestamptz,boolean)`.
- `public.validate_academic_master_record()`.

**Distinct seven-argument creator:** `public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text,text)`. Its ordered names/types/default-presence appear separately in A.2. It must not be conflated with the six-argument sensitive identity.

The preserved JSON records the following rename/drop history. History is a source comparison seed; a dropped source signature is not evidence of deployed absence, and the renamed original is not an approved direct entry.

| Source history | Exact identities | Source record |
| --- | --- | --- |
| Rename | `public.phase81_manage_faculty_section_assignment(uuid,uuid,uuid,uuid,boolean)` to `public.phase81_manage_faculty_section_assignment_original(uuid,uuid,uuid,uuid,boolean)` | `supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql`:281 |
| Drop | `public.search_similar_chunks(extensions.vector,integer,uuid,uuid,uuid,uuid,uuid,text)` | `supabase/migrations/20260905000001_phase_3_7_2_vector_similarity_search.sql`:5 |
| Drop | `public.search_similar_chunks(extensions.vector,integer)` | `supabase/migrations/20260905000002_phase_3_8_metadata_access_filtering.sql`:3 |
| Drop | `public.search_similar_chunks(extensions.vector,integer,uuid,uuid,uuid,uuid,uuid,text)` | `supabase/migrations/20260905000002_phase_3_8_metadata_access_filtering.sql`:7 |

The original candidate comment identifies proposed helper `security_containment_prevent_audit_truncate()`; that name is proposed source context only. Exact schema/signature/body identity, existence and INCLUDE/EXCLUDE decision for any proposed helper remain **[UNFILLED: target-specific reviewed boundary; no assumed deployed helper]**.

Exact target/private rename/drop/helper-history selection and additional finite dependency identities: **[UNFILLED: per-identity boundary record and reviewer decision]**. These source lists do not complete this target-specific prerequisite.

Source comparison role labels `postgres`, `anon`, `authenticated`, `service_role` and privilege grantee PUBLIC are contextual labels in the package/matrix. PUBLIC is not a login identity. Exact deployed roles/owners/creators/inherited/settable closure and permissions remain **[UNFILLED: section 4 boundary records]**.

### A.4. Seventeen retained source trigger bindings

The copied `tgtype` number is source inventory metadata; live event/enabled/internal/column/WHEN/argument/transition/definition fields remain uncollected.

| Source relation | Source trigger name | Exact bound source signature | Source tgtype |
| --- | --- | --- | --- |
| `public.student_attendance` | `trg_student_attendance_tenant_guard` | `public.student_attendance_tenant_guard()` | 23 |
| `public.student_results` | `trg_student_results_tenant_guard` | `public.student_results_tenant_guard()` | 23 |
| `public.student_notifications` | `trg_student_notifications_tenant_guard` | `public.trg_student_notifications_tenant_guard()` | 23 |
| `public.institutions` | `trg_phase613_institutions_status` | `public.phase613_sync_institution_status()` | 23 |
| `public.user_roles` | `trg_phase613_user_roles_scope` | `public.phase613_assert_role_scope()` | 23 |
| `public.user_roles` | `trg_phase712_super_admin_scope` | `public.phase712_assert_super_admin_scope()` | 23 |
| `public.admin_audit_log` | `phase81_admin_audit_append_only` | `public.phase81_prevent_audit_mutation()` | 27 |
| `public.students` | `trg_reconcile_faculty_attendance_roster` | `public.reconcile_faculty_attendance_roster_student()` | 21 |
| `public.students` | `test_student_visibility` | `public.refresh_student_test_visibility()` | 17 |
| `public.departments` | `academic_master_validate` | `public.validate_academic_master_record()` | 23 |
| `public.programs` | `academic_master_validate` | `public.validate_academic_master_record()` | 23 |
| `public.courses` | `academic_master_validate` | `public.validate_academic_master_record()` | 23 |
| `public.academic_years` | `academic_master_validate` | `public.validate_academic_master_record()` | 23 |
| `public.semesters` | `academic_master_validate` | `public.validate_academic_master_record()` | 23 |
| `public.program_courses` | `academic_master_validate` | `public.validate_academic_master_record()` | 23 |
| `public.course_offerings` | `academic_master_validate` | `public.validate_academic_master_record()` | 23 |
| `public.sections` | `academic_master_validate` | `public.validate_academic_master_record()` | 23 |

## 14. Local verification scope and limitations

This task creates only this separate Markdown annex. A pre-edit byte inventory covers **846 existing regular tracked/untracked non-ignored files listed by Git**, including existing user edits and the reference package. It is a new task-local inventory; the package's earlier 845-file claim is preserved as historical text. Ignored/unlisted files are outside this inventory and no blanket workspace attestation is made. Git reported unavailable access to its global ignore file; the scope is the actual returned Git file list. No secret stores or ignored secret files were inspected.

Only new-annex structural/whitespace/link/source-copy checks and preservation comparison of those inventoried files are in scope. Verification is documentation-only; it supplies no target/preflight/runtime evidence. The original candidate fingerprint in the inventory is `897a4c786adc487bce04462690f8a4bbcab215f2e3e53841f84a82f40c1a63c7`. Its [C002 unconditional stop](SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql#L28), [C003 unconditional stop](SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql#L31) and [final ROLLBACK](SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql#L443) are preserved source controls, not executed checks.

No owner contact, public retrieval, target/Supabase/provider call, secret inspection, Docker/engine readiness work, SQL/parser execution, application import/test, builder/verifier run, implementation, deployment or push occurred. Final local check outcomes and the annex's measured hash are reported outside this document after verification to avoid self-hashing.

**NO-GO for collection: E23 remains PENDING / NOT APPROVED; required identities, selections, boundaries, methods, permissions, window, storage, suppliers and acceptance fields are UNFILLED. GO only for continued offline draft completion/review. B01–B07 and N01–N03 OPEN; T01–T14 NOT RUN.**

