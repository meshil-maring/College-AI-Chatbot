# B05 Stage 1.13 independent targeted re-review

2026-10-12, Asia/Calcutta.

**TARGETED RE-REVIEW FAIL — SPECIFICATION GAPS REMAIN**

The three current oracle revisions are consistent with the inspected source.
However, required check 1 is incomplete: the exact Stage 1.10 matrix contents or
an authenticated Stage 1.12 matrix patch are unavailable. Its before hash cannot
show the actual edits or establish that unrelated specifications were preserved.
This is a specification-verification evidence gap, not a newly demonstrated
incorrect outbox, cancellation or tenant-denial expectation. A complete targeted
PASS cannot be certified from the available evidence. Supply the prior matrix
matching the recorded raw identity, then review its actual diff.

B01–B07 and every execution gate remain open independently of this gap. Every
M01–M21 remains NOT RUN. This review gives no execution or collection approval.

Inputs: [Stage 1.12 report](B05_STAGE_1_12_TARGETED_ORACLE_REMEDIATION_REPORT.md),
[Stage 1.12 evidence](B05_STAGE_1_12_OFFLINE_HASH_EVIDENCE.json),
[Stage 1.10 independent findings](B05_STAGE_1_10_INDEPENDENT_READINESS_REVIEW.md),
entry inventories, actual preparation package, and relevant migration/backend
source. Stage 1.12 evidence raw SHA-256:
`e8118c9d3896902be1903141115fdf355b748c8b605d4c29fe4379e13f893bfc`.

## Actual diff and artifact checks

The package is untracked in this working tree. The scoped tracked diff against
HEAD is empty, and `git log --all --oneline --
scripts/validation/b05_containment/test_matrix.md` returns no history. Neither
result establishes its Stage 1.12 patch. Repository file searches found only the
current matrix, test and manifest, not prior copies.

The prior test and manifest were recovered in memory and accepted only after
their raw lengths and SHA-256 values matched the Stage 1.12 entry inventory.
Their actual unified diffs are retained in the
[verified patch](B05_STAGE_1_13_VERIFIED_TEST_MANIFEST_DIFF.patch).

| File | Verified result |
| --- | --- |
| test_preparation_safety.py | Prior bytes 7876 / SHA-256 `230a3ecf3abb0713d3b3afce7221430b93a945e7d8631d0bd93e1803748c737f`; current bytes 14464 / `2e8a7f5ae269a1c056451e0587362063d527b7374e23964e40cfc05916fe4982`. Exactly one new class with three source-text tests; original nine tests, imports and main guard preserved. |
| migration_manifest.json | Prior bytes 25314 / `76abfbb8679f31c7cbb8907a3262eb1141325cd88490c6d8240237dfea746bde`; current bytes 25694 / `52d1bfc38db7f1466b884cf8c971c75c44b44ebb77df1b54b08d5d49b0720208`. Only matrix/test hash and length refreshes plus targeted_oracle_revision changed. The 40 migration entries, twelve input identities/order, stage 1.10, existing approval status and other fields are preserved exactly. |
| test_matrix.md | Current bytes 106301 / `a654bf895a26acd8d5f19edb2535185925c36b532c79d26ecc54e6b50324a13d` match the manifest/evidence. Prior identity is bytes 84107 / `df11a19fc8f18c3b3fecfd61930657be52a06ed510c435f36b64ee05e474e4aa`. Current OB12/C12/T19 sections and M09/M12/M19 references were read, but the exact before/after matrix patch is UNVERIFIED. No guessed prior text is treated as evidence. |

The Stage 1.12 report, verifier, entry snapshot and historical records match all
171 supplied hash-record occurrences. All 115 unchanged entry files still match;
exactly the three reported preparation files differ from the entry inventory.
This establishes the bounded file-change set, not the line-level matrix delta.
The original Stage 1.12 verifier was inspected and rerun with its sole write
intercepted into memory. Windows newline translation reproduced the existing
evidence byte-for-byte; original evidence was not overwritten.

The new tests check finite schema/write-set text and important specification
markers. They are useful consistency checks, but do not independently prove
every case's semantics, trigger order, SQLSTATE, time or runtime outcome. The
source conclusions below come from reading the implementations and case setup.

## Original targeted findings reassessed

**1. Terminal outbox oracles: source-consistent in the current specification.**
The [worker schema and trigger](../../../supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql#L7)
and [delivery sequence addition](../../../supabase/migrations/20261002010000_phase_7_18_mailgun_webhook_reconciliation.sql#L6)
support exactly eighteen observation columns. There is no version column;
delivery_sequence is a generated identity. The FK permits institution invitation
aggregates, not platform invitations. Full outbox/attempt/event snapshots use
row IDs and contents rather than counts alone.

The actual terminal trigger at worker lines 112–128 requires OLD invited and
NEW non-invited, updating only matching pending rows: status cancelled,
locked_at/protected_token NULL, INVITATION_TERMINAL and updated_at=now(). It
does not alter attempt_count, delivery_sequence, provider correlation or attempt/
event history. OB12-T captures this exact write set. OB12-N preserves non-pending
and unrelated rows, including processing rows with protected tokens and existing
attempts. Their persistence remains a B06 source limitation.

Accepted finalization's [early return](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L353)
and lifecycle repeat/repair branch at B05 lines 907–933 do not perform a new
terminal transition. OB12-I correctly preserves the immediate retry baseline,
including intentionally pending rows on historical terminal invitations. Missing
lifecycle-event repair can add one event without sweeping the queue. Platform
commands leave institution queues unchanged.

Creation is separately specified from terminalization. The actual create6/
create7 bodies insert one pending row using schema defaults; the chosen setup
rules out same-email housekeeping updates. Legacy invite_approve7 retry returns
already_applied without creating another invitation/outbox. This does not promise
standalone creator idempotence. OB12-R matches the B05 rotation write set at
lines 452–514 under its explicitly pending-only setup; lease recovery/processing
behavior is outside that setup. It cancels old pending rows with
INVITATION_SUPERSEDED and inserts one new row. Stale timestamp retry is conditional
on an observed timestamp difference, not inferred time passage.

| Affected case group | Current supported before/after and retry oracle |
| --- | --- |
| M01–M08 | Empty replay/pre-fixture preservation, migration rollback, publication/ACL/hash/stopped-copy refusals, and S rollback compare the appropriate full baseline; no queue work is invented. |
| M09 | I(2) cancellation changes pending suffix 2 by OB12-T; creator/legacy approval inserts use OB12-C; legacy retry preserves rows; helper/claim denials and expiry-candidate reads do not mutate queues. |
| M10–M11 | Valid institution acceptance uses T; reserve/identity/issuer/scope failures use N; accepted retry uses I. Rotation uses R. Decision-clock failure rolls back grants and queue effects. Platform has no outbox. |
| M12 | Complete direct and eligible forged-recovery cancellation use T; guards/CHECK failures use N; identical direct/RPC retries and historical repair use I. |
| M13 | Acceptance/cancel/expiry winners use T; repeat/denied losers use I/N. Rotation winner uses R, legacy creation/retry C/I, cross-tenant loser retains its own pending queue. Each ordering has an independent baseline. |
| M14–M15 | Reached audit faults restore the pre-operation queue/history even if another trigger ran first. Fresh lifecycle transitions use T; historical repair/repeat I; audit/reset-predicate probes N. |
| M16–M18 | Reservation/provider/provision steps leave pending queues unchanged. Finalize commit uses T; before-COMMIT failure restores pending rows; lost response after commit retains terminal rows. Resolution/confirmation/recovery retries preserve the terminal baseline. No provider or SQL rollback equivalence is inferred. |
| M19–M21 | Membership/student/tenant-control calls do not create invitation emails; default/consumer probes preserve queues; mocked pre-database gate failure creates no database evidence. |

The OB12 register covers all 21 cases, retains NOT RUN and requires snapshots
after operation before restoration, then after rollback/commit. Row IDs/contents
restore on rollback; identity sequence consumption is not promised to roll back.
Current positive terminal oracles no longer conflict with the zero-change rule.

**2. M12 cancellation setup: source-consistent in the current specification.**
[C12](../../../scripts/validation/b05_containment/test_matrix.md#L1030) binds an
invited synthetic row with NULL accepted/terminal/acceptance fields, valid issuer,
created_at=fixture_anchor−1 day and expires_at=fixture_anchor+7 days. Institution
delivery columns use the actual Phase 7.15 schema, with a pending queue and
separate controls; platform invents no institution/delivery/updated_at columns.

The direct action changes only status and cancelled_at to an explicit validated
timestamptz fixture_anchor. It preserves identity, accepted fields, delivery and
institution updated_at. The [institution terminal CHECK](../../../supabase/migrations/20261001020000_phase_7_14_super_admin_university_admin_lifecycle.sql#L66)
requires non-NULL cancelled_at and NULL accepted_at; the platform schema has no
equivalent CHECK. Status-only institution cancellation is a separate 23514 case
with that constraint origin and zero changes, not a positive cancellation test.

Actual role/claims and empty routing/lifecycle settings are bound. Direct
cancellation produces OB12-T at observed transaction now(), separately from
the explicit fixture timestamp, plus one unrepaired unrecorded_initiator event
and an issuer-fallback institution admin projection. The platform projection
delta is zero. B05 guard/lifecycle bodies at lines 152–203 and 838–933 support
these results. No general automatic updated_at trigger for these rows was found
in the source chain.

Fresh lifecycle RPC assigns clock_timestamp(); server bounds replace assumed
fixture/host-clock equality. Repeats preserve its returned timestamp. Identical
direct retries preserve the explicit timestamp and existing event. Historical
repair preserves its stored timestamp, adds one repaired event, no historical
projection and no outbox change. The terminal guard omits cancelled_at from its
immutable field list: arbitrary timestamp overwrites are not asserted forbidden.
Matching forged recovery settings on a provider_started operation remain a
documented trusted-service exposure; the operation remains provider_started.
Wrong settings expect the exact 55P03 reconciliation diagnostic.

**3. M19 tenant isolation: source-consistent in the current specification.**
[T19](../../../scripts/validation/b05_containment/test_matrix.md#L1096) uses
confirmed active synthetic U(2)/H(2), admin-a@example.invalid, with only an active
institution-admin role in A/OA. The resource RB=R(4) is restaged together to B/OB
for active confirmed U(6); it preserves the existing request ID to avoid the
global pending (user_id, requested_role) uniqueness collision. Phase 6.13 child
scope checks support this paired restaging. Setup is specified, not loaded.

The actual [administrator guard](../../../supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql#L132)
checks service claims, actor activity, active admin role in the supplied tenant,
and active tenant. Both immediate/reject invoke it before request lookup at B05
lines 535–550 and 747–753. U(2), RB, B therefore expects exactly 42501 / 'Phase
8.1: active institution administrator required', rather than not_found/NULL.
Same-actor A and independent B-admin controls distinguish tenant scope from
inactive actor/role/tenant, bad claims or missing EXECUTE. There is no separate
permission-code or cryptographic human-identity check in these routines.

The guard performs no writes and reaches no audit insert. Full membership,
resource, identity, grant, queue and audit contents remain unchanged after nested
error recovery, before outer rollback. auth_security_events delta0 is correct;
no HTTP audit result is claimed. Authorized U(3)/H(3) with R(1), supplied B is
the separate lookup-miss control returning {not_found:true}/NULL and zero writes.

## Independent blockers and earlier findings

| Area | Stage 1.13 disposition |
| --- | --- |
| T1/T2/T3/C/A expected-error and restoration contracts | Retained in current matrix; tests/contract and baseline files preserved. No wrapper or engine verification established. Exact prior matrix diff remains unavailable. |
| Runtime identities and components | Image/digest/tool/engine/host/shim/supervisor/adapter/fake/observer/derivative identity and availability remain unresolved. No runtime inspected. |
| B01 | Actual credential/claim/human actor/role/BYPASSRLS boundary remains unapproved. Synthetic T19 claims cannot certify gateway identity. |
| B02 | Helpers, retained service defaults, direct-write bridges and external-consumer disposition remain open. |
| B03 | Actual creators/global defaults/cross-schema and extension compatibility remain open. |
| B04 | Target catalog and applied-byte provenance remain open; local manifest/ledger arrays prove no deployed equivalence. |
| B05 | assign4 self-grant/scope overwrite, create7/invite_approve7 supplied-actor trust, SC-06/SC-07 ordering and organization-admin compatibility remain hard blockers. |
| B06 | External consumers, adjacent audit mutation, reset incompatibility already after B05, retention/cutover, processing token persistence, historical queue repair and provider uncertainty remain open. |
| B07 | Exact owner approval, environment/component identities, approved derivatives/wrappers, bounded scope and cleanup proof remain open. |

The further Stage 1.10 coverage limit also remains: the rejected branch of
b05_decide_legacy_membership does not invoke the five-argument assignment guard
or validate actor_auth. The backend service at lines 656–705 checks management
authority and active tenant before calling it. T19 immediate/reject denial
semantics cannot be transferred to this different identity. The requested
synthetic mismatched-actor/Auth observation and owner disposition remain B01/B05
work outside the three targeted revisions; no deployed bypass is established.

## Preserved stops and safeguards

Raw entry checks and the scoped tracked diff preserve original drafts and the
successor validation copy. Direct source inspection confirms unconditional
review_stop/dependency_stop and the final ROLLBACK:

| Artifact | Stop lines | Final rollback |
| --- | --- | --- |
| SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql | 28 / 31 | 443 |
| SECURITY_CONTAINMENT_POST_B05_SUCCESSOR_DRAFT.sql | 42 / 45 | 475 |
| containment_successor.validation.sql | 42 / 45 | 475 |

Successor source/copy are byte-identical; ledger array has the exact forty
versions. prepare.py/runner_contract/bootstrap/fixtures/shared guard/top-level
runners/recovery contract/backend sources/authorization annex and prior review
artifacts are unchanged. The contract still has execution_authorized=false,
runtime_adapter=NULL and file_only_preparation. Shared ALLOWED_PURPOSES has no
B05 registration. Existing runner ownership/target checks and ON_ERROR_STOP=1
remain intact. No runner was invoked.

## Exact offline verification commands and results

Working directory `F:/Git Project/CollegeAIChatbot`, PowerShell. No preparation
main/plan is called. Tests import definitions only; the Stage 1.13 verifier uses
raw local files/JSON and the reviewed in-memory Stage 1.12 verifier capture.

```powershell
python -B -m unittest discover -s scripts/validation/b05_containment -p test_preparation_safety.py -v
python -B docs/reviews/student_enrollment_final_2026-10-11/verify_b05_stage_1_13_offline.py
git diff --no-ext-diff --no-textconv --exit-code HEAD -- scripts/validation docs/reviews/student_enrollment_final_2026-10-11/SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql docs/reviews/student_enrollment_final_2026-10-11/SECURITY_CONTAINMENT_POST_B05_SUCCESSOR_DRAFT.sql supabase/migrations scripts/maintenance/reset_supabase_data.sql backend/tests/B05_RECOVERY_CONTRACT.md
git diff --check
git status --short
```

All exited 0. Tests: **12/12 passed**, reported 0.060 seconds. The two Git diff
commands produced no diff/whitespace findings. Git warned that its global ignore
file was inaccessible; it was not inspected or changed. Status confirms the
pre-existing untracked entries remain and this review adds only four Stage 1.13
artifacts: this report, verifier, independent evidence and verified patch.

Stage 1.13 verifier output:

```text
PASS: supplied evidence records/current raw hashes; 115 preserved/3 changed
PASS: Stage 1.12 checks; byte-identical in-memory evidence; original untouched
PASS: exact hash-verified prior tests/manifest and unified diffs
PASS: changed-file whitespace; no SQL/runtime behavior verified
UNVERIFIED: exact prior matrix contents and Stage 1.12 matrix diff
WROTE: docs/reviews/student_enrollment_final_2026-10-11/B05_STAGE_1_13_INDEPENDENT_HASH_EVIDENCE.json
WROTE: docs/reviews/student_enrollment_final_2026-10-11/B05_STAGE_1_13_VERIFIED_TEST_MANIFEST_DIFF.patch
```

The intercepted Stage 1.12 checks independently reproduced 52/52 raw pins,
40/40 identities/order/declared transaction boundaries, 115/118 preserved files,
both stops/final rollback/copy equality/ledger array, 21 NOT RUN statuses, unchanged
runtime contract and seven OPEN decisions. Its historical printed WROTE message
refers to the intercepted call only. The original artifact remains unchanged.

The [independent evidence](B05_STAGE_1_13_INDEPENDENT_HASH_EVIDENCE.json) records
these bounded checks and the matrix-diff limitation. Its raw SHA-256 is
`ff508a6777aa1397a87073e5a611808f7bce9f03c75555237372ebcba085d1af`.
The verified patch raw SHA-256 is
`12949cf6d8d2ca18cde0e56c38d34ea3671c3568a6b001286f6eebbc0939425f`.
Final report/evidence/verifier whitespace and preservation checks use the
command recorded below; patch context-space markers are standard unified-diff
syntax and are not evaluated as Markdown/Python trailing whitespace.

```powershell
@'
import hashlib,json
from pathlib import Path
r=Path('docs/reviews/student_enrollment_final_2026-10-11')
e=json.loads((r/'B05_STAGE_1_13_INDEPENDENT_HASH_EVIDENCE.json').read_bytes())
for row in e['preserved_entry_files']+[c['after'] for c in e['changes']]+[e['supplied_stage_1_12_evidence'],e['verified_exact_diff']]:
    raw=Path(row['path']).read_bytes()
    assert (len(raw),hashlib.sha256(raw).hexdigest())==(row['bytes'],row['sha256']),row['path']
for name in ['B05_STAGE_1_13_INDEPENDENT_TARGETED_RE_REVIEW.md','B05_STAGE_1_13_INDEPENDENT_HASH_EVIDENCE.json','verify_b05_stage_1_13_offline.py']:
    p=r/name
    assert all(line==line.rstrip() for line in p.read_text(encoding='utf-8').splitlines()),name
print('PASS: all 118 entry current identities, original Stage 1.12 evidence and verified diff preserved; Stage 1.13 source/report/evidence whitespace clean')
'@ | python -B -
```

Exit 0; printed the exact PASS line in the command. The final scoped tracked
diff and `git diff --check` were also rerun separately: both exit 0, no findings.

No AGENTS.md was found in the repository or checked parents. The first read
batch exceeded the output budget; relevant documents/source ranges were reread
in smaller chunks before conclusions. No failed runtime attempt occurred.

No SQL/migration/runtime case/provider, Docker/PostgreSQL/database connection,
secret inspection, deployment, push or executor implementation occurred. Local
file identities are not live database, consumer-absence or owner-approval proof.
Resolving the exact matrix-diff evidence gap can enable a targeted re-review
PASS; it would leave B01–B07 and execution authorization open.
