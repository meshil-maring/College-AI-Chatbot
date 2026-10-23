import type { PendingStudent } from '../../types/admin.ts'
import { ADMIN_BASE, requestJson } from './http.ts'

/** Tenant and decision permissions are resolved by the server; no actor or tenant is submitted. */
export function listPendingStudents(accessToken: string, limit = 100, offset = 0): Promise<PendingStudent[]> {
  return requestJson('GET', `${ADMIN_BASE}/students/pending?limit=${limit}&offset=${offset}`, accessToken)
}
export function approvePendingStudent(accessToken: string, studentId: string): Promise<PendingStudent> {
  return requestJson('POST', `${ADMIN_BASE}/students/${encodeURIComponent(studentId)}/approve`, accessToken)
}
export function rejectPendingStudent(accessToken: string, studentId: string): Promise<PendingStudent> {
  return requestJson('POST', `${ADMIN_BASE}/students/${encodeURIComponent(studentId)}/reject`, accessToken)
}
