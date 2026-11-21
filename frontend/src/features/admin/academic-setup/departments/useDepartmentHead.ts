import { useEffect, useRef } from 'react'
import { queryOptions, useMutation, useQuery } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../../../lib/queryClient.ts'
import { addDepartmentHead, endDepartmentHead, getDepartmentHeads } from '../../../../services/students/transferApi.ts'
import type { DepartmentHeadChange } from '../../../../types/transfer.ts'
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

/**
 * Current Heads of Department of one department (there may be several, all
 * equal), the faculty who may be appointed, and add/end commands that change
 * one appointment at a time.
 */
export function useDepartmentHead(identity: string, institutionId: string, token: string, departmentId: string) {
  const query = useQuery(departmentHeadsOptions(identity, institutionId, token), queryClient)
  const alive = useRef(true)
  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [])

  function verified(result: DepartmentHeadChange) {
    if (result.institution_id !== institutionId || result.department_id !== departmentId)
      throw new Error('The Head of Department change could not be verified.')
    return result
  }

  async function refresh() {
    if (!alive.current) return
    await queryClient.invalidateQueries({ queryKey: departmentHeadsKey(identity) })
    // Staff and Faculty Management shows the same appointments on its roster.
    await queryClient.invalidateQueries({
      predicate: (item) => item.queryKey[1] === 'staff-faculty' && item.queryKey[3] === 'department-heads',
    })
    // The appointment changes which transfers an HOD reviews.
    await queryClient.invalidateQueries({ queryKey: transferReviewsKey(identity) })
  }

  const add = useMutation(
    {
      mutationFn: async (facultyUserId: string) =>
        verified(await addDepartmentHead(token, departmentId, facultyUserId)),
      onSettled: refresh,
    },
    queryClient,
  )
  const end = useMutation(
    {
      mutationFn: async (facultyUserId: string) =>
        verified(await endDepartmentHead(token, departmentId, facultyUserId)),
      onSettled: refresh,
    },
    queryClient,
  )
  const heads = query.data?.heads.filter((item) => item.department_id === departmentId) ?? []
  return { query, add, end, heads, faculty: query.data?.faculty ?? [] }
}
