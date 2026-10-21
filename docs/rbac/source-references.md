# Source references

**CAI-RBAC-001 v1.2; DRAFT - REVIEW ONLY; 21 October 2026.** Read the [reading guide](README.md) and relevant role first. Source observations are not live-deployment certification.

Paths are relative to the CollegeAIChatbot repository. Line references identify inspected symbols in the local working tree and can move after edits. These references establish source observations only.

| ID | Source | Evidence used |
|---|---|---|
| S01 | `backend/app/core/security.py` — `get_current_user` (78), `has_permission` (269), `authorize_permissions` (297), `require_institution_roles` (343), `require_super_admin` (373), `resolve_primary_role` (442) | Authenticated identity, canonical roles, permission and scope guards. |
| S02 | `backend/app/core/permissions.py` | 78-code catalog, bootstrap grants, alias, wildcard matching, Staff delegation allowlist. |
| S03 | `backend/app/db/supabase.py` — `get_user_by_auth_id` | Database role/permission projection and resolved-permissions marker. |
| S04 | `backend/app/api/admin.py` — route map, `_authorize_admin_endpoint` (177), approval handlers (922–951), student workspace handlers (1433 onward) | Admin/Staff route eligibility and per-operation permissions. |
| S05 | `backend/app/api/faculty.py` — registration (46), invitation (60), history (169) | Faculty institution guard and student workflow delegation. |
| S06 | `backend/app/api/platform.py` | Separate platform guard, route permissions, and explicit institution-targeted platform operations. |
| S07 | `backend/app/services/authorization.py` — validity (39), scope containment (57), effective authorization (75), institution context (139) | Validity intervals, ownership, academic responsibilities, and institution authorization. |
| S08 | `backend/app/services/faculty_responsibilities.py` — `authorize_section` (133), `_assert_manager` (160) | Teaching/responsibility scope and management authority. |
| S09 | `backend/app/schemas/faculty_responsibilities.py` | Supported scope types and timezone-aware validity contracts. |
| S10 | `backend/app/services/phase81_rbac.py` | Staff delegation, inherited/direct grant distinction, and teaching assignment access. |
| S11 | `backend/app/services/student_registrations.py`; `backend/app/schemas/student_registrations.py` | Class-only saves, required email, cohort reference, identity checks, and invitation opt-in. |
| S12 | `frontend/src/features/faculty/FacultyStudents.tsx`; `frontend/src/features/admin/students/StudentManager.tsx` | Shared Students workspace and role-specific pending/approval behavior. |
| S13 | `frontend/src/features/staff/StaffShell.tsx`; `frontend/src/features/students/StudentApprovalQueue.tsx` | Approval-only Staff Students navigation and permission-gated decisions. |
| S14 | `backend/app/api/users.py`; `backend/app/services/user_registration.py` | Public account registration, strict fields, and pending membership workflow. |
| S15 | `backend/app/services/student_registration_invitations.py`; `backend/app/services/email_delivery.py` | Saved-recipient scope, signup URL, delivery outcomes, and safe errors. |
| S16 | `frontend/src/features/auth/AuthProvider.tsx`; `frontend/src/types/auth.ts` | Server-authoritative identity, canonical role types, logout, and shared browser session behavior. |
| S17 | `backend/app/api/academic_setup.py`; `backend/app/services/academic_setup.py` | Academic resource mapping, including batch management permissions. |
| S18 | `frontend/src/features/students/StudentRegistrationInvitations.tsx`; `supabase/migrations/20261020020000_student_registration_invitation_delivery.sql` | Invitation choices, results, and declared claim/completion design. Migration existence does not establish deployment. |
| S19 | `frontend/src/App.tsx`; `frontend/src/features/auth/LoginForm.tsx`; `frontend/src/features/auth/RegistrationForm.tsx` | Student registration query handling and existing-session account-switch entry. |
| S20 | `backend/app/api/students.py`; `backend/app/services/student_context.py` — `get_student_context` (52) | Eligible student context and own academic access entry points. |
| S21 | `backend/app/api/ingestion.py`; `backend/app/api/conversations.py`; `backend/app/services/public_knowledge_policy.py`; `backend/app/repositories/public_knowledge.py` | Representative ingestion/chat guards and public-knowledge policy boundary. |
| S22 | `README.md` — Authentication security and session lifecycle | Documented access-JWT and refresh-session revocation distinction. |
| S23 | `supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql`; `20261013000000_faculty_tests_examination.sql`; `20261014000000_scoped_faculty_teaching_assignment_management.sql` | Declared HOD, Class In-Charge, coordinator scopes and scoped permission additions. Files were read, not executed; deployment and live grant contents are unverified. |
