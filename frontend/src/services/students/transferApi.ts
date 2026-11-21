import type {
  DepartmentHeadChange,
  DepartmentHeads,
  DirectTransferBody,
  DirectTransferOptions,
  DirectTransferResult,
  DirectTransferStudents,
  StudentTransfers,
  TransferCommandResult,
  TransferDecisionAction,
  TransferReviews,
  TransferSubmit,
} from '../../types/transfer.ts'
import { ADMIN_BASE, API_BASE_URL, STUDENT_BASE, requestJson } from '../admin/http.ts'

const OWN = `${STUDENT_BASE}/me/transfer-requests`
const REVIEWS = `${API_BASE_URL}/v1/transfer-reviews`
const DIRECT = `${API_BASE_URL}/v1/transfer-direct`

export function getMyTransfers(token: string, signal?: AbortSignal): Promise<StudentTransfers> {
  return requestJson('GET', OWN, token, undefined, signal)
}

export function submitTransfer(token: string, body: TransferSubmit): Promise<TransferCommandResult> {
  return requestJson('POST', OWN, token, body)
}

export function cancelTransfer(token: string, requestId: string): Promise<TransferCommandResult> {
  return requestJson('POST', `${OWN}/${encodeURIComponent(requestId)}/cancel`, token)
}

export function getTransferReviews(
  token: string,
  status: 'open' | 'all',
  signal?: AbortSignal,
): Promise<TransferReviews> {
  return requestJson('GET', `${REVIEWS}?status=${status}`, token, undefined, signal)
}

export function decideTransfer(
  token: string,
  requestId: string,
  action: TransferDecisionAction,
  comment: string | null,
): Promise<TransferCommandResult> {
  return requestJson('POST', `${REVIEWS}/${encodeURIComponent(requestId)}/decision`, token, { action, comment })
}

export function getDepartmentHeads(token: string, signal?: AbortSignal): Promise<DepartmentHeads> {
  return requestJson('GET', `${ADMIN_BASE}/department-heads`, token, undefined, signal)
}

export function assignDepartmentHead(
  token: string,
  departmentId: string,
  facultyUserId: string | null,
): Promise<{ department_id: string; faculty_user_id: string | null; institution_id: string }> {
  return requestJson('PUT', `${ADMIN_BASE}/department-heads/${encodeURIComponent(departmentId)}`, token, {
    faculty_user_id: facultyUserId,
  })
}

/** Appoint one more Head of Department; the department's other heads stay. */
export function addDepartmentHead(
  token: string,
  departmentId: string,
  facultyUserId: string,
): Promise<DepartmentHeadChange> {
  return requestJson('POST', `${ADMIN_BASE}/department-heads/${encodeURIComponent(departmentId)}/heads`, token, {
    faculty_user_id: facultyUserId,
  })
}

/** End one Head of Department's appointment; the department's other heads stay. */
export function endDepartmentHead(
  token: string,
  departmentId: string,
  facultyUserId: string,
): Promise<DepartmentHeadChange> {
  return requestJson(
    'DELETE',
    `${ADMIN_BASE}/department-heads/${encodeURIComponent(departmentId)}/heads/${encodeURIComponent(facultyUserId)}`,
    token,
  )
}

export function getDirectTransferStudents(token: string, signal?: AbortSignal): Promise<DirectTransferStudents> {
  return requestJson('GET', `${DIRECT}/students`, token, undefined, signal)
}

export function getDirectTransferOptions(
  token: string,
  studentId: string,
  signal?: AbortSignal,
): Promise<DirectTransferOptions> {
  return requestJson('GET', `${DIRECT}/students/${encodeURIComponent(studentId)}`, token, undefined, signal)
}

export function directTransfer(token: string, body: DirectTransferBody): Promise<DirectTransferResult> {
  return requestJson('POST', DIRECT, token, body)
}
