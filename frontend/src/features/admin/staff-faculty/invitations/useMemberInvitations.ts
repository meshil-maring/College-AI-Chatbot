import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../../../lib/queryClient.ts'
import {
  cancelMembershipInvitation,
  createMembershipInvitation,
  listMembershipInvitations,
  resendMembershipInvitation,
} from '../../../../services/admin/adminApi.ts'
import type { MemberInvitation, MemberInvitationCreate } from '../../../../types/admin.ts'
import { staffFacultyKeys } from '../staffFacultyKeys.ts'

function message(cause: unknown, fallback: string) {
  return cause instanceof Error ? cause.message : fallback
}

/**
 * Staff and Faculty invited by the administrator: the pending list and the
 * create, resend and cancel commands. The server decides the institution,
 * expiry and token; results from an earlier session are ignored.
 */
export function useMemberInvitations(accessToken: string) {
  const query = useQuery(
    {
      queryKey: staffFacultyKeys.invitations(accessToken),
      queryFn: () => listMembershipInvitations(accessToken),
      ...NAVIGATION_QUERY_POLICY,
    },
    queryClient,
  )
  const [actionKey, setActionKey] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const identity = useRef(accessToken)
  identity.current = accessToken

  useEffect(() => {
    setActionKey(null)
    setNotice(null)
    setError(null)
  }, [accessToken])

  function refresh() {
    return queryClient.invalidateQueries({ queryKey: staffFacultyKeys.invitations(accessToken) })
  }

  /** Send a new invitation. Returns an error message for the form, or null when sent. */
  async function create(draft: MemberInvitationCreate): Promise<string | null> {
    setActionKey('create')
    setNotice(null)
    setError(null)
    try {
      const result = await createMembershipInvitation(accessToken, draft)
      if (identity.current !== accessToken) return null
      setNotice(result.message)
      await refresh()
      return null
    } catch (cause) {
      if (identity.current !== accessToken) return null
      return message(cause, 'The invitation could not be sent.')
    } finally {
      if (identity.current === accessToken) setActionKey(null)
    }
  }

  async function run(key: string, work: () => Promise<string>, failure: string) {
    setActionKey(key)
    setNotice(null)
    setError(null)
    try {
      const text = await work()
      if (identity.current !== accessToken) return
      setNotice(text)
    } catch (cause) {
      if (identity.current !== accessToken) return
      setError(message(cause, failure))
    } finally {
      if (identity.current === accessToken) {
        await refresh()
        setActionKey(null)
      }
    }
  }

  async function resend(invitation: MemberInvitation) {
    await run(
      `resend:${invitation.invitation_id}`,
      async () => {
        const result = await resendMembershipInvitation(accessToken, invitation.invitation_id)
        // A failed email is reported as the server describes it, never as sent.
        if (result?.email_delivery?.status === 'failed') return result.message
        return `A new invitation link was sent to ${invitation.email}. The previous link no longer works.`
      },
      'The invitation could not be resent.',
    )
  }

  async function cancel(invitation: MemberInvitation) {
    if (!window.confirm(`Cancel the invitation for ${invitation.full_name || invitation.email}?`)) return
    await run(
      `cancel:${invitation.invitation_id}`,
      async () => (await cancelMembershipInvitation(accessToken, invitation.invitation_id)).message,
      'The invitation could not be cancelled.',
    )
  }

  return {
    invitations: query.data?.invitations ?? [],
    loading: query.isPending,
    loadError: query.error ? message(query.error, 'Could not load invitations.') : null,
    actionKey,
    notice,
    error,
    create,
    resend,
    cancel,
  }
}

export type MemberInvitationsModel = ReturnType<typeof useMemberInvitations>
