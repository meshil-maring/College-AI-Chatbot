import { type AuthOperation, AuthError } from './errors.ts'
/** Best-effort JSON body parse; returns undefined when the body is not JSON. */
export async function readJsonBody(response: Response): Promise<unknown> {
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
export function extractAppError(body: unknown): { code: string | null; message: string | null } {
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
export async function buildAuthError(response: Response, operation: AuthOperation): Promise<AuthError> {
  const status = response.status
  const body = await readJsonBody(response)
  const { code } = extractAppError(body)

  if (operation === 'session' && status === 403 && code === 'ACCOUNT_INACTIVE') {
    return new AuthError('account_inactive', status, code)
  }

  if (
    status === 503 &&
    (code === 'AUTH_SERVICE_UNAVAILABLE' ||
      code === 'AUTH_VERIFICATION_UNAVAILABLE' ||
      code === 'AUTH_AUDIT_UNAVAILABLE')
  ) {
    return new AuthError('unavailable', status, code)
  }

  // Backend error code wins over status: both /auth/login (400) and
  // /auth/student/login (401) use `INVALID_CREDENTIALS` for rejected
  // credentials.
  if (code === 'INVALID_CREDENTIALS') {
    return new AuthError('invalid_credentials', status, code)
  }
  if (code === 'REGISTRATION_PENDING') {
    return new AuthError('registration_pending', status, code)
  }
  if (code === 'EMAIL_CONFIRMATION_REQUIRED') {
    return new AuthError('email_confirmation_required', status, code)
  }
  if (code === 'PASSWORD_VERIFICATION_FAILED') {
    return new AuthError('password_verification', status, code)
  }
  if (status === 429 || code === 'AUTH_RATE_LIMITED') {
    return new AuthError('rate_limited', status, code)
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
export async function requestAuthJson<T>(
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
