import { useState } from 'react'
import { useApiMutation, useApiQuery } from '../../../hooks/useApiQuery.ts'
import { queryClient } from '../../../lib/queryClient.ts'
import type { SubjectAssignmentStudent } from '../../../services/students/studentRegistrationApi.ts'
import { useStudentWorkspaceApi } from '../StudentWorkspaceContext.tsx'

export function useSubjectAssignment(token: string, sectionId: string, batchId: string, canManage: boolean) {
  const api = useStudentWorkspaceApi()
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')
  const [draftSearch, setDraftSearch] = useState('')
  const [notice, setNotice] = useState('')
  const query = useApiQuery([api.namespace, 'subject-assignments', token, sectionId, batchId, search, page], () =>
    api.getSubjectAssignmentStudents(token, sectionId, page * 25, { batchId, search }),
  )
  const mutation = useApiMutation({
    mutationFn: (student: SubjectAssignmentStudent) =>
      api.assignStudentSubject(token, sectionId, student.registration_id),
    onSuccess: async (result, student) => {
      setNotice(
        `${student.student_name} ${result.status === 'already_assigned' ? 'is already assigned' : 'was assigned'} to this subject.`,
      )
      if (page > 0 && query.data?.items.length === 1) setPage(page - 1)
      await queryClient.invalidateQueries({
        predicate: (item) => item.queryKey[0] === api.namespace && item.queryKey.includes(token),
      })
    },
  })

  function assign(student: SubjectAssignmentStudent) {
    if (!canManage || mutation.isPending || query.isFetching || query.isError || student.assignment_errors.length)
      return
    setNotice('')
    mutation.mutate(student)
  }

  function searchStudents() {
    if (mutation.isPending) return
    setPage(0)
    setSearch(draftSearch.trim())
    setNotice('')
    mutation.reset()
  }

  return { query, mutation, page, setPage, draftSearch, setDraftSearch, notice, search, searchStudents, assign }
}
