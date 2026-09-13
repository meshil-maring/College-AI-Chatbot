# Phase 6.8 — Lock Record

**Phase:** 6.8  
**Subject:** Test / Exam Results  
**Lock date:** 2026-09-13  
**Precedence:** Phase 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7 are all formally locked before this lock step.

---

## 1. Objective

Phase 6.8 delivers secure Test / Exam Results functionality for the College AI Chatbot backend.

Phase 6.8 covers:

- test/exam/assessment result data
- student-specific results
- marks/scores
- maximum marks
- grade/result information where implemented
- academic context
- institution/tenant isolation
- student self-service result access
- authorized administrative result management
- validation
- duplicate protection
- auditability
- database integrity protections

---

## 2. Scope Status

**Phase 6.8 — IMPLEMENTED and LOCKED.**  
**Phase 6.9 and later — NOT implemented.** No Phase 6.9+ functionality exists in this repository as of this lock.

No Phase 6.9+ functionality has been implemented as part of this lock.

---

## 3. Existing Model / Schema

Before implementation, the existing academic and result schema was inspected. The inspection covered Supabase migrations, existing tables, foreign keys, unique constraints, CHECK constraints, indexes, triggers, repositories, services, APIs, schemas, and existing admin academic functionality.

The implementation reused existing structures wherever possible.

**Existing structures reused:**

- `students` — canonical student anchor with `student_id`, `institution_id`, and `program_id` relationships
- `test_results` — existing per-test/exam result table reused and hardened; no new result table was created
- `student_results` — existing per-student consolidated result table reused and hardened; no new result table was created
- `student_result_items` — existing per-course grade rows reused and hardened
- `institutions` — canonical tenant/institution table
- `academic_years` — academic year with `institution_id` as a strong tenant anchor
- `semesters` — semester with relationship to academic year
- `courses` → `departments` → `institutions` — academic chain used for tenant validation
- `course_offerings` and `sections` — academic context where applicable
- `programs` → `departments` → `institutions` — program academic chain where applicable
- `admin_audit_log` / `record_admin_action` — existing audit mechanism reused

**Model decision:**


---

## 4. Student Relationship

Student identity and ownership are resolved through the existing chain:

public.users
→ students.user_id
→ students.student_id

Student self-service identity is derived from the authenticated user/JWT.

Explicitly:

- students cannot select another student as their identity
- student result reads are limited to the authenticated student's own results
- missing student profiles fail safely
- ownership cannot be overridden through request parameters

No client-supplied `student_id` is trusted for determining whose results are returned.

---

## 5. Tenant / Institution Isolation

`students.institution_id` remains the canonical tenant/institution key.

Documented protections:

- institution-bound administrative access
- cross-tenant protection
- server-side tenant resolution
- academic-context tenant validation
- database-level protection where implemented
- platform admin behavior according to the already locked Phase 6.4/6.6 policy

No new `tenant_id` was introduced.

Phase 6.8 hardened the result tables by storing `institution_id` on the result rows themselves, derived from the canonical student/institution relationship, so that guard logic can defend results even when accessed outside the normal request pipeline.

---

## 6. Academic Context

Results are tied to the existing academic hierarchy.

Where applicable, the relationship is:

student
→ section
→ offering
→ course
→ department

and the relationship to:

- academic year
- semester
- assessment/test/exam

Inconsistent or cross-institution academic relationships fail closed.

---

## 7. Score / Mark Validation

Implemented and verified validation rules:

- negative scores are rejected
- maximum marks must be positive
- score greater than maximum marks is rejected
- numeric validation is enforced server-side
- grade validation is applied where applicable; blank/empty grades are normalized
- decimal handling is consistent with the chosen schema
- database-level CHECK constraints provide a second defense layer

Score validation is enforced at multiple layers, not only in the frontend.

The Phase 6.8 implementation reused the existing `test_results` and `student_results` tables and extended them with stronger integrity protections rather than creating a new result model.

Results connect to students through `students.student_id`. Results connect to the academic structure through the existing foreign-key relationships into academic years, semesters, courses, sections, and programs.
