# Student enrollment schema review package

Prepared 2026-10-11 (Asia/Calcutta) in the active checkout. **Complete as a design/static review package; not an installed or runtime-validated schema.** No application/frontend/harness/migration source was changed, no database contacted, no SQL or database test executed, and no deployment, push or remote Supabase operation performed.

The SQL draft has now received a second static repair review. [SQL_REPAIR_REVIEW.md](SQL_REPAIR_REVIEW.md) provides line-specific fixed findings, unresolved dependencies, source contracts, and required runtime cases; it takes precedence over earlier draft details in this package. Changes enforce initial-admission institution membership, explicit source/destination handoff actors, same-day placement closures, finite semester-bounded placements, curriculum applicability, immutable identifier bindings, stricter lifecycle/event snapshots, and exact retries after midnight. Postflight now reconciles CHECK/FK/PK/UNIQUE/EXCLUDE counts for every table. The supplied placement DDL already had **eight** explicit CHECKs; all eight are now named and checked individually. The handoff signature now has eight arguments.

The unconditional review exception and final ROLLBACK are preserved. Historical corrections remain rejected pending a separately authorized workflow. Remaining blockers include curriculum-stage/attempt policy, stale prepared-admission cleanup, placement-aware master/calendar guards, historical application/context adapters, authority/audit privilege containment, revocation concurrency semantics, and PostgreSQL catalog/role/transaction/concurrency validation. Existing source grants allow audit truncation and client default function execution; prerequisite assertions now fail closed until separately reviewed containment addresses those effective privileges. No claim is made about today's database state.

[STATIC_REVIEW_RESULTS.json](STATIC_REVIEW_RESULTS.json) now records the rerun via [verify_review_static.py](verify_review_static.py), including all constraint categories, ten routine signatures/call arities, current SQL/source hashes, report links, and preservation of 1,074 existing files. The original SQL and original static results are retained in `.before_repair` files. **PostgreSQL validation has not run.**

## Deliverables

All files reside in `docs/reviews/student_enrollment_final_2026-10-11/`, separated from historical reports and migrations.

| Required artifact | Contents |
| --- | --- |
| [ADR-ENROLLMENT-003.md](ADR-ENROLLMENT-003.md) | Recommended identity, identifier, admission, progression, event and historical-access decisions, with approval gates. |
| [STUDENT_ENROLLMENT_SCHEMA_FINAL_REVIEW.md](STUDENT_ENROLLMENT_SCHEMA_FINAL_REVIEW.md) | Verified schema contracts, four justified entities, constraints, lifecycle policies, master-guard reuse, unresolved decisions. |
| [student_enrollment_schema_review_draft.sql](student_enrollment_schema_review_draft.sql) | New proposed core DDL, guarded admin routines, atomic handoff, RLS/ACLs, append-only history and pre/postflight assertions. Unconditional review stop and ROLLBACK; no legacy changes. |
| [STUDENT_ENROLLMENT_MIGRATION_PLAN.md](STUDENT_ENROLLMENT_MIGRATION_PLAN.md) | Dependency map, nine gated stages, deterministic/quarantined mapping, historical associations, contracts/caches, atomicity and rollback limits. |
| [STUDENT_ENROLLMENT_TEST_PLAN.md](STUDENT_ENROLLMENT_TEST_PLAN.md) | 35 scenarios with explicit outcomes, existing regressions, future fixture/runner contract and runtime acceptance gates. |
| [STUDENT_ENROLLMENT_SECURITY_REVIEW.md](STUDENT_ENROLLMENT_SECURITY_REVIEW.md) | Conflicting snapshot interpretation, authority/academic access prerequisites, role/column/default/overload checks, service-role and routine implications. |
| [REVIEW_SUMMARY.md](REVIEW_SUMMARY.md) | Evidence, decisions, remaining risks, artifact inventory and disposable-validation decision. |

Supporting artifacts: [synthetic_fixtures.json](synthetic_fixtures.json) contains invented structured fixture specifications and all 35 expected outcomes; [SOURCE_EVIDENCE.json](SOURCE_EVIDENCE.json) captures Git HEAD, initial status and SHA-256 preservation baseline for 1,074 existing files; [STATIC_REVIEW_RESULTS.json](STATIC_REVIEW_RESULTS.json) records the bounded static checks actually performed and final artifact hashes.

## Evidence and recovery

No applicable AGENTS.md was found in the repository or checked ancestors (`F:/`, `F:/Git Project/`). Existing modified and untracked validation-harness/evidence changes were preserved. Fingerprinting is preservation evidence, not a claim every inventoried file was read semantically.

| Verified current source evidence | Conclusion |
| --- | --- |
| [Admin-1 student definition](../../../supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql), lines 41–101; [identity migration](../../../supabase/migrations/20260912000000_phase_6_2_student_identity_model.sql) | Preserve student/user uniqueness and current identifier namespace; membership/approval/lifecycle are currently conflated on the identity. |
| [Baseline](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql), lines 741, 899, 999, 1049, 1173–1174 | Existing semester/year composite unique key, academic ancestry, Auth/public-user distinction, and explicit future client function defaults. |
| [Registration](../../../backend/app/services/user_registration.py), lines 110–145; [student registration](../../../backend/app/services/student_registration.py), lines 79–122 and 473 | Identifier-derived student_number is not separate issuer proof; default registration date is not historical admission evidence. |
| [Attendance guard](../../../supabase/migrations/20260913000000_phase_6_7_attendance.sql), line 82 onward; [results guard](../../../supabase/migrations/20260913010000_phase_6_8_results.sql), line 249 onward; [notification guard](../../../supabase/migrations/20260914000000_phase_6_11_student_notifications.sql) | Current student tenant is reused on writes, including historical updates. New episode tables alone do not repair record ownership. |
| [Attendance workflow](../../../supabase/migrations/20261012000000_faculty_attendance_workflow.sql), lines 92 and 289; [faculty-test workflow](../../../supabase/migrations/20261013000000_faculty_tests_examination.sql), lines 388–540 | Current identity matching/roster reconciliation and publication recomputation need coordinated replacement before lifecycle cutover. |
| [Master-data guards](../../../supabase/migrations/20261016000000_academic_master_data_management.sql), lines 19, 38 and 155; [convergence](../../../supabase/migrations/20261016010000_academic_curriculum_semester_convergence.sql) | Reuse ancestry helper/guards, preserve alternate curriculum convergence, add future placement-aware calendar checks without duplicating master triggers. |
| [Service DB client](../../../backend/app/db/supabase.py), lines 20–71; [security](../../../backend/app/core/security.py), lines 99–140; student context/profile services | Server-derived identity and permissions are essential with privileged backend access; new context selection must remain own/tenant checked. |
| [Student cache](../../../frontend/src/features/student/useStudentResource.ts), line 37; [student client](../../../frontend/src/services/studentApi.ts); AuthProvider/query client | Current keys omit enrollment/placement context; introduce explicit context revision and late-response isolation. Academic projections currently omit internal identifiers. |
| [Saved harness review](../../evidence/enrollment_harness_remediation/REVIEW.md), verification_summary.json and docker_availability.json; active guard/runner/test source | Prior 27 Python + 92 mock + 8 parse results were inspected, not rerun. Docker was reported unavailable; actual replay/engine behavior remains pending. Enrollment runner/purpose does not yet exist. |

The archived v2 ZIP was inventoried directly: **14 entries, no SQL**. Its three enrollment documents were recovered and inspected from the preserved extracted source. Their intended top-level documentation paths are absent. No exact older enrollment SQL draft was recovered; the SQL here is newly authored and must be reviewed on its own bytes. The ZIP/source/historical reports were not overwritten.

Root `schemaV2_export.sql` has 60 table definitions; tracked `docs/schema/schemaV2_export.sql` has 26 and no students. Relevant definitions were read, including the alternate curriculum column. Neither export is treated as live authority. All 39 current migration filenames are present; highest `20261016010000` is future-named relative to today's review date. Choose a later forward migration version only at approved implementation time.

Earlier M1/security reports describe local catalog observations on 2026-10-10, including empty academic populations, RLS/client privilege defects, exposed RPCs and writable authorization resources. These remain **historical findings requiring later catalog revalidation**, not verified current database facts. No statement about today's local/remote population, ledger or ACLs is made.

## Decisions and material risks

Keep one stable identity; use all four new entities; reserve one operational enrollment globally; reuse institution-owned identifiers across same-person readmission; use immutable institution/known program and separate placements/attempts; preserve missing dates as unknown/quarantined. Require both institutions for transfer, atomic state/event/audit writes, operation-key retries and server-derived actors. Recommend no browser table/RPC access.

Critical prerequisites are effective client denial on trusted authority and legacy academic tables, complete overload/default/column/inherited privilege review, and preserving all existing security guards. Current source publication and historical-tenant dependencies cannot be fixed by additive core DDL alone. Legacy ambiguity must remain quarantined. Rollback after multiple episodes/attempts cannot flatten data to a single student membership.

Institutional decisions remain: one operational episode versus dual enrollment; identifier case/namespace/mandatory values and nonreuse; attempt/curriculum equivalence; leave limits; transfer consent and approval expiry; archived-institution historical access; retention/anonymization; and authorized backdated or ownership-changing correction workflows. Conservative defaults are supplied. The core draft deliberately rejects operational backdating, zero-length interval transitions, and cancellation needing prepared-placement cleanup; these need separately reviewed adapters before those extended workflows are enabled.

## Verification limits and next steps

Static checks cover package completeness, link targets, fixture JSON/scenario consistency, source preservation, whitespace, SQL delimiter/parenthesis balance, routine call/signature inventory and declared constraint counts. They do **not** parse PostgreSQL/PLpgSQL grammar or prove function, trigger, FK, RLS or concurrency behavior. No installed PostgreSQL parser library was available and none was installed. No pytest, Vitest, harness tests, Docker or database validation ran in this task. Consult STATIC_REVIEW_RESULTS.json for the actual findings.

**NO-GO for disposable local SQL validation now.** Remaining blockers:

1. Explicit user approval for the exact SQL candidate and database testing has not been given.
2. Docker Desktop remains unavailable per saved evidence; engine/image/bootstrap/storage/cleanup checks and full-chain replay are pending.
3. Current local catalog and security prerequisites need an authorized recheck and a separately reviewed containment migration; this draft intentionally fails if they are absent.
4. Institutional defaults and the exact new SQL hash require acceptance; the review stop/ROLLBACK must only be changed in a later approved migration.
5. A dedicated enrollment-purpose runner/fixture loader and approved harness allowlist extension are needed. Full end-to-end validation additionally requires historical-record/backend/trigger/frontend adapters, including calendar and publication fixes.

Once blockers 1–5 are resolved for a defined **core-only** scope, proceed with fresh full migration replay and core schema/role/concurrency fixtures in the run-owned disposable container. Keep integration tests gated until their adapters exist. Operational cutover and remote deployment remain separate approvals requiring the complete acceptance matrix and populated mapping/rollback evidence.
