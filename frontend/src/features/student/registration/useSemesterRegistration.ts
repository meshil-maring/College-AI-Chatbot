import { useContext, useEffect, useRef } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { queryClient } from '../../../lib/queryClient.ts'
import { completeMySemester } from '../../../services/academics/semesterRegistration.ts'
import { AdminApiError } from '../../../services/admin/http.ts'
import { StudentAccessContext } from '../shared/useStudentResource.ts'
import { studentRegistrationKey, studentRegistrationOptions } from './registrationQueries.ts'

export function useSemesterRegistration(identity: string, institutionId: string, token: string) {
  const query = useQuery(studentRegistrationOptions(identity, institutionId, token), queryClient)
  const alive = useRef(true)
  const locked = useRef(false)
  const reportDenial = useContext(StudentAccessContext)
  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [])
  const mutation = useMutation(
    {
      mutationFn: async ({ id, options }: { id: string; options: string[] }) => {
        const result = await completeMySemester(token, id, options)
        if (result.institution_id !== institutionId || result.semester_registration_id !== id)
          throw new Error('The saved registration could not be verified.')
        return result
      },
      onSuccess: async () => {
        if (alive.current) await queryClient.invalidateQueries({ queryKey: studentRegistrationKey(identity) })
      },
      onError: async (error) => {
        if (alive.current && error instanceof AdminApiError && error.code === 'REGISTRATION_CAPACITY')
          await queryClient.invalidateQueries({ queryKey: studentRegistrationKey(identity) })
      },
    },
    queryClient,
  )
  const error = query.error ?? mutation.error
  useEffect(() => {
    if (
      error instanceof AdminApiError &&
      ['STUDENT_NOT_APPROVED', 'STUDENT_INACTIVE', 'ACCOUNT_INACTIVE'].includes(error.code ?? '')
    )
      reportDenial?.(error.code as 'STUDENT_NOT_APPROVED' | 'STUDENT_INACTIVE' | 'ACCOUNT_INACTIVE')
  }, [error, reportDenial])
  async function complete(id: string, options: string[]) {
    if (!alive.current || locked.current || query.isFetching || query.isError) return
    locked.current = true
    try {
      await mutation.mutateAsync({ id, options })
    } catch {
      // Mutation state owns the actionable error; keep the student's choices.
    } finally {
      locked.current = false
    }
  }
  const denied = error instanceof AdminApiError && [401, 403].includes(error.status)
  return {
    query,
    data: denied ? undefined : query.data,
    error,
    complete,
    refreshing: query.isFetching || mutation.isPending,
    busy: query.isFetching || query.isError || mutation.isPending || denied,
  }
}
