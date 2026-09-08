/**
 * Phase 5.4 — Authentication service.
 *
 * The only authentication boundary the frontend is allowed to use. It talks
 * exclusively to the existing FastAPI backend endpoints:
 *     POST /api/v1/auth/login   (obtain a Supabase JWT access token)
 *     GET  /api/v1/auth/me      (validate a token and resolve the app user)
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

import type { CurrentUser, LoginRequest, LoginResponse } from '../types/auth.ts'

const API_BASE_URL: string = (
  import.meta.env?.VITE_API_BASE_URL ?? '/api'
).replace(/\/+$/, '')

const LOGIN_ENDPOINT: string = `${API_BASE_URL}/v1/auth/login`
const ME_ENDPOINT: string = `${API_BASE_URL}/v1/auth/me`

/** Distinguishes why an authentication operation failed. */
export type AuthErrorKind =
  | 'invalid_credentials' // 400 INVALID_CREDENTIALS from /login
  | 'validation' // 422 FastAPI request validation failure
  | 'session_invalid' // 401/404 from /auth/me — token rejected or user gone
  | 'server' // 5xx upstream error
  | 'network' // request never produced an HTTP response
  | 'unknown'

/** User-safe message for each failure kind (never contains secrets). */
function messageFor(kind: AuthErrorKind): string {
  switch (kind) {
    case 'invalid_credentials':
      return 'The email or password is incorrect. Please try again.'
    case 'validation':
      return 'Please enter a valid email and a password of at least 6 characters.'
    case 'session_invalid':
      return 'The saved session could not be verified. Please sign in again.'
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

/** Classify a received HTTP error response into a user-safe AuthError. */
async function buildAuthError(response: Response): Promise<AuthError> {
  const status = response.status
  const body = await readJsonBody(response)
  const { code } = extractAppError(body)

  // 400 from /login — bad credentials (live-verified backend contract).
  if (status === 400 && code === 'INVALID_CREDENTIALS') {
    return new AuthError('invalid_credentials', status, code)
  }
  // 422 — FastAPI request validation (email format / password length).
  if (status === 422) {
    return new AuthError('validation', status, code ?? 'VALIDATION_ERROR')
  }
  // 401/404 from /auth/me — the token is not accepted for a current user.
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
    throw await buildAuthError(response)
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
  return requestAuthJson<LoginResponse>('POST', LOGIN_ENDPOINT, request, null)
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
  return requestAuthJson<CurrentUser>('GET', ME_ENDPOINT, undefined, accessToken)
}