import type {
  AdminInvitationCancellation,
  AdminInvitationCreateInput,
  AdminInvitationCreated,
  AdminInvitationExpirySweep,
  AdminInvitationResend,
  AdminRoster,
} from '../../types/platform.ts'
import { API_BASE_URL, PLATFORM_BASE, requestJson } from './http.ts'
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
export async function getAdminRoster(accessToken: string, institutionId: string): Promise<AdminRoster> {
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
export async function runInvitationExpirySweep(accessToken: string): Promise<AdminInvitationExpirySweep> {
  return requestJson<AdminInvitationExpirySweep>(
    'POST',
    `${API_BASE_URL}/v1/platform/admin-invitations/expire-sweep`,
    accessToken,
  )
}
