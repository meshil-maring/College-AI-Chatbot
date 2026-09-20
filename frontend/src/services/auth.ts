/**
 * Phase 5.4 — Authentication service (extended by Phase 6.15.3).
 *
 * The only authentication boundary the frontend is allowed to use. It talks
 * exclusively to the existing FastAPI backend endpoints:
 *     POST /api/v1/auth/login        (email + password — admin/staff/faculty)
 *     POST /api/v1/auth/student/login (unified identifier + password — students)
 *     GET  /api/v1/auth/me           (validate a token and resolve the app user)
 *
 * Boundaries:
 * - No password hashing, JWT signing/decoding, authorization decisions,
 *   database access, or Supabase client usage. The backend is authoritative.
 * - The access token is handled as an opaque string: it is only sent in the
 *   `Authorization: Bearer` header, never in URLs, query strings, bodies,
 *   or log/source output, and never rendered by the UI.
 * - Network failures are distinguished from authentication failures via the
 *   typed `AuthError.kind` so the UI can react correctly.
 *
 * The Phase 5.3 API client (frontend/src/services/api.ts) is intentionally
 * unchanged: `auth.ts` only *produces* the token that the chat API client
 * will later consume. The chat client never performs login, and this module
 * never sends chat requests.
 *
 * Base URL follows the Phase 5.3 strategy (`VITE_API_BASE_URL=/api`, proxied
 * by the Vite dev server to the FastAPI backend).
 */

import { SESSION_EXPIRED_MESSAGE } from './sessionEvents.ts'
import type { CurrentUser, LoginRequest, LoginResponse, StudentLoginRequest } from '../types/auth.ts'

const API_BASE_URL: string = (
  import.meta.env?.VITE_API_BASE_URL ?? '/api'
).replace(/\/+$/, '')

const LOGIN_ENDPOINT: string = `${API_BASE_URL}/v1/auth/login`
const STUDENT_LOGIN_ENDPOINT: string = `${API_BASE_URL}/v1/auth/student/login`
const ME_ENDPOINT: string = `${API_BASE_URL}/v1/auth/me`

/**
 * Distinguishes which authentication operation a response belongs to, so the
 * SAME HTTP status can be classified differently by context (Phase 6.15.3):
 *   - `login`   — POST /auth/login or POST /auth/student/login. A 401 here
 *                 means the credentials were rejected (the student endpoint
 *                 normalizes every auth failure to 401 INVALID_CREDENTIALS).
 *   - `session` — GET /auth/me with a saved token. A 401/404 here means the
 *                 token is no longer accepted (session invalid/expired).
 */
type AuthOperation = 'login' | 'session'

/** Distinguishes why an authentication operation failed. */
export type AuthErrorKind =
  | 'invalid_credentials' // 400 INVALID_CREDENTIALS (/auth/login) or 401 INVALID_CREDENTIALS (/auth/student/login)
  | 'validation' // 422 FastAPI request validation failure
  | 'session_invalid' // 401/404 from /auth/me — token rejected or user gone
  | 'server' // 5xx upstream error
  | 'network' // request never produced an HTTP response
  | 'unknown'

/** User-safe message for each failure kind (never contains secrets). */
function messageFor(kind: AuthErrorKind): string {
  switch (kind) {
    case 'invalid_credentials':
      // Generic on purpose: must not reveal whether the email / register
      // number / roll number exists or which part was wrong.
      return 'Invalid login credentials. Please check your details and try again.'
    case 'validation':
      return 'Please enter a valid email and a password of at least 6 characters.'
    case 'session_invalid':
      // Phase 6.15.6 — ONE session-expiry sentence for the whole application:
      // the message shown when a saved token is rejected during restore is
      // byte-identical to the message published by the session-expiry bus
      // (services/sessionEvents.ts), so every expiry path is consistent.
      return SESSION_EXPIRED_MESSAGE
    case 'server':
      return 'The authentication server reported an error. Please try again later.'
    case 'network':
      return 'Could not reach the backend. Please make sure the server is running, then try again.'
    default:
      return 'Something went wrong during authentication. Please try again.'
  }
}

/**
 * Error raised for every failed authentication operation.
 * `message` is always safe for end-user display: it never contains
 * credentials, tokens, or backend internals.
 */
export class AuthError extends Error {
  readonly kind: AuthErrorKind
  /** HTTP status when a response was received, otherwise null (network failure). */
  readonly status: number | null
  /** Backend `error.code` when the AppError envelope was present, otherwise null. */
  readonly code: string | null

  constructor(
    kind: AuthErrorKind,
    status: number | null,
    code: string | null,
    message: string | null = null,
  ) {
    super(message ?? messageFor(kind))
    this.name = 'AuthError'
    this.kind = kind
    this.status = status
    this.code = code
  }
}

/** Map a classified auth failure to a user-safe message. */
export function authErrorMessage(error: AuthError): string {
  return messageFor(error.kind)
}

/** Best-effort JSON body parse; returns undefined when the body is not JSON. */
async function readJsonBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    return undefined
  }
  try {
    return await response.json()
  } catch {
    return undefined
  }
}

/**
 * Extract `{ code, message }` from the backend AppError envelope
 * `{ "error": { "code", "message" } }` when present.
 */
function extractAppError(body: unknown): { code: string | null; message: string | null } {
  if (typeof body === 'object' && body !== null) {
    const error = (body as Record<string, unknown>).error
    if (typeof error === 'object' && error !== null) {
      const errorObject = error as Record<string, unknown>
      return {
        code: typeof errorObject.code === 'string' ? errorObject.code : null,
        message: typeof errorObject.message === 'string' ? errorObject.message : null,
      }
    }
  }
  return { code: null, message: null }
}

/**
 * Classify a received HTTP error response into a user-safe AuthError.
 *
 * Phase 6.15.3 fix: classification is driven by the backend `error.code`
 * first and by the AUTHENTICATION OPERATION context, not by HTTP status
 * alone. The student login endpoint intentionally returns HTTP 401
 * `INVALID_CREDENTIALS` for bad credentials (anti-enumeration), while
 * GET /auth/me returns 401 for an expired/rejected token — the same status
 * must NOT collapse into `session_invalid` on a login request.
 */
async function buildAuthError(
  response: Response,
  operation: AuthOperation,
): Promise<AuthError> {
  const status = response.status
  const body = await readJsonBody(response)
  const { code } = extractAppError(body)

  // Backend error code wins over status: both /auth/login (400) and
  // /auth/student/login (401) use `INVALID_CREDENTIALS` for rejected
  // credentials.
  if (code === 'INVALID_CREDENTIALS') {
    return new AuthError('invalid_credentials', status, code)
  }
  // 422 — FastAPI/AppError request validation (e.g. missing
  // institution_code for an academic identifier login, password length).
  if (status === 422) {
    return new AuthError('validation', status, code ?? 'VALIDATION_ERROR')
  }
  // 401 on a LOGIN request — the credentials were rejected. Even without an
  // `INVALID_CREDENTIALS` code this can never mean "the saved session
  // expired": no session exists yet on a login request.
  if (operation === 'login' && status === 401) {
    return new AuthError('invalid_credentials', status, code)
  }
  // 401/404 from /auth/me (operation `session`) — the token is not accepted
  // for a current user.
  if (status === 401 || status === 404) {
    return new AuthError('session_invalid', status, code)
  }
  // Any other non-2xx with a real response.
  if (status >= 500) {
    return new AuthError('server', status, code)
  }
  return new AuthError('unknown', status, code)
}

/**
 * JSON request helper for the auth endpoints.
 *
 * Throws `AuthError` with kind `network` when no HTTP response arrives
 * (fetch-level failure) and a classified `AuthError` for non-2xx responses.
 */
async function requestAuthJson<T>(
  method: 'GET' | 'POST',
  endpoint: string,
  body: unknown,
  accessToken: string | null,
  operation: AuthOperation,
): Promise<T> {
  let response: Response
  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (accessToken !== null) {
      headers.Authorization = `Bearer ${accessToken}`
    }
    response = await fetch(endpoint, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    // fetch rejects only when the request never reached a server (DNS,
    // connection refused, CORS, aborted, ...). Never fall through as 2xx.
    throw new AuthError('network', null, null)
  }

  if (!response.ok) {
    throw await buildAuthError(response, operation)
  }

  return (await response.json()) as T
}

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
export async function studentLogin(
  request: StudentLoginRequest,
): Promise<LoginResponse> {
  return requestAuthJson<LoginResponse>(
    'POST',
    STUDENT_LOGIN_ENDPOINT,
    request,
    null,
    'login',
  )
}

/**
 * Mirror of the backend's heuristic email detection
 * (app/schemas/student_auth.py `_is_email`): a value is treated as an email
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