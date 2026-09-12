/**
 * DEVELOPMENT / TESTING ONLY — password recovery service client.
 *
 * WARNING: This module talks to backend endpoints that are themselves gated
 * by the `DEV_TEST_MODE` server-side flag and return 404 when that flag is
 * disabled (the default). This is NOT part of the final demo lock and must
 * never be relied on in production.
 *
 * Boundaries mirror `services/auth.ts`:
 * - No password hashing, JWT handling, or Supabase client usage in the
 *   frontend. The backend (via Supabase Auth) is authoritative.
 * - Passwords are only ever sent in POST request bodies over HTTPS in a
 *   real deployment — never in URLs or query strings.
 * - Nothing is logged; errors surfaced here are user-safe messages only.
 */

const API_BASE_URL: string = (
  import.meta.env?.VITE_API_BASE_URL ?? '/api'
).replace(/\/+$/, '')

const DEV_AUTH_BASE = `${API_BASE_URL}/v1/dev/auth`
const STATUS_ENDPOINT = `${DEV_AUTH_BASE}/status`
const FORGOT_PASSWORD_ENDPOINT = `${DEV_AUTH_BASE}/forgot-password`
const CHANGE_PASSWORD_ENDPOINT = `${DEV_AUTH_BASE}/change-password`

export type DevAuthErrorKind =
  | 'disabled' // 404 — dev/test mode is off
  | 'invalid_credentials'
  | 'user_not_found'
  | 'validation'
  | 'server'
  | 'network'
  | 'unknown'

function messageFor(kind: DevAuthErrorKind): string {
  switch (kind) {
    case 'disabled':
      return 'This development-only feature is disabled.'
    case 'invalid_credentials':
      return 'The current password is incorrect.'
    case 'user_not_found':
      return 'No account was found for that email.'
    case 'validation':
      return 'Please check the email and password fields and try again.'
    case 'server':
      return 'The server reported an error. Please try again later.'
    case 'network':
      return 'Could not reach the backend. Please make sure the server is running.'
    default:
      return 'Something went wrong. Please try again.'
  }
}

export class DevAuthError extends Error {
  readonly kind: DevAuthErrorKind
  readonly status: number | null

  constructor(kind: DevAuthErrorKind, status: number | null, message: string | null = null) {
    super(message ?? messageFor(kind))
    this.name = 'DevAuthError'
    this.kind = kind
    this.status = status
  }
}

export function devAuthErrorMessage(error: DevAuthError): string {
  return messageFor(error.kind)
}

async function readJsonBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) return undefined
  try {
    return await response.json()
  } catch {
    return undefined
  }
}

function extractCode(body: unknown): string | null {
  if (typeof body === 'object' && body !== null) {
    const error = (body as Record<string, unknown>).error
    if (typeof error === 'object' && error !== null) {
      const code = (error as Record<string, unknown>).code
      if (typeof code === 'string') return code
    }
  }
  return null
}

async function buildError(response: Response): Promise<DevAuthError> {
  const status = response.status
  const body = await readJsonBody(response)
  const code = extractCode(body)

  if (status === 404 && code === 'NOT_FOUND') {
    return new DevAuthError('disabled', status)
  }
  if (status === 404 && code === 'USER_NOT_FOUND') {
    return new DevAuthError('user_not_found', status)
  }
  if (status === 400 && code === 'INVALID_CREDENTIALS') {
    return new DevAuthError('invalid_credentials', status)
  }
  if (status === 422) {
    return new DevAuthError('validation', status)
  }
  if (status >= 500) {
    return new DevAuthError('server', status)
  }
  return new DevAuthError('unknown', status)
}

async function postJson<T>(endpoint: string, body: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    throw new DevAuthError('network', null)
  }
  if (!response.ok) {
    throw await buildError(response)
  }
  return (await response.json()) as T
}

export interface DevAuthStatus {
  dev_test_mode: boolean
}

/**
 * Checks whether the backend has DEV_TEST_MODE enabled. Fails closed
 * (returns disabled) on any network or unexpected error so the UI never
 * shows the dev-only feature by accident.
 */
export async function fetchDevAuthStatus(): Promise<DevAuthStatus> {
  try {
    const response = await fetch(STATUS_ENDPOINT, { method: 'GET' })
    if (!response.ok) return { dev_test_mode: false }
    const body = (await response.json()) as DevAuthStatus
    return { dev_test_mode: body.dev_test_mode === true }
  } catch {
    return { dev_test_mode: false }
  }
}

export interface DevForgotPasswordRequest {
  email: string
  new_password: string
  confirm_password: string
}

export interface DevChangePasswordRequest {
  email: string
  current_password: string
  new_password: string
  confirm_password: string
}

export interface DevAuthMessageResponse {
  message: string
}

/** DEVELOPMENT / TESTING ONLY. */
export async function devForgotPassword(
  request: DevForgotPasswordRequest,
): Promise<DevAuthMessageResponse> {
  return postJson<DevAuthMessageResponse>(FORGOT_PASSWORD_ENDPOINT, request)
}

/** DEVELOPMENT / TESTING ONLY. */
export async function devChangePassword(
  request: DevChangePasswordRequest,
): Promise<DevAuthMessageResponse> {
  return postJson<DevAuthMessageResponse>(CHANGE_PASSWORD_ENDPOINT, request)
}
