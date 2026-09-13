# PHASE 6.5 - STUDENT AUTHENTICATION LOCK

## STATUS: LOCKED

Lock date: 2026-09-13
Locked at final verification completion. Remaining blockers: NONE.

---

## 1. Phase Number

Phase 6.5

## 2. Phase Name

Phase 6.5 - Student Authentication (Email / Register Number / University Roll Number)

## 3. Final Implementation State

Phase 6.5 implements student authentication on top of the LOCKED Phase 6.1/6.2/6.3/6.4
foundations. The verified final state:

- Endpoint (backend/app/api/student_auth.py):
  POST /api/v1/auth/student/login -- accepts identifier, password, and optional
  institution_code.
- Service layer (backend/app/services/student_auth.py):
  authenticate_student(identifier, password, institution_code) resolves the identifier
  to a student record, validates approval + lifecycle state, then delegates to Supabase
  Auth (sign_in_with_password).
- Schema (backend/app/schemas/student_auth.py):
  StudentLoginRequest with model_config = ConfigDict(extra="forbid") -- rejects
  client-controlled role, user_id, student_id, institution_id, approval_status,
  auth_user_id.
- Routing (backend/app/main.py): student_auth_router mounted at /api/v1.

## 4. Architecture Decision

- No second authentication system. Supabase Auth (GoTrue) remains the SINGLE
  credential authority. The application resolves the identifier to the student's email
  and forwards email + password to client.auth.sign_in_with_password().
- No password storage. The application never stores, hashes, or compares passwords.
- No custom JWT generation. Existing JWT validation (get_current_user, verify_jwt)
  and Supabase Auth sessions are reused.
- Email login is globally deterministic. Email is unique per public.users.
  No institution context is required.
- Academic identifier login requires institution_code. Phase 6.2 established
  institution-scoped uniqueness for register_number and university_roll_number.
  The existing institutions.code column (public identifier) is reused - no new
  institution identifier was invented. institution_code maps to institution_id
  server-side; the internal UUID is never exposed to the client.
- No Phase 6.2 migration. The existing schema provides all required fields.

## 5. Identity Resolution

### Email Login (no institution context)
- identifier contains @ and a . after @ -> treated as email
- get_student_by_email_global() resolves email -> student (globally unique)
- institution_code is ignored if provided

### Academic Identifier Login (institution_code REQUIRED)
- identifier does NOT match email pattern -> treated as academic identifier
- _find_institution_by_code(db, institution_code) maps institutions.code to institution_id
- _resolve_academic_id_with_context() performs institution-scoped lookups:
  get_student_by_register_number(db, institution_id, identifier) and
  get_student_by_university_roll_number(db, institution_id, identifier)
- If both match the same student -> unambiguous match
- If both match different students -> SafeAuthFailure (ambiguity within institution)
- If none match -> None -> SafeAuthFailure

### Cross-Tenant Ambiguity Prevention
- The same register_number in institution A and institution B CANNOT cross-authenticate
- The institution_code parameter scopes the lookup to exactly one institution

## 6. Approval Enforcement

- Only approval_status = "approved" students may authenticate
- Pending students -> SafeAuthFailure (no student session)
- Rejected students -> SafeAuthFailure (no student session)
- approval_status is NEVER modified during login
- Phase 6.4 approval workflow remains intact

## 7. Lifecycle Enforcement

- student.is_active = False -> blocked (SafeAuthFailure)
- institution.is_active = False -> blocked (SafeAuthFailure)

## 8. Tenant Security

- students.institution_id remains the canonical tenant key (Phase 6.1, LOCKED)
- institution_code maps to internal institution_id server-side only
- Client CANNOT override institution_id via the login request (extra="forbid")

## 9. Security Boundary

- No password storage or comparison by the application
- No custom JWT creation - Supabase Auth sessions are used directly
- No second authentication architecture
- All authentication failures normalized to generic 401 INVALID_CREDENTIALS
- No account enumeration: same response regardless of failure reason
- No passwords logged; no access tokens logged; no full auth payloads logged
- Admin/staff credentials against the student login endpoint fail safely (401)

## 10. API Endpoint

POST /api/v1/auth/student/login

Request:
  {"identifier": "<email>|<register_number>|<university_roll_number>",
   "password": "<password>",
   "institution_code": "<institutions.code>"}  // required for academic IDs only

Response (200):
  {"access_token": "<supabase-jwt>",
   "message": "Login successful.",
   "user": {"id": "<auth-user-id>", "email": "<email>"}}

Errors:
  401 INVALID_CREDENTIALS - "Invalid identifier or password"
  422 VALIDATION_ERROR - "institution_code is required for academic identifier login"
  422 ValidationError - malformed input (missing/extra fields, empty values)

## 11. Test Baseline

### Phase 6.5 tests: 46 passed, 0 failed
### Full backend suite: 737 passed, 5 skipped, 0 failed

(8 pre-existing integration test files excluded - require running server
with Supabase connectivity)

## 12. Files

New files:
- PHASE_6_5_LOCK.md (this document)
- PHASE_6_5_STATUS.md
- backend/app/api/student_auth.py
- backend/app/schemas/student_auth.py
- backend/app/services/student_auth.py
- backend/tests/test_student_auth_phase_6_5.py (46 tests)

Modified file:
- backend/app/main.py - added student_auth_router import + include_router

## 13. Database Changes

NONE. No Phase 6.5 migration was required. Phase 6.2 schema provides all required
fields. institutions.code is reused as the public institution identifier.

## 14. Known Limitations

1. Email detection heuristic uses simple @ + . check.
2. Rate limiting not implemented at the application layer.
3. Unit tests use mocks for Supabase Auth; no live integration tested.
4. Institution code normalized to uppercase in lookup.

## 15. Explicit Phase 6.6+ Exclusions (NOT implemented)

- Phase 6.6 RBAC redesign
- Phase 6.7 attendance
- Phase 6.8 test/exam results
- Phase 6.9 student-specific data access
- Phase 6.10 personalized chatbot
- Phase 6.11 broader security testing beyond authentication scope
- Phase 6.12 final demo validation

## 16. Git

- Baseline HEAD: 75a794e28bd42c5d3f8008428a4457cd7e2818ce
- No Phase 6.1-6.4 lock files modified
- No temporary/debug files remain
- No secrets/passwords/tokens added
- Only this lock document added as a new file; all implementation files and
  tests were verified unchanged since the final test run.

---

## Official lock statement

"Phase 6.5 is complete and locked. Student authentication supports email login
(globally deterministic, no institution context) and academic identifier login
(register number or university roll number with institution_code, scoped via
the existing institutions.code to prevent cross-tenant ambiguity). Supabase
Auth remains the sole credential authority with no application password
storage, no custom JWT generation, and no second authentication system. No
Phase 6.6+ functionality is implemented."

## PHASE 6.5 — LOCKED
