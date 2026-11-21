import type { StudentNotification, StudentNotificationList } from '../../types/student.ts'
import { STUDENT_BASE, requestJson } from '../admin/http.ts'

const BASE = `${STUDENT_BASE}/me/notifications`

export function getMyNotifications(token: string, page = 1, signal?: AbortSignal): Promise<StudentNotificationList> {
  return requestJson('GET', `${BASE}?page=${page}&page_size=50`, token, undefined, signal)
}

export function markNotificationRead(token: string, notificationId: string): Promise<StudentNotification> {
  return requestJson('PATCH', `${BASE}/${encodeURIComponent(notificationId)}/read`, token)
}
