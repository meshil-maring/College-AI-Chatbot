import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../lib/queryClient.ts'
import {
  decideTeachingAssignment,
  endTeachingAssignment,
  getTeachingAssignments,
  getTeachingOptions,
  requestTeachingAssignment,
} from '../../services/academics/teachingApi.ts'
import type { TeachingAssignment, TeachingAssignmentCreate } from '../../types/teaching.ts'
import { assignmentLabel } from './teachingLabels.ts'
import { notification } from '../../lib/notifications/notification.ts'

export const teachingKeys = {
  all: (token: string) => ['teaching', token] as const,
  list: (token: string) => ['teaching', token, 'assignments'] as const,
  options: (token: string) => ['teaching', token, 'options'] as const,
}

function message(cause: unknown, fallback: string) {
  return cause instanceof Error ? cause.message : fallback
}

/**
 * Teaching assignments the viewer may see, the offerings and Faculty to choose
 * from, and the assign / decide / end commands. Results from an earlier
 * session are ignored.
 */
export function useTeaching(accessToken: string) {
  const list = useQuery(
    {
      queryKey: teachingKeys.list(accessToken),
      queryFn: ({ signal }) => getTeachingAssignments(accessToken, signal),
      ...NAVIGATION_QUERY_POLICY,
    },
    queryClient,
  )
  const options = useQuery(
    {
      queryKey: teachingKeys.options(accessToken),
      queryFn: ({ signal }) => getTeachingOptions(accessToken, signal),
      ...NAVIGATION_QUERY_POLICY,
    },
    queryClient,
  )
  const [actionKey, setActionKey] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const identity = useRef(accessToken)
  identity.current = accessToken

  useEffect(() => {
    setActionKey(null)
    setError(null)
  }, [accessToken])

  /** Runs one command; returns an error message, or null when it succeeded. */
  async function run(key: string, work: () => Promise<string>, failure: string): Promise<string | null> {
    setActionKey(key)
    setError(null)
    try {
      const text = await work()
      if (identity.current === accessToken) notification.success(text)
      return null
    } catch (cause) {
      if (identity.current !== accessToken) return null
      const reason = message(cause, failure)
      setError(reason)
      return reason
    } finally {
      if (identity.current === accessToken) {
        await queryClient.invalidateQueries({ queryKey: teachingKeys.list(accessToken) })
        setActionKey(null)
      }
    }
  }

  const assign = (body: TeachingAssignmentCreate) =>
    run(
      'assign',
      async () => {
        const result = await requestTeachingAssignment(accessToken, body)
        if (result.already_applied) return 'This teacher already has this subject.'
        return result.status === 'pending'
          ? 'Request sent. It waits for the Head of the subject’s department to approve it.'
          : 'Teaching assigned.'
      },
      'Could not assign the teaching.',
    )

  const decide = (item: TeachingAssignment, approve: boolean, note: string | null) =>
    run(
      `decide:${item.assignment_id}`,
      async () => {
        await decideTeachingAssignment(accessToken, item.assignment_id, approve ? 'approve' : 'reject', note)
        return `${approve ? 'Approved' : 'Rejected'}: ${item.faculty_name} for ${assignmentLabel(item)}.`
      },
      'Could not record the decision.',
    )

  const end = (item: TeachingAssignment) => {
    const pending = item.status === 'pending'
    const question = pending
      ? `Withdraw the request for ${item.faculty_name} to teach ${assignmentLabel(item)}?`
      : `End ${item.faculty_name}'s teaching of ${assignmentLabel(item)}? The record is kept.`
    if (!window.confirm(question)) return Promise.resolve(null)
    return run(
      `end:${item.assignment_id}`,
      async () => {
        await endTeachingAssignment(accessToken, item.assignment_id)
        return pending ? 'Request withdrawn.' : 'Teaching ended.'
      },
      'Could not end the teaching.',
    )
  }

  return {
    data: list.data ?? null,
    assignments: list.data?.assignments ?? [],
    offerings: options.data?.offerings ?? [],
    faculty: options.data?.faculty ?? [],
    loading: list.isPending,
    loadError: list.error ? message(list.error, 'Could not load teaching assignments.') : null,
    optionsError: options.error ? message(options.error, 'Could not load subjects and faculty.') : null,
    actionKey,
    error,
    dismiss: () => setError(null),
    assign,
    decide,
    end,
  }
}

export type TeachingModel = ReturnType<typeof useTeaching>
