import { useEffect, useRef } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../../lib/queryClient.ts'
import {
  directTransfer,
  getDirectTransferOptions,
  getDirectTransferStudents,
} from '../../../services/students/transferApi.ts'
import type { DirectTransferBody } from '../../../types/transfer.ts'
import { transferReviewsKey } from '../review/useTransferReviews.ts'
import { invalidateStudentDirectory } from '../../admin/students/directory/studentDirectoryQueries.ts'

export const directTransferKey = (identity: string) => ['academics', identity, 'direct-transfer'] as const

function assertTenant<T extends { institution_id: string }>(result: T, institutionId: string, message: string) {
  if (result.institution_id !== institutionId) throw new Error(message)
  return result
}

/** Students the admin/HOD may move, the selected student's options and the transfer command. */
export function useDirectTransfer(identity: string, institutionId: string, token: string, studentId: string | null) {
  const students = useQuery(
    {
      ...NAVIGATION_QUERY_POLICY,
      queryKey: [...directTransferKey(identity), 'students'] as const,
      queryFn: async ({ signal }) =>
        assertTenant(
          await getDirectTransferStudents(token, signal),
          institutionId,
          'Students are unavailable for this institution.',
        ),
    },
    queryClient,
  )
  const options = useQuery(
    {
      queryKey: [...directTransferKey(identity), 'options', studentId ?? ''] as const,
      enabled: studentId !== null,
      queryFn: async ({ signal }) => {
        const result = assertTenant(
          await getDirectTransferOptions(token, studentId ?? '', signal),
          institutionId,
          'Transfer options are unavailable for this institution.',
        )
        if (result.student_id !== studentId) throw new Error('Transfer options did not match the selected student.')
        return result
      },
    },
    queryClient,
  )
  const alive = useRef(true)
  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [])
  const transfer = useMutation(
    {
      mutationFn: async (body: DirectTransferBody) => {
        const result = await directTransfer(token, body)
        if (result.institution_id !== institutionId || result.student_id !== body.student_id)
          throw new Error('The transfer could not be verified.')
        return result
      },
      onSettled: async () => {
        if (!alive.current) return
        await queryClient.invalidateQueries({ queryKey: directTransferKey(identity) })
        await queryClient.invalidateQueries({ queryKey: transferReviewsKey(identity) })
        // A transfer changes the student's placement shown in All Students.
        await invalidateStudentDirectory()
      },
    },
    queryClient,
  )
  return { students, options, transfer }
}
