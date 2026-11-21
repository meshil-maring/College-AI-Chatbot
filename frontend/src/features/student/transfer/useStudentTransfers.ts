import { useEffect, useRef } from 'react'
import { queryOptions, useMutation, useQuery } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../../lib/queryClient.ts'
import { cancelTransfer, getMyTransfers, submitTransfer } from '../../../services/students/transferApi.ts'
import { AdminApiError } from '../../../services/admin/http.ts'
import type { TransferCommandResult, TransferSubmit } from '../../../types/transfer.ts'

export const studentTransfersKey = (identity: string) => ['academics', identity, 'own-transfers'] as const

export function studentTransfersOptions(identity: string, institutionId: string, token: string) {
  return queryOptions({
    ...NAVIGATION_QUERY_POLICY,
    queryKey: studentTransfersKey(identity),
    queryFn: async ({ signal }) => {
      const result = await getMyTransfers(token, signal)
      if (result.institution_id !== institutionId) throw new Error('Transfer data is unavailable for this institution.')
      return result
    },
  })
}

function verified(result: TransferCommandResult, institutionId: string) {
  if (result.institution_id !== institutionId) throw new Error('The saved transfer request could not be verified.')
  return result
}

/** Placement, options and own requests, plus submit/cancel that refresh them. */
export function useStudentTransfers(identity: string, institutionId: string, token: string) {
  const query = useQuery(studentTransfersOptions(identity, institutionId, token), queryClient)
  const alive = useRef(true)
  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [])
  const refresh = async () => {
    if (alive.current) await queryClient.invalidateQueries({ queryKey: studentTransfersKey(identity) })
  }
  // Conflicts mean the server state moved on (seat taken, request closed), so reload it.
  const refreshOnConflict = async (error: Error) => {
    if (error instanceof AdminApiError && error.status === 409) await refresh()
  }
  const submit = useMutation(
    {
      mutationFn: async (body: TransferSubmit) => verified(await submitTransfer(token, body), institutionId),
      onSuccess: refresh,
      onError: refreshOnConflict,
    },
    queryClient,
  )
  const cancel = useMutation(
    {
      mutationFn: async (requestId: string) => verified(await cancelTransfer(token, requestId), institutionId),
      onSuccess: refresh,
      onError: refreshOnConflict,
    },
    queryClient,
  )
  return { query, submit, cancel }
}
