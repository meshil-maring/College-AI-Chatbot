/**
 * Phase 7.13 — Super Admin platform institution-management types.
 *
 * These mirror the backend's explicit response schemas
 * (`backend/app/schemas/platform/platform.py`). The frontend never models an
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
