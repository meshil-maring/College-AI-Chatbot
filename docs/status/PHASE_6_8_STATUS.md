# Phase 6.8 � Test / Exam Results � Status

**Status:** Implementation complete � Focused tests passing � Full regression passing � Remote migration NOT yet applied (credentials unavailable)

## 10. API contracts

### 10.1 Student self-service (read-only)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/students/me/results` | List own published result summaries (optional `academic_year_id`, `semester_id` filters) |
| `GET` | `/api/v1/students/me/results/{result_id}` | One own published result summary **with** per-course grade rows |
| `GET` | `/api/v1/students/me/test-results` | List own published test scores (optional filters; limit 100) |

All three resolve identity from the JWT only; no `student_id` parameter exists on these paths (asserted by `test_student_identity_params_are_never_trusted`).

### 10.2 Administrative management

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/admin/students/{student_id}/results` | List result summaries for a student (tenant-gated) |
| `POST` | `/api/v1/admin/results` | Create one result summary + items (201; audited `result.create`) |
| `GET` | `/api/v1/admin/results/{result_id}` | Get one result summary (tenant-gated) |
| `PATCH` | `/api/v1/admin/results/{result_id}` | Update mutable fields (audited `result.update`) |
| `DELETE` | `/api/v1/admin/results/{result_id}` | Hard-delete summary + items (audited `result.delete`) |
| `GET` | `/api/v1/admin/students/{student_id}/test-results` | List test scores for a student (tenant-gated) |
| `POST` | `/api/v1/admin/test-results` | Create one test result row (201; audited `test_result.create`) |
| `PATCH` | `/api/v1/admin/test-results/{test_result_id}` | Update mutable fields (audited `test_result.update`) |
| `DELETE` | `/api/v1/admin/test-results/{test_result_id}` | Delete one test result (audited `test_result.delete`) |

### 10.3 Request schemas

- `ResultCreate`, `ResultUpdate`, `ResultItemCreate`, `TestResultCreate`, `TestResultUpdate` all use **`extra="forbid"`** � clients cannot inject `institution_id`, `user_id`, `role`, `approval_status`, `student_result_id`, `created_at`, etc.
- `TestResultCreate` has **no `institution_id` field** and **no accepted `percentage`** (derived server-side).
- `ResultUpdate` and `TestResultUpdate` omit ownership fields � `extra="forbid"` rejects any attempt to inject them.
- Malformed UUIDs ? **422** (FastAPI path validation).
- Empty update payload ? **422 `EMPTY_UPDATE`**.

---

## 11. RBAC

| Actor | Mutation (create/update/delete results) | Read own results | Read any student's results (admin) |
|---|---|---|---|
| **Admin** (institution-bound) | ? Allowed (tenant-scoped) | N/A | ? Within own tenant |
| **Admin** (platform, `institution_id=None`) | ? Allowed (any tenant) | N/A | ? Any tenant |
| **Staff** | ? 403 `FORBIDDEN` | N/A | ? |
| **Faculty** | ? 403 `FORBIDDEN` | N/A | ? |
| **Student** | ? 403 `FORBIDDEN` on admin paths | ? Own published only via `/me/*` | ? Cannot access others' results |
| **Unauthenticated** | ? 401 `AUTH_REQUIRED` | ? 401 | ? 401 |

**Preserved product policy:** staff/faculty do **not** get result-mutation authority (admin-only), consistent with locked Phase 6.6 RBAC. Asserted by `test_student_role_cannot_mutate_results`, `test_staff_and_faculty_roles_cannot_mutate_results`, and the admin endpoint dependency on `Depends(_ADMIN)`.

---

## 12. Student self-service

- `student_data.get_own_student(user_id)` resolves the profile from `public.users` ? `students` using the JWT-derived `user_id`.
- `get_own_results` / `get_own_test_results` return only rows where `status == "published"`.
- `get_own_result` returns one row **with** `student_result_items`, but only if:
  - the row exists,
  - `row.student_id == own_student.student_id`,
  - `row.status == "published"`.
- Otherwise ? **404 `RESULT_NOT_FOUND`** (identical for missing, foreign, unpublished).
- A missing student profile ? **404 `STUDENT_PROFILE_NOT_FOUND`** (never a silent broadening).
- Defense-in-depth tenant assertion: `assert_tenant_object(current_user, result.institution_id)` in the `/me/results/{result_id}` handler.

---

## 13. Security protections

| Protection | Mechanism |
|---|---|
| No client-controlled tenant | `institution_id` derived from student record (service + DB trigger); `extra="forbid"` on all schemas |
| No client-controlled ownership | Ownership fields absent from update schemas; DB guard trigger refuses reassignment |
| No percentage trust | Derived server-side; DB CHECK retained |
| No result enumeration by students | Foreign/unpublished/missing all ? 404 `RESULT_NOT_FOUND` |
| Cross-tenant admin access blocked | `_assert_student_tenant` + service-layer tenant checks ? 403 `TENANT_MISMATCH` |
| Cross-tenant result creation blocked | Service validates student/academic-year/course/program all belong to same institution ? `TENANT_MISMATCH` |
| Invalid scores blocked | Schema `Field(ge=0, gt=0)` + service `INVALID_SCORES` + DB `score_marks_check` |
| Duplicate creation safe | DB UNIQUE + service mapping to 409; concurrent-safe by DB authority |
| Malformed IDs rejected | FastAPI UUID path param ? 422 |
| Tampered fields rejected | `extra="forbid"` ? 422 |
| Missing student profile fails safely | 404 `STUDENT_PROFILE_NOT_FOUND` |
| DB guard triggers | `test_results_tenant_guard`, `student_results_tenant_guard` enforce tenant derivation, academic-context integrity, ownership immutability, and `updated_at` freshness on every INSERT/UPDATE |

---

## 14. Audit behavior

Privileged mutations reuse `admin_audit_log` / `record_admin_action`:

| Action | Table | Audited by |
|---|---|---|
| `result.create` | `student_results` | `POST /admin/results` |
| `result.update` | `student_results` | `PATCH /admin/results/{id}` |
| `result.delete` | `student_results` | `DELETE /admin/results/{id}` |
| `test_result.create` | `test_results` | `POST /admin/test-results` |
| `test_result.update` | `test_results` | `PATCH /admin/test-results/{id}` |
| `test_result.delete` | `test_results` | `DELETE /admin/test-results/{id}` |

Audit payloads include the minimal identifying context (student_id, result_type / test_name, test_type). Student reads do **not** produce action-level admin audit entries (consistent with existing architecture). Asserted by `test_result_creation_is_audited`, `test_admin_result_endpoints_require_authentication`, and the existing `test_admin_api.py` result tests.

---

## 15. Migration

---

## 10. API contracts

### 10.1 Student self-service (read-only)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/students/me/results` | List own published result summaries (optional `academic_year_id`, `semester_id` filters) |
| `GET` | `/api/v1/students/me/results/{result_id}` | One own published result summary **with** per-course grade rows |
| `GET` | `/api/v1/students/me/test-results` | List own published test scores (optional filters; limit 100) |

All three resolve identity from the JWT only; no `student_id` parameter exists on these paths (asserted by `test_student_identity_params_are_never_trusted`).

### 10.2 Administrative management

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/admin/students/{student_id}/results` | List result summaries for a student (tenant-gated) |
| `POST` | `/api/v1/admin/results` | Create one result summary + items (201; audited `result.create`) |
| `GET` | `/api/v1/admin/results/{result_id}` | Get one result summary (tenant-gated) |
| `PATCH` | `/api/v1/admin/results/{result_id}` | Update mutable fields (audited `result.update`) |
| `DELETE` | `/api/v1/admin/results/{result_id}` | Hard-delete summary + items (audited `result.delete`) |
| `GET` | `/api/v1/admin/students/{student_id}/test-results` | List test scores for a student (tenant-gated) |
| `POST` | `/api/v1/admin/test-results` | Create one test result row (201; audited `test_result.create`) |
| `PATCH` | `/api/v1/admin/test-results/{test_result_id}` | Update mutable fields (audited `test_result.update`) |
| `DELETE` | `/api/v1/admin/test-results/{test_result_id}` | Delete one test result (audited `test_result.delete`) |

### 10.3 Request schemas

- `ResultCreate`, `ResultUpdate`, `ResultItemCreate`, `TestResultCreate`, `TestResultUpdate` all use **`extra="forbid"`** — clients cannot inject `institution_id`, `user_id`, `role`, `approval_status`, `student_result_id`, `created_at`, etc.
- `TestResultCreate` has **no `institution_id` field** and **no accepted `percentage`** (derived server-side).
- `ResultUpdate` and `TestResultUpdate` omit ownership fields — `extra="forbid"` rejects any attempt to inject them.
- Malformed UUIDs → **422** (FastAPI path validation).
- Empty update payload → **422 `EMPTY_UPDATE`**.

---

## 11. RBAC

| Actor | Mutation (create/update/delete results) | Read own results | Read any student's results (admin) |
|---|---|---|---|
| **Admin** (institution-bound) | ✅ Allowed (tenant-scoped) | N/A | ✅ Within own tenant |
| **Admin** (platform, `institution_id=None`) | ✅ Allowed (any tenant) | N/A | ✅ Any tenant |
| **Staff** | ❌ 403 `FORBIDDEN` | N/A | ❌ |
| **Faculty** | ❌ 403 `FORBIDDEN` | N/A | ❌ |
| **Student** | ❌ 403 `FORBIDDEN` on admin paths | ✅ Own published only via `/me/*` | ❌ Cannot access others' results |
| **Unauthenticated** | ❌ 401 `AUTH_REQUIRED` | ❌ 401 | ❌ 401 |

**Preserved product policy:** staff/faculty do **not** get result-mutation authority (admin-only), consistent with locked Phase 6.6 RBAC. Asserted by `test_student_role_cannot_mutate_results`, `test_staff_and_faculty_roles_cannot_mutate_results`, and the admin endpoint dependency on `Depends(_ADMIN)`.

---

## 12. Student self-service

- `student_data.get_own_student(user_id)` resolves the profile from `public.users` → `students` using the JWT-derived `user_id`.
- `get_own_results` / `get_own_test_results` return only rows where `status == "published"`.
- `get_own_result` returns one row **with** `student_result_items`, but only if:
  - the row exists,
  - `row.student_id == own_student.student_id`,
  - `row.status == "published"`.
- Otherwise → **404 `RESULT_NOT_FOUND`** (identical for missing, foreign, unpublished).
- A missing student profile → **404 `STUDENT_PROFILE_NOT_FOUND`** (never a silent broadening).
- Defense-in-depth tenant assertion: `assert_tenant_object(current_user, result.institution_id)` in the `/me/results/{result_id}` handler.


**File:** `supabase/migrations/20260913010000_phase_6_8_results.sql`


---

## 13. Security protections

| Protection | Mechanism |
|---|---|
| No client-controlled tenant | `institution_id` derived from student record (service + DB trigger); `extra="forbid"` on all schemas |
| No client-controlled ownership | Ownership fields absent from update schemas; DB guard trigger refuses reassignment |
| No percentage trust | Derived server-side; DB CHECK retained |
| No result enumeration by students | Foreign/unpublished/missing all → 404 `RESULT_NOT_FOUND` |
| Cross-tenant admin access blocked | `_assert_student_tenant` + service-layer tenant checks → 403 `TENANT_MISMATCH` |
| Cross-tenant result creation blocked | Service validates student/academic-year/course/program all belong to same institution → `TENANT_MISMATCH` |
| Invalid scores blocked | Schema `Field(ge=0, gt=0)` + service `INVALID_SCORES` + DB `score_marks_check` |
| Duplicate creation safe | DB UNIQUE + service mapping to 409; concurrent-safe by DB authority |
| Malformed IDs rejected | FastAPI UUID path param → 422 |
| Tampered fields rejected | `extra="forbid"` → 422 |
| Missing student profile fails safely | 404 `STUDENT_PROFILE_NOT_FOUND` |
| DB guard triggers | `test_results_tenant_guard`, `student_results_tenant_guard` enforce tenant derivation, academic-context integrity, ownership immutability, and `updated_at` freshness on every INSERT/UPDATE |

---

## 14. Audit behavior

Privileged mutations reuse `admin_audit_log` / `record_admin_action`:

| Action | Table | Audited by |
|---|---|---|
| `result.create` | `student_results` | `POST /admin/results` |
| `result.update` | `student_results` | `PATCH /admin/results/{id}` |
| `result.delete` | `student_results` | `DELETE /admin/results/{id}` |
| `test_result.create` | `test_results` | `POST /admin/test-results` |
| `test_result.update` | `test_results` | `PATCH /admin/test-results/{id}` |
| `test_result.delete` | `test_results` | `DELETE /admin/test-results/{id}` |

Audit payloads include the minimal identifying context (student_id, result_type / test_name, test_type). Student reads do **not** produce action-level admin audit entries. Asserted by `test_result_creation_is_audited`, `test_admin_result_endpoints_require_authentication`, and the existing `test_admin_api.py` result tests.

**What it does (additive only � no new tables, no locked migration modified):**

1. **A.** `student_results.institution_id` � add column, backfill from `students.institution_id`, `SET NOT NULL`, FK to `institutions`.

---

## 15. Migration

**File:** `supabase/migrations/20260913010000_phase_6_8_results.sql`

**What it does (additive only — no new tables, no locked migration modified):**

1. **A.** `student_results.institution_id` — add column, backfill from `students.institution_id`, `SET NOT NULL`, FK to `institutions`.
2. **B.** Score/credit integrity CHECKs:
   - `test_results_score_marks_check`: `(scored_marks IS NULL) OR (scored_marks <= max_marks)`
   - `student_results_credits_earned_max_check`: `(total_credits_earned IS NULL) OR (total_credits_max IS NULL) OR (total_credits_earned <= total_credits_max)`
3. **C.** `test_results.institution_id` — add column, backfill, `SET NOT NULL`, FK to `institutions`.
4. **D.** `test_results_tenant_guard` trigger function + `trg_test_results_tenant_guard` (BEFORE INSERT OR UPDATE):
   - Re-derives `institution_id` from `students.institution_id` (overrides caller input)
   - Validates academic year exists + belongs to student's institution
   - Validates course exists + belongs to student's institution (via departments)
   - If `section_id` attached: validates offering matches course/academic_year/semester and belongs to student's institution
   - On UPDATE: refuses to change `student_id`, `course_id`, `academic_year_id`, `semester_id`; refreshes `updated_at`
5. **E.** `student_results_tenant_guard` trigger function + `trg_student_results_tenant_guard` (BEFORE INSERT OR UPDATE):
   - Re-derives `institution_id` from `students.institution_id`
   - Validates academic year exists + belongs to student's institution
   - Validates semester exists + belongs to academic year
   - Validates program exists + belongs to student's institution (via departments)
   - On UPDATE: refuses to change `student_id`, `academic_year_id`, `semester_id`, `program_id`; refreshes `updated_at`
6. **F.** Indexes:
   - `idx_test_results_institution_id`
   - `idx_test_results_student_conducted`
   - `idx_test_results_ay_semester`
   - `idx_student_results_institution_id`
   - `idx_student_results_student_issued`
   - `idx_student_results_ay_semester`
7. **G.** Column comments on both `institution_id` columns.
8. **ROLLBACK** section (commented) with the inverse DDL.

**Seed-data compatibility:** Verified against the existing Admin-1 seed rows (88/100, 76/100, 94/100, 18/20 and credits 8/8, 4/4) — all CHECKs pass.

---

## 16. Local / Remote migration verification

### Local

- Migration file present and syntactically valid.
- `supabase migration list` shows:
  ```
  Local   | Remote  | Time (UTC)
  20260913010000 |          | 2026-09-13 01:00:00
  ```
  → The migration is **registered locally** but **not yet present on Remote**.

### Remote

- **`supabase db push` FAILED** with: `failed to connect to postgres: … FATAL: password authentication failed for user "cli_login_postgres" (SQLSTATE 28P01)`.
- Root cause: no `SUPABASE_DB_PASSWORD` (or equivalent) is available in the environment for the `cli_login_postgres` role. The `.env` file stores `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_USER`, `SUPABASE_DB_HOST`, `SUPABASE_DB_NAME`, `SUPABASE_DB_PORT` but **not** the password required for the CLI login role.
- **No hardcoded credentials were used.** The push was attempted with the project's existing `.env` configuration.
- **Impact:** The Phase 6.8 migration has been applied to the **local** development database but has **not** been pushed to the **Remote** (Supabase Cloud) database. A reviewer with valid Remote credentials must run `supabase db push` to complete the Remote deployment.
- **Live-database physical validation tests** (`TestResultsPhysicalValidationPhase68`) are present in `test_results_phase_6_8.py` but marked `@pytest.mark.skip` (opt-in convention). They cannot run until the Remote DB has the migration applied.

2. **B.** Score/credit integrity CHECKs:
   - `test_results_score_marks_check`: `(scored_marks IS NULL) OR (scored_marks <= max_marks)`
   - `student_results_credits_earned_max_check`: `(total_credits_earned IS NULL) OR (total_credits_max IS NULL) OR (total_credits_earned <= total_credits_max)`
3. **C.** `test_results.institution_id` � add column, backfill, `SET NOT NULL`, FK to `institutions`.
4. **D.** `test_results_tenant_guard` trigger function + `trg_test_results_tenant_guard` (BEFORE INSERT OR UPDATE):
   - Re-derives `institution_id` from `students.institution_id` (overrides caller input)
   - Validates academic year exists + belongs to student's institution
   - Validates course exists + belongs to student's institution (via departments)
   - If `section_id` attached: validates offering matches course/academic_year/semester and belongs to student's institution
   - On UPDATE: refuses to change `student_id`, `course_id`, `academic_year_id`, `semester_id`; refreshes `updated_at`
5. **E.** `student_results_tenant_guard` trigger function + `trg_student_results_tenant_guard` (BEFORE INSERT OR UPDATE):
   - Re-derives `institution_id` from `students.institution_id`
   - Validates academic year exists + belongs to student's institution
   - Validates semester exists + belongs to academic year
   - Validates program exists + belongs to student's institution (via departments)
   - On UPDATE: refuses to change `student_id`, `academic_year_id`, `semester_id`, `program_id`; refreshes `updated_at`
6. **F.** Indexes:
   - `idx_test_results_institution_id`
   - `idx_test_results_student_conducted`
   - `idx_test_results_ay_semester`
   - `idx_student_results_institution_id`
   - `idx_student_results_student_issued`
   - `idx_student_results_ay_semester`
7. **G.** Column comments on both `institution_id` columns.
8. **ROLLBACK** section (commented) with the inverse DDL.

**Seed-data compatibility:** Verified against the existing Admin-1 seed rows (88/100, 76/100, 94/100, 18/20 and credits 8/8, 4/4) � all CHECKs pass.

---

## 16. Local / Remote migration verification

### Local

- Migration file present and syntactically valid.
- `supabase migration list` shows:
  ```
  Local   | Remote  | Time (UTC)
  20260913010000 |          | 2026-09-13 01:00:00
  ```
  ? The migration is **registered locally** but **not yet present on Remote**.

### Remote

- **`supabase db push` FAILED** with:
  ```
  failed to connect to postgres: � FATAL: password authentication failed for user "cli_login_postgres" (SQLSTATE 28P01)
  ```
- Root cause: no `SUPABASE_DB_PASSWORD` (or equivalent) is available in the environment for the `cli_login_postgres` role. The `.env` file stores `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_USER`, `SUPABASE_DB_HOST`, `SUPABASE_DB_NAME`, `SUPABASE_DB_PORT` but **not** the password required for the CLI login role.
- **No hardcoded credentials were used.** The push was attempted with the project's existing `.env` configuration.
- **Impact:** The Phase 6.8 migration has been applied to the **local** development database but has **not** been pushed to the **Remote** (Supabase Cloud) database. A reviewer with valid Remote credentials must run `supabase db push` (or `supabase migration apply`) to complete the Remote deployment.
- **Live-database physical validation tests** (`TestResultsPhysicalValidationPhase68`) are present in `test_results_phase_6_8.py` but marked `@pytest.mark.skip` (opt-in convention). They cannot run until the Remote DB has the migration applied.

---

## 17. Tests

### 17.1 Focused Phase 6.8 tests � `backend/tests/test_results_phase_6_8.py`

**Result: 46 passed, 3 skipped, 0 failed** (6.64s)

Covers:

1. ? Schema contract � migration adds hardening without creating tables; projections include `institution_id`; vocabularies match existing CHECK constraints; UNIQUE constraints preserved; indexes defined.
2. ? Test result service � tenant + percentage derivation, percentage `None` without score, letter-grade normalization, invalid scores (negative, over-max, non-positive max), invalid type/status, unknown student.
3. ? Test result academic-context validation � unknown academic year, cross-tenant academic year, unknown/mismatched semester, unknown course, cross-tenant course, unknown section, mismatched section offering.
4. ? Test result update/delete/duplicate/concurrency � percentage re-derivation, merged score validation, empty update, 404, section revalidation, stable 409 `TEST_RESULT_DUPLICATE`, concurrent-create safety.
5. ? Student result service � tenant + credits validation, invalid type/status, duplicate `RESULT_DUPLICATE`, 404, update, delete.
6. ? API authorization � 401 unauthenticated, 403 student/staff/faculty mutation, 403 cross-tenant admin update/delete, tenant admin can manage own results, audit recording, malformed UUIDs, `extra="forbid"` rejection.
7. ? Student self-service � retrieve own published result, cannot retrieve another's (same 404), cannot retrieve unpublished, fails safely without profile, tenant guard, no `student_id` params on `/me` paths.
8. ? Physical (live DB) validation � **3 skipped** (`@pytest.mark.skip`, opt-in): live schema + backfill, live test result guard trigger, live student result guard trigger.

### 17.2 Existing tests extended

- `backend/tests/test_admin_api.py` � `test_create_result_with_items_audits`, `test_create_result_rejects_invalid_result_type`, `test_create_test_result_audits`, `test_create_test_result_rejects_scored_over_max` (and related) already cover result creation with audit and score validation via the admin API.
- `backend/tests/test_admin_academics_service.py` � updated to route through the new `app.services.results` delegates; validates academic-context lookup chain.

### 17.3 Full regression suite

**Command:** `cd backend && python -m pytest tests --ignore=tests/test_physical_validation_phase_4_4.py -q`

**Result: 865 passed, 8 skipped, 0 failed** (22.07s)

Zero unexpected failures. The 8 skipped tests are pre-existing opt-in/live-database skips (Phase 4.4 physical validation, plus the Phase 6.8 physical validation class).

---

## 18. Full regression baseline

| Suite | Passed | Skipped | Failed |
|---|---|---|---|
| `tests/test_results_phase_6_8.py` (focused) | 46 | 3 | 0 |
| Full backend (`--ignore=test_physical_validation_phase_4_4.py`) | 865 | 8 | 0 |

---

## 19. Files changed

### Created (new)

| File | Purpose |
|---|---|
| `supabase/migrations/20260913010000_phase_6_8_results.sql` | Phase 6.8 additive hardening migration |
| `backend/app/repositories/results.py` | Results repository � projections, context lookups, CRUD over existing tables |
| `backend/app/services/results.py` | Results service � validation, tenant derivation, academic-context checks, duplicate mapping, percentage derivation |
| `backend/tests/test_results_phase_6_8.py` | Phase 6.8 security + integrity test suite |

### Modified (existing)

| File | Change |
|---|---|
| `backend/app/api/students.py` | Added `GET /me/results/{result_id}` (self-service single-result read) |
| `backend/app/api/admin.py` | Added result management endpoints: `GET/POST/PATCH/DELETE /admin/results[/{id}]`, `GET/POST/PATCH/DELETE /admin/test-results[/{id}]`, `GET /admin/students/{id}/results`, `GET /admin/students/{id}/test-results`; imports `results` service |
| `backend/app/services/admin_academics.py` | Added result/test-result management delegates that route to `app.services.results`; added `RESULT_STATUSES`, `RESULT_TYPES`, `TEST_RESULT_STATUSES`, `TEST_TYPES`, `ResultCreate`, `ResultUpdate`, `ResultItemCreate`, `TestResultCreate`, `TestResultUpdate`, `_validate_choice` |
| `backend/app/services/student_data.py` | Added `get_own_result(user_id, result_id)` � self-service single-result read with ownership + publication + tenant checks |
| `backend/tests/test_admin_api.py` | Extended with result/test-result creation + audit + score-validation tests |
| `backend/tests/test_admin_academics_service.py` | Updated to route through new service delegates; validates academic-context lookup chain |

**Note:** `backend/app/repositories/attendance.py`, `backend/app/services/attendance.py`, `backend/tests/test_attendance_phase_6_7.py`, and `supabase/migrations/20260913000000_phase_6_7_attendance.sql` are part of **Phase 6.7** (already complete and locked). They are not modified by Phase 6.8.

---

## 20. Known limitations

1. **Remote database migration not applied.** The Phase 6.8 migration has been applied to the local development database but has **not** been pushed to the Remote (Supabase Cloud) database because no valid `SUPABASE_DB_PASSWORD` for the `cli_login_postgres` role is available in the environment. A reviewer with Remote credentials must run `supabase db push` to complete Remote deployment.

2. **Live-database physical validation tests are skipped.** `TestResultsPhysicalValidationPhase68` is marked `@pytest.mark.skip` (opt-in convention). They require the migration applied to a live database with valid credentials. They verify the tenant backfill, guard triggers (derivation, academic-context rejection, ownership immutability), the score CHECK, and the duplicate constraint against real data.

3. **No grading-scale table exists.** The project has no reference grading scale, so `letter_grade` is stored as recorded (normalized: trimmed, blank ? NULL) but not validated against a scale. `sgpa`/`cgpa` are institution-computed summaries, not derived server-side. This is consistent with the existing Admin-1 schema and is documented as a known limitation, not a Phase 6.8 regression.

4. **`percentage` is derived by the app layer only.** The DB does not recompute percentage on write (the existing `test_results_percentage_check` remains a guard, not a calculator). This matches the existing model where `percentage` is a stored but app-derived field.

5. **`student_result_items` does not have its own `institution_id` column.** It inherits tenant safety from the CASCADE parent (`student_results`) and the service-layer validation. Adding a denormalized tenant column to items is not required for Phase 6.8.

6. **Results CSV upload endpoint** (`POST /admin/results/csv-upload`) already existed in the admin API and is **not** modified by Phase 6.8. It is out of Phase 6.8 scope.

7. **Platform admin behavior** is consistent with the locked Phase 6.4/6.6 policy (admin with `institution_id=None` is not tenant-gated). This is tested implicitly through the existing admin test patterns.

---

## 21. Explicit Phase 6.9 boundary

**Phase 6.9 has NOT started.** The following are explicitly out of scope and NOT implemented:

- No student-specific data access beyond what is strictly required for result ownership (the `/me/results*` endpoints are Phase 6.8 self-service, not Phase 6.9).
- No personalized chatbot, no recommendation system, no AI-generated result explanations.
- No new authentication system, no new RBAC system, no new tenant system.
- No security hardening beyond what is necessary for Phase 6.8 (the guard triggers and tests are Phase 6.8 deliverables).
- No Phase 6.10, 6.11, or 6.12 implementation.

The implementation stops at: student self-service read of own results + admin management of results with RBAC/tenant/validation/audit/duplicate protection.

---

## 22. Implementation summary

Phase 6.8 is **functionally complete**:

- ? Existing result tables reused and hardened (no new table)
- ? Server-derived `institution_id` on both result tables (migration + guard triggers)
- ? Score/credit integrity CHECKs added
- ? Tenant + academic-context guard triggers (test_results + student_results)
- ? Indexes added
- ? Student self-service: `GET /me/results`, `/me/results/{id}`, `/me/test-results` (own published only, no enumeration)
- ? Admin management: full CRUD for results + test-results with RBAC + tenant + audit
- ? Score validation (negative, over-max, non-positive max) at schema + service + DB layers
- ? Duplicate protection via existing UNIQUE constraints ? stable 409 codes; concurrent-safe
- ? `extra="forbid"` on all result schemas
- ? Percentage derived server-side, never client-trusted
- ? Letter-grade normalization
- ? 46 focused tests passing, full regression 865 passing / 0 failing
- ?? Remote DB migration not yet pushed (credentials unavailable) � requires reviewer action

**Phase 6.8 lock has NOT been created.** Waiting for external review before locking.

---

*Prepared: 2026-09-13*
