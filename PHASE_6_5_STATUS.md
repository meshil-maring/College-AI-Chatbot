# Phase 6.5 - Status

## Objective

Implement student authentication so a student can log in using:
1. Email + password
2. Register number + password (institution_code required)
3. University roll number + password (institution_code required)

Supabase Auth (GoTrue) remains the SINGLE credential authority. No password
storage, no custom JWT, no second authentication system.

## Existing Authentication Architecture

- Supabase Auth (GoTrue): client.auth.sign_in_with_password() in app/api/auth.py
- JWT validation: app/core/security.py
- Tenant isolation: app/core/security.py - scope_tenant(), assert_tenant_object()
- Users table: public.users linked via auth_user_id
- Students table: students linked to public.users via user_id, institution_id as tenant key
- Institutions table: institutions with code column (public identifier, e.g., "GIT")
- Phase 6.2 (LOCKED): email, register_number, university_roll_number, student_number,
  approval_status, institution_id, user_id
- Phase 6.4 (LOCKED): Approval workflow
- Repository: app/repositories/admin_academics.py with global lookup functions

## Implementation

### Authentication Flow

POST /api/v1/auth/student/login
  identifier + password (+ institution_code for academic identifiers)
    |
Request schema validation (extra="forbid")
    |
Identity resolution:
  - Email -> _resolve_by_email() (global)
  - Academic ID -> _resolve_academic_id_with_context():
    1. Look up institution by code -> institution_id
    2. Lookup register_number/roll_number SCOPED to institution_id
    3. Ambiguous within institution -> SafeAuthFailure
    4. No match -> None
    |
Lifecycle checks:
  - approval_status must be "approved"
  - student.is_active must be True
  - institution.is_active must be True
    |
Supabase Auth sign-in with resolved email + password
    |
Return: { access_token, message, user }

### Identifier Resolution

Email login (no institution context needed):
- identifier looks like an email -> get_student_by_email_global()
- Email is globally unique per public.users

Academic identifier login (institution_code REQUIRED):
- institution_code maps to institutions.code -> internal institution_id
- register_number and university_roll_number resolved WITHIN institution_id
- Prevents cross-tenant ambiguity

### Approval Enforcement
- Only approval_status = "approved" students may authenticate
- Pending/rejected students -> SafeAuthFailure
- approval_status never modified during login

### Lifecycle Enforcement
- Inactive students -> blocked
- Inactive institutions -> blocked

### Tenant Security
- students.institution_id is canonical tenant key
- institution_code maps to internal institution_id server-side
- Client cannot override institution_id (extra="forbid")

## API Endpoint

```
POST /api/v1/auth/student/login

Request:
{
  "identifier": "student@example.com" | "REG2026001" | "UR2026001",
  "password": "secret",
  "institution_code": "GIT"  // required for academic IDs, ignored for email
}

Response (200):
{ "access_token": "...", "message": "Login successful.", "user": {"id": "...", "email": "..."} }

Errors:
  401 INVALID_CREDENTIALS - "Invalid identifier or password"
  422 VALIDATION_ERROR - "institution_code is required for academic identifier login"
```

## Security Behavior

- All auth failures normalized to generic 401 INVALID_CREDENTIALS
- No account enumeration (same error for all failure cases)
- No passwords logged or persisted
- No client-controlled role, user_id, student_id, institution_id,
  approval_status, or auth_user_id accepted

## Files Changed

New files:
- backend/app/schemas/student_auth.py
- backend/app/services/student_auth.py
- backend/app/api/student_auth.py
- backend/tests/test_student_auth_phase_6_5.py (46 tests)

Modified:
- backend/app/main.py (student_auth_router import + include_router)

Pre-existing files NOT modified:
- backend/app/repositories/admin_academics.py (already had lookup functions)
- Phase 6.1-6.4 implementation files

## Database / Migrations

No new migrations. Phase 6.2 schema provides all required fields.
institutions.code is the existing public institution identifier.

## Tests

Phase 6.5 tests: 46 passed

Coverage:
- A. Valid email + correct password -> success
- B. Valid email + wrong password -> 401
- C. Valid register number + correct password -> success (with institution_code)
- D. Valid register number + wrong password -> 401
- E. Valid university roll number + correct password -> success (with institution_code)
- F. Valid university roll number + wrong password -> 401
- G. Unknown identifier -> 401
- H. Empty identifier -> 401/422
- I. Invalid email format -> handled by schema
- J. Empty password -> 422
- K. Pending student -> blocked
- L. Rejected student -> blocked
- M. Inactive student -> blocked
- N. Inactive institution -> blocked
- O. Identifier at another institution -> blocked (cross-tenant)
- P. Conflicting identifier records -> SafeAuthFailure
- Q. Ambiguous identity resolution -> SafeAuthFailure
- R. Cross-user authentication -> blocked
- S. Admin/staff credentials -> 401
- U. Supabase Auth failure -> 401
- V. Missing student linkage -> 401

## Full Backend Test Result

46 Phase 6.5 tests: 46 passed, 0 failed
8 existing auth tests: 8 passed, 0 failed
74 tenant/RBAC/approval tests: 74 passed, 0 failed
Full backend suite: 737 passed, 5 skipped, 0 failed
(8 integration test files excluded - require running server)

## Git Verification

New (untracked) files:
  backend/app/api/student_auth.py
  backend/app/schemas/student_auth.py
  backend/app/services/student_auth.py
  backend/tests/test_student_auth_phase_6_5.py

Modified:
  backend/app/main.py (student_auth_router only)

No Phase 6.1-6.4 lock files modified.
No temporary/debug files remain.
No secrets/passwords/tokens added.

## Known Limitations

1. Email detection heuristic uses simple @ + . check.
2. Rate limiting not implemented (handled by Supabase Auth / gateway).
3. Tests use mocks; real Supabase Auth not tested in unit tests.
4. Institution code normalized to uppercase in lookup.

## Phase 6.6 Boundary

Phase 6.5 is ONLY student authentication.
DO NOT IMPLEMENT Phase 6.6+ functionality.

## Lock Status

Phase 6.5 remains UNLOCKED pending review.
No PHASE_6_5_LOCK.md has been created.
