import type { AdminIdentity, DashboardSummary } from '../../types/admin.ts'
import { ADMIN_BASE, requestJson } from './http.ts'
// ============================================================================
// Admin identity + Dashboard
// ============================================================================

export async function getAdminIdentity(accessToken: string): Promise<AdminIdentity> {
  return requestJson<AdminIdentity>('GET', `${ADMIN_BASE}/me`, accessToken)
}

/**
 * Phase 7.21 — fetch the institution-scoped operational dashboard.
 *
 * SECURITY: this client deliberately sends NO `institution_id`. The backend
 * removed that query parameter entirely and resolves the tenant from the
 * server-side authorization context, so there is nothing for a caller to
 * influence. The optional argument is not offered on purpose.
 */
export async function getDashboardSummary(accessToken: string): Promise<DashboardSummary> {
  return requestJson<DashboardSummary>('GET', `${ADMIN_BASE}/dashboard`, accessToken)
}
