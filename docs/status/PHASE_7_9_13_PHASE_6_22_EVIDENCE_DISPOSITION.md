# Phase 7.9.13 — Phase 6.22 Evidence Artifact Disposition & Commit Unblock

## Phase

Phase 7.9.13 — Phase 6.22 Evidence Artifact Disposition & Commit Unblock

## Initial Blocker

The Phase 7.9.12 commit gate was blocked because
`docs/evidence/complete_product_demo_phase_6_22.json` differed from the
committed 40/40 PASS evidence and contained a 35/39 result. The artifact was
preserved during this investigation and remains byte-for-byte unchanged.

## Comparison

| Property | Committed | Working tree |
| --- | --- | --- |
| Overall result | 40/40 PASS | 35/39; 4 FAIL |
| Test/check count | 40 | 39 |
| Passed | 40 | 35 |
| Failed | 0 | 4 |
| Warned | 0 | 0 |
| Skipped | 0 | 0 |
| Generated | 2026-09-23 12:01:34 UTC | 2026-09-29 16:42:44 UTC |
| Completed | 2026-09-23 12:03:10 UTC | 2026-09-29 16:43:09 UTC |
| Environment | `http://127.0.0.1:8000`, `dev_test_mode=true`, institution `GIT` | Same |
| Version/commit | Evidence committed in `9f970d5` (Phase 6.22) | No source commit/version field in JSON |
| Evidence source | Documented Phase 6.22 live validation | Same script, later run |

The JSON top-level schema is unchanged. All 39 working-tree checks have unique
names and statuses that reconcile exactly to the summary (`35 + 4 = 39`). The
three grounded-answer records agree with their three failed checks. There are
no WARN, SKIP, duplicate names, or records with a missing status. One check
present in the committed artifact, `admin role resolved server-side`, is absent
from the newer artifact. The current generator emits that check only when the
`/api/v1/auth/me` request returns HTTP 200. The newer artifact has no
`admin_identity` observation, so this check is **MISSING EVIDENCE / NOT RUN**;
the exact HTTP outcome is not recorded. The top-level summary correctly counts
only the 39 recorded checks and does not claim this absent check passed.

## Provenance Investigation

- Git reports the artifact as a tracked modification, not an untracked file.
- Its committed version was introduced with Phase 6.22 in commit `9f970d5`.
- The working-tree timestamps identify a separate run on September 29, six days
  after the committed evidence.
- `backend/scripts/validation/test_complete_product_demo_phase_6_22.py`
  documents this exact JSON output path and writes the checks it collected,
  including failures. The admin-role check is conditional on `/auth/me`
  returning HTTP 200; the newer artifact lacks that check and its related
  observation. Its final summary and exit code reflect failed checks; it does
  not manufacture a passing result for a partial run.
- The Phase 6.22 status report documents the earlier September 23 run as
  40/40 PASS. It does not claim the September 29 run passed.
- The Phase 7.9 worktree changes concern local migration reconstruction and the
  `users.id` contract. The changed evidence records failed Phase 6.22 public
  chat generation checks and is separate from that recovery scope.

These facts establish a genuine newer Phase 6.22 validation run. They do not
establish the underlying cause of its generation endpoint errors. The artifact
contains no server trace or provider error details, and no Phase 6.22 rerun was
needed to identify its provenance.

## Current Evidence Result

- Total checks: **39**
- Passed: **35**
- Failed: **4**
- Warned: **0**
- Skipped: **0**
- Duplicate check names or missing status fields: **none detected**
- `admin role resolved server-side`: **MISSING EVIDENCE / NOT RUN** in this
  artifact; `/auth/me` outcome and reason are **UNKNOWN**

The four exact failed checks and evidence are:

| Check | Recorded evidence | Classification |
| --- | --- | --- |
| Grounded answer: “When does the central library close on weekdays?” | `status=http_500`, zero retrieved chunks in the answer response | **FAIL**; underlying server/provider cause **UNKNOWN** |
| Grounded answer: “How many books may a student borrow at one time from…” | `status=null`, zero retrieved chunks, empty answer | **FAIL**; underlying cause **UNKNOWN** |
| Grounded answer: “What is the late return fine per book per day?” | `status=http_500`, zero retrieved chunks in the answer response | **FAIL**; underlying server/provider cause **UNKNOWN** |
| Unknown question returns a valid response contract | recorded status `null` | **FAIL**; underlying cause **UNKNOWN** |

Other retrieval and ingestion checks passed in that run, including four retrieved
chunks, source/document provenance, tenant filtering, and the configured
embedding dimension. Those checks do not turn the failed generation checks
into passes. The exact individual outcomes are recorded in the preserved JSON;
there is no additional request trace in the artifact to explain the `http_500`
or null responses, nor the absent admin-role check.

## Disposition

**PRESERVE_AND_RECLASSIFY**

The September 29 artifact is valid output from a later Phase 6.22 validation
execution. Keep it exactly as-is as Phase 6.22 evidence, including its failures.
It is legitimate newer evidence, and it is unrelated to the Phase 7.9 migration
recovery series. No evidence was changed to make the result appear successful.

## Commit Boundary

`docs/evidence/complete_product_demo_phase_6_22.json` **does not belong in the
Phase 7.9 recovery commit**. Keep it separate as Phase 6.22 evidence. The Phase
7.9.12 recovery commit gate is now `READY_TO_COMMIT`; this disposition does not
stage or commit any files.

## Validation

Validation results below are reused from Phase 7.9.12 because the application,
migration, validation, and test code has not changed since those runs. Phase
7.9.13 changed only status documentation; the evidence JSON was not modified.

- Migrations: **PASS** — 16 ordered migrations; two fresh local resets passed;
  ledger count 16; Phase 6.11, 7.2, and 7.4 objects and hardening passed.
- Backend normal suite: **PASS** — 2,126 passed, 15 skipped, 6 warnings; the
  two debug-only tests were explicitly deselected in normal mode.
- Backend debug-only suite: **PASS** — 2 passed separately with `DEBUG=true`.
- Frontend: **PASS** — 50 files, 431 tests, 0 failures.
- TypeScript: **PASS** — `npx tsc --noEmit -p tsconfig.json`.
- Build: **PASS** — `npm run build`, 97 modules transformed.
- `git diff --check`: **PASS** in Phase 7.9.12; run again after this report.

The earlier all-collected backend run also reported the two debug-only tests as
failures with `DEBUG=false`; both passed in their intended debug-mode run. The
split suite result above reports the established execution contract.

## Remote Safety

```text
Remote database modified: NO
Remote Auth modified: NO
Remote migrations applied: NO
Remote data modified: NO
```

Phase 7.9.13 performed repository-only provenance and JSON inspection. No
Supabase operation was run.

## Final Status

```text
COMPLETE
```

The artifact has a defensible disposition, is preserved unchanged, and is
excluded from the Phase 7.9 recovery commit. Phase 7.9.12 can proceed with
`READY_TO_COMMIT` for the recovery-scoped files. A future local commit decision
does not authorize remote reconciliation or deployment.
