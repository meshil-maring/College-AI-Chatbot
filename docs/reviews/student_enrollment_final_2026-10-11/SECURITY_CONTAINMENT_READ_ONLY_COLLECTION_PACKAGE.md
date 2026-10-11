# Security containment: read-only evidence-collection package for review

2026-10-11, Asia/Calcutta. **NON-EXECUTABLE REQUEST SPECIFICATION. Documentation/local source inspection only. No target collection authorized or performed. B01–B07 OPEN; N01–N03 OPEN; T01–T14 NOT RUN.**

**GO for offline package review. NO-GO for target collection until the target-specific authorization in section 10 is complete.** This package specifies E01–E26 without supplying SQL, scripts, connection commands, credentials or provider calls. It does not implement a collector, obtain owner acceptance, authorize implementation or close a blocker. Successful future read-only collection would provide inputs for decisions and later validation, not runtime security acceptance.

Authority and definitions: [owner-decision/evidence-readiness report](SECURITY_CONTAINMENT_OWNER_DECISIONS_AND_EVIDENCE_READINESS.md), [B05 remediation design](SECURITY_CONTAINMENT_B05_REMEDIATION_DESIGN.md), [blocker matrix](SECURITY_CONTAINMENT_BLOCKER_EVIDENCE_MATRIX.md), [routine inventory](SECURITY_CONTAINMENT_ROUTINE_INVENTORY.md), [source evidence](SECURITY_CONTAINMENT_SOURCE_EVIDENCE.json), [independent review](SECURITY_CONTAINMENT_INDEPENDENT_REVIEW.md), and [original T definitions](SECURITY_CONTAINMENT_CHANGE_PLAN.md#L53). Collector D01–D04/K01–K10 and readiness V01–V08 retain the matrix's namespaces; design scenarios D01–D28 are different identifiers. B05-F01–F11 remain distinct from findings in other reports. No additional security finding is asserted here.

## 1. Collection manifest and status contract

Proposed package ID: `SC-RO-2026-10-11-01`. Revision: `review-draft-1`. These identify this request, not an approved run. This document is the only artifact created by this task. All proposed output names below are specifications; directories, item bundles, authorizations and attestations have **not** been created or collected.

The future manifest `00_manifest.json` must contain the following fields. Placeholders are deliberately unbound; each required field must be filled and independently approved before target collection. A blank field, assumed default or invented owner is a NO-GO.

| Manifest field | Concrete requirement / present state |
| --- | --- |
| Package/version/hash | Package ID and revision above; externally record SHA-256 of these final document bytes. Package self-hash is not embedded. Any revised package/method needs its own hash and approval. |
| Collection identity | Fresh collection ID, named collector(s), organizational roles, database login alias and effective privileges; **UNASSIGNED**. Do not publish credentials or personal contact details. |
| Target identity | Approved target alias, environment class, database/service/deployment identifiers under controlled alias mapping, expected engine/app/gateway identities and deployment revision; **UNBOUND**. Host/project addresses and connection material stay outside this package/repository. |
| Authorization | E23 approval record ID/hash, named approver, permitted E items/operation IDs/object boundaries, access method/tool versions and exact reviewed method/statement hashes; **PENDING**. |
| Time and consistency | Approved start/end in Asia/Calcutta and UTC, per-operation start/end and target metadata snapshot/revision markers; **UNBOUND**. No snapshot consistency is claimed across independent exports. |
| Scope | E01–E26 mapping in section 4; catalog object scope in section 2; no application rows. R components are requests only and excluded from collection execution. |
| Permissions | Existing least-privilege read profiles in section 3, permission-verification record and visibility limits. No privilege provisioning, role changes or privilege escalation within this package. |
| Methods | Operation IDs in section 2 with approved fields, object filters, caller, method hash, time/size limits and redaction path. No arbitrary SQL/RPC/shell capability follows from this document. |
| Outputs | Proposed repository root: `docs/evidence/security_containment_read_only/<collection_id>/<target_alias>/`; exact resolved root/filenames must be approved and new, not overwrite existing artifacts. **NOT CREATED**. |
| Restricted storage | Approved access-controlled location for any authorized non-secret originals and alias mapping, permitted readers, encryption/access logging and retention owner; **UNBOUND**. No raw sensitive originals in Git/chat. |
| Retention | Owner-selected duration/legal-hold policy, review deadline, access/export policy and separately approved disposition procedure; **UNBOUND**. No deletion authority is granted here. |
| Provenance | Reference hashes below, source/deployed revisions, tool/method hashes, per-file byte length/SHA-256, supplier/collector/time/target and derivation links. |
| Coverage and review | E-by-E status, missing/denied fields, object/role coverage, unexpected variants, redaction limits, reviewers and acceptance record hashes. No implied pass from an empty export. |

Reference byte fingerprints captured from preserved local files for this package:

| Reference | SHA-256 |
| --- | --- |
| [Owner decisions](SECURITY_CONTAINMENT_OWNER_DECISIONS_AND_EVIDENCE_READINESS.md) | `a733cf6a92f5d00a41123606941bebca454194d89ada239e8651ffc89fc3ec30` |
| [B05 design](SECURITY_CONTAINMENT_B05_REMEDIATION_DESIGN.md) | `a5846632243ee52eb28b8d02c34a9d5530a54376619f59ebefa32612a3900c27` |
| [Blocker matrix](SECURITY_CONTAINMENT_BLOCKER_EVIDENCE_MATRIX.md) | `fab90b17a703c75ec17f0017bb8164183020107babcec12edc6a6275373cc1be` |
| [Source evidence](SECURITY_CONTAINMENT_SOURCE_EVIDENCE.json) | `2aee432277ad5fb794fa179e22ea34148c7d8232277c47967d77861163c8f75a` |
| [Routine inventory](SECURITY_CONTAINMENT_ROUTINE_INVENTORY.md) | `2f1b2eb1dc7e09711a22a177d2ce259a9175189b371a4a8c29e6f1cd6c43f1cf` |
| [Change plan](SECURITY_CONTAINMENT_CHANGE_PLAN.md) | `073543f966608d247e1d09427bc78cea8d8dfdb800bf846b7c5ba4ca234f8fe8` |
| [Original candidate](SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql) | `897a4c786adc487bce04462690f8a4bbcab215f2e3e53841f84a82f40c1a63c7` |
| [Candidate results](SECURITY_CONTAINMENT_CANDIDATE_RESULTS.json) | `42e4678c417b0b0c73fc85107323802a3746b3ce134f4a5fb937cbe0d2e2ca5a` |

Future status vocabulary: `REQUESTED` → `SUPPLIED_UNREVIEWED` → `ACCEPTED_INPUT`, or `PARTIAL`, `DENIED_VISIBILITY`, `REDACTED_LIMITATION`, `UNEXPECTED_VARIANT`, `REJECTED`, `DEFERRED_VALIDATION`. `ACCEPTED_INPUT` means a reviewer accepted the packet's stated scope/provenance; it does not mean an OD decision was accepted, a T test passed or a blocker closed. **All new target/provider/consumer/attestation requests are presently REQUESTED / NOT COLLECTED; all R components are DEFERRED_VALIDATION / NOT RUN.** Existing S references are existing local material, not newly collected target evidence.

## 2. Strict scope and permitted operation specifications

No DDL/DML or database mutations; no application/provider/RPC/HTTP behavioral probes; no provider mutations; no application-row exports or row counts; no deployment/push. Do not execute the containment candidate, migrations, reset scripts, validators, application imports or tests. Do not start/inspect Docker, check engine readiness, run EXPLAIN/ANALYZE against application queries, switch roles, set request claims, create temporary objects or install a helper. No user/role/invitation/outbox/audit/auth-session/password records may be read as data. No full database/schema dump, unrestricted log export or wildcard configuration/environment dump is permitted.

Read-only means no intentional application/database state change. Future metadata reads may create normal connection/access logs; this is not an assurance of zero physical side effects. If the only available method invokes application routines, traverses user data or requires mutation/privilege changes, stop and request a distinct scope rather than treating it as metadata collection.

Object boundaries proposed for review:

- **21 public containment relations, metadata only:** `admin_audit_log`, `users`, `user_roles`, `roles`, `role_permissions`, `permissions`, `institutions`, `user_permission_grants`, `students`, `student_attendance`, `student_results`, `student_result_items`, `student_notifications`, `departments`, `programs`, `courses`, `academic_years`, `semesters`, `program_courses`, `course_offerings`, `sections`. Source boundary: [candidate:68](SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql#L68).
- **Routine/binding scope:** the 64 latest source identities, exact six sensitive identities, distinct seven-argument creator, protected/private/helper identities and 17 retained trigger bindings enumerated in `latest_source_routines` and `candidate_review_allowlists` of the preserved source JSON. Copy their exact signature/name/type/default and binding lists into the future approved manifest; this document does not turn source identities into deployed facts. Inspect all same-name overload metadata within the approved schemas; unknown variants are findings for review, not callable entries.
- **Additional dependency metadata:** institution/super-admin invitations, membership requests, delivery/recovery tables, adjacent ledgers and teaching/test/roster/knowledge dependencies identified in the preserved source inventory/design. Their exact relation/routine identities and authorized catalog fields must be listed in the target authorization before detailed export. No automatic access to their rows. New acceptance-operation tables/routines are proposed contracts only, not assumed existing objects.
- **Creator/schema/bridge metadata:** approved creators plus directly referenced owner/inherited/settable role closure, affected schema/extension identities, defaults, relation/routine dependencies, views/rules/partitions. Approved initial metadata discovery may list identity/owner/edge records within the approved boundary. Discovering a new schema, role or bridge outside it does not authorize exporting its body/configuration; record the unexpected identity and pause that item for scope review.
- **Migration ledger exception, metadata only:** if separately allowed, read only `version` and `name` fields of `supabase_migrations.schema_migrations` as deployment metadata. No `statements` payload, other ledger columns, user rows or executable migration content from the target. If the deployment has a different ledger shape, stop that item; do not query guessed columns. Applied bytes require independently supplied deployment provenance.

The operation register specifies allowed *kinds of reads* for later review. It contains no executable commands/queries. Every target operation needs a reviewed exact read method, approved function/getter allowlist if any, caller and bounded output. A SELECT wrapper is not enough: it must not call an application/extension function with side effects. No statement is approved for execution now.

| Operation ID / route | Permitted information / method boundary | Prohibited substitution |
| --- | --- | --- |
| **OP-S SOURCE** | Read allowlisted non-secret local source/reports using `rg`, file reads, Git read/status/diff/file-list operations and byte hashing. Read files as text/bytes; no app imports, builders/verifiers or SQL/parser execution. | `.env`, credential/config secret files, shell profiles, secret stores, dependency/install execution, application invocation. |
| **OP-C0 TARGET** | Approved connection/engine/session identity metadata and version/extension identity only, bounded timestamps; K01/K02. Method reads collector identity, not production JWT/claim values. | Auth routine calls, claim emulation, role switching, test authentication or API request. |
| **OP-C1 TARGET** | K02/K03/K08 role attributes/memberships, creator/default ACL, schema/database/language/extension ACL and lookup metadata. Catalog field allowlist, no password catalogs. | `pg_authid` or credential attributes; granting rights; executing SET ROLE; querying live request text. |
| **OP-C2 TARGET** | K04/K05 relation/column/constraint/index/policy/default metadata for approved identities, no relation scans. | Reading/counting application or Auth rows, materialized-view contents, sampling or data reconciliation. |
| **OP-C3 TARGET** | K06/K07/K09 routine/trigger/view/rule definitions/attributes and dependencies, metadata only after handling review. Approved built-in definition getters only. | Executing functions/triggers/RPCs/default expressions; broad schema dump; capturing embedded secrets. |
| **OP-C4 TARGET** | Approved ledger version/name metadata described above and engine deployment identifiers. | Treating ledger versions or reconstructed definitions as an applied-byte attestation. |
| **OP-V TARGET** | Owner-supplied sanitized deployment manifests, artifact/version/creator records and approved non-secret config fields; read existing controlled records. | Running application/SDK version commands, inspecting environment secrets, changing config or deployment. |
| **OP-X TARGET/OWNER** | Owner-authorized consumer inventory and pre-sanitized aggregate usage metadata over an agreed window; no raw logs. | Searching payloads/tokens/URLs/emails/query text, sending test requests or treating no observed use as no consumer. |
| **OP-P PUBLIC/OWNER** | Later review of version-applicable public official documentation, or owner-supplied document extracts with URL/version/date and bounded quotations. | Provider account/API calls, login, project inspection, custom support contact or runtime guarantees inferred from marketing/docs. |
| **OP-O OWNER** | After contact authorization, obtain dated policy/consumer/permission attestations from named accountable owners through the approved channel. | Current owner contact, signatures fabricated by a collector, or collection permission treated as policy acceptance. |
| **OP-A OFFLINE** | Review supplied sanitized packets and source; derive dependency/effective-access comparison and requests/decision templates without calls. | Calling privilege-sensitive/application routines to prove a denial or committing fixes. |
| **OP-R EXCLUDED** | Specify future V01–V08/D01–D28/T01–T14 scope and missing results only. | Any disposable engine startup, readiness check, SQL, test, adapter or failure injection. Separate later authorization is required. |

## 3. Minimum permissions, handling profiles and output contract

These profiles are minimum information access proposals, not grants. E entries reference them explicitly. If visibility is insufficient, report `DENIED_VISIBILITY`; do not add grants, ask for superuser/BYPASSRLS or silently reuse a service/owner credential. All target credentials must be supplied through an approved existing secure mechanism, never inspected or copied by this documentation task.

| Permission profile | Proposed collector / minimum read capability |
| --- | --- |
| **RP-S** | Source analyst: local read access to allowlisted repository source/reports and Git metadata; create only approved new sanitized output files later. No secret-file read or code execution. |
| **RP-C** | Authorized DB metadata collector: existing non-owner/non-superuser/non-BYPASSRLS read identity, permitted connection and visibility of the exact approved system catalogs/fields and safe built-in metadata getters. No application table SELECT, DML/DDL/role-management or application EXECUTE required. Existing wider credentials are not the default; a separate review must justify any exception and controls. |
| **RP-L** | Provenance collector: RP-C plus existing read of only approved ledger version/name fields. If unavailable, obtain a provider-owner sanitized metadata export instead; no grants under this package. |
| **RP-V** | Deployment/provenance owner: read permission on existing non-secret build/release/creator/configuration records; supplies sanitized exports to analyst. No deploy permission or secret/env access is required for collection. |
| **RP-X** | Integration/worker/operator owner: read approved consumer registry/schedule/release records and pre-sanitized aggregate activity report; no raw operational logs, user tables or mailbox-wide access. |
| **RP-P** | Documentation analyst: unauthenticated public official documentation read, or read owner-supplied authorized versioned documents. No provider account permission. |
| **RP-O** | Named accountable owner and reviewer: access only to applicable sanitized decision/consumer/evidence records; authority to attest own area through an explicitly authorized channel. Collector does not inherit that authority. |
| **RP-A** | Independent source/security reviewer: read sanitized approved packets and reference bytes, plus restricted non-secret originals only where separately permitted; no target execution. |
| **RP-R** | **No runtime permission in this package.** Future validation owner can supply a design/approval-request record; engine/provider/test permissions remain absent. |

Catalog scope for RP-C includes only approved fields from role/member/default/schema/database/language/extension, relation/attribute/type/constraint/index/policy, procedure/trigger/dependency/inheritance/view/rule metadata (matrix K01–K10). Exact catalog identities/column lists and permitted built-in getters must be finalized in the later method annex for the evidenced engine version. Password catalogs, connection settings containing secrets, user-value statistics, active-query text and unbounded monitoring views are excluded. Offline ACL analysis must preserve NULL-versus-explicit ACL distinctions, ownership, role inheritance/SET paths, grantors/options and version limits; it is an assessment, not a behavioral result.

**H0 applies to every item:** no keys, passwords, password digests/fingerprints, bearer/JWT/signature values, raw/digested invitation or resume capabilities, protected/ciphertext token payloads, provider response bodies, emails, student/audit/application rows or connection strings in output, filenames, logs or chat. Role/object identities needed for comparison are controlled metadata; operational person/service identifiers use stable aliases with mapping outside the repository. Preserve relevant type/structure/privilege distinctions; record redaction limitations instead of declaring unseen equality.

| Additional handling profile | Exact rule |
| --- | --- |
| **H-S SOURCE** | Copy/hash only allowlisted non-secret source/reference bytes; cite file/line/revision. A source hash proves those bytes, not deployed identity or behavior. |
| **H-C CATALOG** | Allowlisted structural metadata only. Routine bodies, defaults, policy/view/rule expressions may embed sensitive literals: owner pre-screening and approved sanitization must precede publication/transmission to the collector's ordinary output. Stop the affected item if safe handling cannot be assured. Do not inspect/dump secrets to redact them later. |
| **H-V VERSION** | Publish artifact/config names, mode/type, revisions and non-secret selected values only; replace URLs/accounts/operational paths with approved aliases. No full environment/config/history dump. |
| **H-X CONSUMER** | Registry/aggregate fields only: caller alias/type/version/command/grant/use window/count if owner-approved, not event payloads/user IDs/tokens/query text/addresses. Preserve sampling, retention and seasonal coverage limits. |
| **H-P DOCUMENT** | Official URL/title/version/retrieval date and short compliant supporting excerpt or paraphrase; store support/no-guarantee statements and version limits. No account/project/API data. |
| **H-O OWNER** | Named approval identity retained in restricted approval record; repository-facing role/stable alias, date, scope, option, exceptions and acceptance reference. No personal contact details or copied correspondence. |

**A0 output/provenance contract, mandatory for every E item:** each proposed `E##_*.md` packet is accompanied by an entry in `00_manifest.json` and `01_hashes.json`; supplemental metadata is `E##_metadata.json` and safely handled definition derivatives are listed by exact object identity. Record byte length/SHA-256 of each file, source/target alias/revision, supplier/collector/time in UTC and Asia/Calcutta, method/tool versions/hashes, permissions and visibility, object/role coverage, field status and reviewer/date/disposition. For a supplied source/definition original, use its original-byte SHA-256 only when the authorized supplier attests how it was obtained; store a separate derivative hash and redaction/normalization log. Secret material must not be acquired or hashed as evidence. If an original cannot be safely supplied/reviewed, record that limitation; an unreviewed hash does not establish definition equivalence.

Proposed common artifacts: `00_manifest.json`, `01_hashes.json`, `02_redaction_and_coverage.md`, `03_review_dispositions.md`, and the 26 named packets below. All remain **NOT CREATED**. Manifests/signatures receive detached hashes or signatures in a controlled approval record to avoid circular self-hashing. Source/deployed-definition normalization comparisons retain separate raw/normalized hashes and documented rules; do not erase meaningful body/ACL differences. File hashes authenticate bytes only; named supplier/reviewer records supply provenance and acceptance.

## 4. E01–E26 manifest index

Classes: **S** local source; **C** live catalog metadata; **V** deployed-version/provenance; **X** external consumers; **P** provider documentation; **O** owner attestation; **R** future disposable validation. Every item has existing S references; listed classes describe its requested additional components. **OFFLINE** permits preparation/review of local source or already supplied sanitized material; **TARGET** requires explicit target-specific approval; **OWNER** requires explicit contact/attestation authority; **PUBLIC** is future public-document review without account access; **R excluded** means no testing through this package.

Blocker mappings include the primary evidence family and related uses; B07/E23–E26 and A0 govern every target packet. OD mappings include the originating register's dependencies and additional direct consumers of that E item. T mappings are prerequisites/coverage only, never test results; T13 is conditional and unpassed if deferred.

| E / requested classes | Preparation versus acquisition / operations | B mappings | OD mappings | Applicable T cases | Proposed packet |
| --- | --- | --- | --- | --- | --- |
| **E01 C/V/O** | OFFLINE source trace; TARGET C0/C1/V; OWNER O | B01/B04/B05/B07 | OD01/OD05/OD06/OD10/OD17/OD20 | T01/T04–T09/T11/T12/T14 | `E01_request_modes.md` |
| **E02 V/O/R** | OFFLINE source map; TARGET V; OWNER O; R excluded | B01/B04/B05/B07 | OD01/OD02/OD07/OD11/OD12 | T04/T09/T10/T11/T12/T14 | `E02_principal_identity.md` |
| **E03 C/O** | OFFLINE path map; TARGET C1/C2/C3; OWNER O | B01/B02/B04/B05/B07 | OD06/OD17/OD18 | T01–T04/T06/T09–T13 | `E03_effective_access.md` |
| **E04 X/V/O** | OFFLINE caller list; TARGET X/V; OWNER O | B02/B04/B06/B07 | OD06/OD09/OD10/OD15/OD17 | T04–T12/T14 | `E04_consumers.md` |
| **E05 S/O** | OFFLINE proposed matrix; OWNER O | B02/B03/B05/B07 | OD06/OD09/OD17 | T04–T09/T11/T12 | `E05_explicit_grants.md` |
| **E06 C/V/R** | OFFLINE signature map; TARGET C3/V; R excluded | B02/B04/B05/B07 | OD06/OD09/OD17/OD18 | T05–T08/T12/T13 | `E06_dependencies_overloads.md` |
| **E07 C/V** | OFFLINE creator statements; TARGET C1/V | B03/B04/B07 | OD17/OD20 | T01/T05–T07/T09/T10 | `E07_creators_defaults.md` |
| **E08 X/O** | OFFLINE impact template; TARGET X; OWNER O | B03/B04/B06/B07 | OD17/OD19 | T05/T07/T12/T13 | `E08_global_impact.md` |
| **E09 O/R** | OFFLINE variant contract; OWNER O; R excluded | B02/B03/B07 | OD06/OD17/OD20 | T05–T07/T12 | `E09_creator_acceptance.md` |
| **E10 C/V** | OFFLINE source chain; TARGET C0/C4/V | B04/B01/B03/B07 | OD03/OD12/OD18/OD20 | T01–T14 | `E10_versions_applied_bytes.md` |
| **E11 C** | OFFLINE structural reference; TARGET C2 | B04/B01/B05/B06/B07 | OD02/OD03/OD08/OD14/OD16/OD18 | T01–T04/T07–T12/T14 | `E11_relations_policies.md` |
| **E12 C/V** | OFFLINE body/binding reference; TARGET C3/V | B04/B02/B05/B07 | OD06/OD07/OD09–OD12/OD14/OD15/OD18/OD19 | T01–T14 | `E12_definitions_bridges.md` |
| **E13 S/O/R** | OFFLINE all-writer oracle; OWNER O; R excluded | B05/B01/B02/B04/B06/B07 | OD03–OD08/OD12/OD18 | T04/T07–T09/T11/T12/T14 | `E13_ordering_contract.md` |
| **E14 C/S/O/R** | OFFLINE lookup assessment; TARGET C1/C3; OWNER O; R excluded | B05/B01/B02/B04/B07 | OD06/OD07/OD17/OD19 | T05–T07/T09–T14 | `E14_lookup_authority.md` |
| **E15 X/V/O** | OFFLINE missing-caller list; TARGET X/V; OWNER O | B05/B02/B04/B06/B07 | OD09–OD11/OD15/OD17/OD18 | T04/T06–T12/T14 | `E15_missing_consumers.md` |
| **E16 P/V/O** | OFFLINE questions; PUBLIC P; TARGET V; OWNER O | B05/B01/B04/B06/B07 | OD01/OD02/OD05/OD08/OD12/OD13 | T04/T11/T12/T14 | `E16_provider_semantics.md` |
| **E17 V/O/R** | OFFLINE identity/safe-adapter contract; TARGET V; OWNER O; R excluded | B05/B01/B04/B06/B07 | OD02/OD12/OD13/OD20 | T04/T09/T11/T12/T14 | `E17_identity_reconciliation.md` |
| **E18 C/X/O** | OFFLINE audit design; TARGET C2/C3/X; OWNER O | B05/B01/B02/B04/B06/B07 | OD11/OD14/OD16/OD19 | T01–T05/T07/T08/T11/T12/T14 | `E18_audit_contract.md` |
| **E19 O/R** | OFFLINE recovery oracle; OWNER O; R excluded | B06/B01/B05/B07 | OD04/OD05/OD07/OD08/OD10/OD12–OD14 | T04/T09/T11/T12/T14 | `E19_recovery_revocation.md` |
| **E20 X/V/O** | OFFLINE delivery/cutover contract; TARGET X/V; OWNER O | B06/B01/B02/B04/B05/B07 | OD04/OD09/OD15/OD18 | T04/T06–T08/T11/T12/T14 | `E20_delivery_cutover.md` |
| **E21 C/V/O** | OFFLINE non-destructive methodology; TARGET C2/V; OWNER O | B06/B04/B05/B07 | OD02/OD03/OD08/OD11/OD18 | T01–T12/T14; T13 conditional | `E21_data_rollout_plan.md` |
| **E22 C/X/O/R** | OFFLINE reset/retention analysis; TARGET C2/C3/X; OWNER O; R excluded | B06/B01/B04/B05/B07 | OD14/OD16/OD20 | T01–T04/T09/T12/T14 | `E22_retention_maintenance.md` |
| **E23 O** | OFFLINE authorization template; OWNER approval required first | B07; collection prerequisites for B01–B06 | OD17/OD20 | T01–T14 prerequisites only | `E23_collection_authorization.md` |
| **E24 S/O** | OFFLINE future review scope; OWNER O; execution excluded | B07/B02/B04/B05 | OD18–OD20 | T01–T14 prerequisites only | `E24_successor_review_request.md` |
| **E25 S/O/R** | OFFLINE environment/bootstrap requirements; OWNER O; R excluded | B07/B01/B03/B04 | OD20 | T01–T14 prerequisites only | `E25_runner_bootstrap_request.md` |
| **E26 S/O/R** | OFFLINE fixture/oracle requests; OWNER O; R excluded | B07 and all B01–B06 validation dependencies | OD01–OD20 as scoped | T01–T14 NOT RUN | `E26_validation_request.md` |

## 5. Item-by-item acquisition and review contracts

Each subsection supplies the exact payload, need, collector/permission, handling and acceptance beyond A0. No request is fulfilled by this package. RP/H profiles are binding constraints for that item, not optional shorthand. Supplied policies may be reviewed as input even if unsigned; only a named accountable owner's dated acceptance can establish an attestation. References to existing source JSON/matrix fields are exact reference schemas, not a database parser or complete deployed call graph.

### E01 — actual server, worker and operator modes

- **Required / why:** collector D01/D02/K02/K10; per accepted backend/worker/operator route: credential mode/type and header names only, gateway role transition contract, authenticated human versus service/system boundary, session/current collector role, role attributes/inherited/settable closure and RLS/BYPASSRLS/owner implications. State capability separation and residual shared-secret trust. This grounds service assertions without assuming that `service_role` text proves a human actor.
- **Collector / permissions:** authentication/deployment owner RP-V/RP-O plus authorized catalog collector RP-C using C0/C1. Deployment owner supplies sanitized existing gateway/configuration records; do not generate requests, call `auth.role()`/`auth.uid()` or inspect real JWTs to fill a gap.
- **Handling / output:** H0/H-C/H-V/H-O; `E01_request_modes.md` plus approved role metadata, A0 and collector D01/D02 references. Claims are a documented mapping, not copied token values.
- **Reviewer / acceptance:** independent authentication/security and DB reviewers; every command family identifies trusted caller/mode, source/deployment revision and role evidence, with unknown gateway behavior marked. Metadata alone does not prove real request authentication; T11/T12 remain NOT RUN.

### E02 — verified principal and canonical identity

- **Required / why:** collector D03; per command, verified JWT subject-to-application/Auth-ID mapping algorithm, tenant/actor construction, delegated/system/token modalities, recipient normalization/verification/changed-email/ambiguous-mapping policy and protected parameter merge rules. Include N02 missing actor and N03 approval pathways. Prevent equating different UUID domains or accepting supplied identity as proof.
- **Collector / permissions:** backend/identity owner RP-S/RP-V/RP-O; existing sanitized deployed routing/build and policy records only. No read of users, Auth tables or sessions; R requires a separate authorization.
- **Handling / output:** H0/H-S/H-V/H-O; `E02_principal_identity.md`, source file/line and deployed revision references with synthetic example labels only; A0. No real identity samples.
- **Reviewer / acceptance:** authentication/authorization reviewer verifies complete per-entry provenance/policy and code/version linkage; actual mapping correctness, wrong-session denial and recipient ownership await T11/T12, not declared proven.

### E03 — effective authority and direct writers

- **Required / why:** K02/K04/K05/K09/K10; approved roles and inheritance/SET closure, relation/column/function/view grants/grantors/options, owners/RLS/FORCE/policies, direct invitation/authority write paths, bridge security modes and potential operation writer exposure. Preserve raw ACL absence versus default interpretation. Determine where command logic can be bypassed.
- **Collector / permissions:** RP-C C1/C2/C3 for system metadata only; independent RP-A offline reachability assessment; authorization owner RP-O. No permission probes, table reads, role switching or granting rights.
- **Handling / output:** H0/H-C/H-O; `E03_effective_access.md`, exact object/role metadata and derivation rules/coverage, A0. Pseudonymize operational account roles while preserving permission edges.
- **Reviewer / acceptance:** DB/security reviewers accept a complete metadata-based access assessment for the approved boundary, identifying unresolved dynamic/mode paths. No denied/allowed behavior or blanket absence of privileged bridges is established by this item.

### E04 — legitimate command, worker and operator consumers

- **Required / why:** collector D04; consumer alias/owner/type, deployed version, DB/gateway/table/column/view/RPC entry, exact signature/named/default keys, return/retry/idempotency/trigger/default/invoker needs, expected grants, seasonality and last verified window. Include bootstrap, seven/six creator and private-helper consumers. Supports compatibility decisions and explicit grants.
- **Collector / permissions:** integration/worker/operator owners RP-X/RP-V/RP-O; source analyst RP-S. Owner may supply approved pre-sanitized aggregates; no raw traffic/log/database access or owner contact now.
- **Handling / output:** H0/H-S/H-X/H-V/H-O; `E04_consumers.md` and coverage/window attestation, A0. No payloads, recipient names/emails or raw query/URL text.
- **Reviewer / acceptance:** integration/security reviewers reconcile source and attested external callers, unresolved owners and seasonal limits. Absence in source or aggregates cannot certify no consumer; unknowns prevent accepted withdrawal.

### E05 — explicit grant and private-helper contract

- **Required / why:** exact schema/signature/named/type/default/return/mode/owner, intended creator and caller class; direct versus owner-nested/invoker/trigger/default-expression execution, per-grantee privileges and reason, creation-time grants and no PUBLIC window. Distinguish bootstrap/acceptance/private writer; justify preserving service defaults pending dependency acceptance.
- **Collector / permissions:** SQL/backend/worker owners RP-S/RP-O; reviewer RP-A. Read source declarations/ACL history and E03/E04/E06; no live privilege changes or executable SQL authoring.
- **Handling / output:** H0/H-S/H-O; `E05_explicit_grants.md`, signed proposed grant matrix referencing exact source and packet hashes, A0.
- **Reviewer / acceptance:** SQL/security reviewers accept legitimate direct entries and required nested/trigger use, while owner-only helpers have no unreviewed direct service path. This is a policy contract, not evidence that target grants or trigger creation work.

### E06 — overloads, bindings and gateway routing

- **Required / why:** K06/K07/K09/K10; exact routine identities/OIDs/prokind, names/modes/types/defaults/return/owner/ACL, private rename history and nested dependencies; trigger bindings/creation needs; gateway exposed schemas/version/cache routing configuration. Compare six-key platform and mandatory seventh-role creator identities without invoking either.
- **Collector / permissions:** DB collector RP-C C3 and gateway/deployment owner RP-V; RP-A source comparison. Configuration records must be existing sanitized exports; no RPC or cache reload.
- **Handling / output:** H0/H-C/H-V; `E06_dependencies_overloads.md` with signature/binding/cache manifest and difference list, A0.
- **Reviewer / acceptance:** database/gateway reviewers accept exact identity/default/binding comparison and known routing configuration. Actual gateway overload selection, owner-nested calls and trigger execution await T06/T07. Unknown overloads remain unexpected variants.

### E07 — creators and global/schema defaults

- **Required / why:** K02/K03; creator role/OID, namespace/global scope, object category, raw/exploded ACL/grantors/options, membership/inherited/SET closure; deployment creation-session/SET ROLE records for migrations/extensions. Owner statements alone cannot identify creation sessions or inherited default impact.
- **Collector / permissions:** RP-C C1 and migration/extension provenance owner RP-V; source analyst RP-S. Read only selected historical role/method identifiers from sanitized records; no replay/SET ROLE.
- **Handling / output:** H0/H-C/H-V/H-S; `E07_creators_defaults.md` and provenance references distinguishing current owner, original creator, source assertion and independently evidenced session; A0.
- **Reviewer / acceptance:** DB/migration reviewers accept verified versus unknown creator/default variants and comparison to eight source default statements. Fresh object behavior is not collected; T05 remains NOT RUN.

### E08 — global default business and extension impact

- **Required / why:** schema/extension/routine/procedure/aggregate consumer owner, creator linkage, required future EXECUTE expectations, affected deployments and cross-schema business effects of global postgres PUBLIC default change. Inventory uncertainty and unsupported seasonal windows must remain visible.
- **Collector / permissions:** platform/extension/integration owners RP-X/RP-O; use approved E07 metadata and RP-S source, not an automatically expanded catalog scrape.
- **Handling / output:** H0/H-X/H-O/H-S; `E08_global_impact.md`, dated affected-consumer/scope attestations and references to E07; A0.
- **Reviewer / acceptance:** platform/security and affected consumer reviewers accept scope/effects or explicitly reject/limit proposed change. No assumed absence of extensions or unknown creators; T05/T12 behavior awaits separate validation.

### E09 — accepted creator/default variants

- **Required / why:** reconcile E05/E07/E08 into a per-creator/per-schema/object-category grant policy, allowed owner/helper/trigger use, existing ACL preservation, exceptions and denial impacts. Retained service-default policy must be explicit; metadata cannot supply owner acceptance.
- **Collector / permissions:** DB/security accountable owners RP-O; RP-A offline review of supplied packets; RP-R no runtime access.
- **Handling / output:** H0/H-O; `E09_creator_acceptance.md` with selected/rejected variants, approval identity/date/scope/evidence hashes and future T05–T07 oracle, A0.
- **Reviewer / acceptance:** independent DB/security reviewer validates attestation authority and coverage without treating creation/execution as tested. Unsigned variants remain proposed; no default repair occurs.

### E10 — deployed versions and independent applied-byte provenance

- **Required / why:** collector D01/K01; aliased target/engine/database identity and version, extensions/schema/version, app/frontend/worker revision, gateway/PostgREST/Supabase/Python SDK versions, deployment records; exact ledger version/name metadata and independent per-migration applied-source fingerprints/release/source records for the 39-file reference chain. This binds source review to a time-bound target, not merely ledger names.
- **Collector / permissions:** DB collector RP-C C0 and RP-L C4 only if existing column-level read is approved; deployment/provenance owner RP-V supplies controlled artifact records. No install/import/version execution or statement-body ledger export.
- **Handling / output:** H0/H-C/H-V/H-S; `E10_versions_applied_bytes.md`, `E10_metadata.json`, 39-reference comparison and independent supplier provenance, A0. Target connections/URLs remain aliased.
- **Reviewer / acceptance:** deployment/migration and independent DB reviewers require demonstrated applied-byte linkage and record every unknown/difference. A source hash, ledger entry or reconstructed body alone cannot meet that criterion; no target version is assumed PG17.

### E11 — relation, policy and structural definitions

- **Required / why:** K04/K05 for approved 21 tables and explicitly approved dependencies: namespace/name/OID/kind/owner/partition/inheritance/RLS/FORCE/table ACL, live column name/type/order/nullability/generated/identity/default/ACL; full policies/roles/commands/USING/WITH CHECK/permissive flag; PK/check/FK/unique/exclusion/index definitions/keys/actions/validation/deferrability. Include invitation lifecycle/index and audit restrictions. Shape counts alone cannot verify equivalence.
- **Collector / permissions:** RP-C C2 on catalogs, no application table reads even for empty/sample/count checks. Definition handling pre-screen under H-C; no schema/data dump.
- **Handling / output:** H0/H-C; `E11_relations_policies.md`, approved object metadata/definition derivatives and per-field diff/visibility, A0.
- **Reviewer / acceptance:** DB/security reviewer accepts complete approved object/column/policy/constraint coverage against reference definitions. Missing visibility is unknown, not object absence; actual rows/conflicts and enforcement remain untested.

### E12 — full routines, triggers and bridge definitions

- **Required / why:** K06/K07/K09/K10; exact routines/prokind/args/defaults/results/owner/language/definer/config/path/strict/volatility/parallel/leakproof/ACL/full bodies; triggers event mask/internal/enabled/column/WHEN/args/transition tables/bound function; relevant view/materialized-view/rule security/owner/ACL/definition and dependency/partition edges; gateway/app version/routing linkage. Resolve replaced/renamed/overloaded definitions and 17 retained bindings without executing them.
- **Collector / permissions:** RP-C C3, owner-supplied pre-screened non-secret definitions, RP-V routing records and RP-A comparison. Catalog dependencies alone do not resolve dynamic/textual lookups.
- **Handling / output:** H0/H-C/H-V; `E12_definitions_bridges.md`, approved per-object definition derivatives, original/derivative hash provenance where safely available and unexpected variants, A0.
- **Reviewer / acceptance:** independent routine/database/security reviewers accept exact full-definition/binding comparison or enumerate each blocked comparison. A matching signature/hash from an unreviewed original or redacted unknown fragment does not establish body equivalence or reachability behavior.

### E13 — token/reservation/all-writer ordering contract

- **Required / why:** digest/generation, invitation state/unique operation/key/principal binding; all begin/finalize/rotate/cancel/expire/issue writers, account and absent-role serialization, deterministic lock order; DB-time post-lock decision, deadlines, revocation/cancel policies and same-operation retry/unknown rules. Include separate N01 expiry and D01–D28 oracles. Needed to choose P01 safely rather than infer it from metadata.
- **Collector / permissions:** routine/security owner RP-S/RP-O and reviewer RP-A; use E01/E10–E12, no locking, timing or race probes; RP-R excluded.
- **Handling / output:** H0/H-S/H-O; `E13_ordering_contract.md`, non-executable state/lock/transition and failure oracle with dated selected policy, A0. No token/digest/password samples.
- **Reviewer / acceptance:** independent security/database reviewer accepts complete all-writer policy and evidence limitations. Barrier/expiry/provider-count outcomes remain future T04/T11/T14, NOT RUN.

### E14 — lookup safety and authority boundaries

- **Required / why:** per definer/invoker/trigger/helper relation/type/operator/function/cast/dynamic lookup, qualification/path/owner/language, schema USAGE/CREATE and database TEMP rights, extension ownership, role/bridge access, supplied-actor versus authenticated-principal evidence. Include the 44 source definers and relevant invoker triggers, private/bootstrap boundaries and proposed hardening order; preserve structural versus human authorization distinction.
- **Collector / permissions:** RP-C C1/C3 plus RP-S/RP-A assessment and security/database owners RP-O. No hostile object creation, temp schema use, role switching or GUC spoofing.
- **Handling / output:** H0/H-C/H-S/H-O; `E14_lookup_authority.md`, qualified lookup/authority matrix with E03/E12 references, unresolved dynamic lookups and scope decisions, A0.
- **Reviewer / acceptance:** independent DB/security reviewer accepts bounded threat/lookup assessment and declares conditional hardening scope. Schema metadata alone cannot prove exploitability or harmless lookup behavior; T13 is NOT RUN and unpassed if deferred.

### E15 — latent, broken and missing consumers

- **Required / why:** owner-attested current/external consumers for seven-argument legacy approval/creator, legacy tenancy decision service, controlled bootstrap/revoke, production worker/scheduler and N02 student approval; version/entry/grant/expected behavior/seasonal window and migration/outage acceptance. Source caller absence and caught errors cannot settle live reachability/compatibility.
- **Collector / permissions:** academic/integration/operator/worker owners RP-X/RP-V/RP-O; RP-S source traces. No test calls, scheduler startup or owner contact through this task.
- **Handling / output:** H0/H-X/H-V/H-O/H-S; `E15_missing_consumers.md`, per-consumer attestation and unresolved owner/window list, A0.
- **Reviewer / acceptance:** onboarding/academic/integration/security reviewers reconcile E04 and legitimate student/immediate/legacy/bootstrap contracts. Unknowns remain blockers to withdrawal; N02 remains separate/open pending approved fix/test.

### E16 — documented provider/SDK semantics

- **Required / why:** version-specific official documents for Auth create/update/email-confirm/recovery; timeout/retry configuration, documented idempotency/correlation and response certainty, email uniqueness/ownership, session invalidation/recovery and absent guarantees. Separate documented semantics from actual deployed config and owner-selected unknown-outcome policy; do not promise password readback or exactly-once mutation.
- **Collector / permissions:** documentation analyst RP-P OP-P; identity deployment owner RP-V and policy owner RP-O. Public document retrieval can be reviewed separately without a target connection; it has not occurred here. No provider API/project/support calls.
- **Handling / output:** H0/H-P/H-V/H-O; `E16_provider_semantics.md` with URL/title/document version/retrieval date, deployed SDK/config provenance and claim-to-section/limitations table, A0. Use compliant short excerpts/paraphrases only.
- **Reviewer / acceptance:** identity/security reviewer accepts applicability and documented/no-guarantee distinctions. Docs/config do not establish observed provider outcomes; N03 confirmation and compatibility password uncertainty await separate safe validation.

### E17 — canonical ownership, baseline access and safe reconciliation

- **Required / why:** accepted canonical Auth/application binding and concurrency/changed-email policy, baseline privileges/sign-in behavior of prepared users, no existing/shared identity deletion, conditions/proof for any operation-created cleanup; prospective synthetic provider adapter and independent outcome evidence. Needed for new-account failure/recovery and N03 readiness decisions.
- **Collector / permissions:** identity/security owners RP-V/RP-O with RP-S source; RP-R future design only. No existing-user/password/session reads, provider account listing or identity creation/deletion.
- **Handling / output:** H0/H-V/H-O/H-S; `E17_identity_reconciliation.md`, baseline-policy/deployed config references and safe-adapter request, A0; synthetic scenario identifiers only.
- **Reviewer / acceptance:** identity/security reviewer accepts ownership/reconciliation policy and clearly unresolved baseline/runtime evidence. This package cannot certify existing data uniqueness, cleanup safety or provider behavior.

### E18 — audit provenance and mandatory completion

- **Required / why:** main/adjacent/operation ledger structural fields/FKs/CHECK vocabularies/owners/ACLs/guards; initiator versus subject/system/issuer modalities, truthful pre-identity events/verification, role-change versus completion, atomic state/audit/dispatch and downstream dedupe/retention consumers. Preserve B05-F09 history and F10 boundaries; never fabricate historical success.
- **Collector / permissions:** RP-C C2/C3 structural metadata, audit/routine owners RP-O and downstream consumer owners RP-X; RP-S/RP-A review. No audit/event/application row exports.
- **Handling / output:** H0/H-C/H-X/H-O/H-S; `E18_audit_contract.md`, ledger structure and required-event transaction/dispatch policy references, A0. No provider bodies or capability digests in examples.
- **Reviewer / acceptance:** audit/security/database reviewers accept attribution/atomicity/retention scope or enumerate gaps. Metadata does not prove event completeness, immutability enforcement or downstream exactly-once delivery; T01–T04/T14 remain NOT RUN.

### E19 — recovery, cancellation and revocation policy

- **Required / why:** matrix M06 and OD04/OD05/OD07/OD08; deadline/cancel/revocation both-ordering outcomes, bound resume/status authentication, account-wide priority with recovery and invite kinds, support queue/SLA/escalation and definitive/known/unknown result distinctions. Lease expiry is not no-effect evidence; no token reopening or old-password restoration.
- **Collector / permissions:** operations/security/identity/routine owners RP-O; RP-S/RP-A offline oracle; RP-R excluded. No real operation/status or recovery-session inspection.
- **Handling / output:** H0/H-O/H-S; `E19_recovery_revocation.md`, dated policy and owner responsibilities with non-executable failure/race oracles, A0.
- **Reviewer / acceptance:** security/operations reviewer accepts accountable policy, not race outcomes or recoverability. Unknown policy stays unresolved; T11/T14 behavior and provider confirmation are separate evidence.

### E20 — delivery, worker and denial/cutover effects

- **Required / why:** real worker/scheduler ownership/deployed version/entry/mode/provider contract; generation/lease/attempt settlement/resend/accepting/callback rules, current consumer grants, expected denial/customer effects and late delivery/recovery communications policy. No in-flight send can be assumed retracted by cancellation.
- **Collector / permissions:** messaging/integration/operations owners RP-X/RP-V/RP-O; RP-S source. Read existing sanitized schedule/config/aggregate records only; no worker run, webhook request, resend or provider call.
- **Handling / output:** H0/H-X/H-V/H-O/H-S; `E20_delivery_cutover.md`, consumer/job/version inventory, sampling limits and accepted cutover effects, A0. No message content, delivery payloads, recipient addresses or protected tokens.
- **Reviewer / acceptance:** messaging/security/integration reviewer accepts configured runner/consumer provenance and proposed business policy. Actual worker/HMAC/replay/lease behavior awaits T08/T12/T14.

### E21 — existing-data and rollout methodology

- **Required / why:** non-destructive preflight/backfill/conflict/quarantine method, initial generation compatibility, accepted partial-row handling, unresolved accepting uniqueness/account conflicts, all-writer routing/version/drain/hold and rollback limits. Metadata informs feasibility; it cannot prove absence of duplicates or completeness of historical accepted workflows.
- **Collector / permissions:** DB/rollout owners RP-C C2 for already approved structural fields and RP-V/RP-O for deployment/rollout policy; RP-S source. No row counts, duplicate queries, accepted-row samples or reconciliation execution.
- **Handling / output:** H0/H-C/H-V/H-O/H-S; `E21_data_rollout_plan.md`, structural/version prerequisites and separately scoped future data-assessment request, A0. No target-row evidence is requested here.
- **Reviewer / acceptance:** database/rollout/security reviewers accept methodology, transition responsibilities and explicit unresolved data-state facts. No safe backfill, actual conflict resolution or mixed-version behavior is established.

### E22 — reset, retention, lifecycle and restoration

- **Required / why:** M01–M04/M05; source reset-versus-TRUNCATE-guard incompatibility, live guard/FK/ledger structural definitions and external maintenance dependencies; signed reset unavailability, retention/access/archive/legal-hold, deactivation/reference and backup/restore/target-verification policies. Do not weaken guards or infer operational deletion rights.
- **Collector / permissions:** maintenance/audit owners RP-O/RP-X and RP-C C2/C3 metadata; RP-S source, RP-R restoration testing excluded. Backup metadata policies only, no backup contents or restore commands.
- **Handling / output:** H0/H-C/H-X/H-O/H-S; `E22_retention_maintenance.md`, owner policy/dependency and existing sanitized backup manifest references, A0. Aliased storage targets only.
- **Reviewer / acceptance:** audit/maintenance/database reviewer accepts business/retention impact and known metadata. Operational retention compliance, restoration integrity and actual lifecycle deletion constraints require separate evidence/testing, not a metadata pass.

### E23 — collection authorization and manifest

- **Required / why:** all manifest fields, approved operation/method/object/read-permission/output/retention boundaries, named collectors/reviewers/approver, package/annex hashes and abort controls. This prerequisite is not an evidence request that can be fulfilled after connection.
- **Collector / permissions:** designated approver and authorized scope/retention owners RP-O; independent RP-A reviewer; offline RP-S draft preparation. No target permission until the record is signed/accepted.
- **Handling / output:** H0/H-O/H-S; `E23_collection_authorization.md` plus detached approval hash and completed manifest/method annex, A0. Connection/secrets remain outside review artifacts.
- **Reviewer / acceptance:** independent scope/security reviewer checks section 7 and section 10 field completeness, exact bytes and denial scope. Pending/blank/expired authorization fails preflight; approving collection supplies neither implementation nor test authority.

### E24 — exact successor and validation-copy review request

- **Required / why:** V01/V02; prospective authoring scope, command/API/access/rollback changes and original-versus-successor/validation-copy boundaries. If separately authored artifacts already exist later, inventory their exact hashes, owners and independent review status; do not infer authoring permission from this package. Original candidate remains stopped/rollback-only.
- **Collector / permissions:** designated approver/independent reviewer RP-S/RP-O/RP-A reading existing non-secret approved artifacts only; no SQL/app/test authoring or execution under this task/package.
- **Handling / output:** H0/H-S/H-O; `E24_successor_review_request.md`, available-versus-missing artifact/hash/approval list and preserved original hash, A0. Never copy a stopped original into an executable file as collection.
- **Reviewer / acceptance:** independent migration/security reviewer accepts a request or records actual separately authorized review; missing successor/diff/transaction approvals remain pending. Collection cannot supply executable validation-copy or install acceptance.

### E25 — dedicated environment and bootstrap review request

- **Required / why:** V03–V05; proposed dedicated purpose, image/engine identity, run ownership/storage/network/cleanup criteria, complete 39-hash replay/auth/roles/extensions/ledger bootstrap and provenance. Source helper currently excludes security-containment purpose; raw replay alone is not ledger/applied-byte evidence.
- **Collector / permissions:** validation/environment owner RP-S/RP-O and independent RP-A reviewer; RP-R excludes Docker, engine checks/replay/cleanup. Read existing source/design records only.
- **Handling / output:** H0/H-S/H-O; `E25_runner_bootstrap_request.md`, requirements/gaps and available separately authorized artifact hashes; A0. No local infrastructure/credential enumeration.
- **Reviewer / acceptance:** independent runner/database reviewer accepts a concrete design/request or records missing prerequisites. No actual engine ownership/readiness/bootstrap/cleanup result can be established through this collection package.

### E26 — native role, fixture, adapter and validation request

- **Required / why:** V06–V08; planned caller/owner/native/inherited role and claim evidence, populated synthetic two-tenant fixtures, D01–D28 plus original T01–T14 oracles, domain/HTTP/provider adapters, both-ordering barriers/failure points, independent state/outcome evidence and cleanup. Distinguish simulated GUC claims from real deployed credential mapping.
- **Collector / permissions:** validation/security/domain/identity owners RP-S/RP-O/RP-A; **RP-R supplies no testing permission**. Design/approval request only; no fixture insertion or execution.
- **Handling / output:** H0/H-S/H-O; `E26_validation_request.md` with scope/oracle/available artifact hashes/missing-results matrix, A0. Synthetic identifiers, no passwords/tokens or real identities.
- **Reviewer / acceptance:** independent validation/security reviewer accepts a future bounded request, not outcomes. All T01–T14 and provider/HTTP/concurrency results remain **NOT RUN**; T13 stays conditional and unpassed if excluded.

## 6. Offline preparation versus target/owner acquisition

Offline work can organize existing source references, exact object/signature/binding allowlists, reference hashes, decision templates, comparisons of already supplied sanitized records, redaction/output schemas and proposed T/D oracles. This task prepares those requirements in this document only. Offline draft/source checks are not target collection or proof of deployed behavior. Public official-document review can later be performed without target access, but this task did not retrieve or call providers.

Target-dependent work includes C0–C4, deployed release/configuration/creator/provenance records, external usage metadata and environment-linked owner attestations. Target-specific E23 authorization must define which of these is permitted and who may supply it. Owner contact needs an explicitly approved recipient/channel/scope; no automatic email/chat messages arise from the package. Existing source-only authority cannot authorize remote account/app access.

E24–E26 can yield requests/available-artifact inventories only. Their R portions are outside collection, regardless of collector permissions. Actual data-conflict assessment for E21, identity/account/provider state, restoration, native-role/HTTP/gateway/concurrency and failure-injection evidence are separate later scopes. Approval of catalog SELECT methods does not authorize application SELECT, function invocation or tests.

## 7. Mandatory preflight and abort checklist (proposed, NOT RUN)

Preflight is a future review/permission check, not permission to run an engine or behavioral probe. All boxes are **PENDING / NOT PERFORMED**. Pre-connection checks use approved documents; only the explicitly approved minimal C0 identity metadata may follow connection. If that cannot verify target/caller without a prohibited operation, stop. Owner-supplied approved exports are an alternative to granting the collector additional rights.

- [ ] **PF01 Authorization/bytes:** named approver has approved the completed E23 record, package SHA-256, selected E/OP IDs, exact method/statement hashes, tool versions and start/end window. Check approval validity before any contact/connection or target read; no implicit inherited task authorization.
- [ ] **PF02 Target alias:** controlled target mapping matches approved environment/deployment/database alias; after permitted C0 verify identity/version markers against that record. Mismatch, unexpected production target or redirect aborts target collection; do not retry another host/project.
- [ ] **PF03 Collector identity:** named individual/service login matches authorization and existing secure access mechanism; metadata identifies actual collector/session role. Record minimum role/visibility without exposing passwords/tokens or changing session role/claims.
- [ ] **PF04 Commands/methods:** independent reviewer has checked each exact permitted read method, getter dependency and output filter for non-mutation/no side-effect functions. No arbitrary SELECT, psql file execution, application RPC, probes or debug flags; no connection instructions are supplied here.
- [ ] **PF05 Permissions/visibility:** existing RP profiles suffice for approved fields. No new grant, superuser/BYPASSRLS escalation, owner credential substitution or application-row access. Missing rights produce explicit partial/denied evidence; broad credential exceptions require prior separate review.
- [ ] **PF06 Object/role boundary:** approved 21-table/routine/binding/dependency and creator/schema/role-closure annex lists exact identities/fields. Limit discovery metadata and detailed export; new variants are logged and reviewed before scope expansion.
- [ ] **PF07 Output paths:** exact resolved new repository/output and restricted-storage roots match approval; no overwrite/symlink escape or existing user artifact replacement. Set bounded file/size/time limits; permit writes only to approved evidence artifacts, never target state.
- [ ] **PF08 Secret/data handling:** H0/profiles and owner pre-screened metadata/document exports exclude secrets/application rows before ordinary output; disable token/connection/payload tracing. No local `.env`/credential store/raw log reads. Unsafe definitions or logging paths stop the item before export.
- [ ] **PF09 Provenance/time:** supplier/deployed revision/method/tool/role/permission/time metadata and original/derivative hash handling are agreed. Define snapshot consistency limits/change indicators; target revision changes invalidate comparisons until reviewed. Never assert a multi-operation atomic snapshot without evidence.
- [ ] **PF10 Abort conditions:** explicit response to wrong target/role, denied visibility, unexpected variants, sensitive material, unapproved method, schema/version drift, timeout/size overrun, output/retention failure or revoked/expired authorization. Stop affected collection; do not silently omit fields, broaden permissions, invoke routines or execute retries outside approved bounds.
- [ ] **PF11 Evidence retention:** named retention/data owner approves duration/access/encryption/audit/legal hold, restricted originals/alias mapping and derivative sharing. Unknown policy blocks acquisition/storage; this package grants no purge/destruction permission.
- [ ] **PF12 Reviewer readiness:** named independent reviewers can read permitted non-secret evidence, understand redaction limits and issue A0 dispositions; collector may not self-certify a blocked equality comparison or policy acceptance.
- [ ] **PF13 Forbidden runtime boundary:** acknowledge no DDL/DML, provider/account calls, application-row exports, Docker, SQL tests, R execution, app/migration/test changes, deployment or push. E24–E26 requests remain pending and all T cases NOT RUN.

On an abort, record operation ID/target alias/time/approved scope and a redacted reason, not secret error bodies. Preserve already safe artifacts with incomplete status; withhold unsafe outputs from publication through the approved data-handling process. Any authorized retry must remain the same approved read scope and window, not switch target/role or fill gaps through a behavior test. Resume only after documented reviewer/approver disposition when the cause affects authority, identity, scope, safety or provenance. New security observations receive separate `RO-OBS-###` entries with metadata/source anchors, confidence and runtime limitations; do not rewrite or resolve original B/F/N records.

## 8. Facts collection cannot establish and future validation gaps

| Gap | What metadata/docs can establish | Additional requirement / applicable tests |
| --- | --- | --- |
| Actual authenticated principal/service gateway behavior | Configured modes, source mapping and role/ACL intent | Accountable deployment/authentication attestation plus separately approved real gateway/native-role/HTTP evidence. E01/E02/E26; T04/T08/T11/T12. No auth probes in collection. |
| Enforcement versus declared ACL/guard/lookup state | Grants/policies/definitions and bounded offline reachability | Owner policy plus denied/allowed populated fixtures, owner/inherited/private/trigger paths and lookup adversarial tests. E03/E06/E09/E14/E26; T01–T07/T09/T10/T13. T13 deferred remains unpassed. |
| N01 locked time, F01/F02 reservation and cancellation races | Current backend-time source and proposed locks/contracts | Accepted OD03–OD05 policy and deterministic DB-time/expiry/concurrency/provider-admission evidence. E13/E19/E26; T04/T08/T11/T12/T14. N01 remains OPEN. |
| N02 student approval/role/audit outcome | Missing actor and staff/faculty-only wrapper source | OD11 separately approved student successor/compatibility and real role/audit/lifecycle evidence. E15/E18/E26; T04/T09/T10/T11/T12/T14. No widening of invitation roles; N02 OPEN. |
| N03 confirmation and immediate approval readiness | Before-RPC provider call source, configured docs/versions | OD12 policy plus safe separately approved request/reject/role/audit/provider-failure evidence. E16–E19/E26; T04/T11/T12/T14. N03 OPEN, separate from B05-F10. |
| Provider exactly-once/uncertain credentials/session effects | Version-applicable documented guarantees or lack thereof | Identity-owner accepted unknown policy plus provider-supported outcome evidence/failure adapters under later approval. E16/E17/E19/E26; T04/T11/T12/T14. No password readback assumption. |
| No external/seasonal consumer | Known source/registry and approved aggregate use window | Named consumer/owner attestations, coverage/seasonality limitations and accepted outage/cutover; absence of use is not proof. E04/E08/E15/E20; T05–T08/T12/T14 later. |
| Applied migration file bytes | Ledger versions/names and current definitions | Independent controlled deployment/applied-source provenance from E10; ledger/body reconstruction alone insufficient. T01–T14 inherit this provenance requirement. |
| Clean existing data/history/identity ownership | Schema/uniqueness and non-destructive method proposal | Separately scoped data-state/reconciliation authority outside this no-row-export package; no duplicates/partial-acceptance absence claimed. E17/E21; T07/T09/T11/T12/T14 later. |
| Recovery, retention and restoration outcomes | M01–M06 policy, metadata constraints and source reset conflict | Named operational/audit acceptance and separately authorized fixtures/restoration/retention evidence. E18/E19/E22/E25/E26; T01–T04/T12/T14. No reset or deletion permitted. |
| Safe engine/bootstrap/full regression | V01–V08 requirements and source helper/replay incompatibilities | Separate authoring/exact-byte review, engine/storage/roles/ledger/adapters and runtime approval. E24–E26; **T01–T14 NOT RUN**. No Docker or readiness checks through collection. |

## 9. Completion matrix and preservation verification

The following is a **conditional projection**, not collected evidence. “After successful collection” assumes all approved packets were supplied and independently accepted within their stated limits. Unsupplied policy/consumer records remain missing even if catalog export succeeds. Every blocker remains OPEN until its entire independent acceptance criteria are met in a later scope.

| Blocker | Inputs potentially available after approved read-only collection | Still unresolved / NO-GO after metadata collection alone | Present status |
| --- | --- | --- | --- |
| **B01** | E01–E03/E10–E12 actual role/ACL/config/deployment and documented principal mapping; accepted owner records if supplied | Authentic deployed gateway/human binding, native service/RLS behavior and untrusted bypass denial need scoped validation; shared-secret residual trust/policy must be accepted. T01/T04/T09/T11/T12. | OPEN; target evidence NOT COLLECTED |
| **B02** | E04–E06/E12 known consumer/signature/default/binding/grant contracts and target metadata | Complete consumer acceptance, private/invoker/trigger/gateway execution and future explicit grant behavior untested. T05–T08/T12. Unknown external entries still block withdrawal. | OPEN; target/owner evidence NOT COLLECTED |
| **B03** | E07–E09/E10 actual defaults/creator provenance, cross-schema impact and accepted variants if owners attest | Unknown historical creators/consumers remain gaps; global impact requires explicit acceptance; fresh creator/service/owner/trigger behavior needs T05/T07. | OPEN; target/owner evidence NOT COLLECTED |
| **B04** | E10–E12 time-bound full definitions/ACLs/bindings/bridge/versions and independent applied-byte records if supplied | Permission/redaction/dynamic/temporal limitations, unexpected variants or missing applied-byte linkage remain blockers. Target compatibility is not behavioral acceptance; T01–T14 required as scoped. | OPEN; target evidence NOT COLLECTED |
| **B05** | E13–E18/E01–E03/E11/E12 body/order/lookup/provider/consumer assessments and accepted policy inputs if supplied | B05-F01–F11 and N01–N03 are not fixed by collection. Safe reservation/credential/authority/legacy/lookup contracts require later authorized implementation/review and T04/T07–T14, conditional T13. | OPEN; no remediation or runtime result |
| **B06** | E19–E22/E04/E08/E15/E18 accepted recovery/delivery/retention/reset/consumer/rollout inputs if supplied | M01–M06 cannot be inferred from catalogs; actual data conflicts, recovery/restore/retention compliance and race outcomes need separate authority/evidence. T01–T04/T08/T12/T14. | OPEN; decisions unattested, runtime NOT RUN |
| **B07** | E23 collection approval and E24–E26 bounded review/readiness requests, missing-artifact map and available separate approvals | Collection is not implementation authoring, exact-byte successor/runner/fixture acceptance, engine readiness or disposable test permission/results. Both original stops and final rollback remain. All T01–T14 NOT RUN. | OPEN; collection approval PENDING |

Current preservation boundary: a pre-edit byte inventory covers **845 existing regular tracked/untracked non-ignored files** listed by Git. It excludes unlisted ignored files and is not a blanket workspace attestation. Only this new Markdown package may be added; all previous reports/evidence, user edits, application/frontend/tests, scripts, migrations and candidate history remain untouched. Existing builders/verifiers were not run. This task performed no owner contact, network collection, secret inspection, Supabase/provider call, Docker/engine check, SQL/parser execution, application import/test, database-dependent validation, deployment or push.

Local artifact verification passes: **845/845** pre-edit byte fingerprints match, and this package is the only added path in that inventory. **20/20** local links resolve with cited lines in bounds; **8/8** tables have consistent columns; **8/8** reference hashes match the preserved files. All **26** manifest entries have separate item contracts, proposed artifact names, B/OD/T mappings, collector/permission and handling/output/review fields. All **13** preflight items and **7** blocker-completion rows are present. New-document whitespace checks and `git diff --check` pass; the untracked package was checked directly because Git's diff check does not cover it.

The original [C002 stop at 28](SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql#L28) and [C003 stop at 31](SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql#L31) remain unconditional before [C008 at 189](SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql#L189), with [final `ROLLBACK;` at 443](SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql#L443) unchanged. Its byte hash matches the preserved reference above and candidate-results JSON. These are artifact/preservation checks only: no target evidence was collected, no runtime check ran, and no blocker was closed. **All runtime checks, including T01–T14, are NOT RUN.**

## 10. Exact next approval and remaining NO-GO conditions

**The next required approval is E23: a dated, named, target-specific read-only collection authorization for the final SHA-256 of `SC-RO-2026-10-11-01`, plus a completed manifest and exact read-method/permission/object/output annex.** A general “continue” or approval of this document as design does not fill those fields. Request the authorization only after the proposed target-specific annex is concrete and reviewable; this document leaves targets/people/windows/storage deliberately UNBOUND and supplies no executable methods.

The authorization must explicitly state:

1. Named approver, collectors and independent reviewers; exact target alias/environment/deployment/database identity; permitted start/end window in Asia/Calcutta and UTC; authorization expiry and identity-verification method.
2. Selected E items, OP IDs, exact catalog/schema/role/object/column/signature/getter boundaries and reviewed method/statement/tool hashes. No behavioral SELECT/RPC/application/function probes; no data reads other than approved ledger version/name deployment metadata.
3. Existing minimum read permissions and approved secure access mechanism; no secret inspection, privilege provisioning, role switching or owner/service credential fallback. Explicit handling of denied visibility and unexpected objects/versions.
4. Exact new output paths and restricted storage, H0/profile handling, redaction/original/derivative provenance, output/time/size bounds, retention/legal-hold/access owner and abort/resume process.
5. Authorized deployed-record/external-consumer suppliers, permitted contact channels and metadata/aggregate window; whether public official-document retrieval is included. No provider accounts/calls or raw operational logs.
6. Explicit exclusion of DDL/DML/database/provider mutations, application-row exports, tests/engine/Docker/readiness work, implementation, deployment/push, and any edits to preserved reports/migrations/candidate/stops/rollback. E24–E26 R components remain future approval requests.

**NO-GO for collection** while any required E23/preflight field is absent, unapproved, expired or mismatched; while exact safe read methods, existing visibility, redaction/output/retention controls or named reviewers are unavailable; or if collection needs prohibited access/mutations/probes. **NO-GO for implementation, runtime validation, B01–B07 closure, installation/deployment/push** continues after collection until separately authorized owner policies, exact successor/runner/fixture reviews and applicable test evidence exist. **B01–B07 and N01–N03 remain OPEN; T01–T14 are NOT RUN. GO only for continued offline package/annex review under the present authorization.**
