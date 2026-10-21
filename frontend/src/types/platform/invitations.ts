/**
 * Phase 7.14 — Super Admin University Admin lifecycle types.
 *
 * These mirror the backend's explicit response schemas
 * (`backend/app/schemas/invitations/admin_invitations.py`). The frontend never models an
 * invitation as a raw database row and never derives authority from these
 * values: authorization is decided by the server on every request.
 */

/**
 * The invitation lifecycle. `invited` is the only non-terminal state; the
 * backend enforces that `accepted`, `cancelled` and `expired` are permanent.
 */
export type AdminInvitationStatus = 'invited' | 'accepted' | 'cancelled' | 'expired'

/**
 * Phase 7.15 — invitation email delivery bookkeeping.
 *
 * This is delivery state, NOT a lifecycle state: an invitation whose email
 * failed is still a live `invited` invitation. Keeping the two vocabularies
 * separate is what stops a delivery outage from being mistaken for a revoked
 * or cancelled access grant.
 */
export type EmailDeliveryStatus = 'pending' | 'sent' | 'delivered' | 'failed'

/**
 * What actually happened when the server tried to send the invitation email.
 *
 * The backend never reports a success it did not observe: `status` is the
 * provider's real result. Only the provider NAME and a bounded, non-sensitive
 * status code are exposed — never an API key, SMTP response or message body.
 */
export interface EmailDeliveryOutcome {
  readonly status: 'pending' | 'sent' | 'failed'
  readonly provider: string
  readonly detail: string | null
}

/**
 * Safe invitation projection for the Super Admin roster.
 *
 * Note the ABSENCE of any token or digest field — the backend has no such
 * response field, so a token hash cannot reach the browser even by accident.
 */
export interface AdminInvitationView {
  readonly invitation_id: string
  readonly institution_id: string
  readonly email: string
  readonly role_name?: 'admin' | 'staff' | 'faculty'
  readonly status: AdminInvitationStatus
  readonly expires_at: string | null
  readonly created_at: string | null
  readonly accepted_at: string | null
  readonly cancelled_at: string | null
  readonly email_verified_at: string | null
  readonly email_delivery_status: EmailDeliveryStatus
  readonly email_delivery_at: string | null
  readonly email_delivery_attempts: number
  readonly resend_count: number
  readonly last_sent_at: string | null
}

/**
 * Result of creating an invitation.
 *
 * `invitation_token` and `invitation_url` are shown ONCE, to the operator who
 * just created the invitation. They are never persisted, never logged and are
 * not re-servable — if lost, the invitation is cancelled and reissued.
 */
export interface AdminInvitationCreated {
  readonly invitation: AdminInvitationView
  readonly invitation_token: string
  readonly invitation_url: string
  readonly expires_in_hours: number
  readonly email_delivery: EmailDeliveryOutcome
}

/**
 * Result of superseding a pending invitation's token and re-sending it.
 *
 * The NEW token is returned exactly once, by the same rule as creation. The
 * previous URL is already dead when this response is produced, so there is
 * never more than one usable invitation link per invitation.
 */
export interface AdminInvitationResend {
  readonly invitation: AdminInvitationView
  readonly invitation_token: string
  readonly invitation_url: string
  readonly expires_in_hours: number
  readonly email_delivery: EmailDeliveryOutcome
  readonly previous_token_invalidated: boolean
  readonly message: string
}

/** How many invitations the expiry sweep transitioned on its last run. */
export interface AdminInvitationExpirySweep {
  readonly scanned: number
  readonly expired: number
  readonly already_terminal: number
}

/**
 * What the invited person may see about their own link. Deliberately minimal:
 * no invitation id, no user record, no audit data, no other tenant's data.
 */
export interface AdminInvitationPublicView {
  readonly account_recovery_available?: boolean
  readonly status: AdminInvitationStatus
  readonly institution_name: string
  readonly institution_code: string
  readonly email: string
  readonly role?: 'admin' | 'staff' | 'faculty'
  readonly expires_at: string | null
  /**
   * The SERVER's verification state, not the browser's. The acceptance request
   * schema has no such field and rejects extras, so this can never be asserted
   * by the client — it can only become true because acceptance proved the Auth
   * account carries exactly the invited address.
   */
  readonly email_verified: boolean
}

/** Result of accepting an invitation and setting up the account. */
export interface AdminInvitationAcceptance {
  readonly institution_id: string
  readonly institution_name: string
  readonly email: string
  readonly role: 'admin' | 'staff' | 'faculty'
  readonly scope: 'institution'
  readonly message: string
}

/** Result of cancelling a pending invitation. */
export interface AdminInvitationCancellation {
  readonly invitation_id: string
  readonly institution_id: string
  readonly status: 'cancelled'
  readonly already_applied: boolean
  readonly message: string
}

/**
 * Create payload: an email and nothing else.
 *
 * There is deliberately no `role`, `institution_id`, `scope`, `status` or
 * `expires_at` here — the backend rejects them, and this type makes them
 * unrepresentable. No password is ever sent through this endpoint.
 */
export interface AdminInvitationCreateInput {
  readonly email: string
}

/**
 * Acceptance payload: only what Supabase Auth needs to create the account.
 * No role, institution or scope — those come from the invitation server-side.
 */
export interface AdminInvitationAcceptInput {
  readonly password: string
  readonly first_name?: string
  readonly last_name?: string
}
