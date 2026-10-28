import { SESSION_EXPIRED_MESSAGE } from '../shared/sessionEvents.ts'

/**
 * Distinguishes which authentication operation a response belongs to, so the
 * SAME HTTP status can be classified differently by context (Phase 6.15.3):
 *   - `login`   — POST /auth/login or POST /auth/student/login. A 401 here
 *                 means the credentials were rejected (the student endpoint
 *                 normalizes every auth failure to 401 INVALID_CREDENTIALS).
 *   - `session` — GET /auth/me with a saved token. A 401/404 here means the
 *                 token is no longer accepted (session invalid/expired).
 */
export type AuthOperation = 'login' | 'session' | 'mutation'

/** Distinguishes why an authentication operation failed. */
export type AuthErrorKind =
  | 'invalid_credentials' // 400 INVALID_CREDENTIALS (/auth/login) or 401 INVALID_CREDENTIALS (/auth/student/login)
  | 'registration_pending' // verified faculty/staff credentials awaiting admin approval
  | 'email_confirmation_required' // provider verified the password but email setup is incomplete
  | 'account_inactive' // existing ACCOUNT_INACTIVE denial while validating a session
  | 'validation' // 422 FastAPI request validation failure
  | 'session_invalid' // 401/404 from /auth/me — token rejected or user gone
  | 'server' // 5xx upstream error
  | 'unavailable' // authentication dependency temporarily unavailable
  | 'network' // request never produced an HTTP response
  | 'rate_limited'
  | 'password_verification'
  | 'unknown'

/** User-safe message for each failure kind (never contains secrets). */
export function messageFor(kind: AuthErrorKind): string {
  switch (kind) {
    case 'invalid_credentials':
      // Generic on purpose: must not reveal whether the email / register
      // number / roll number exists or which part was wrong.
      return 'Invalid login credentials. Please check your details and try again. For help with account approval or access, contact your administrator.'
    case 'registration_pending':
      return 'Your registration is pending. You can sign in after your institution approves it. Contact your institution administrator if you need help.'
    case 'email_confirmation_required':
      return 'Confirm your email address before signing in. If your staff or faculty registration is already approved, ask your institution administrator to retry sign-in setup in Staff & Faculty.'
    case 'account_inactive':
      return 'Your account is inactive. Contact your institution administrator for help with access.'
    case 'validation':
      return 'Please enter a valid email and a password of at least 6 characters.'
    case 'session_invalid':
      // Phase 6.15.6 — ONE session-expiry sentence for the whole application:
      // the message shown when a saved token is rejected during restore is
      // byte-identical to the message published by the session-expiry bus
      // (services/shared/sessionEvents.ts), so every expiry path is consistent.
      return SESSION_EXPIRED_MESSAGE
    case 'server':
      return 'The authentication server reported an error. Please try again later.'
    case 'unavailable':
      return 'Authentication is temporarily unavailable. Please try again shortly.'
    case 'network':
      return 'Could not reach the backend. Please make sure the server is running, then try again.'
    case 'rate_limited':
      return 'Too many authentication requests. Please wait a moment and try again.'
    case 'password_verification':
      return 'Current credentials could not be verified.'
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

  constructor(kind: AuthErrorKind, status: number | null, code: string | null, message: string | null = null) {
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
