import { useEffect, useRef } from 'react'
import { queryOptions, useMutation, useQuery } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../../../lib/queryClient.ts'
import { assignDepartmentHead, getDepartmentHeads } from '../../../../services/students/transferApi.ts'
import { transferReviewsKey } from '../../../transfers/review/useTransferReviews.ts'

export const departmentHeadsKey = (identity: string) => ['academics', identity, 'department-heads'] as const

function departmentHeadsOptions(identity: string, institutionId: string, token: string) {
  return queryOptions({
    queryKey: departmentHeadsKey(identity),
    queryFn: async ({ signal }) => {
      const result = await getDepartmentHeads(token, signal)
      if (result.institution_id !== institutionId)
        throw new Error('Department heads are unavailable for this institution.')
      return result
    },
    ...NAVIGATION_QUERY_POLICY,
  })
}

/** Current HOD of one department, the faculty who may be appointed, and the save command. */
export function useDepartmentHead(identity: string, institutionId: string, token: string, departmentId: string) {
  const query = useQuery(departmentHeadsOptions(identity, institutionId, token), queryClient)
  const alive = useRef(true)
  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [])
  const save = useMutation(
    {
      mutationFn: async (facultyUserId: string | null) => {
        const result = await assignDepartmentHead(token, departmentId, facultyUserId)
        if (result.institution_id !== institutionId || result.department_id !== departmentId)
          throw new Error('The Head of Department change could not be verified.')
        return result
      },
      onSettled: async () => {
        if (!alive.current) return
        await queryClient.invalidateQueries({ queryKey: departmentHeadsKey(identity) })
        // The appointment changes which transfers an HOD reviews.
        await queryClient.invalidateQueries({ queryKey: transferReviewsKey(identity) })
      },
    },
    queryClient,
  )
  const head = query.data?.heads.find((item) => item.department_id === departmentId) ?? null
  return { query, save, head, faculty: query.data?.faculty ?? [] }
}
