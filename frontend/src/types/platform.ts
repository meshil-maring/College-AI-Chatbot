/**
 * Phase 7.13 — Super Admin platform institution-management types.
 *
 * These mirror the backend's explicit response schemas
 * (`backend/app/schemas/platform.py`). The frontend never models an
 * institution as a raw database row and never derives authority from these
 * values: authorization is decided by the server on every request.
 */

/**
 * The canonical institution lifecycle, reusing the existing Phase 6.13
 * `institutions.status` vocabulary rather than introducing a second one.
 */
export type InstitutionStatus = 'pending' | 'active' | 'suspended' | 'rejected'

/** Safe list projection: platform metadata only, never tenant-owned data. */
export interface InstitutionSummary {
  readonly id: string
  readonly code: string
  readonly name: string
  readonly status: InstitutionStatus
  readonly is_active: boolean
  readonly admin_count: number
}

/** Safe detail projection including the optional branding foundation. */
export interface InstitutionDetail {
  readonly id: string
  readonly code: string
  readonly name: string
  readonly display_name: string | null
  readonly status: InstitutionStatus
  readonly is_active: boolean
  readonly logo_url: string | null
  readonly primary_color: string | null
  readonly secondary_color: string | null
  readonly welcome_message: string | null
  readonly created_at: string | null
  readonly updated_at: string | null
  readonly admin_count: number
}

/** Result of a suspend/activate transition, with the retention guarantee. */
export interface InstitutionLifecycleResult {
  readonly id: string
  readonly code: string
  readonly name: string
  readonly status: 'active' | 'suspended'
  readonly is_active: boolean
  readonly already_applied: boolean
  readonly message: string
}

/** Result of assigning an existing account as University Admin. */
export interface InstitutionAdminAssignment {
  readonly institution_id: string
  readonly assigned: boolean
  readonly already_assigned: boolean
  readonly admin: {
    readonly user_id: string
    readonly email: string
    readonly institution_id: string
    readonly scope: 'institution'
  }
}

/**
 * Phase 7.14 — Super Admin University Admin lifecycle types.
 *
 * These mirror the backend's explicit response schemas
 * (`backend/app/schemas/admin_invitations.py`). The frontend never models an
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

/**
 * One roster row: EITHER an accepted admin (with a user id) OR an invitation
 * (with an invitation id). Only platform-administration fields appear.
 */
export interface AdminRosterEntry {
  readonly email: string
  readonly kind: 'admin' | 'invitation'
  readonly status: string
  readonly user_id: string | null
  readonly invitation_id: string | null
  readonly institution_id: string
  readonly expires_at: string | null
  readonly email_delivery_status: EmailDeliveryStatus | null
  readonly email_delivery_attempts: number | null
  readonly email_verified: boolean
  readonly resend_count: number | null
}

/** An institution's University Admins plus its pending invitations. */
export interface AdminRoster {
  readonly institution_id: string
  readonly admins: readonly AdminRosterEntry[]
  readonly pending_invitations: readonly AdminRosterEntry[]
  readonly admin_count: number
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
 * Result of revoking an institution admin. `message` states explicitly that the
 * account and any other role were preserved.
 */
export interface AdminRevocationResult {
  readonly institution_id: string
  readonly user_id: string
  readonly revoked: boolean
  readonly already_revoked: boolean
  readonly message: string
}

/** The platform audit vocabulary, mirroring the Phase 7.14 migration CHECK. */
export type PlatformAuditAction =
  | 'institution_created'
  | 'institution_updated'
  | 'institution_suspended'
  | 'institution_activated'
  | 'admin_assigned'
  | 'institution_admin_invited'
  | 'institution_admin_invitation_accepted'
  | 'institution_admin_invitation_expired'
  | 'institution_admin_invitation_cancelled'
  | 'institution_admin_revoked'
  | 'institution_admin_invitation_email_sent'
  | 'institution_admin_invitation_email_failed'
  | 'institution_admin_invitation_resent'
  | 'institution_admin_invitation_verified'

/** One read-only platform audit record. */
export interface PlatformAuditEntry {
  readonly audit_id: string
  readonly actor_user_id: string | null
  readonly actor_email: string | null
  readonly action: PlatformAuditAction
  readonly institution_id: string
  readonly institution_name: string | null
  readonly target_user_id: string | null
  readonly result: string
  readonly details: Readonly<Record<string, unknown>>
  readonly performed_at: string | null
}

/** A paginated, read-only page of the platform audit ledger. */
export interface PlatformAuditPage {
  readonly entries: readonly PlatformAuditEntry[]
  readonly total: number
  readonly limit: number
  readonly offset: number
}

/** Optional server-side filters for the audit page. */
export interface PlatformAuditFilters {
  readonly institution_id?: string
  readonly action?: PlatformAuditAction
  readonly date_from?: string
  readonly date_to?: string
  readonly limit?: number
  readonly offset?: number
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

/**
 * Create payload. Only `name` and `code` are required; branding is optional so
 * an institution can always be provisioned with the minimum viable input.
 *
 * Note there is deliberately no `status`, `institution_id`, `organization_id`,
 * or role/scope field here — the backend rejects them, and the types make them
 * unrepresentable.
 */
export interface InstitutionCreateInput {
  readonly name: string
  readonly code: string
  readonly display_name?: string
  readonly logo_url?: string
  readonly primary_color?: string
  readonly secondary_color?: string
  readonly welcome_message?: string
  readonly email?: string
  readonly address?: string
  readonly city?: string
  readonly country?: string
}

/**
 * Partial configuration update. Every field is optional and only supplied
 * fields are sent, so an omitted value is never blanked.
 */
export interface InstitutionUpdateInput {
  readonly name?: string
  readonly code?: string
  readonly display_name?: string
  readonly logo_url?: string
  readonly primary_color?: string
  readonly secondary_color?: string
  readonly welcome_message?: string
  readonly email?: string
  readonly address?: string
  readonly city?: string
  readonly country?: string
}
