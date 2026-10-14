# B05 Stage 1.10 independent source readiness re-review

2026-10-12, Asia/Calcutta. **READINESS REVIEW FAIL — BLOCKERS REMAIN.**

The reported offline integrity results are reproducible. The expanded transaction,
runtime-identity and decision specifications materially address Stage 1.9's
preparation gaps, but the positive terminal-transition oracles and some negative
setups still need source-level clarification. Runtime identities/components,
compatibility, consumers and B01–B07 decisions remain unresolved. All M01–M21
remain **NOT RUN**. This review grants no execution or collection authorization.

Reviewed input: manifest raw SHA-256
`76abfbb8679f31c7cbb8907a3262eb1141325cd88490c6d8240237dfea746bde`;
[existing Stage 1.10 evidence](B05_STAGE_1_10_OFFLINE_HASH_EVIDENCE.json) raw SHA-256
`7a3c4660ee2c3497bfca68d7ab95108958f5acad07c29f2cfe01eae95981d91b`.
These are observed file identities, not approved identities.

## Findings requiring preparation changes

1. **High — Positive terminal transitions omit required outbox mutations and
   conflict with the blanket zero-change rule.** The matrix states that all
   unlisted row/permission-grant/audit deltas are zero
   ([matrix:323](../../../scripts/validation/b05_containment/test_matrix.md#L323)).
   Its concrete M09 operation closes I(2) as cancelled and specifies a lifecycle
   event, without specifying its outbox changes
   ([matrix:479](../../../scripts/validation/b05_containment/test_matrix.md#L479)).
   The supplied fixture has a pending outbox row with suffix 2
   ([fixture:101](../../../scripts/validation/b05_containment/fixtures_pre_b05.sql#L101)).
   The preserved terminal-email trigger changes every matching pending row to
   cancelled, clears locked_at/protected_token, sets last_error_category to
   INVITATION_TERMINAL and assigns updated_at=now()
   ([worker migration:112](../../../supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql#L112)).
   Successful institution acceptance/cancellation/expiry similarly needs this
   oracle whenever pending rows exist; retries and historical event repair need
   a separate no-new-transition oracle. Add explicit before/after outbox fields,
   matching-row counts, unchanged non-pending/unrelated rows and rollback
   assertions across M09–M16. Clarify that row-count delta zero does not imply
   unchanged existing row contents. Otherwise a future runner could either fail
   correct source behavior or overlook retained token material. This is a
   specification gap; no trigger behavior has been observed at runtime.

2. **Medium — M12 direct-cancellation variants do not bind the complete UPDATE
   needed to reach the intended success/exposure.** M12 specifies successful
   direct invited-to-cancelled updates and a forged-recovery setting variant
   ([matrix:584](../../../scripts/validation/b05_containment/test_matrix.md#L584),
   [matrix:591](../../../scripts/validation/b05_containment/test_matrix.md#L591)).
   For institution invitations, the retained terminal-state CHECK requires
   cancelled_at IS NOT NULL and accepted_at IS NULL
   ([lifecycle migration:66](../../../supabase/migrations/20261001020000_phase_7_14_super_admin_university_admin_lifecycle.sql#L66)).
   An otherwise eligible UPDATE that changes only status can pass the B05 routing
   guard and still fail this CHECK with 23514 instead of demonstrating the intended
   successful cancellation. Specify the changed columns and valid timestamp/state
   values per invitation kind, the actual effective role/GUC baseline, and the
   outbox/lifecycle/projection outcomes from finding 1. Keep a status-only
   constraint-negative variant separate. No executable wrapper is required to
   make this textual setup reviewable.

3. **Medium — M19's wrong-tenant return oracle leaves the actor setup unspecified.**
   M19 requires immediate approval to return not_found and rejection to return
   NULL for a wrong request tenant
   ([matrix:800](../../../scripts/validation/b05_containment/test_matrix.md#L800)).
   Both routines call phase81_assert_institution_admin for the *supplied tenant*
   before selecting the request
   ([B05:540](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L540),
   [B05:750](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L750)).
   For example, R(1), tenant B and actor U(2), who is admin of A, encounter the
   administrator guard first. To isolate lookup absence, bind R(1), B and U(3),
   the active B administrator, with valid matching service claims; then require
   not_found/NULL and zero writes. Retain U(2)/B as a separate 42501 authorization
   variant with the exact guard diagnostic. Generic instructions to restage an
   earlier failure do not replace these case-specific preconditions.

The detailed M19 distinction between strict legacy-decision retries and
immediate/reject same-status retries agrees with the preserved bodies
([matrix:788](../../../scripts/validation/b05_containment/test_matrix.md#L788));
it is not an additional finding. Changed actor/reason behavior must remain
specified per identity rather than generalized across all membership commands.

## Stage 1.9 reassessment and remaining boundaries

| Area | Stage 1.10 re-review |
| --- | --- |
| Continuing expected errors | T1 specifies a single invoker statement inside a nested exception subtransaction, exact SQLSTATE plus origin, assertions outside the catch and outer-savepoint restoration. T2/T3 distinguish whole-file abort and committed/concurrent steps. ON_ERROR_STOP remains enabled. Source design is improved; wrapper and engine verification remain absent. |
| M01–M21 oracles | All 21 detailed sections and statuses are present. NULL/error, audit fault reachability, legacy overload differences, decision-clock expiry and race order are substantially clearer. Findings 1–3 prevent complete oracle acceptance. Wider academic/attendance/test consumers remain explicitly blocked. |
| Runtime identities | Required PostgreSQL 170006/vector 0.8.0/btree_gist 1.7 are requirements only. Image, CLI, engine/API/Desktop, host/interpreter/config, shim/supervisor/adapter/fake/observer and derivative identities remain unresolved. No availability inferred. |
| Legacy compatibility | assign4 self-grant/scope overwrite, create7/invite_approve7 supplied-actor trust and organization-admin disposition remain hard blockers. No signature/body/grant changes are approved by this review. |
| Hash versus SQL refusal | M07 now distinguishes refusal before create/SQL from named SQL guards and comparison to the tampered baseline. Ledger versions do not prove applied bytes. |
| Maintenance | Reset incompatibility already after B05 is correctly identified. The proposed predicate-only negative check does not execute the reset file or establish earlier reset preconditions. |
| Decisions | B01–B07 remain OPEN with owner identities and approvals unresolved. The E23 authorization annex remains a draft. Source work does not establish external-consumer absence or deployed equivalence. |

One further source coverage limit should remain explicit in B01/B05: the
rejected branch of b05_decide_legacy_membership does not call the five-argument
assignment guard and does not validate p_actor_auth_user_id
([B05:775](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L775)).
The backend checks management authority and active tenant before calling it
([service:656](../../../backend/app/services/tenancy.py#L656)). Thus approval's
actor/auth rejection oracle cannot be transferred to this service-only rejection
branch. Add a source-derived synthetic observation for a mismatched supplied
actor/Auth pair and an owner disposition of the backend/service trust boundary;
no deployed bypass or exploitation is established here.

## Independent offline verification

- Re-ran `python -B -m unittest discover -s scripts/validation/b05_containment -p test_preparation_safety.py -v`: exit 0, **9/9 passed**. These test path guards and fixture linkage, not PostgreSQL or runtime cases.
- Independently compared current raw hashes/lengths to the evidence's pinned,
  preserved, manifest and review-artifact records; all matched.
- Ran the reviewed Stage 1.10 verifier with its sole Path.write_text intercepted
  into memory. Its checks passed: **52/52 pins**, **40/40 migration
  identities/order/declared boundaries**, **76/80 preserved entry files**, exactly
  four allowed changes, successor-copy equality, preserved stops/final rollbacks,
  exact ledger array, 21 NOT RUN cases, seven open decisions and unresolved pins.
  Captured output, using Windows write_text newline translation, reproduced the
  existing evidence **byte-for-byte**. The verifier's printed WROTE line refers
  to the intercepted call; the original evidence was not overwritten.
- The initial in-memory comparison used LF without Windows newline translation
  and failed the byte-equality assertion. The corrected CRLF-aware capture
  passed; the mismatch was in the comparison harness, not the supplied evidence.
- The scoped tracked preservation diff against HEAD and `git diff --check`
  returned exit 0 with no diff output. Git reported its inaccessible global
  ignore file; it was not inspected or changed. Untracked-file preservation is
  supported by the raw-entry comparison rather than tracked diff alone.

The separately emitted [independent hash evidence](B05_STAGE_1_10_INDEPENDENT_HASH_EVIDENCE.json)
records this review's current manifest/package/artifact and historical entry
comparisons. Original evidence, report, package, migrations, safeguards and
authorization annex are preserved. This turn adds only these two review artifacts.

Read-only source inspection included the matrix, README, runner contract,
preparation code/tests, bootstrap/fixtures, B05, successor preflight, relevant
legacy guards/outbox/constraints and backend decision boundary. All 40 migration
identities were verified; this is not a new full semantic audit of every statement
in all 40 files. No AGENTS.md was found in repository or checked parents. Two
inspection commands needed correction (a nonnumeric Select-Object count and a
guessed legacy filename); neither supplied verification evidence.

No preparation plan/main, validation runner, SQL, Docker command, service,
provider, credentials, external collection or deployment was executed. Only
offline Python tests/checks, source reads, Git checks and these review-artifact
writes occurred. Complete findings 1–3 as source-only specifications and retain
the remaining evidence/owner decisions before presenting any separately bounded
execution proposal. Successful offline verification does not authorize execution.
