/**
 * Phase 7.13 — Super Admin institution-management API client.
 *
 * Talks exclusively to the server-authoritative platform boundary:
 *   GET   /api/v1/platform/institutions
 *   POST  /api/v1/platform/institutions
 *   GET   /api/v1/platform/institutions/{id}
 *   PATCH /api/v1/platform/institutions/{id}
 *   POST  /api/v1/platform/institutions/{id}/suspend
 *   POST  /api/v1/platform/institutions/{id}/activate
 *   POST  /api/v1/platform/institutions/{id}/admins
 *
 * Security notes:
 * - The session token is sent ONLY in the `Authorization` header, never in the
 *   URL or a query string, so it cannot leak through logs or history.
 * - This client performs NO authorization decision. Hiding a button is a UX
 *   affordance only; the backend independently enforces `require_super_admin`
 *   on every one of these endpoints.
 * - No credential material is ever handled here — the admin-assignment call
 *   carries only an email for an ALREADY existing account.
 */

import type {
  AdminInvitationCancellation,
  AdminInvitationCreateInput,
  AdminInvitationCreated,
  AdminInvitationExpirySweep,
  AdminInvitationResend,
  AdminRevocationResult,
  AdminRoster,
  InstitutionAdminAssignment,
  InstitutionCreateInput,
  InstitutionDetail,
  InstitutionLifecycleResult,
  InstitutionSummary,
  InstitutionUpdateInput,
  PlatformAuditFilters,
  PlatformAuditPage,
} from '../types/platform.ts'
import { notifySessionExpired } from './sessionEvents.ts'

const API_BASE_URL: string = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')
const PLATFORM_BASE = `${API_BASE_URL}/v1/platform/institutions`

/** A platform API failure carrying the server's stable error code. */
export class PlatformInstitutionError extends Error {
  readonly status: number
  readonly code: string | null

  constructor(status: number, message: string, code: string | null = null) {
    super(message)
    this.name = 'PlatformInstitutionError'
    this.status = status
    this.code = code
  }
}

/** Extract the `{ error: { code, message } }` envelope used by AppError. */
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

async function requestJson<T>(
  method: 'GET' | 'POST' | 'PATCH',
  endpoint: string,
  accessToken: string,
  body?: unknown,
): Promise<T> {
  let response: Response
  try {
    const headers: Record<string, string> = { Authorization: `Bearer ${accessToken}` }
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    response = await fetch(endpoint, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new PlatformInstitutionError(0, 'Could not reach the backend. Please try again.')
  }

  if (response.status === 401) notifySessionExpired(accessToken)
  if (!response.ok) {
    const { message, code } = await readError(response)
    throw new PlatformInstitutionError(response.status, message, code)
  }
  return (await response.json()) as T
}

/** List every institution with safe platform metadata. */
export async function listInstitutions(accessToken: string): Promise<InstitutionSummary[]> {
  const body = await requestJson<{ institutions: InstitutionSummary[] }>(
    'GET',
    PLATFORM_BASE,
    accessToken,
  )
  return body.institutions
}

/** Read one institution's safe configuration detail. */
export async function getInstitution(
  accessToken: string,
  institutionId: string,
): Promise<InstitutionDetail> {
  return requestJson<InstitutionDetail>(
    'GET',
    `${PLATFORM_BASE}/${encodeURIComponent(institutionId)}`,
    accessToken,
  )
}

/** Create an institution. The code is normalized and validated server-side. */
export async function createInstitution(
  accessToken: string,
  input: InstitutionCreateInput,
): Promise<InstitutionDetail> {
  return requestJson<InstitutionDetail>('POST', PLATFORM_BASE, accessToken, input)
}

/** Update an institution's safe configuration (never its lifecycle status). */
export async function updateInstitution(
  accessToken: string,
  institutionId: string,
  input: InstitutionUpdateInput,
): Promise<InstitutionDetail> {
  return requestJson<InstitutionDetail>(
    'PATCH',
    `${PLATFORM_BASE}/${encodeURIComponent(institutionId)}`,
    accessToken,
    input,
  )
}


/**
 * Suspend an institution. Existing data is retained and no accounts are
 * revoked — the server's returned message states this explicitly.
 */
export async function suspendInstitution(
  accessToken: string,
  institutionId: string,
): Promise<InstitutionLifecycleResult> {
  return requestJson<InstitutionLifecycleResult>(
    'POST',
    `${PLATFORM_BASE}/${encodeURIComponent(institutionId)}/suspend`,
    accessToken,
  )
}

/** Activate a pending institution or reactivate a suspended institution. */
export async function activateInstitution(
  accessToken: string,
  institutionId: string,
): Promise<InstitutionLifecycleResult> {
  return requestJson<InstitutionLifecycleResult>(
    'POST',
    `${PLATFORM_BASE}/${encodeURIComponent(institutionId)}/activate`,
    accessToken,
  )
}

/**
 * Assign an EXISTING account as University Admin of one institution.
 *
 * This is an assignment, not provisioning: no password is sent and no Auth
 * account is created. The granted role is fixed server-side to the
 * institution-scoped `admin` role.
 */
export async function assignInstitutionAdmin(
  accessToken: string,
  institutionId: string,
  email: string,
): Promise<InstitutionAdminAssignment> {
  return requestJson<InstitutionAdminAssignment>(
    'POST',
    `${PLATFORM_BASE}/${encodeURIComponent(institutionId)}/admins`,
    accessToken,
    { email },
  )
}

// ===========================================================================
// Phase 7.14 — University Admin invitation lifecycle
//
// Security notes:
// - Every call sends the session token ONLY in the `Authorization` header.
// - None of these calls ever sends a password, a token hash, or any credential
//   other than the caller's own session token. In particular `createInvitation`
//   carries ONLY an email.
// - `invitation_token` from the create response is held in component state just
//   long enough for the operator to copy the link; it is never persisted to
//   localStorage, never logged, and never put into a URL by this client.
// - These functions make NO authorization decision. Every endpoint
//   independently enforces `require_super_admin` on the server.
// ===========================================================================

/**
 * Invite one person to be University Admin of an institution.
 *
 * The email is the only input. No password is ever sent through the
 * platform-management API, and the returned raw token is surfaced to the
 * operator exactly once.
 */
export async function createInvitation(
  accessToken: string,
  institutionId: string,
  input: AdminInvitationCreateInput,
): Promise<AdminInvitationCreated> {
  return requestJson<AdminInvitationCreated>(
    'POST',
    `${PLATFORM_BASE}/${encodeURIComponent(institutionId)}/admins/invitations`,
    accessToken,
    input,
  )
}

/** Read an institution's University Admins and pending invitations. */
export async function getAdminRoster(
  accessToken: string,
  institutionId: string,
): Promise<AdminRoster> {
  return requestJson<AdminRoster>(
    'GET',
    `${PLATFORM_BASE}/${encodeURIComponent(institutionId)}/admins/roster`,
    accessToken,
  )
}

/** Cancel a pending invitation, making its token permanently unusable. */
export async function cancelInvitation(
  accessToken: string,
  institutionId: string,
  invitationId: string,
): Promise<AdminInvitationCancellation> {
  return requestJson<AdminInvitationCancellation>(
    'POST',
    `${PLATFORM_BASE}/${encodeURIComponent(institutionId)}/admins/invitations/${encodeURIComponent(invitationId)}/cancel`,
    accessToken,
  )
}

/**
 * Phase 7.15 — supersede a pending invitation's token and re-send it.
 *
 * The server overwrites the stored token digest in place, so the previously
 * issued link stops working immediately and only ONE invitation URL is ever
 * live. The new raw token is returned exactly once here (it is stored solely as
 * a SHA-256 digest) and is never persisted, logged or put into a URL by this
 * client.
 *
 * Only a PENDING invitation can be resent; a terminal one returns
 * `INVITATION_NOT_RESENDABLE` (409). Rate limiting returns a safe
 * `INVITATION_RATE_LIMITED` (429). A delivery failure is reported as
 * `email_delivery.status === 'failed'`, never as a success.
 */
export async function resendInvitation(
  accessToken: string,
  institutionId: string,
  invitationId: string,
): Promise<AdminInvitationResend> {
  return requestJson<AdminInvitationResend>(
    'POST',
    `${PLATFORM_BASE}/${encodeURIComponent(institutionId)}/admins/invitations/${encodeURIComponent(invitationId)}/resend`,
    accessToken,
  )
}

/**
 * Phase 7.15 — run the invitation expiry sweep (Super Admin only).
 *
 * This is CLEANUP, not a security boundary: acceptance independently refuses an
 * elapsed invitation, so this call's absence or failure can never make an
 * expired invitation usable. Running it repeatedly is safe.
 */
export async function runInvitationExpirySweep(
  accessToken: string,
): Promise<AdminInvitationExpirySweep> {
  return requestJson<AdminInvitationExpirySweep>(
    'POST',
    `${API_BASE_URL}/v1/platform/admin-invitations/expire-sweep`,
    accessToken,
  )
}

/**
 * Revoke one institution-scoped University Admin.
 *
 * Only the (admin, this institution) grant is removed server-side; the account
 * and any other role the person holds are preserved.
 */
export async function revokeInstitutionAdmin(
  accessToken: string,
  institutionId: string,
  userId: string,
): Promise<AdminRevocationResult> {
  return requestJson<AdminRevocationResult>(
    'POST',
    `${PLATFORM_BASE}/${encodeURIComponent(institutionId)}/admins/${encodeURIComponent(userId)}/revoke`,
    accessToken,
  )
}

/** Read one bounded page of the platform audit ledger. Read-only by contract. */
export async function listPlatformAudit(
  accessToken: string,
  filters: PlatformAuditFilters = {},
): Promise<PlatformAuditPage> {
  const query = new URLSearchParams()
  if (filters.institution_id !== undefined) {
    query.set('institution_id', filters.institution_id)
  }
  if (filters.action !== undefined) query.set('action', filters.action)
  if (filters.date_from !== undefined) query.set('date_from', filters.date_from)
  if (filters.date_to !== undefined) query.set('date_to', filters.date_to)
  if (filters.limit !== undefined) query.set('limit', String(filters.limit))
  if (filters.offset !== undefined) query.set('offset', String(filters.offset))
  const suffix = query.toString()
  return requestJson<PlatformAuditPage>(
    'GET',
    `${API_BASE_URL}/v1/platform/audit${suffix === '' ? '' : `?${suffix}`}`,
    accessToken,
  )
}
