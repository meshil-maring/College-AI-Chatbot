/**
 * Phase 5.4 — Authentication contract types.
 *
 * Typed mirror of the actual backend authentication boundary verified against:
 *     POST /api/v1/auth/login   (backend/app/api/auth.py)
 *     GET  /api/v1/auth/me      (backend/app/main.py)
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

/** User object embedded in the login response (mirrors `/login` response `user`). */
export interface AuthUser {
  id: string
  email: string | null
}

/** Response returned by POST /api/v1/auth/login. */
export interface LoginResponse {
  access_token: string
  message: string
  user: AuthUser
}

/** Response returned by GET /api/v1/auth/me (mirrors main.py `auth_me`). */
export interface CurrentUser {
  authenticated: boolean
  user_id: string
  auth_user_id: string
  email: string | null
}