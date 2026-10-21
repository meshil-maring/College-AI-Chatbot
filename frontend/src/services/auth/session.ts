import type { CurrentUser, LoginRequest, LoginResponse, StudentLoginRequest } from '../../types/auth.ts'
import {
  CHANGE_PASSWORD_ENDPOINT,
  FORGOT_PASSWORD_ENDPOINT,
  LOGIN_ENDPOINT,
  LOGOUT_ALL_ENDPOINT,
  LOGOUT_ENDPOINT,
  ME_ENDPOINT,
  REFRESH_ENDPOINT,
  RESET_PASSWORD_ENDPOINT,
  STUDENT_LOGIN_ENDPOINT,
} from './endpoints.ts'
import { requestAuthJson } from './http.ts'
/**
 * Authenticate with the backend password flow.
 *
 * @param request `{ email, password }` exactly as accepted by the backend.
 * @returns The parsed login response containing the Supabase JWT
 *          (`access_token`), the backend message, and the auth user.
 * @throws AuthError Classified per `AuthErrorKind`; never includes
 *                   credentials or tokens in the message.
 */
export async function login(request: LoginRequest): Promise<LoginResponse> {
  return requestAuthJson<LoginResponse>('POST', LOGIN_ENDPOINT, request, null, 'login')
}

/**
 * Authenticate a student via POST /api/v1/auth/student/login using the
 * backend's UNIFIED `identifier` field (email / register number /
 * university roll number). The backend resolves the identifier type itself;
 * the frontend never classifies register-number vs roll-number formats.
 *
 * The response reuses the existing locked login contract
 * (`{ access_token, message, user: { id, email } }`), so identity bootstrap
 * via GET /auth/me works unchanged afterwards.
 *
 * @throws AuthError kind `invalid_credentials` on HTTP 401 (the backend
 *                   normalizes EVERY student auth failure — unknown
 *                   identifier, wrong password, pending/rejected student,
 *                   inactive lifecycle — to 401 INVALID_CREDENTIALS so no
 *                   account information is ever disclosed), `validation`
 *                   on 422 (e.g. missing institution_code), `server`,
 *                   `network`, or `unknown`.
 */
export async function studentLogin(request: StudentLoginRequest): Promise<LoginResponse> {
  return requestAuthJson<LoginResponse>('POST', STUDENT_LOGIN_ENDPOINT, request, null, 'login')
}

/**
 * Mirror of the backend's heuristic email detection
 * (app/schemas/auth/student_auth.py `_is_email`): a value is treated as an email
 * when it contains "@" and the part after it contains ".". Everything else
 * is an academic identifier (register number / university roll number).
 *
 * Used ONLY to decide which endpoint to call and whether an institution
 * code is required — never to interpret identifier semantics (the backend
 * remains authoritative).
 */
export function isEmailAddress(value: string): boolean {
  const trimmed = value.trim()
  if (!trimmed.includes('@')) return false
  const domain = trimmed.split('@').pop() ?? ''
  return domain.includes('.')
}

/**
 * Authenticate with EITHER backend password flow from a single UI input:
 *
 * - Email identifier        → existing POST /api/v1/auth/login (admin,
 *                             staff, faculty, and email-based student
 *                             login all keep working unchanged).
 * - Academic identifier     → POST /api/v1/auth/student/login with
 *   (register/roll number)    `institution_code` (required by the backend;
 *                             the caller must supply it).
 *
 * @param identifier Email, register number, or university roll number.
 * @param password The plaintext password (sent only in the POST body).
 * @param institutionCode Public institution code — REQUIRED for academic
 *                        identifier login, ignored (not sent) for email.
 * @throws AuthError Classified per `AuthErrorKind`.
 */
export async function authenticate(
  identifier: string,
  password: string,
  institutionCode?: string,
): Promise<LoginResponse> {
  const trimmed = identifier.trim()
  if (isEmailAddress(trimmed)) {
    // Existing general email contract — unchanged for admin/staff/faculty.
    return login({ email: trimmed, password })
  }
  // Academic identifier → student login contract (institution-scoped).
  return studentLogin({
    identifier: trimmed,
    password,
    institution_code: institutionCode?.trim() || undefined,
  })
}

/**
 * Resolve the authenticated application user for a bearer token
 * via GET /api/v1/auth/me.
 *
 * @param accessToken The JWT obtained from `login`.
 * @returns The current user's identity (user_id, auth_user_id, email).
 * @throws AuthError kind `session_invalid` when the token is rejected or the
 *                   application user does not exist.
 */
export async function fetchCurrentUser(accessToken: string): Promise<CurrentUser> {
  return requestAuthJson<CurrentUser>('GET', ME_ENDPOINT, undefined, accessToken, 'session')
}

export interface AuthMessageResponse {
  message: string
}

export async function requestPasswordRecovery(email: string): Promise<AuthMessageResponse> {
  return requestAuthJson<AuthMessageResponse>('POST', FORGOT_PASSWORD_ENDPOINT, { email }, null, 'mutation')
}

export async function completePasswordReset(
  accessToken: string,
  newPassword: string,
  confirmPassword: string,
): Promise<AuthMessageResponse> {
  return requestAuthJson<AuthMessageResponse>(
    'POST',
    RESET_PASSWORD_ENDPOINT,
    { new_password: newPassword, confirm_password: confirmPassword },
    accessToken,
    'mutation',
  )
}

export async function changePassword(
  accessToken: string,
  currentPassword: string,
  newPassword: string,
  confirmPassword: string,
): Promise<AuthMessageResponse> {
  return requestAuthJson<AuthMessageResponse>(
    'POST',
    CHANGE_PASSWORD_ENDPOINT,
    {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    },
    accessToken,
    'mutation',
  )
}

export async function refreshSession(refreshToken: string): Promise<LoginResponse> {
  return requestAuthJson<LoginResponse>('POST', REFRESH_ENDPOINT, { refresh_token: refreshToken }, null, 'session')
}

export async function revokeSession(accessToken: string, revokeAll = false): Promise<AuthMessageResponse> {
  return requestAuthJson<AuthMessageResponse>(
    'POST',
    revokeAll ? LOGOUT_ALL_ENDPOINT : LOGOUT_ENDPOINT,
    undefined,
    accessToken,
    'session',
  )
}
