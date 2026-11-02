import { useState } from 'react'
import {
  cancelStudentInvitation,
  deleteStudentProfile,
  resendStudentInvitation,
  setStudentActive,
  updateStudentInvitation,
  updateStudentProfile,
} from '../../../../services/admin/students.ts'
import { getAcademicStructure } from '../../../../services/admin/academicStructure.ts'
import { useApiQuery } from '../../../../hooks/useApiQuery.ts'
import { queryClient } from '../../../../lib/queryClient.ts'
import type {
  StudentDirectoryRow,
  StudentDirectoryUpdateInput,
  StudentInvitationUpdateResult,
} from '../../../../types/admin/students.ts'
import { studentDirectoryKeys } from './studentDirectoryQueries.ts'

export function useStudentManagementActions(accessToken: string, identity: string, canManagePlacement: boolean) {
  const [busyId, setBusyId] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const structure = useApiQuery(
    ['admin', 'student-management-structure', identity],
    () => getAcademicStructure(accessToken),
    canManagePlacement,
  )

  async function mutate<T>(
    student: StudentDirectoryRow,
    successMessage: string | ((result: T) => string),
    operation: () => Promise<T>,
  ): Promise<boolean> {
    setBusyId(student.record_id)
    setMessage('')
    setError('')
    try {
      const result = await operation()
      setMessage(typeof successMessage === 'function' ? successMessage(result) : successMessage)
      await queryClient.invalidateQueries({ queryKey: [...studentDirectoryKeys.all, identity] })
      return true
    } finally {
      setBusyId('')
    }
  }

  function edit(student: StudentDirectoryRow, input: StudentDirectoryUpdateInput) {
    if (student.record_type === 'invitation') {
      if (!('email' in input)) {
        throw new Error('Pending invitation email is required.')
      }
      return mutate(
        student,
        (result: StudentInvitationUpdateResult) =>
          result.email_changed
            ? (result.delivery_message ?? 'Invitation email updated; setup-link delivery status is unavailable.')
            : 'Invitation details updated.',
        () => updateStudentInvitation(accessToken, student.record_id, input),
      )
    }
    if ('email' in input) throw new Error('Registered student email cannot be changed here.')
    return mutate(student, 'Student details updated.', () =>
      updateStudentProfile(accessToken, student.record_id, input),
    )
  }

  function setActive(student: StudentDirectoryRow, active: boolean) {
    return mutate(student, active ? 'Student reactivated.' : 'Student deactivated.', () =>
      setStudentActive(accessToken, student.record_id, active),
    )
  }

  function remove(student: StudentDirectoryRow) {
    return mutate(student, 'Student profile deleted.', () => deleteStudentProfile(accessToken, student.record_id))
  }

  function cancelInvitation(student: StudentDirectoryRow) {
    return mutate(student, 'Student invitation cancelled.', () =>
      cancelStudentInvitation(accessToken, student.record_id),
    )
  }

  async function resend(student: StudentDirectoryRow) {
    setBusyId(student.record_id)
    setMessage('')
    setError('')
    try {
      const result = await resendStudentInvitation(accessToken, student.record_id)
      setMessage(result.delivery_message)
      await queryClient.invalidateQueries({ queryKey: [...studentDirectoryKeys.all, identity] })
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'A new setup link could not be sent.')
    } finally {
      setBusyId('')
    }
  }

  return {
    busyId,
    message,
    error,
    structure,
    edit,
    setActive,
    remove,
    cancelInvitation,
    resend,
  }
}
