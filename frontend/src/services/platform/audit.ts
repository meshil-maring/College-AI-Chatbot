import type { AdminRevocationResult, PlatformAuditFilters, PlatformAuditPage } from '../../types/platform.ts'
import { API_BASE_URL, PLATFORM_BASE, requestJson } from './http.ts'

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
