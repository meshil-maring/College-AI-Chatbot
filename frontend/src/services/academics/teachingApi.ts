import type {
  TeachingAssignmentCreate,
  TeachingAssignments,
  TeachingCommandResult,
  TeachingOptions,
} from '../../types/teaching.ts'
import { API_BASE_URL, requestJson } from '../admin/http.ts'

/** Shared by administrators and Heads of Department; the server decides what each may do. */
const BASE = `${API_BASE_URL}/v1/teaching-assignments`

export function getTeachingAssignments(token: string, signal?: AbortSignal): Promise<TeachingAssignments> {
  return requestJson('GET', BASE, token, undefined, signal)
}

export function getTeachingOptions(token: string, signal?: AbortSignal): Promise<TeachingOptions> {
  return requestJson('GET', `${BASE}/options`, token, undefined, signal)
}

export function requestTeachingAssignment(
  token: string,
  body: TeachingAssignmentCreate,
): Promise<TeachingCommandResult> {
  return requestJson('POST', BASE, token, body)
}

export function decideTeachingAssignment(
  token: string,
  assignmentId: string,
  action: 'approve' | 'reject',
  note: string | null,
): Promise<TeachingCommandResult> {
  return requestJson('POST', `${BASE}/${encodeURIComponent(assignmentId)}/decision`, token, { action, note })
}

export function endTeachingAssignment(token: string, assignmentId: string): Promise<TeachingCommandResult> {
  return requestJson('POST', `${BASE}/${encodeURIComponent(assignmentId)}/end`, token)
}
