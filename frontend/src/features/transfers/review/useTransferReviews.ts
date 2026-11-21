import { useEffect, useRef } from 'react'
import { queryOptions, useMutation, useQuery } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../../lib/queryClient.ts'
import { decideTransfer, getTransferReviews } from '../../../services/students/transferApi.ts'
import { AdminApiError } from '../../../services/admin/http.ts'
import type { TransferDecisionAction } from '../../../types/transfer.ts'
import { invalidateStudentDirectory } from '../../admin/students/directory/studentDirectoryQueries.ts'

export type ReviewFilter = 'open' | 'all'

export const transferReviewsKey = (identity: string) => ['academics', identity, 'transfer-reviews'] as const

export function transferReviewsOptions(identity: string, institutionId: string, token: string, filter: ReviewFilter) {
  return queryOptions({
    ...NAVIGATION_QUERY_POLICY,
    queryKey: [...transferReviewsKey(identity), filter] as const,
    queryFn: async ({ signal }) => {
      const result = await getTransferReviews(token, filter, signal)
      if (result.institution_id !== institutionId)
        throw new Error('Transfer reviews are unavailable for this institution.')
      return result
    },
  })
}

/** Whether the signed-in admin or faculty member may review any transfer. */
export function useTransferReviewAccess(identity: string, institutionId: string | null, token: string | null) {
  const query = useQuery(
    {
      ...transferReviewsOptions(identity, institutionId ?? '', token ?? '', 'open'),
      enabled: Boolean(institutionId && token),
      select: (data) => data.can_review,
    },
    queryClient,
  )
  return query.data === true
}

export interface DecisionInput {
  requestId: string
  action: TransferDecisionAction
  comment: string | null
}

export function useTransferReviews(identity: string, institutionId: string, token: string, filter: ReviewFilter) {
  const query = useQuery(transferReviewsOptions(identity, institutionId, token, filter), queryClient)
  const alive = useRef(true)
  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [])
  const refresh = async () => {
    if (!alive.current) return
    await queryClient.invalidateQueries({ queryKey: transferReviewsKey(identity) })
    // An approved transfer changes the student's placement shown in All Students.
    await invalidateStudentDirectory()
  }
  const decide = useMutation(
    {
      mutationFn: async ({ requestId, action, comment }: DecisionInput) => {
        const result = await decideTransfer(token, requestId, action, comment)
        if (result.institution_id !== institutionId || result.transfer_request_id !== requestId)
          throw new Error('The transfer decision could not be verified.')
        return result
      },
      onSuccess: refresh,
      onError: async (error) => {
        if (error instanceof AdminApiError && error.status === 409) await refresh()
      },
    },
    queryClient,
  )
  return { query, decide }
}
