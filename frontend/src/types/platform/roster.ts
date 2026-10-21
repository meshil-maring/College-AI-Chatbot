import { type EmailDeliveryStatus } from './invitations.ts'

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
