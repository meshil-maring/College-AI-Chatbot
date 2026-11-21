import { useEffect, useRef } from 'react'
import { queryOptions, useMutation, useQuery } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../../lib/queryClient.ts'
import { getMyNotifications, markNotificationRead } from '../../../services/students/notificationsApi.ts'

export const studentNotificationsKey = (identity: string) => ['students', identity, 'notifications'] as const

export function studentNotificationsOptions(identity: string, institutionId: string, token: string) {
  return queryOptions({
    ...NAVIGATION_QUERY_POLICY,
    queryKey: studentNotificationsKey(identity),
    queryFn: async ({ signal }) => {
      const result = await getMyNotifications(token, 1, signal)
      if (result.items.some((item) => item.institution_id !== institutionId))
        throw new Error('Notifications are unavailable for this institution.')
      return result
    },
  })
}

/** The student's own notifications and a command to mark one or many as read. */
export function useStudentNotifications(identity: string, institutionId: string, token: string) {
  const query = useQuery(studentNotificationsOptions(identity, institutionId, token), queryClient)
  const alive = useRef(true)
  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [])
  const markRead = useMutation(
    {
      mutationFn: async (ids: string[]) => {
        for (const id of ids) await markNotificationRead(token, id)
      },
      onSettled: async () => {
        if (alive.current) await queryClient.invalidateQueries({ queryKey: studentNotificationsKey(identity) })
      },
    },
    queryClient,
  )
  return { query, markRead }
}
