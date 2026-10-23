import type { AdminIdentity } from '../../types/admin.ts'
import { ADMIN_BASE, requestJson } from './http.ts'

export function getAdminIdentity(accessToken: string): Promise<AdminIdentity> {
  return requestJson('GET', `${ADMIN_BASE}/me`, accessToken)
}
