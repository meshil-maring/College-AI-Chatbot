# Academic identity verification - revised design proposal

Status: **PROPOSAL ONLY; NOT AN AUTHORIZED OR EXECUTED MIGRATION.**

All seven artifacts describe the same proposed boundary. The SQL remains outside migration discovery and retains its unconditional execution stop. No application, existing migration, schema export, approval function or B05/E23 artifact is changed. No policy, authority mandate or verifier permission is seeded. Missing approved policy blocks enablement.

## Confirmed requester requirements; formal policies still pending

The task establishes the requirements below. It supplies no formal institutional policy approval, named authority appointment or implementation approval. Synthetic approval references in tests are fixtures only.

* The official register is an uploaded, institution-verified copy, retained as an immutable source version.
* Register number is mandatory and the primary academic matching identifier. University roll number is optional and cannot replace it.
* Only active institution-scoped staff/admin users with an explicit individual `academic_identity.verify` assignment may verify. Role membership, shared role permissions, wildcards, attendance permissions and platform scope do not substitute.
* Authorized staff upload and independently authenticated source provenance are required. Exact source/entry evidence and attributable decision history must be retained. Self-grant and positive self-approval are prohibited.
* Every new positive must establish the exact subject-to-account binding in `rpc_contract.md`; matching register/roll identifiers cannot substitute for ownership evidence. Current usability must reject later association/evidence changes without rewriting history.
* Existing profiles, attendance and roster rows remain unchanged. Approval, ACTIVE/LINKED roster states and old imports do not establish invitation eligibility. Independent positive verification is required.
* Verification never authenticates a student, approves an account, grants a role, proves email ownership or bypasses email verification. No invitation functionality is implemented here.

## Existing patterns inspected and proposed reuse

| Local pattern | Reuse and limitation |
| --- | --- |
| `student_registration.py`, `user_registration.py`; `students` schema | Self-reported candidate identifiers, not official evidence. `student_number` can derive from roll number; it is not proof of register number. |
| `admin_academics.py`, admin approval routes | Account creation/approval remains a separate workflow. No approval function is called or modified. |
| `faculty_attendance.py`; attendance migrations dated 20261010 and 20261012 | Tenant-local ambiguity/conflict handling and raw-row provenance are useful. Existing roster uniqueness is per section. Historical backfill can copy `student_number` into the roster register field; no such row is trusted automatically. |
| `security.py`, `authorization.py`, `db/supabase.py` | JWT-derived user/Auth pairing and tenant resolution. Generic wildcard/union permission matching is insufficient for this command. |
| `permissions.py`, `phase81_rbac.py`; Phase 8.1 SQL | Current direct delegation is Staff-only and allowlisted. It does not assign this capability to selected admins. Proposed private individual grant events avoid broad shared-role enablement; existing grant tables/functions stay unchanged. |
| `admin_audit.py`, `phase81_prevent_audit_mutation` | Reuse existing audit rows and append-only trigger implementation. A separate Python audit insert is not atomic with a decision; the proposed RPC inserts both. |
| `ingestion.py`, `admin_documents.py`, document-version/storage metadata | Server hashing and version references are useful patterns. General document publication, processing, supersession/purge and deletion are unsuitable defaults for a private retained register. Do not send registers through these flows or RAG. |

These are local source observations, not claims about deployed state.

## Register custody and exact evidence

A trusted upload service must check active institution staff/admin membership plus an explicit owner-created `register_uploader` mandate, compute SHA-256 over the original bytes and persist them to a private, non-overwriting object key with a concrete storage version identifier. Recheck uploader identity/scope/mandate at acceptance. Retain byte length, uploader user/Auth snapshots, mandate, upload time and DB receipt time. No user-supplied digest, filename, URL or version label establishes trust.

An owner-designated institution register custodian independently confirms issuer/custodian provenance through an approved procedure (for example, a documented handoff from the registrar confirmed through a trusted institutional channel, or a validated issuer signature where available). Retain the procedure/method, provenance description and restricted retrievable evidence binding the institution, issuer or official custodian, handoff and exact copy. A reference string alone is insufficient; the custody writer must inspect that evidence and record who authenticated it and when. A checksum proves byte integrity, not institutional authenticity or human consultation.

Record issuer name/version and effective/as-of date **where available**, separately from the mandatory internal immutable source-version UUID and upload/storage version. If issuer metadata is absent, retain NULL plus a custodian-attested missing-metadata reason; never invent a date or use upload time as the effective date. The approved freshness policy may later require such metadata and refuse that copy. Acceptable authenticity methods and uploader/authenticator separation remain owner decisions; until selected, no source can be accepted for enablement.

`register_versions` holds only accepted immutable copies. Unaccepted uploads remain outside this trusted schema, cannot be consulted by verification, and need a separately specified staging/cleanup policy. Acceptance requires complete approved policy/governance; acceptance, entry import and the existing audit event must be one reviewed custody transaction under the institution lock; object upload precedes it. Failed acceptance leaves an inaccessible staged object for cleanup, never an accepted source. The trusted custody writer and storage policies are prerequisites, not implemented application features in this package.

Each `register_entries` row belongs to exactly one accepted version and retains an exact locator plus raw original string values and a stable official-person key. Locator syntax must be chosen for the supplied format: page and printed entry identifier for PDF/image, or sheet and physical row/cell range for spreadsheet. Parsed/OCR values require custodian confirmation against the original and explicit `confirmed_original_strings` extraction status; unreviewed, numeric/formula or OCR ambiguity is refused even when represented as a string. Numeric cells that cannot preserve leading zeros are not silently repaired. A locator is unique within that version. All source entries must be checked for duplicate/conflicting canonical ownership during acceptance; verification independently refuses any overlapping official identifier in another entry of that version.

Every positive decision references the exact source version and entry with institution-safe FKs and snapshots raw source values, locator, checksum, source version/date and object/version reference. It also retains checked identifier kinds, canonical values, policy, verifier, reason, audit, prior decision and DB time. Request bodies cannot replace official values. A client source id is a locator, never authority. Read-back checksum checking, restricted access, encryption, backup retention and source-integrity incident handling belong to the custody implementation plan.

`source_invalidations` appends actor/Auth, mandate, time, reason, incident evidence and audit reference without deleting a version or rewriting decisions. The proposed conservative current-state guard treats dependent positives as unusable immediately after invalidation commits; their recorded status remains positive until an authorized withdrawal/correction appends history. This guard is not a batch revocation or an approved institutional remediation policy. Recovery requires a newly accepted version and independent verification/correction; there is no undo-invalidation command. Source replacement/supersession alone never transfers, overwrites or automatically revokes decisions; the owner must decide its freshness and remediation consequences.

## Narrow proposed model

* `policies`: immutable approved normalization, freshness, person-key interpretation and governance references. Register number and person key are always required; roll is always optional. No rows are supplied.
* `authority_mandates` / `authority_revocations`: owner-designated, institution-bound permission grantors, uploaders and register custodians. No implicit admin or platform authority. Bootstrap/replacement/revocation is a reviewed DB-owner operation with existing audit, never self-service.
* `permission_events`: immutable per-user revisions of exact individual grants/revocations for staff or admins, including grantor, mandate, target-role snapshot, reason, idempotency and audit. No shared-role grant qualifies.
* `register_versions`, `register_entries`, `source_invalidations`: retained custody evidence described above.
* `identities`, `decisions`, `identifier_claims`: stable account-independent identity; immutable verified/withdrawn head history; institution-wide current claims. Historical positive claims are also reserved pending owner-approved reuse/adjudication rules.
* `candidate_findings`: separate immutable rejected/unresolved observations. These neither create ownership nor change an established identity head or its claims.
* Offline-only `AccountAssociation`, `BindingEvidence` and `SubjectBinding`: trusted directory snapshot, structured institutional proofing receipt and separate attributable approval. Their registries, method/mode allowlist, explicit establishing/reviewing mandates and validity boundaries are synthetic fixture prerequisites. `DirectoryBaseline`/`DirectoryRevision` additionally specify explicit directory completeness provenance, retained institution-wide generations/history and an independent highwater continuity anchor for absence evidence. No SQL tables, production writer/resolver or real owner appointments for them are supplied.

The draft proposes a redundant `students(student_id, institution_id)` UNIQUE constraint solely for composite FKs. It changes no row but has index/locking costs. Canonical and rejected-candidate references can block profile deletion/tenant movement. This retention consequence remains subject to owner approval; no unlink, reassociation, purge or adjudication command is supplied.

## Matching and lifecycle rules

Positive verification obtains **all** available identifiers from the selected accepted entry. Required normalization rules must exist even for an optional roll. Preserve raw values; canonicalization never converts to a number. Only register number, roll number and the stable person key are official kinds here. Existing `student_number` is context, never an alternate matching key.

Check every available relevant identifier against canonical owners, historical ownership, all tenant-local student candidates and all section rosters. No first-match selection. Duplicate profiles, a register/roll disagreement or incompatible roster link blocks success. Optional roll can be absent from the source; when a candidate has a roll that the accepted entry lacks, positive linking is blocked pending independent source reconciliation, rather than quietly ignoring that value. Missing profile register number cannot be replaced by roll-only matching; reconciliation uses a separately authorized legacy workflow. Repeated consistent rosters across sections may describe one person and remain unchanged.

The source stable key may equal register number only if the owner confirms lifetime stability and ownership semantics. No invented key is permitted. The ordinary RPC cannot change a previously positive person key or reassign a canonical student link. Ordinary correction can change a register number only for the same established person, using a newly checked accepted entry; historical ownership remains reserved.

| Operation | Proposed behavior |
| --- | --- |
| `verify` | New identity, expected revision zero, independent complete register and binding checks. Account mode requires an exact explicit profile/user/Auth/revision; separately approved no-accounts mode selects no profile and grants no account entitlement. |
| `reverify` | Existing identity, unchanged canonical identifiers and profile link; new independent check/current expected revision. |
| `correct` | Existing identity; explicit reason and newly checked entry/binding. Preserve person key and the entire historical profile/user/Auth/association-revision tuple, including NULL fields. Ordinary correction cannot attach/replace an account or migrate verification. Wrong-person repair/recovery/reassociation requires a separate owner-approved workflow. |
| `withdraw` | Previously positive identity; append withdrawn head and release current claims, retaining historical ownership/link/evidence. Requires current verifier permission but **does not require a current policy or usable source**. References the previous decision; no new register assertions. Repeated withdrawal requires a new positive head first. |
| Candidate `rejected_match` / `unresolved` | Separate finding against an accepted version and entry/search locator. Retain candidate context, never change an established identity or acquire claims. |
| Source invalidation | Custodian appends source invalidation; all dependent positives become unusable in current-state reads. History/claims remain reserved until reviewed withdrawal/correction. |

Future invitation reads must independently check exact positive head, source not invalidated, configured freshness, current conflict-free legacy relationship, issuer authorization and normal email/account requirements. A linked roster/profile does not inherit verification automatically. No invitation is issued, repaired or consumed here.

## Assignment, authorization and transaction contract

Permission grantors require an active owner mandate plus active institution-admin membership; verification capability alone cannot delegate. Targets must be active institution staff/admin. Self-grant **and self-revocation** are refused by this management command. An owner-appointed alternate grantor can revoke a grantor's verifier permission; mandate revocation is a separate owner operation. A grant event is a direct authorization decision, independent of later grantor turnover; revoking a mandate does not silently revoke previously assigned verifiers. Those assignments must be explicitly reviewed/revoked.

Positive self-approval (`verify`, `reverify`, `correct`) is prohibited using both user and Auth identity, including dual-role users and linked profiles. Excluding the verifier is only one part of ownership proof: an exact selected-account binding is mandatory. The normative invariant and trust/transaction prerequisites are in `rpc_contract.md`, **Exact subject-binding invariant**. The SQL has **no trusted binding writer/resolver** and explicitly refuses every new positive with `AV_SELF_APPROVAL_CONTROL_UNRESOLVED`. The stronger oracle control remains an offline specification, not SQL readiness or institutional approval. Withdrawal remains available with live verifier permission and no new positive approval, including withdrawal of one's own prior decision; no automatic second-review rule is invented.

The two independent-review probes are now explicit rejection cases. A `no_accounts` receipt cannot select any profile, even when its identifiers match. A receipt for account B cannot authorize profile/account A: institution, official person, exact source/entry, profile, user, Auth id and association revision must agree with retained proof and the active authoritative directory. Missing fields, conflicting/additional associations, missing proof, stale/revoked/altered evidence, wrong institution or unauthorized reviewer fail closed. A name, account id in a reference string or matching register/roll values cannot establish ownership.

The model's trusted receipt registry represents an upstream institutional proofing procedure that has already authenticated the subject's exact account and independently established its official identity (or a complete absence search). Separate explicit establishing/reviewing mandates and method/mode allowlists must exist; there are no permissive defaults. Collection, approval and current times must precede the explicit evidence-validity end. Real authorities, acceptable proof, completeness, validity and independent-review rules remain owner decisions. Synthetic fixture records/durations do not settle them.

Each positive retains the exact receipt/approval and observed association snapshot. Future `current_usable` reads recheck those live records, source/entry, policy, directory/profile association and conflicts. A changed user/Auth/profile/person link, association revision, evidence/authority revocation or reapproval returns false without rewriting the old decision. A newly approved receipt alone never refreshes an old verification. Ordinary reverify/correct cannot change the account tuple, including an unlinked-to-linked change; account recovery/replacement needs a separate approved workflow. An unchanged-key historical retry remains an attributable historical result after current verifier authorization and is never an eligibility assertion.

The proposed service-only management RPC requires expected target permission revision, an actor-scoped request id, reason and mandate evidence; it appends the event and existing audit together. Revocation remains available when a target has become inactive/lost its role. No policy is required to revoke. Enablement/grant requires a complete approved policy. Application routes must resolve JWT identity and institution on the server and check exact assignment provenance; generic wildcard or role permission unions are insufficient. The DB repeats active actor/Auth/tenant/role/individual-assignment checks, even on retries.

All verification, finding, grant/revoke, custody acceptance/invalidation and policy/mandate operations coordinate through the same institution transaction advisory lock, with READ COMMITTED and bounded lock waits and outer statement/transaction deadlines. For positive verification, lock legacy tables in order `user_roles`, `roles`, `students`, `faculty_attendance_rosters` in SHARE mode **before** authorization-row locks. Grant/finding operations lock the first two tables; withdrawal also locks the first two but does not need source/profile conflict scans. This blocks role/scope insertion phantoms without modifying existing writers. It also blocks writes across tenants; deployment volume and lock limits require later review.

After these locks, lock the institution, participating user rows sorted by UUID, role memberships/roles, capability row and relevant mandate/grant records, then identity/head, policy, source and entry records. Reviewed custody/owner operations use this order as applicable. Existing writers do not necessarily follow it; deadlocks/timeouts must abort and be tested later, not assumed absent. Pending actor/institution/permission disablement must be observed after waits or serialize after a successful decision. Source invalidation and permission revocation serialize with verification through the institution lock. No human, file parsing, network or storage work occurs inside these DB transactions.

Idempotency is actor/institution/command scoped. Same key plus identical logical payload returns the original result only after current authorization; changed input conflicts. Return recorded and current head separately. Stale expected revisions require reload and human review, never automatic rebasing. Audit, finding/decision, claims and head writes are intended to share one transaction; no swallowed exception or best-effort audit. Disconnect uncertainty is resolved by retrying the unchanged command/key after checking outcome. Time is taken after lock waits. The lock/rollback/security behavior is a design requirement, **not verified PostgreSQL behavior**.

## Academic identity verification owner decision register

Status: **OWNER DECISION REQUIRED**. Every entry below is **UNDECIDED**; its decision and approval evidence are **not recorded**. Every linked follow-up is **TECHNICAL VALIDATION REQUIRED**, deferred until the decisions, reviewed design and separate authorization exist. This register organizes existing blockers; it grants no implementation or SQL-execution approval.

Review baseline: the recorded offline result is **199 passed, 0 failures, 0 errors, 0 skipped** ([correction evidence](offline_test_plan.md#four-finding-correction-validation-2026-10-18)). The latest independent review, as supplied in the task, confirmed the four prior defects fixed for the reviewed cases. They remain closed absent new evidence. That review confirmation is task-provided; this register does not invent a separate review artifact or claim a new test run. Sequential model passes establish no PostgreSQL, storage or operational guarantee.

**Decision authority for every entry:** existing documents reserve policy choices and authority designations to the owner, but establish no named institutional decision-maker or delegated approval mandate. Each entry therefore requires owner resolution; proposed operational roles below are not appointments or authority to approve policy. Record the actual decider's authority evidence before recording any decision as approved. No admin, verifier, DB owner or fixture mandate is inferred to be that decider.

**How to complete each entry:** record its ID, explicit answer and scope, accountable decider and authority evidence, dated retrievable approval evidence, policy/version and effective date, and any unresolved conditions. The entry-specific evidence below is also required. An evidence-reference string alone is insufficient. Do not change an entry's status on the strength of a test result; track the linked technical results separately. Where no alternatives are listed, the proposal supplies no settled option set.

### 1. Authority and ownership

**A1 - Who owns the authoritative academic directory, and who may attest that it is complete and current?**

* **Why / blocked:** account ownership and absence searches require full institution, account, alias and historical coverage. Observed emptiness cannot establish completeness; safe positive verification remains blocked without trusted authority and coverage.
* **Decision / evidence needed:** identify the directory owner, completeness attester and revision/continuity authority; document their mandates, institution scope, coverage, attestation procedure and baseline provenance. No such real appointments are established. The synthetic `subject_directory_writer` mandate is only a model prerequisite.
* **Follow-up:** T2, T4, T6 must validate authoritative inputs, writer coverage, baseline provenance and continuity. Basis: [persistent directory invariant](rpc_contract.md#persistent-no-accounts-directory-invariant-proposed-control-not-owner-approved).

**A2 - Who may approve proofing procedures and appoint proofing staff, independent reviewers and other verification authorities?**

* **Why / blocked:** role membership cannot confer proofing, review or delegation authority. Positive evidence and source acceptance cannot be trusted while appointments, separation and succession are unresolved.
* **Decision / evidence needed:** record authorized appointing/approving authority and explicit institution-bound appointments for proof establishers/reviewers, uploaders/custodians, permission grantors and selected verifiers. Specify uploader/authenticator separation, independent review, any additional correction/withdrawal dual control, succession and emergency revocation. The proposed distinct subject/establisher/reviewer/verifier guard is not an approved operating policy; self-grant and positive self-approval remain prohibited.
* **Follow-up:** T1, T3, T6 must validate authority provenance, independence, revocation and succession against the chosen policy. Basis: [permission authority](rpc_contract.md#individual-permission-assignmentrevocation), [subject-binding invariant](rpc_contract.md#exact-subject-binding-invariant-normative-proposal).

**A3 - Who may authorize recovery after an integrity incident and restoration of trusted service?**

* **Why / blocked:** repairing rows or restoring a backup cannot authorize renewed trust. Ordinary writers and bootstrap cannot clear a latched incident; operational incident recovery remains unavailable.
* **Decision / evidence needed:** designate incident, evidence-invalidation, recovery and restoration approval responsibilities, including succession and the evidence required to authorize recovery. No recovery authority or ordinary incident-clear workflow is established. B4 covers the recovery procedure separately.
* **Follow-up:** T1, T4, T5 must validate authorization boundaries, durable incident state and restoration gates. Basis: [unresolved directory responsibilities](rpc_contract.md#persistent-no-accounts-directory-invariant-proposed-control-not-owner-approved).

#### A1–A3 owner decision handoff

Status for **A1**, **A2** and **A3**: **UNDECIDED / OWNER DECISION REQUIRED**. This handoff is for obtaining documented answers; no answer, appointment or approval evidence has been supplied. It supplements the entries above without changing their questions or the remaining register.

For each response, supply the decision ID, explicit answer and institution scope, actual decider and documentation establishing that person's authority, dated retrievable approval evidence, policy/version and effective date, and unresolved conditions. These are the register's existing recording requirements. A reference string, job title, fixture mandate or test result alone cannot establish approval. The README does not identify the responsible person or establish a delegated approval chain; that gap must be resolved before routing for an authoritative decision.

**A1 handoff — Directory ownership and completeness authority**

* **Decision required:** identify who owns the authoritative academic directory, who may attest that it is complete and current, and who holds revision/continuity authority.
* **Authorized decider:** not established by existing evidence. The register reserves designation to the owner but names no institutional decision-maker or delegate. A proposed directory writer is not evidence of appointment or policy authority.
* **Documentation to supply:** mandates/designations for the directory owner, completeness attester and revision/continuity authority; institution, account, alias and historical coverage; the completeness/currentness attestation procedure; and baseline provenance. Supply the common decision/authority evidence above. No real appointments or supporting attestation evidence are recorded.
* **Blocked until recorded:** safe positive verification cannot rely on unestablished directory authority or coverage; account ownership and absence searches cannot infer trust from observed rows or emptiness.
* **Later validation:** **T2** — complete writer/input coverage; **T4** — durable baseline/history and continuity; **T6** — actual authority, completeness and provenance. All remain **TECHNICAL VALIDATION REQUIRED**.

**A2 handoff — Proofing approval and verification appointments**

* **Decision required:** identify who may approve proofing procedures and appoint proof establishers, independent reviewers, uploaders/custodians, permission grantors and selected verifiers; specify separation, succession and emergency revocation rules.
* **Authorized decider:** not established by existing evidence. Admin status, verifier capability and proposed operational roles do not establish appointment or proofing-policy approval authority.
* **Documentation to supply:** the appointing/approving authority's mandate; explicit institution-bound appointments; uploader/authenticator separation and independent-review requirements; any additional correction/withdrawal dual control; succession and emergency revocation rules. Supply the common decision/authority evidence above. Self-grant and positive self-approval remain prohibited; proposed distinct-person guards are not approved operating policy.
* **Blocked until recorded:** positive evidence and source acceptance cannot be trusted while appointments, separation and succession remain unresolved. This decision does not itself settle C5's acceptable proofing methods or evidence-validity policy.
* **Later validation:** **T1** — authority and permission boundaries; **T3** — authorization/revocation behavior under transactions and races; **T6** — authority provenance, independence and succession in the trusted process. All remain **TECHNICAL VALIDATION REQUIRED**.

**A3 handoff — Incident recovery and restoration authority**

* **Decision required:** identify who may authorize recovery after an integrity incident and restoration of trusted service, with responsibilities for incident handling and evidence invalidation.
* **Authorized decider:** not established by existing evidence. No recovery or restoration approval authority is appointed; technical access or the ability to restore a backup does not establish that authority.
* **Documentation to supply:** explicit incident, evidence-invalidation, recovery and restoration approval responsibilities; succession; and the required evidence for authorizing recovery, together with the common decision/authority evidence above. **Gap:** the README requires recovery-authorization evidence but does not specify its final contents; that requirement must be decided, not filled with assumed criteria. B4 separately covers the recovery procedure.
* **Blocked until recorded:** operational incident recovery remains unavailable. Repair, ordinary directory writes, bootstrap or backup restoration cannot authorize renewed trust or clear a latched incident.
* **Later validation:** **T1** — recovery authorization boundaries; **T4** — durable incident state and authorized recovery gates; **T5** — backup/restoration gates and continuity. All remain **TECHNICAL VALIDATION REQUIRED**.

**Dependencies and routing gaps**

* **A1 and A2 require coordination:** directory ownership/completeness supplies the trusted boundary used by proofing and review; proofing appointments alone cannot attest directory completeness. A1 does not appoint proofing reviewers or approve their procedures.
* **A3 requires alignment with A1 and A2:** recovery/restoration responsibilities must be reconciled with directory revision/continuity authority and the appointments, succession and revocation rules. Neither A1 nor A2 automatically grants incident recovery authority, and A3 cannot replace directory completeness or independent proofing.
* The README establishes no single common decider, mandatory ordering or delegation chain among A1–A3. Their answers can be prepared together, but each needs its own explicit decision and authority evidence. A3's operational procedure remains B4; A1–A3 do not resolve B1–D3 or validate T1–T6.

**Next action:** obtain documentation identifying the institutional decision-maker(s) and their authority, then request the three evidence-backed responses above. Keep all three decisions **UNDECIDED** while that evidence is missing. Recording owner decisions does not authorize implementation, validation execution or SQL execution. Both **DESIGN_ONLY_NOT_AUTHORIZED** and **AV_SELF_APPROVAL_CONTROL_UNRESOLVED** remain unchanged.

### 2. Directory changes and continuity

**B1 - Which changes must advance directory revisions, and what invalidation scope and operating limits are acceptable?**

* **Why / blocked:** an untracked account or alias change can reuse stale ownership/absence evidence. Complete writer coverage and an acceptable operating model remain prerequisites.
* **Decision / evidence needed:** approve the operation inventory covering account/alias/profile/Auth creation and removal, reassignment, activation/inactivity, recovery/replacement, legacy cleanup and restore, including change-away-and-back and identical-value restores. Specify per-account revision rules, directory generation granularity, and operational lock/deadline limits. The proposal uses institution-wide generations, conservatively invalidating unrelated subjects' absence evidence; no alternative granularity is specified or approved.
* **Follow-up:** T2, T3 must map every real writer and validate atomic revision changes, compatible reads, races and measured blocking. Basis: [directory invariant](rpc_contract.md#persistent-no-accounts-directory-invariant-proposed-control-not-owner-approved), [lock boundary](rpc_contract.md#lock-order-races-and-retry-boundary).

**B2 - What durable directory history, baselines and deletion tombstones must survive?**

* **Why / blocked:** removed or inactive associations must not become apparent never-associated subjects. Without retained history and trustworthy bootstrap, absence evidence and historical ownership cannot be relied upon.
* **Decision / evidence needed:** specify baseline/bootstrap provenance, before/after history, writer/time/reason/audit attribution, tombstones and continuity retention requirements, coordinated with D1/D3. Consecutive snapshots, a retained bootstrap receipt and a separate highwater anchor are proposed representations, not approved storage or retention choices.
* **Follow-up:** T1, T2, T4, T5 must validate protected history, monotonic revisions, deletion/recreation and persistence through failure and restoration. Basis: [directory invariant](rpc_contract.md#persistent-no-accounts-directory-invariant-proposed-control-not-owner-approved).

**B3 - What independent continuity guarantees must detect restoration or rollback of trusted state?**

* **Why / blocked:** coherent rollback of every model-held store can make old evidence usable again and erase later incidents/audit. The passing limitation test does not solve this; safe continuity remains unestablished.
* **Decision / evidence needed:** identify the accountable continuity authority and required independently trusted continuity/restore guarantees, including what must survive backup restoration and how unknown continuity is treated. No external mechanism is selected. Missing trusted continuity must fail closed; restarting generation at one cannot restore trust.
* **Follow-up:** T4, T5 must assess the resulting technical design and test independent/mixed and coherent rollback, witness loss and restoration against a surviving independent trust source. Basis: [restoration characterization](rpc_contract.md#strict-generation-validation-and-restoration-characterization).

**B4 - What must happen after an integrity incident before evidence or service can be trusted again?**

* **Why / blocked:** deleting bad rows or repairing history cannot clear observed unreliability. Durable detection/reporting, evidence invalidation and recovery are unresolved operational prerequisites.
* **Decision / evidence needed:** define incident handling, reliability marking, reporting/delivery responsibility, affected-evidence treatment and recovery/revalidation conditions under A3's authority. Preserve decisions and history; a new receipt or baseline cannot itself authorize recovery. No ordinary reset/rebootstrap is a supported recovery option.
* **Follow-up:** T3, T4, T5 must validate read-side and command-side detection, durable delivery despite transaction rollback, incident persistence after repair and separately authorized recovery. Basis: [directory invariant](rpc_contract.md#persistent-no-accounts-directory-invariant-proposed-control-not-owner-approved), [evidence/event boundary](rpc_contract.md#evidence-provenance-and-collection-to-commit-boundary).

### 3. Identity and source policies

**C1 - How current must sources and decisions be, and what happens when a source or policy is replaced?**

* **Why / blocked:** source age, decision age and proof validity are distinct. Missing rules block positives; replacement alone cannot transfer or silently renew prior decisions.
* **Supported options:** bounded decision lifetime or explicit no-expiry; neither is selected. Source-age and supersession consequences remain to be specified.
* **Decision / evidence needed:** record source dating/missing-date rules, renewal triggers, policy-version effects, supersession/invalidation remediation and treatment of prior decisions and expired claims. Coordinate proof validity with C5 and reuse with C4.
* **Follow-up:** T1, T3, T6 must validate policy representation, expiry boundaries after waits and replacement/invalidation effects on new commands and current reads. Basis: [source custody](rpc_contract.md#accepted-immutable-source-versions---custody-prerequisite), [read contract](rpc_contract.md#error-and-read-contracts).

**C2 - What proves a register copy authentic and its imported entries complete and exact?**

* **Why / blocked:** hashes and references do not prove institutional authenticity or faithful extraction. No source acceptance can support enablement without approved custody and confirmation procedures.
* **Supported examples:** trusted institutional handoff or validated issuer signature; PDF/image page-entry or spreadsheet sheet-row/cell locators, according to format. These are examples, not selected procedures.
* **Decision / evidence needed:** specify acceptable provenance evidence, exact locator syntax, import-completeness/original-string confirmation and source-integrity read-back schedule. Retain actual authenticated handoff/issuer and extraction evidence for the exact copy; resolve uploader/authenticator separation through A2.
* **Follow-up:** T1, T5, T6 must validate custody, complete atomic imports, OCR/numeric/formula ambiguity refusal, original-byte integrity and retrievable evidence. Basis: [custody prerequisite](rpc_contract.md#accepted-immutable-source-versions---custody-prerequisite).

**C3 - How are identifiers normalized, and how are ambiguous or colliding values resolved?**

* **Why / blocked:** normalization can merge different people or lose leading zeros. Missing approved rules block positives; conflicts cannot be resolved by first-match selection.
* **Decision / evidence needed:** approve per-kind characters/length, whitespace/case, Unicode/confusables, collation, extraction handling and collision adjudication, with representative raw/canonical and conflict examples. The ASCII mechanisms and 256-character sketch ceiling are not approved institutional rules. Register number stays mandatory; roll stays optional and cannot replace it.
* **Follow-up:** T1, T6 must validate complete policy representation, source-wide and historical collisions, actual DB comparisons and raw-string preservation. Basis: the earlier matching rules in this README and [retention/security limits](rpc_contract.md#retention-and-security-limits).

**C4 - What identifies the same person over time, and may identifiers ever be reused or reassigned?**

* **Why / blocked:** identifier reuse or a wrong-person repair can transfer another person's history. Historical positive identifiers remain reserved pending policy; that guard is not approval of lifetime uniqueness.
* **Supported conditional choice:** register number may serve as the stable person key only with owner confirmation of lifetime stability and ownership semantics; no invented replacement key is supported.
* **Decision / evidence needed:** document stable-key semantics, reuse/transfer adjudication and exceptional wrong-person-key/profile reassociation, including ownership history and approval evidence required for exceptions.
* **Follow-up:** T1, T3, T6 must validate uniqueness/reservations, collision review, unchanged ordinary-correction tuples and any separately designed exceptional workflow. Basis: the earlier matching/lifecycle rules and [owner binding decisions](rpc_contract.md#owner-decisions-that-block-a-safe-positive-contract).

**C5 - What identity proofing, account authentication and independent review are acceptable?**

* **Why / blocked:** matching academic identifiers or controlling an account does not prove the human owns the official entry. Real proofing and reviewer authority remain absent; positive SQL stays disabled.
* **Supported policy choice:** whether to permit the separately governed `no_accounts` mode; it grants no account entitlement. Account mode requires the exact person/profile/user/Auth/revision binding. No proofing method is selected.
* **Decision / evidence needed:** approve method/mode allowlists, authenticated-session/institutional proof procedures, alias/multiple-account search coverage, evidence validity/renewal/revocation, review independence and authority succession. Provide procedure and retrievable evidence requirements, with A1/A2 appointments; fixture mandates and durations are not approval.
* **Follow-up:** T1, T2, T3, T6 must validate real proof provenance, complete absence searches, exact binding versions, authority and expiry/revocation without replacing owner judgment with tests. Basis: [subject-binding invariant](rpc_contract.md#exact-subject-binding-invariant-normative-proposal).

**C6 - How may account recovery, identity correction and legacy reconciliation change an established association?**

* **Why / blocked:** ordinary reverify/correct cannot attach or replace an account or migrate the historical tuple, including NULL fields. Removing a legacy conflict or issuing fresh evidence cannot authorize that transition.
* **Decision / evidence needed:** specify separately authorized attachment, recovery/replacement, reassociation and wrong-person repair workflows; reconcile missing/disagreeing legacy identifiers and optional roll values. Decide treatment of previously associated subjects seeking `no_accounts` status; the current historical-association guard refuses them. Record required proof, reviewers and retained ownership history.
* **Follow-up:** T1, T2, T3, T6 must validate the eventual workflow, all revision changes, preserved history, invalidation of old evidence and races with positives/current reads. Basis: [subject-binding invariant](rpc_contract.md#exact-subject-binding-invariant-normative-proposal), [directory invariant](rpc_contract.md#persistent-no-accounts-directory-invariant-proposed-control-not-owner-approved).

### 4. Data governance

**D1 - How long must evidence/history be kept, and when may deletion, unlinking or exceptions occur?**

* **Why / blocked:** append-only history and restrictive references can block profile deletion or tenant movement, including rejected-candidate references. Lawful retention/deletion rules remain unresolved enablement blockers.
* **Decision / evidence needed:** specify periods, legal holds and deletion/purge/unlink exceptions for original registers/entries, decisions/findings/claims, mandates/permissions, proof/session receipts/approvals, directory history/tombstones, invalidations/incidents, denials and audit. Reconcile deletion with B2/B3 continuity and historical reservations; no purge/unlink command is supplied.
* **Follow-up:** T1, T4, T5 must validate immutable records, FK consequences, holds, any separately designed exceptions and backup expiry. Basis: [retention/security limits](rpc_contract.md#retention-and-security-limits).

**D2 - Who may view retained evidence and history, for which purposes and with what exceptional access?**

* **Why / blocked:** verifier capability is not unrestricted download/history authority. Read projections, storage access and exceptional access cannot be enabled safely without a separate policy.
* **Decision / evidence needed:** designate tenant-scoped reader authority, purpose limits, redaction, access logging and exceptional-access approval/logging for sources, proof/session evidence, directory history, incidents/denials and audit. Public publication and public RAG ingestion remain excluded.
* **Follow-up:** T1, T4, T5 must validate DB permissions/RLS, reader APIs, storage restrictions, cross-tenant denial, redaction and access-log durability. Basis: [retention/security limits](rpc_contract.md#retention-and-security-limits).

**D3 - What private storage, backup, restoration and cleanup requirements must protect retained material?**

* **Why / blocked:** an immutable DB reference does not protect original bytes, backups or independent continuity. Custody and recovery cannot be trusted without aligned storage and backup governance.
* **Decision / evidence needed:** approve encryption, non-overwriting private object/version retention, backup retention/expiry, recovery/restoration and purge requirements, plus failed-upload staging/cleanup policy. Align with legal holds, B2/B3 continuity and A3 restoration authority; accepted evidence cannot be treated as disposable staging.
* **Follow-up:** T4, T5 must validate overwrite/delete restrictions, private retrieval, failed acceptance cleanup, byte integrity, backup expiry and restored evidence/history/incident state. Basis: earlier register custody rules, [retention/security limits](rpc_contract.md#retention-and-security-limits).

### 5. Technical validation after decisions

All rows are **TECHNICAL VALIDATION REQUIRED / NOT RUN**. These are engineering obligations, not additional policy approvals or substitutes for A1-D3. The existing [PostgreSQL and custody plan](postgres_integration_tests.md) supplies deferred cases; this register authorizes none of them.

| ID | Required validation and evidence after owner decisions |
| --- | --- |
| T1 - Constraints and permissions/RLS | Review the resulting schema and demonstrate tenant-safe FKs, uniqueness, heads/revisions, immutable evidence, deletion consequences, ownership/default/inherited privileges, service/API boundaries, private helpers, RLS and restricted readers at actual privilege levels. Record negative-access and integrity results; reference checks alone cannot enforce complete policy. |
| T2 - Complete writer coverage | Inventory every directory, alias, profile, account/Auth, external identity, recovery, legacy, evidence and authority writer and relevant reader. Demonstrate atomic revision/generation/history updates and compatible locking, including deletion/recreation and change-away-and-back. Synthetic writer methods do not prove real coverage. |
| T3 - Locks, transactions, rollback and concurrency | Finalize deterministic lock order and approved operating budgets; test real multi-session races, post-wait authorization/evidence/time checks, stale heads, idempotency, disconnects, deadlocks/timeouts, audit failures and full rollback. Include permission/source/binding changes and compatible usability reads. Sequential tests supply none of these guarantees. |
| T4 - Durable history and incident delivery | Demonstrate persistent baselines/tombstones/bootstrap/highwater, immutable successful history, attributable denials/incidents and read-side reporting that survives rolled-back commands. Repair or rebootstrap must not erase incidents. Validate the separately designed recovery authority and workflow under the owner's conditions. |
| T5 - Storage, backups and restoration | Test private immutable original bytes/versioning, hashing/read-back, staging cleanup, encryption/access, retention/holds/purge, backups and expiry. Exercise partial/mixed and coherent trusted-state rollback, including audit/incident history, against an independently trusted continuity source. Missing witness/unknown continuity must fail closed; the offline total-rollback test remains a limitation. |
| T6 - Trusted process and policy enforcement | Validate actual institutional source authenticity, directory completeness/alias searches, identity/session proofing and independent review with approved procedures and retrievable evidence. Demonstrate normalization, collision/reuse, freshness and recovery policies in the resulting design. Database tests cannot establish real-world authority or completeness. |

Recommended sequence: obtain documented answers and authority evidence for A1-A3 first; complete B1-D3 with those accountable authorities; then review the resulting policy/design and seek separate authorization for the necessary validation. Owner answers alone do not authorize implementation or execution. **DESIGN_ONLY_NOT_AUTHORIZED** and **AV_SELF_APPROVAL_CONTROL_UNRESOLVED** remain unchanged; final design approval, implementation and SQL execution remain blocked.

No policy rows, mandates, accepted registers or permission assignments are included. Complete policy governance references are required in SQL; absence blocks positive verification and permission enablement. Withdrawal and permission revocation deliberately remain possible without new policy/source approval.

## Review limits and next boundary

The SQL is an inspection-only design sketch, intentionally stopped before DDL. It has not been parsed or executed by PostgreSQL. Private ACL/RLS, FK chains, no-TRUNCATE triggers, source custody, grants, row locks, concurrency, transaction durability and deployment compatibility remain unverified. Owners/DB superusers and compromised backend/storage credentials remain privileged trust boundaries.

Draft Python tests exercise a sequential specification plus static boundaries. They do not simulate or prove PostgreSQL security or transactions. See `rpc_contract.md`, `offline_test_plan.md` and `postgres_integration_tests.md`. Review may assess the documented blockers; final sign-off and implementation authorization require their resolution.

## Readiness for independent review

Ready for **independent design review of the proposal and its explicit blockers**; not ready for final design sign-off, implementation or execution. Implementation approval has not been granted. Required review decisions include the subject-binding control, freshness/normalization/reuse policies and operational/security prerequisites. The SQL's execution stop and additional positive-command guard remain intact. No database security or PostgreSQL behavior has been validated.

Evidence categories: requester requirements above are confirmed for this revision; formal owner policies remain undecided; offline test results support only the sequential model/static guards; PostgreSQL, storage and application behavior remain untested. Registers and detailed audit/evidence records require separately authorized tenant-scoped readers, purpose-limited/redacted responses and access logging. They must never enter public publication or public RAG/knowledge ingestion. Retention/deletion/backup/legal-hold/exceptional-access decisions remain open; append-only audit history is a **proposed control** until immutability, access control and retention are technically validated.

The earlier 85-test evidence predates the subject-binding correction and did not detect the reviewed false positives. Current revision results and exact command are recorded in `offline_test_plan.md`. The new tests check unchanged decisions/claims/history on refusal, separate denial attribution and actual current usability, across all three positive operations. SQL is read/commented only, never executed; both unconditional refusals remain. Only the seven existing proposal artifacts are in scope; no application/schema/configuration or B05/E23 change, deployment, commit or push is authorized.

Earlier subject-binding revision evidence: **111 tests passed; 0 failures, 0 errors, 0 skipped**, including 26 then-new adversarial test methods. That run predates the persistent no-accounts directory revision below and does not establish its behavior. Real proofing authority, evidence/absence methods, directory completeness/revision controls, validity/independence and recovery/reassociation policies are still owner decisions. No PostgreSQL behavior/security has been validated.

## Persistent no-accounts directory revision

The proposed absence-evidence invariant now requires an exact institution-bound `directory_baseline_id` and `directory_generation`, independently attested directory completeness/history, consecutive retained change snapshots, a retained bootstrap receipt, a matching head/highwater and live directory snapshot, and explicit `absence_directory` governance. Account association revision remains NULL in no-accounts mode. The fixture's empty dictionary or a reference string cannot bootstrap authority; `DirectoryBaseline` is an explicit synthetic upstream trust prerequisite, never discovery of real completeness.

Every institution directory change advances the proposed generation, including deletion, reassociation, recovery/replacement, inactivity and change-away-and-back. Prior snapshots remain as tombstones. An old absence proof cannot match the new generation when rows disappear; removing legacy conflicts cannot restore it. Historical decisions/claims remain intact and unusable. Missing/unreliable history, baseline, authority or continuity anchor refuses. Observed directory integrity failures, including untracked rows, latch a separate security incident during commands or reads; deleting those rows or restoring an old checkpoint cannot clear it. This changes no decision/history/claim or successful audit. A fresh receipt also cannot authorize a historically associated subject: that transition needs a separately approved workflow and currently fails closed. No ordinary reset/rebootstrap clears an incident or forgotten history. Historical replay remains a recorded result, not current usability.

This institution-wide generation, retained history and highwater design is a **proposed technical control, not an owner-approved operating mechanism**. Directory writer/revision authority, completeness and alias coverage, tombstone retention, external continuity/anti-rollback and restore guarantees, generation granularity, all-writer transactions and evidence invalidation/incident/recovery responsibilities remain unresolved. The model cannot detect a coherent rollback of every trusted store or prove upstream completeness. Real owners must approve and implement those prerequisites before enablement. Full normative detail is in `rpc_contract.md`, **Persistent no-accounts directory invariant**; offline cases/results are in `offline_test_plan.md`.

Ready for independent review of this revised proposal/model; **not ready for final design approval, implementation or execution**. Both unconditional SQL refusals remain; SQL changes for this revision are comments only.

Earlier directory revision offline evidence (2026-10-17): **136 tests passed, 0 failures, 0 errors, 0 skipped**, including **25 then-new directory-focused test methods** and all 111 earlier methods. That run predates the strict-head/restoration hardening below. Its exact command and results remain in `offline_test_plan.md`, **Executed offline results for this revision**. No database or PostgreSQL behavior/security was validated.

## Strict directory-head and restoration hardening (2026-10-18)

The model independently validates the head generation as an actual positive integer before comparing it with any journal, highwater or receipt. Each of those generation fields and the writer expected generation must also exclude booleans, floating/numeric substitutes, strings, NULL/missing, nonpositive and inconsistent values. A registered receipt cannot make corrupted state trustworthy. Directory corruption latches a separate integrity marker; invalid receipt/request generation alone does not mark a healthy directory unreliable.

Focused tests now prove each accepted writer transition's exact generation increment, retained history prefix, actor/time/audit attribution and preservation of decision/claim/receipt state. They cover ordinary previous/identical-snapshot `restore`, independent highwater rollback, mixed head/history/highwater/baseline/live-state/receipt restoration, removal/recreation, same-account/different-account/Auth-only reassociation starting from current usable evidence, recovery/replacement and legacy cleanup. Ordinary writers and bootstrap refuse after a latched incident even when fields are repaired or other continuity markers are removed. Refused bootstrap attempts receive separate attributed denials; no ordinary incident recovery is added.

One test deliberately restores **all** model-held state to a previously valid snapshot, including history, audit, denials and integrity markers. It expects **true usability** because no independent continuity witness survives. That passing test documents an undetectable privileged rollback; it does not demonstrate permanent invalidation or durable history. A synthetic external unreliability signal makes the model refuse, but no real external continuity mechanism is implemented or approved. Real writer coverage, persistent tombstones, authoritative completeness, continuity across backup/rollback and operational incident recovery remain separate owner/technical prerequisites. Within the retained reliable lineage, ordinary cleanup/restoration cannot renew old evidence.

Prior strict-head/restoration evidence: **151 tests passed, 0 failures, 0 errors, 0 skipped; exit 0**, including **15 then-new hardening/restoration methods** and all 136 earlier methods. Exact output: `Ran 151 tests in 4.864s`, `OK`; see `offline_test_plan.md`, **Strict-head/restoration revision results**. That run predates the association-tuple revision below. Both SQL refusals remain; its SQL changes were comments only. PostgreSQL, real directory completeness, durable continuity and operational security remain unvalidated.

## Remaining directory validation gaps (2026-10-18)

The separate head's association tuple is now validated before comparison with the retained journal or live rows. Each association requires all declared fields, exact institution scope, bounded nonempty institution/subject/profile/user/Auth strings, an actual positive integer revision and a boolean active flag. Missing fields, boolean/float/string revisions and malformed containers refuse through the integrity-marker path, rather than escaping as attribute errors or passing dataclass equality. Journal association rows are also checked before snapshot comparisons. An invalid request receipt alone still does not mark a valid directory unreliable.

Nine new test methods independently corrupt only the populated head while keeping journal/highwater/live rows and registered evidence valid, cover well-typed tuple contradictions and missing fields, and assert refusal, attributed denial, false current usability, preservation of retained state and incident persistence after repair. A separate zero/False equality probe treats zero as invalid too; valid retained association revisions are always positive. Read-only fault detection latches without a decision denial. Test snapshots retain scalar types and actual record fields instead of relying on dataclass equality for malformed records.

Populated restoration now has direct coverage: identical populated rows refuse reuse of their current revision specifically under `restore`, then a higher revision succeeds; a prior account tuple refuses both its old revision and the newer related account's historical maximum, then succeeds above that maximum. Accepted restores advance generation and preserve history/audit; old absence evidence remains unusable. These are synthetic writer transitions, not approval to attach an account to a decision or an operational backup/restore guarantee.

Prior association-tuple offline evidence: **160 tests passed, 0 failures, 0 errors, 0 skipped; exit 0**, including all 151 preceding methods and nine new methods. Exact output: `Ran 160 tests in 9.958s`, `OK`; see `offline_test_plan.md`, **Association-tuple and populated-restoration revision results**. This revision changes five existing proposal artifacts only; `proposed_migration.sql` and `postgres_integration_tests.md` are unchanged. Both unconditional SQL refusals remain intact. No new files, database/SQL/migration operations, application/configuration or B05/E23 changes, deployment, commit or push occurred.

Ready for another independent proposal/model review; **not ready for final approval, implementation or execution**. Authoritative completeness, every-writer coverage, persistent history, external continuity across restoration, incident recovery, identity proofing and reviewer authority remain unresolved owner decisions. In-memory checks do not resolve these prerequisites or detect coherent privileged rollback of all trusted inputs.

## Account-mode types and malformed live rows (2026-10-18)

Account-mode verify/reverify/correct and current-usability reads now use the same checked directory state as absence mode before comparing account tuples. Live associations receive independent required-field, string, scope, positive-integer revision and actual-boolean activity validation; `True == 1` and `1.0 == 1` cannot authenticate malformed rows. The selected profile snapshot independently requires valid institution/profile/user/Auth strings and an actual positive integer association revision before ownership comparisons. Existing subject/source/entry, permission provenance, independent review, self-approval and historical-tuple checks remain mandatory.

Live collection uses the institution/profile map key to locate the institution partition, validates each local row before reading its fields and checks key/row agreement. Missing institution/revision or other declared fields and malformed row objects refuse through the directory integrity path. Authoritative faults latch the existing marker, preserve decisions/history/claims/receipts/successful audits, and receive attributed command denials; current reads return false and latch without a decision-denial event. Repairing a live row cannot clear the marker. Historical replay remains authorized recorded history, not current usability.

Malformed receipts, proposed writer payloads and supplied profile snapshots are distinct from detected authoritative directory corruption: they refuse without manufacturing a directory incident when the directory is healthy. A valid replacement profile snapshot can be checked again; this does not authorize changing a persisted account association or bypassing its writer/revision rules. Real directory completeness, every-writer coverage, independent continuity and incident recovery remain unapproved and unvalidated. SQL and the PostgreSQL integration plan are unchanged; both unconditional SQL refusals remain intact. This offline correction supplies no production security, durable continuity or final approval.

Prior account-mode/live-row evidence: **175 passed, 0 failures, 0 errors, 0 skipped; exit 0**. One run reported `Ran 175 tests in 6.755s`, `OK`, including all 160 preceding methods and 15 new adversarial methods; see `offline_test_plan.md`, **Account-mode/live-row correction results**. Only the oracle, its tests and three proposal documents changed. Ready for another independent proposal/model review; **not ready for final design approval, implementation or execution**.

## Four remaining model corrections (2026-10-18)

Retained proof, retained approval, selected current binding and serialized historical binding snapshots now receive independent required-field/type checks before equality. Positive association revisions and absence generations exclude booleans and numeric substitutes in every copy. Commands check each prior positive binding; current reads also check prior positives and the exact head approval. Historical checks validate structure and the unchanged association tuple, not current expiry/authority of old evidence: fresh correction remains possible under the existing contract. Valid authorized replay remains historical only. Malformed evidence alone does not set a directory incident.

Baseline records require their declared fields and bounded writer/provenance identifiers before authority or row access. Detected authoritative baseline faults follow the directory refusal/latch path; repairing a field or replacing an object cannot clear a recorded incident. Missing baseline bootstrap prerequisites retain the existing `UnresolvedPolicy` refusal. Profile/roster identifier types are checked before string operations; NULL/absent optional roll remains permitted, while roll-only matching cannot replace register number. Malformed supplied snapshots refuse without inventing persisted corruption.

Decision and permission expected revisions require actual nonnegative integers. Decision profile selection accepts only NULL or a bounded nonempty string; only NULL preserves an existing selection. Boolean/float revisions and false-like malformed profile values cannot pass validation or fallback. Existing ownership, permission, self-approval, correction and source controls remain mandatory.

See `offline_test_plan.md`, **Four-finding correction validation**, for executed results and isolated-copy tests. Both SQL refusals remain unchanged; no SQL counterpart or production behavior is validated. Directory ownership/completeness, every-writer coverage, durable history/tombstones, independent backup/rollback continuity, incident recovery authority, proofing/reviewer authority and existing policy/retention/access decisions remain unresolved. Coherent rollback of all model-held trusted state remains an undetectable trust boundary without an independent witness. Final design approval, implementation and SQL execution remain blocked.

Latest executed offline evidence: **199 passed, 0 failures, 0 errors, 0 skipped; exit 0**. Output: `Ran 199 tests in 44.656s`, `OK`. This includes 24 added methods and the unchanged 175 preceding methods/assertions. The test plan records the earlier unsuccessful correction run and its resolution. The final comparison against originals retained in session memory confirms exactly five existing files changed; SQL and the PostgreSQL integration plan are unchanged. No files/directories were created.
