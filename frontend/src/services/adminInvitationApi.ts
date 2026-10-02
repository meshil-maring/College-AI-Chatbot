/**
 * Phase 7.14 — University Admin invitation client for the INVITED PERSON.
 *
 * This is the only frontend client that talks to the unauthenticated
 * `/admin-invitations` boundary, and the only one that ever transmits a
 * password. It is deliberately separate from `platformInstitutionsApi.ts`:
 *
 * - The invited person is NOT signed in yet; there is no session token to send,
 *   and none is invented. Authorization here is possession of the opaque
 *   one-time token.
 * - The password is sent ONLY here, ONLY on the accept call, and ONLY to the
 *   backend, which forwards it to Supabase Auth. It is never persisted to
 *   localStorage or sessionStorage, never logged, and never echoed back.
 * - The token is treated as an opaque lookup credential. No institution data is
 *   ever taken from a URL parameter: the server resolves
 *   `invitation -> institution -> role` itself.
 * - This client makes NO authorization decision; the server enforces validity,
 *   expiry and one-time use on every call.
 */

import type {
  AdminInvitationAcceptInput,
  AdminInvitationAcceptance,
  AdminInvitationPublicView,
} from '../types/platform.ts'

const API_BASE_URL: string = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')
const INVITATION_BASE = `${API_BASE_URL}/v1/admin-invitations`

/**
 * A public invitation-boundary failure. Unlike the platform client this carries
 * no session, so a 401 cannot be "session expired" — it means the invitation
 * itself is not currently usable, and the code tells the page which case.
 */
export class AdminInvitationError extends Error {
  readonly status: number
  readonly code: string | null

  constructor(status: number, message: string, code: string | null = null) {
    super(message)
    this.name = 'AdminInvitationError'
    this.status = status
    this.code = code
  }

  /** True when retrying with the same link can never succeed. */
  get isTerminal(): boolean {
    return (
      this.code === 'INVITATION_EXPIRED' ||
      this.code === 'INVITATION_CANCELLED' ||
      this.code === 'INVITATION_ALREADY_ACCEPTED'
    )
  }

  /**
   * Phase 7.15 — true when the server refused for abuse-prevention reasons.
   *
   * This is deliberately NOT terminal: the same link still works, the caller
   * simply has to wait. The page keeps the form so a legitimate invitee who
   * mistyped a few passwords is not locked out of their own account.
   */
  get isRateLimited(): boolean {
    return this.status === 429
  }
}

async function readError(response: Response): Promise<{ message: string; code: string | null }> {
  try {
    const body: unknown = await response.json()
    if (typeof body === 'object' && body !== null) {
      const envelope = (body as Record<string, unknown>).error
      if (typeof envelope === 'object' && envelope !== null) {
        const record = envelope as Record<string, unknown>
        const message = typeof record.message === 'string' ? record.message : null
        const code = typeof record.code === 'string' ? record.code : null
        if (message !== null) return { message, code }
        if (code !== null) return { message: `Request failed (${code})`, code }
      }
    }
  } catch {
    // Non-JSON error body; fall through to the status-based message.
  }
  return { message: `Request failed with HTTP ${response.status}`, code: null }
}

async function request<T>(
  method: 'GET' | 'POST',
  endpoint: string,
  body?: unknown,
): Promise<T> {
  let response: Response
  try {
    const headers: Record<string, string> = {}
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    response = await fetch(endpoint, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new AdminInvitationError(0, 'Could not reach the backend. Please try again.')
  }
  if (!response.ok) {
    const { message, code } = await readError(response)
    throw new AdminInvitationError(response.status, message, code)
  }
  return (await response.json()) as T
}

/**
 * Inspect an invitation link: which institution is it for, and is it still
 * usable? Returns only the bounded public projection — never a token hash, a
 * user record or any other institution's data.
 */
export async function inspectInvitation(token: string): Promise<AdminInvitationPublicView> {
  return request<AdminInvitationPublicView>(
    'GET',
    `${INVITATION_BASE}/${encodeURIComponent(token)}`,
  )
}

/**
 * Accept the invitation and set up the account with a chosen password.
 *
 * The server consumes the token atomically, so a second call with the same
 * token fails with `INVITATION_ALREADY_ACCEPTED` (or `INVITATION_INVALID` when
 * two requests race). On success the person signs in through the ordinary
 * admin login page — this call returns no session.
 */
export async function acceptInvitation(
  token: string,
  input: AdminInvitationAcceptInput,
): Promise<AdminInvitationAcceptance> {
  return request<AdminInvitationAcceptance>(
    'POST',
    `${INVITATION_BASE}/${encodeURIComponent(token)}/accept`,
    input,
  )
}