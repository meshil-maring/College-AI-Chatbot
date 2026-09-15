# PHASE 6.11 — EXTERNAL REVIEW PROMPT
## Student Notifications / Academic Alerts

**To:** External Reviewer
**From:** College AI Chatbot Backend Team
**Status:** Implementation complete — awaiting independent external review before the phase may be locked.

---

## 1. Your role

You are an independent external reviewer performing a security-focused review of **Phase 6.11 — Student Notifications / Academic Alerts** for the College AI Chatbot backend.

Phases 6.1–6.10 are **LOCKED**. Treat all locked functionality as immutable. The only authorized modification in this phase is the additive router registration in `backend/app/main.py`. Any other modification of a locked file is a finding.

Your review determines whether this phase is **ready to lock** or must **reopen for rework**.

---

## 2. Baseline to compare against

- Phase 6.10 lock baseline: **947 passed, 8 skipped, 0 failed** (`python -m pytest tests --ignore=tests/test_physical_validation_phase_4_4.py`).
- Phase 6.11 implementation claims: focused suite **43 passed, 0 failed**; full regression **990 passed, 8 skipped, 0 failed**.
- Established conventions: canonical identity via `student_context.get_student_context(...)` (Phase 6.9), multi-tenant isolation via `institution_id`, RBAC, `AppError {status_code, code}` error convention, existing pagination conventions.

---

## 3. Phase objective (what to verify)

A secure student notification and academic-alert *foundation*. Requirements:

1. **MUST NOT become a second source of truth.** Notifications must only reference authoritative records owned by the institution/student data model (via `source_record_id` + `source_type`).
2. Every notification belongs to exactly **one student and one institution**.
3. Institution is **server-derived** from the authenticated student context — never from the client.
4. Students interact with their **own** notifications only: list, read one, mark read.
5. Notification types use a **controlled vocabulary**, not arbitrary strings.
6. Duplicate academic events (same student + source record + type) must not produce unlimited duplicates.

---

## 4. Files in scope

**New**
- `backend/app/schemas/student_notifications.py`
- `backend/app/repositories/student_notifications.py`
- `backend/app/services/student_notifications.py`
- `backend/app/services/student_notifications_integration.py`
- `backend/app/api/student_notifications.py`
- `backend/tests/test_student_notifications_phase_6_11.py`
- `supabase/migrations/20260914000000_phase_6_11_student_notifications.sql`
- `backend/PHASE_6_11_STATUS.md`

**Modified (additive only)**
- `backend/app/main.py` (new router import + `app.include_router(student_notifications_router, prefix="/api/v1")`)

**Declared out of scope (must remain untouched):** locked migrations, `student_context.py`, `student_data.py`, attendance/results services, chatbot/generation pipeline, admin/RBAC/tenant modules, `app/api/students.py`, all Phase 6.10 files.

---

## 5. Functional requirement checklist

### A. Notification listing — `GET /api/v1/students/me/notifications`
- [ ] Authenticated student only (unauthenticated → 401 `AUTH_REQUIRED`)
- [ ] Own notifications only
- [ ] Institution/tenant isolation
- [ ] Deterministic ordering (newest first by `created_at DESC`)
- [ ] Pagination (`page`, `page_size`, bounded 1..100; `has_more`)
- [ ] Read/unread state (`is_read`, `read_at`)
- [ ] `created_at` timestamp
- [ ] Notification type/category present
- [ ] Title and message
- [ ] Optional reference to the authoritative source record (`source_type`, `source_record_id`)

### B. Read state — `PATCH /api/v1/students/me/notifications/{notification_id}/read`
- [ ] Student can mark own notification read
- [ ] Student CANNOT modify another student's notification
- [ ] Student CANNOT modify ownership
- [ ] Student CANNOT change `institution_id`
- [ ] Student CANNOT alter notification type/content (route accepts no payload)
- [ ] Student CANNOT create arbitrary notifications (no such endpoint)

Also verify `GET /api/v1/students/me/notifications/{notification_id}` (single own) and `GET /api/v1/students/me/notifications/unread-count`.

### C. Controlled vocabulary
- [ ] Exact set: `attendance_alert`, `result_published`, `academic_status`, `academic_admin`
- [ ] Enforced at schema (regex + closed tuple), service (`_validate_notification_type` → 422 `INVALID_NOTIFICATION_TYPE`), and database (CHECK constraint)
- [ ] No unnecessary categories introduced

### D. Academic alerts foundation
- [ ] Explicit service/repository functions an authorized backend workflow may call (integration module)
- [ ] No invented external event infrastructure
- [ ] Confirmed additive — attendance (6.7) / results (6.8) services were NOT modified

---

## 6. Tenant / ownership security invariants (most important)

Verify all of the following in code **and** by attempted attack:

- [ ] Every notification row has exactly one `student_id` and one `institution_id` (NOT NULL, FKs)
- [ ] `institution_id` is derived server-side from the authoritative student context — never the client
- [ ] No endpoint accepts or trusts `student_id`, `user_id`, `institution_id`, or `auth_user_id` for ownership
- [ ] Cross-student read / mark-read → 404 `NOTIFICATION_NOT_FOUND` (identical to "does not exist"; no enumeration)
- [ ] Cross-tenant access → existing canonical tenant error mechanisms (no second tenant mechanism introduced)
- [ ] DB tenant backstop: `trg_student_notifications_tenant_guard` derives and forces `institution_id` from `students`, rejects mismatch (mirrors Phases 6.7/6.8)
- [ ] Eligibility gates intact: unapproved (403 `STUDENT_NOT_APPROVED`) / inactive (403 `STUDENT_INACTIVE`) / non-student (404 `STUDENT_PROFILE_NOT_FOUND`) cannot reach service

---

## 7. Database design checklist

- [ ] No duplicate notification table created if an equivalent structure existed (reviewer confirms none existed)
- [ ] FKs: `student_id → students(student_id) ON DELETE CASCADE`; `institution_id → institutions(institution_id)`
- [ ] NOT NULL: `student_id`, `institution_id`, `notification_type`, `title`, `message`
- [ ] Valid notification type: CHECK on controlled vocabulary
- [ ] Valid read-state: `is_read BOOLEAN NOT NULL DEFAULT FALSE`; `read_at` backstop in trigger
- [ ] Tenant consistency enforced where possible (trigger)
- [ ] No passwords, tokens, or authentication secrets stored
- [ ] No unnecessary duplication of student identity information

---

## 8. Duplicate / idempotency checklist

- [ ] Partial UNIQUE index `uq_student_notification_source_record (student_id, source_record_id, notification_type) WHERE source_record_id IS NOT NULL`
- [ ] Duplicate insert (Postgres `23505` / "duplicate key") maps to existing conflict convention: 409 `NOTIFICATION_DUPLICATE`
- [ ] Same authoritative event processed twice → no duplicate notifications

---

## 9. API design conventions checklist

- [ ] Uses existing `get_current_user` authentication dependency
- [ ] Uses Phase 6.9 `student_context.get_student_context(...)` for identity
- [ ] Follows tenant enforcement, response schema conventions, error conventions, pagination conventions
- [ ] No `student_id` exposed as an ownership parameter in any path/query/body

---

## 10. Verification commands (run these)

From `backend/`:

```
python -m pytest tests/test_student_notifications_phase_6_11.py -q
python -m pytest tests --ignore=tests/test_physical_validation_phase_4_4.py -q
```

Expected: **43 passed** focused; **990 passed, 8 skipped, 0 failed** full.

Also perform a static review of `supabase/migrations/20260914000000_phase_6_11_student_notifications.sql` for the items in §7–§8.

---

## 11. Attack attempts the reviewer should try (security fuzzing)

Write small tests or reasoned code-level arguments for each:

1. Authenticated student reads `GET .../notifications/{other_student_notification_id}` → expect 404.
2. Authenticated student PATCHes read on another student's notification → expect 404.
3. PATCH with body `{"title": "...", "message": "...", "notification_type": "...", "institution_id": "..."}` → content/ownership must NOT change (route accepts no payload).
4. Student attempts `POST /api/v1/students/me/notifications` → expect 405 (no such route).
5. Student enumerates notification ids → uniform 404, no existence oracle.
6. Unauthenticated request → 401 `AUTH_REQUIRED`.
7. Unapproved / inactive student → 403; user with no student profile → 404.
8. `page=0` or `page_size=101` → 422.
9. Direct service call with an arbitrary `notification_type` string → 422 `INVALID_NOTIFICATION_TYPE`.
10. Re-create notification for same `(student_id, source_record_id, notification_type)` → 409 `NOTIFICATION_DUPLICATE`.
11. Direct DB insert with `institution_id` ≠ student's tenant → trigger rejects (static review; `F403`-style error).
12. Confirm no notification data embedded in `/me/profile`, `/me/results`, `/me/attendance` responses.
13. Confirm no secrets/tokens anywhere in the notification schema/migration.

---

## 12. Boundary compliance

- [ ] No Phase 6.12 functionality present
- [ ] No unrelated functionality added
- [ ] No locked-phase behavior changed (other than additive `main.py` router registration)

---

## 13. Your verdict

Produce a report containing:

1. **Verdict:** `READY TO LOCK` | `READY TO LOCK WITH COMMENTS` | `NEEDS REWORK`
2. **Findings table:** `ID | Severity (Critical/Major/Minor/Info) | Location | Description | Required action`
3. **Evidence:** test output (focused + full), migration review notes, attack-attempt results
4. **Boundary statement:** confirm no locked-phase or Phase 6.12 functionality was touched

**Lock criteria:** `READY TO LOCK` requires zero Critical/Major findings, all §5–§9 checkboxes confirmed, and full regression 0 failed. If the verdict is `READY TO LOCK` (with or without comments), the project will follow its change-control process to create `backend/PHASE_6_11_LOCK.md`.

---

*Review prompt prepared: 2026-09-14*