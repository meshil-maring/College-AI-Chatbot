import { useEffect, useState } from 'react'
import { useApiQuery } from '../../hooks/useApiQuery.ts'
import { getFacultyContext } from '../../services/adminApi.ts'
import type { FacultyContext } from '../../types/faculty.ts'

export function useFacultyContext(token: string | null, initial?: FacultyContext) {
  const query = useApiQuery(['faculty', 'context', token], () => getFacultyContext(token!), token !== null && initial !== undefined)
  const [, tick] = useState(0)
  const context = query.isError ? undefined : query.data ?? initial
  const refetch = query.refetch
  useEffect(() => {
    if (!token || !initial) return
    const interval = window.setInterval(() => { tick((value) => value + 1); void refetch() }, 30_000)
    const boundaries = [...(context?.responsibilities ?? []), ...(context?.teaching_assignments ?? [])]
      .flatMap((row) => [row.start_at, row.end_at]).filter((date): date is string => date !== null)
      .map(Date.parse).filter((date) => date > Date.now())
    const delay = boundaries.length ? Math.min(Math.min(...boundaries) - Date.now() + 1, 2_147_483_647) : null
    const timer = delay === null ? null : window.setTimeout(() => { tick((value) => value + 1); void refetch() }, Math.max(delay, 1))
    const focus = () => { tick((value) => value + 1); void refetch() }
    window.addEventListener('focus', focus)
    return () => { window.clearInterval(interval); if (timer !== null) window.clearTimeout(timer); window.removeEventListener('focus', focus) }
  }, [token, initial, context, refetch])
  return { context, error: query.isError ? 'Your responsibilities could not be refreshed. Refresh to retry.' : null }
}
