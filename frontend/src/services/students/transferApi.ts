import type {
  DepartmentHeads,
  StudentTransfers,
  TransferCommandResult,
  TransferDecisionAction,
  TransferReviews,
  TransferSubmit,
} from '../../types/transfer.ts'
import { ADMIN_BASE, API_BASE_URL, STUDENT_BASE, requestJson } from '../admin/http.ts'

const OWN = `${STUDENT_BASE}/me/transfer-requests`
const REVIEWS = `${API_BASE_URL}/v1/transfer-reviews`

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
