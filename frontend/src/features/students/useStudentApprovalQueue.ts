import { useRef, useState } from 'react'
import { useApiMutation, useApiQuery } from '../../hooks/useApiQuery.ts'
import {
  AdminApiError,
  approvePendingStudent,
  listPendingStudents,
  rejectPendingStudent,
} from '../../services/admin/adminApi.ts'
import type { PendingStudent } from '../../types/admin.ts'
import { queryClient } from '../../lib/queryClient.ts'

export interface ApprovalQueueOptions {
  accessToken: string
  namespace: 'admin' | 'staff'
  canApprove?: boolean
  canReject?: boolean
}
export function approvalErrorMessage(error: unknown) {
  return error instanceof AdminApiError && error.message
    ? error.message
    : 'The decision could not be saved. Please try again.'
}
export const PAGE_SIZE = 25
export function useStudentApprovalQueue({
  accessToken,
  namespace,
  canApprove = true,
  canReject = true,
}: ApprovalQueueOptions) {
  const [busyStudentId, setBusyStudentId] = useState<string | null>(null)
  const deciding = useRef(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())
  const [search, setSearch] = useState('')
  const [draftSearch, setDraftSearch] = useState('')
  const [page, setPage] = useState(0)
  const queue = useApiQuery([namespace, 'pending-students', accessToken], () => listPendingStudents(accessToken))
  const decision = useApiMutation<PendingStudent, { studentId: string; action: 'approve' | 'reject' }>({
    mutationFn: ({ studentId, action }) =>
      action === 'approve'
        ? approvePendingStudent(accessToken, studentId)
        : rejectPendingStudent(accessToken, studentId),
  })
  const students = queue.isError ? [] : (queue.data ?? []).filter((student) => !dismissed.has(student.student_id))
  const term = search.trim().toLowerCase()
  const filtered = students.filter((student) =>
    [student.student_number, student.register_number, student.university_roll_number, student.email].some((value) =>
      value?.toLowerCase().includes(term),
    ),
  )
  const currentPage = Math.min(page, Math.max(0, Math.ceil(filtered.length / PAGE_SIZE) - 1))
  const visible = filtered.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE)

  function refresh() {
    setActionError(null)
    setActionSuccess(null)
    void queue.refetch()
  }

  async function decide(student: PendingStudent, action: 'approve' | 'reject') {
    if (deciding.current || (action === 'approve' ? !canApprove : !canReject)) return
    deciding.current = true
    setBusyStudentId(student.student_id)
    setActionError(null)
    setActionSuccess(null)
    try {
      await decision.mutateAsync({ studentId: student.student_id, action })
      setActionSuccess(
        action === 'approve'
          ? `Student ${student.student_number} approved. They can sign in after completing any required email verification.`
          : `Student ${student.student_number} rejected. Their account cannot sign in.`,
      )
      setDismissed((current) => new Set(current).add(student.student_id))
      void queryClient.invalidateQueries({ queryKey: ['admin', 'students', accessToken] })
      await queue.refetch()
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 409 && error.code === 'STUDENT_NOT_PENDING') {
        await queue.refetch()
        setDismissed(new Set())
        setActionError('This student was already processed. The queue has been refreshed.')
      } else setActionError(approvalErrorMessage(error))
    } finally {
      deciding.current = false
      setBusyStudentId(null)
    }
  }

  return {
    busyStudentId,
    actionError,
    actionSuccess,
    search,
    setSearch,
    draftSearch,
    setDraftSearch,
    setPage,
    queue,
    students,
    filtered,
    currentPage,
    visible,
    refresh,
    decide,
    canApprove,
    canReject,
  }
}
export type ApprovalQueueModel = ReturnType<typeof useStudentApprovalQueue>
