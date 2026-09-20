/**
 * Phase 5.4 — Authentication contract types.
 *
 * Typed mirror of the actual backend authentication boundary verified against:
 *     POST /api/v1/auth/login        (backend/app/api/auth.py)
 *     POST /api/v1/auth/student/login (backend/app/api/student_auth.py)
 *     GET  /api/v1/auth/me           (backend/app/main.py)
 *
 * The backend is authoritative:
 *     backend/app/api/auth.py        (AuthRequest, /login handler)
 *     backend/app/main.py            (/api/v1/auth/me handler)
 *     backend/app/core/security.py   (get_current_user dependency)
 *     backend/app/core/errors.py     (AppError JSON error envelope)
 *
 * Only fields the backend actually returns are declared. `access_token` is a
 * Supabase-issued JWT (a string). The login endpoint returns no refresh token
 * and no expiration information, so neither is declared here.
 *
 * Error responses use the backend `AppError` envelope:
 *     { "error": { "code": "...", "message": "..." } }
 * with HTTP 400 (`INVALID_CREDENTIALS`, `AUTH_ERROR`), 401
 * (`AUTH_REQUIRED`, `INVALID_SCHEME`, `TOKEN_MISSING`, `TOKEN_EXPIRED`,
 * `INVALID_TOKEN`), and 404 (`USER_NOT_FOUND`). FastAPI validation failures
 * (422) use the framework's `{ "detail": [...] }` shape.
 */

/** Request body accepted by POST /api/v1/auth/login (mirrors backend AuthRequest). */
export interface LoginRequest {
  email: string
  password: string
}

/**
 * Request body accepted by POST /api/v1/auth/student/login (Phase 6.5,
 * mirrors backend `StudentLoginRequest` in app/schemas/student_auth.py).
 *
 * `identifier` is the backend's UNIFIED identifier field: it may be an email
 * address, a register number, or a university roll number — the backend
 * resolves the type itself, so the frontend never needs to classify
 * register numbers vs roll numbers (there are no per-field formats defined).
 *
 * `institution_code` is REQUIRED by the backend for academic identifier
 * (register number / university roll number) login because those identifiers
 * are institution-scoped (Phase 6.2); it is ignored for email login. The
 * schema uses `extra="forbid"` — nothing else may be submitted.
 */
export interface StudentLoginRequest {
  identifier: string
  password: string
  /** Required for academic identifiers (register/roll number), omitted for email. */
  institution_code?: string
}

/** User object embedded in the login response (mirrors `/login` response `user`). */
export interface AuthUser {
  id: string
  email: string | null
}

/** Response returned by POST /api/v1/auth/login AND POST /api/v1/auth/student/login
 *  (the student endpoint reuses this exact locked contract). */
export interface LoginResponse {
  access_token: string
  message: string
  user: AuthUser
}
/**
 * Phase 6.15.4 — canonical authenticated role.
 *
 * Mirrors the backend's ONLY existing role names (app/core/security.py
 * `SUPPORTED_ROLES` — the same names the Phase 6.6 RBAC `require_roles`
 * primitive and the `roles` table use). No new role is invented; `null`
 * (no supported role) is represented by `CurrentUser.role === null`, not by
 * a string.
 */
export type AuthRole = 'admin' | 'staff' | 'faculty' | 'student'



/** Response returned by GET /api/v1/auth/me (mirrors main.py `auth_me`). */
export interface CurrentUser {
  authenticated: boolean
  user_id: string
  auth_user_id: string
  email: string | null
  /**
   * Phase 6.15.4 — SERVER-authoritative canonical role, resolved by the
   * backend from the authenticated JWT -> public.users -> user_roles ->
   * roles chain. `null` means the account holds no supported role; the
   * frontend must treat that as "no privileged UI". Never derived from
   * email/identifier/localStorage on the client.
   */
  role: AuthRole | null
  /**
   * Phase 6.15.4 — tenant (institution) context, resolved server-side the
   * same way the rest of the application resolves tenancy. `null` for
   * platform-level accounts. Internal database identifiers other than this
   * tenant key are not exposed.
   */
  institution_id: string | null
}
