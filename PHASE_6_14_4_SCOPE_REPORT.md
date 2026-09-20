# Phase 6.14.4 Scope Report — Student Academic Context Resolver

## 1. Files Changed

| File | Change |
| --- | --- |
| `backend/app/schemas/student_academic_context.py` | **New** — student-safe academic-context contracts (`extra="forbid"` everywhere) |
| `backend/app/services/student_academic_context.py` | **New** — resolver service (`get_student_academic_context`, `DEFAULT_ATTENDANCE_LIMIT = 200`, `DEFAULT_TEST_RESULTS_LIMIT = 100`) |
| `backend/tests/test_student_academic_context_6144.py` | **New** — 20 hermetic tests |
| `PHASE_6_14_4_SCOPE_REPORT.md` | **New** — this report |

No existing file was modified. The generation pipeline (`AIContext`,
`app/services/context.py`, `app/services/generation.py`, prompts, retrieval,
vector search), the attendance service, the results service, authentication,
tenancy, and the RAG stack are all untouched.

## 2. Migration Created

**None.** No new database tables, columns, or indexes were required — the
resolver only reuses the existing Phase 6.14.1/6.14.2/6.14.3 services and
repositories.

## 3. Academic Context Schema

`backend/app/schemas/student_academic_context.py` — all models use
`ConfigDict(extra="forbid")`; no internal database identifiers and no
auth secrets exist anywhere in the tree:

```text
StudentAcademicContext            (extra="forbid")
├── student: StudentAcademicIdentity
│   ├── name: str | None            (reserved; always None in this phase)
│   ├── student_number: str | None
│   ├── register_number: str | None
│   └── university_roll_number: str | None
├── institution: StudentAcademicInstitution
│   ├── institution_name: str | None
│   └── institution_code: str | None
├── attendance: StudentOwnAttendance          (Phase 6.14.2 contract reused verbatim)
│   ├── summary: StudentAttendanceSummary     (counts + attendance_percentage)
│   └── records: list[StudentAttendanceRecord] (date / status / notes)
└── results: StudentContextResults
    ├── summary: StudentOwnResultsSummary         (academic results counts)
    ├── records: list[StudentAcademicResultRecord] (result_type, sgpa, cgpa, credits, status, issued_at)
    ├── test_summary: StudentOwnTestResultsSummary (test-result counts)
    └── test_records: list[StudentTestResultRecord] (test_name, course_code/name, marks, percentage, grade)
```

Notes:
- `student.name` is a reserved `None` slot: the `students` contract consumed
  by the existing self-service layer carries no verified name field, and no
  name is fabricated (a new direct `users`-table query would be a new
  data-access pattern, out of scope).
- `attendance` embeds the existing `StudentOwnAttendance` model unchanged;
  `results` reuses the existing Phase 6.14.3 record models unchanged and
  wraps both result families (consolidated academic + per-test).

## 4. Resolver Behavior

`get_student_academic_context(current_user, academic_year_id=None,
semester_id=None, date_from=None, date_to=None, client=None,
attendance_limit=200, test_results_limit=100) -> StudentAcademicContext`

Flow (exactly as specified):

```text
JWT → current_user → Student Academic Context Resolver
  ├── student_academic_profile.get_academic_profile   (6.14.1: identity + institution labels)
  ├── student_attendance.get_own_attendance           (6.14.2: summary + records)
  ├── student_results.get_own_results                 (6.14.3: published academic results)
  └── student_results.get_own_test_results            (6.14.3: published test results)
→ StudentAcademicContext
```

- Identity is derived EXCLUSIVELY from `current_user` (`user_id` key, the
  JWT subject). The signature contains **no** `student_id` / `user_id` /
  `institution_id` / `email` / `register_number` /
  `university_roll_number` parameter — asserted by tests 15/16 via
  `inspect.signature` (unknown kwargs raise `TypeError`).
- The resolver never touches the database itself and never catches or
  bypasses a denial from a delegated service; `AppError`s propagate
  unchanged (400 INVALID_USER_CONTEXT, 404 STUDENT_PROFILE_NOT_FOUND,
  403 TENANT_MISMATCH, 422 INVALID_FILTER).
- Empty academic data is not an authorization failure: any combination of
  no attendance / no results yields a valid context with empty collections
  and zero-count summaries (tests 7, 8, 9).

## 5. Attendance Integration

Delegates to `student_attendance.get_own_attendance` (Phase 6.14.2) with
`academic_year_id`, `semester_id`, `date_from`, `date_to`, `client`, and
`limit` forwarded verbatim. The existing service keeps the full
authorization chain (`get_student_by_user_id` from the JWT-derived user_id,
`assert_tenant_object`, own-row filtering) and the authoritative summary
rule (`attendance_percentage = round(present/total*100, 2)`, `None` when
zero records). Attendance tables are never queried from the resolver.

## 6. Results Integration

Delegates to `student_results.get_own_results` and
`student_results.get_own_test_results` (Phase 6.14.3) with the academic
filters forwarded verbatim (`test_results_limit` bounds test-record size).
Both services retain their published-only projection (`status ==
"published"` — draft/withheld rows are dropped inside the service), own-row
filtering, tenant assertion, and course-label resolution through the
existing personalization helper. Result tables are never queried from the
resolver.

## 7. Security Behavior

- **JWT-based identity** — every delegated service re-resolves
  `students.user_id` from `current_user.user_id` server-side; the resolver
  adds no identity surface (tests 2, 15).
- **Tenant validation** — `assert_tenant_object` remains inside each
  delegated service; a cross-tenant students row fails closed with 403
  TENANT_MISMATCH and no context is produced (tests 11, 12).
- **Own-student-only** — rows of other students are filtered inside the
  delegated services; a client-supplied `student_id` kwarg raises
  `TypeError` because no such parameter exists (test 10).
- **Institution isolation** — institution labels are only ever taken from
  the server-resolved tenant's institution; a client-supplied
  `institution_id` kwarg raises `TypeError` (test 16).
- **Published-results-only** — draft/withheld rows never enter the context
  (test 13); the publication filter stays inside the Phase 6.14.3 service.
- **No leakage** — `model_dump()` of a fully populated context contains no
  internal ids (`student_id`, `user_id`, `institution_id`, `program_id`,
  `academic_year_id`, `semester_id`, `section_id`, `course_id`,
  `*_result_id`), no email, and no password/secret/token fields (test 14).

## 8. Filtering Behavior

- `academic_year_id` and `semester_id` are forwarded verbatim to all three
  delegated services (tests 5, 6); malformed values raise 422
  INVALID_FILTER inside the existing services (forwarded, not duplicated).
- `date_from` / `date_to` are forwarded to the attendance service only
  (the results contracts do not accept date filters — verified against the
  Phase 6.14.3 signatures).
- Size is bounded by the existing service limits, reused via
  `attendance_limit` (default 200) and `test_results_limit` (default 100);
  forwarding is asserted in tests 17/18. No summarization/LLM compression
  is implemented (deferred to the later AI-context phase).

## 9. Tests Run

`backend/tests/test_student_academic_context_6144.py` (20 tests, hermetic —
repos patched with `unittest.mock`, no live Supabase/network/LLM):

1. `test_1_authenticated_context_resolves`
2. `test_2_identity_comes_from_jwt`
3. `test_3_attendance_included`
4. `test_4_results_included`
5. `test_5_academic_year_filter_forwarded`
6. `test_6_semester_filter_forwarded`
7. `test_7_no_attendance`
8. `test_8_no_results`
9. `test_9_neither_attendance_nor_results`
10. `test_10_cross_student_access_denied`
11. `test_11_cross_institution_access_denied`
12. `test_12_institution_mismatch_denied`
13. `test_13_unpublished_results_excluded`
14. `test_14_no_internal_ids_or_secrets_exposed`
15. `test_15_client_student_id_cannot_override_identity`
16. `test_16_client_institution_id_cannot_override_identity`
17. `test_17_existing_attendance_service_unchanged_and_used`
18. `test_18_existing_results_services_unchanged_and_used`
19. `test_19_phase_6142_regression`
20. `test_20_phase_6143_regression`

## 10. Exact Results

```text
backend$ python -m pytest tests/test_student_academic_context_6144.py \
           tests/test_attendance_6142.py tests/test_results_6143.py -q
50 passed, 2 warnings in 3.29s

backend$ python -m pytest tests -q
1460 passed, 15 skipped, 7 warnings in 23.13s
```

Full backend regression: **0 failures**. Existing 6.14.1/6.14.2/6.14.3
suites all pass unchanged.

## 11. Remaining Limitations

1. **No API endpoint / no `AIContext` wiring yet** — the resolver is a
   server-side service only; exposing it via `/api/v1/students/me/...` and
   injecting it into the generation pipeline is the next phase's work.
2. **`student.name` is always `None`** — no verified name field exists in
   the students contract consumed by the existing self-service layer; none
   is fabricated this phase.
3. **Records, not digests** — the context carries bounded raw record lists
   (no LLM compression/summarization; deferred per scope).
4. **No date filtering for results** — the existing Phase 6.14.3 contracts
   do not accept date filters; only academic-year/semester filtering
   applies there.
5. **`attendance_limit` / `test_results_limit` are call-site knobs** —
   there is no global context-budget system yet.
6. **Label enrichment gaps inherited** — attendance records carry no
   course/section labels (Phase 6.14.2 limitation, unchanged).

